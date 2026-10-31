"""Function and basic-block level diffing with semantic vs. cosmetic classification."""

from __future__ import annotations

import difflib
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

import numpy as np
from scipy.optimize import linear_sum_assignment

from core.detectors import SecurityTag, run_all_detectors
from core.fingerprint import (
    FunctionFingerprint,
    compute_normalized_hash,
    extract_fingerprints,
    mnemonic_cosine_similarity,
)
from core.loader import LoadedELF
from core.match import MatchResult
from core.models import BasicBlock, Binary, Function
from core.normalize import InstructionNormalizer, RoleRegisterStrategy


class ChangeClassification(StrEnum):
    """Function-level change classification."""

    IDENTICAL = "identical"
    CHANGED_COSMETIC = "changed-cosmetic"
    CHANGED_SEMANTIC = "changed-semantic"
    ADDED = "added"
    REMOVED = "removed"


class BlockChangeType(StrEnum):
    """Basic-block change classification."""

    UNCHANGED = "unchanged"
    MODIFIED = "modified"
    ADDED = "added"
    REMOVED = "removed"


@dataclass(frozen=True, slots=True)
class BlockDiff:
    """Diff result for an individual basic block pair."""

    block_a: BasicBlock | None
    block_b: BasicBlock | None
    change_type: BlockChangeType
    unified_diff: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "addr_a": self.block_a.start_addr if self.block_a else None,
            "addr_b": self.block_b.start_addr if self.block_b else None,
            "change_type": self.change_type.value,
            "unified_diff": list(self.unified_diff),
        }


@dataclass(frozen=True, slots=True)
class FunctionDiff:
    """Detailed diff result for a matched function pair."""

    func_a: Function | None
    func_b: Function | None
    similarity: float
    classification: ChangeClassification
    block_diffs: tuple[BlockDiff, ...]
    security_tags: tuple[SecurityTag, ...]
    patch_score: float = 0.0
    rank: int = 0

    @property
    def name_a(self) -> str:
        return self.func_a.name if self.func_a else "<NONE>"

    @property
    def name_b(self) -> str:
        return self.func_b.name if self.func_b else "<NONE>"

    @property
    def addr_a(self) -> int | None:
        return self.func_a.addr if self.func_a else None

    @property
    def addr_b(self) -> int | None:
        return self.func_b.addr if self.func_b else None

    @property
    def has_security_tags(self) -> bool:
        return len(self.security_tags) > 0

    def to_dict(self) -> dict[str, object]:
        return {
            "name_a": self.name_a,
            "name_b": self.name_b,
            "addr_a": self.addr_a,
            "addr_b": self.addr_b,
            "similarity": round(self.similarity, 4),
            "classification": self.classification.value,
            "patch_score": round(self.patch_score, 4),
            "rank": self.rank,
            "security_tags": [t.to_dict() for t in self.security_tags],
            "block_diffs": [bd.to_dict() for bd in self.block_diffs],
        }


class FunctionDiffer:
    """Performs deep intra-function basic-block matching and unified diff generation."""

    def __init__(self, normalizer: InstructionNormalizer | None = None) -> None:
        self.normalizer = normalizer or InstructionNormalizer(
            register_strategy=RoleRegisterStrategy()
        )

    def _block_lines(self, block: BasicBlock) -> list[str]:
        """Convert basic block instructions to normalized disassembly lines."""
        lines: list[str] = []
        for insn in block.instructions:
            norm = self.normalizer.normalize_instruction(insn)
            if norm is not None:
                lines.append(f"{norm.mnemonic} {norm.op_str}".strip())
        return lines

    def diff_basic_blocks(
        self,
        func_a: Function,
        func_b: Function,
    ) -> tuple[tuple[BlockDiff, ...], list[tuple[BasicBlock | None, BasicBlock | None]]]:
        """Match basic blocks between func_a and func_b and generate instruction-level diffs."""
        blocks_a = {b.start_addr: b for b in func_a.blocks}
        blocks_b = {b.start_addr: b for b in func_b.blocks}

        lines_map_a = {addr: self._block_lines(b) for addr, b in blocks_a.items()}
        lines_map_b = {addr: self._block_lines(b) for addr, b in blocks_b.items()}

        hash_map_a = {addr: compute_normalized_hash(lines) for addr, lines in lines_map_a.items()}
        hash_map_b = {addr: compute_normalized_hash(lines) for addr, lines in lines_map_b.items()}

        unmatched_a = set(blocks_a.keys())
        unmatched_b = set(blocks_b.keys())
        matched_pairs: list[tuple[int, int, BlockChangeType, tuple[str, ...]]] = []

        # 1. Exact normalized block instruction hash match
        hash_to_b: dict[str, list[int]] = {}
        for b_addr, h in hash_map_b.items():
            hash_to_b.setdefault(h, []).append(b_addr)

        for a_addr in sorted(unmatched_a):
            h = hash_map_a[a_addr]
            cands = [b for b in hash_to_b.get(h, []) if b in unmatched_b]
            if len(cands) == 1:
                b_addr = cands[0]
                matched_pairs.append((a_addr, b_addr, BlockChangeType.UNCHANGED, ()))
                unmatched_a.remove(a_addr)
                unmatched_b.remove(b_addr)

        # 2. Hungarian assignment on remaining blocks using token edit distance
        if unmatched_a and unmatched_b:
            sorted_u_a = sorted(unmatched_a)
            sorted_u_b = sorted(unmatched_b)
            n_rows = len(sorted_u_a)
            n_cols = len(sorted_u_b)

            sim_matrix = np.zeros((n_rows, n_cols), dtype=np.float64)
            for i, a_addr in enumerate(sorted_u_a):
                la = lines_map_a[a_addr]
                for j, b_addr in enumerate(sorted_u_b):
                    lb = lines_map_b[b_addr]
                    sm = difflib.SequenceMatcher(None, la, lb)
                    sim_matrix[i, j] = sm.ratio()

            row_ind, col_ind = linear_sum_assignment(1.0 - sim_matrix)
            for i, j in zip(row_ind, col_ind, strict=False):
                sim = float(sim_matrix[i, j])
                a_addr = sorted_u_a[i]
                b_addr = sorted_u_b[j]
                if sim >= 0.25:
                    la = lines_map_a[a_addr]
                    lb = lines_map_b[b_addr]
                    udiff = tuple(
                        difflib.unified_diff(
                            la,
                            lb,
                            fromfile=f"bb_0x{a_addr:x}",
                            tofile=f"bb_0x{b_addr:x}",
                            lineterm="",
                        )
                    )
                    ctype = (
                        BlockChangeType.UNCHANGED
                        if (sim == 1.0 and la == lb)
                        else BlockChangeType.MODIFIED
                    )
                    matched_pairs.append((a_addr, b_addr, ctype, udiff))
                    unmatched_a.remove(a_addr)
                    unmatched_b.remove(b_addr)

        block_diffs: list[BlockDiff] = []
        raw_matches: list[tuple[BasicBlock | None, BasicBlock | None]] = []

        for a_addr, b_addr, ctype, udiff in matched_pairs:
            ba = blocks_a[a_addr]
            bb = blocks_b[b_addr]
            block_diffs.append(
                BlockDiff(
                    block_a=ba,
                    block_b=bb,
                    change_type=ctype,
                    unified_diff=udiff,
                )
            )
            raw_matches.append((ba, bb))

        for a_addr in sorted(unmatched_a):
            ba = blocks_a[a_addr]
            udiff = tuple(
                difflib.unified_diff(
                    lines_map_a[a_addr],
                    [],
                    fromfile=f"bb_0x{a_addr:x}",
                    tofile="/dev/null",
                    lineterm="",
                )
            )
            block_diffs.append(
                BlockDiff(
                    block_a=ba,
                    block_b=None,
                    change_type=BlockChangeType.REMOVED,
                    unified_diff=udiff,
                )
            )
            raw_matches.append((ba, None))

        for b_addr in sorted(unmatched_b):
            bb = blocks_b[b_addr]
            udiff = tuple(
                difflib.unified_diff(
                    [],
                    lines_map_b[b_addr],
                    fromfile="/dev/null",
                    tofile=f"bb_0x{b_addr:x}",
                    lineterm="",
                )
            )
            block_diffs.append(
                BlockDiff(
                    block_a=None,
                    block_b=bb,
                    change_type=BlockChangeType.ADDED,
                    unified_diff=udiff,
                )
            )
            raw_matches.append((None, bb))

        return tuple(block_diffs), raw_matches

    def classify_change(
        self,
        func_a: Function,
        func_b: Function,
        fp_a: FunctionFingerprint,
        fp_b: FunctionFingerprint,
        similarity: float,
        block_diffs: Sequence[BlockDiff],
        security_tags: Sequence[SecurityTag],
    ) -> ChangeClassification:
        """Classify function pair as identical, changed-cosmetic, or changed-semantic."""
        # 1. Exact identity
        if fp_a.norm_hash == fp_b.norm_hash and similarity >= 0.999:
            return ChangeClassification.IDENTICAL

        # 2. Check for security tags
        if security_tags:
            return ChangeClassification.CHANGED_SEMANTIC

        # 3. Check for added or removed blocks
        has_added_or_removed = any(
            bd.change_type in (BlockChangeType.ADDED, BlockChangeType.REMOVED) for bd in block_diffs
        )
        if has_added_or_removed:
            return ChangeClassification.CHANGED_SEMANTIC

        # 4. Check for altered control-flow topology
        if (
            fp_a.block_count != fp_b.block_count
            or fp_a.edge_count != fp_b.edge_count
            or fp_a.cyclomatic_complexity != fp_b.cyclomatic_complexity
            or fp_a.wl_cfg_hash != fp_b.wl_cfg_hash
        ):
            return ChangeClassification.CHANGED_SEMANTIC

        # 5. Check if semantic mnemonics, callees, or constants differ
        mnem_sim = mnemonic_cosine_similarity(fp_a.mnemonic_hist, fp_b.mnemonic_hist)
        if mnem_sim < 0.96 or fp_a.callees != fp_b.callees or fp_a.constants != fp_b.constants:
            return ChangeClassification.CHANGED_SEMANTIC

        # If CFG is isomorphic, no security checks added, and operations match: cosmetic!
        return ChangeClassification.CHANGED_COSMETIC


def diff_matched_functions(
    match_result: MatchResult,
    binary_a: Binary,
    binary_b: Binary,
    loaded_a: LoadedELF | None = None,
    loaded_b: LoadedELF | None = None,
) -> tuple[FunctionDiff, ...]:
    """Perform function and block-level diffing across all matches and unmatched functions."""
    differ = FunctionDiffer()
    normalizer = differ.normalizer

    funcs_a = {f.addr: f for f in binary_a.functions}
    funcs_b = {f.addr: f for f in binary_b.functions}

    import_map_a = {imp.plt_addr: imp.name for imp in binary_a.imports if imp.plt_addr != 0}
    import_map_b = {imp.plt_addr: imp.name for imp in binary_b.imports if imp.plt_addr != 0}

    results: list[FunctionDiff] = []

    # Diff matched function pairs
    for match in match_result.matches:
        fa = funcs_a.get(match.addr_a)
        fb = funcs_b.get(match.addr_b)
        if fa is None or fb is None:
            continue

        nfa = normalizer.normalize_function(fa, import_map=import_map_a)
        nfb = normalizer.normalize_function(fb, import_map=import_map_b)

        fpa = extract_fingerprints(fa, nfa, loaded=loaded_a, import_map=import_map_a)
        fpb = extract_fingerprints(fb, nfb, loaded=loaded_b, import_map=import_map_b)

        block_diffs, raw_matches = differ.diff_basic_blocks(fa, fb)
        sec_tags = run_all_detectors(fa, fb, raw_matches, fpa.callees, fpb.callees)

        classification = differ.classify_change(
            fa,
            fb,
            fpa,
            fpb,
            match.similarity,
            block_diffs,
            sec_tags,
        )

        results.append(
            FunctionDiff(
                func_a=fa,
                func_b=fb,
                similarity=match.similarity,
                classification=classification,
                block_diffs=block_diffs,
                security_tags=sec_tags,
            )
        )

    # Record unmatched functions in binary A as REMOVED
    for addr_a in match_result.unmatched_a:
        fa = funcs_a.get(addr_a)
        if fa is not None:
            b_diffs = tuple(
                BlockDiff(
                    block_a=b,
                    block_b=None,
                    change_type=BlockChangeType.REMOVED,
                    unified_diff=(),
                )
                for b in fa.blocks
            )
            results.append(
                FunctionDiff(
                    func_a=fa,
                    func_b=None,
                    similarity=0.0,
                    classification=ChangeClassification.REMOVED,
                    block_diffs=b_diffs,
                    security_tags=(),
                )
            )

    # Record unmatched functions in binary B as ADDED
    for addr_b in match_result.unmatched_b:
        fb = funcs_b.get(addr_b)
        if fb is not None:
            b_diffs = tuple(
                BlockDiff(
                    block_a=None,
                    block_b=b,
                    change_type=BlockChangeType.ADDED,
                    unified_diff=(),
                )
                for b in fb.blocks
            )
            results.append(
                FunctionDiff(
                    func_a=None,
                    func_b=fb,
                    similarity=0.0,
                    classification=ChangeClassification.ADDED,
                    block_diffs=b_diffs,
                    security_tags=(),
                )
            )

    return tuple(results)
