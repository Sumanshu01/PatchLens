"""Structural and semantic function fingerprinting for binary diffing."""

from __future__ import annotations

import hashlib
import math
import struct
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from core.cfg import build_nx_cfg
from core.loader import LoadedELF
from core.models import EdgeType, Function
from core.normalize import NormalizedFunction, NormalizedInstruction

_EDGE_WEIGHTS: dict[EdgeType, int] = {
    EdgeType.FALLTHROUGH: 1,
    EdgeType.CONDITIONAL_TRUE: 2,
    EdgeType.CONDITIONAL_FALSE: 3,
    EdgeType.JUMP: 4,
    EdgeType.CALL: 5,
}


@dataclass(frozen=True, slots=True)
class FunctionFingerprint:
    """Consolidated structural, semantic, and sequence fingerprints for a function."""

    func_addr: int
    func_name: str
    norm_hash: str
    token_count: int
    token_ngrams: dict[str, int]
    mnemonic_hist: dict[str, int]
    wl_cfg_hash: str
    wl_subtrees: dict[str, int]
    md_index: float
    block_count: int
    edge_count: int
    cyclomatic_complexity: int
    constants: frozenset[int]
    strings: frozenset[str]
    callees: frozenset[str]


def compute_normalized_hash(norm_tokens: Sequence[str]) -> str:
    """Compute SHA-256 hash of normalized instruction sequence."""
    if not norm_tokens:
        return "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    payload = "\n".join(norm_tokens).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def compute_token_ngrams(norm_tokens: Sequence[str], n: int = 3) -> dict[str, int]:
    """Extract character or token n-grams for fuzzy instruction sequence similarity."""
    if not norm_tokens:
        return {}
    if len(norm_tokens) < n:
        return {"_".join(norm_tokens): 1}
    counts: Counter[str] = Counter()
    for idx in range(len(norm_tokens) - n + 1):
        window = "_".join(norm_tokens[idx : idx + n])
        counts[window] += 1
    return dict(counts)


def ngram_jaccard_similarity(ng1: Mapping[str, int], ng2: Mapping[str, int]) -> float:
    """Compute weighted Jaccard / multiset similarity between two n-gram frequency maps."""
    if not ng1 and not ng2:
        return 1.0
    if not ng1 or not ng2:
        return 0.0
    all_keys = set(ng1.keys()) | set(ng2.keys())
    intersection = sum(min(ng1.get(k, 0), ng2.get(k, 0)) for k in all_keys)
    union = sum(max(ng1.get(k, 0), ng2.get(k, 0)) for k in all_keys)
    return intersection / union if union > 0 else 0.0


def compute_mnemonic_histogram(
    norm_insns: Sequence[NormalizedInstruction],
) -> dict[str, int]:
    """Compute frequency distribution of normalized mnemonics."""
    counts: Counter[str] = Counter(i.mnemonic for i in norm_insns)
    return dict(counts)


def mnemonic_cosine_similarity(
    h1: Mapping[str, int],
    h2: Mapping[str, int],
) -> float:
    """Compute cosine similarity between two mnemonic frequency histograms."""
    if not h1 and not h2:
        return 1.0
    if not h1 or not h2:
        return 0.0

    dot = sum(h1.get(k, 0) * h2.get(k, 0) for k in h1)
    norm1 = math.sqrt(sum(v * v for v in h1.values()))
    norm2 = math.sqrt(sum(v * v for v in h2.values()))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


def compute_wl_cfg_hash(
    func: Function,
    iterations: int = 3,
) -> tuple[str, dict[str, int]]:
    """Compute Weisfeiler-Lehman (WL) structural graph hash and subtree histogram."""
    if not func.blocks:
        empty_hash = hashlib.sha256(b"empty").hexdigest()
        return empty_hash, {empty_hash: 1}

    graph = build_nx_cfg(func)
    block_map = {b.start_addr: b for b in func.blocks}

    # Initial node label: (in_degree, out_degree, sorted_edge_types, instruction_count_bucket)
    current_labels: dict[int, str] = {}
    for node in graph.nodes():
        block = block_map.get(node)
        insn_count = len(block.instructions) if block else 0
        bucket = min(insn_count // 4, 16)
        in_deg = graph.in_degree(node)
        out_deg = graph.out_degree(node)
        out_types = sorted(
            str(graph.edges[node, dst].get("edge_type", "")) for dst in graph.successors(node)
        )
        raw_seed = f"{in_deg}:{out_deg}:{bucket}:{','.join(out_types)}"
        current_labels[node] = hashlib.sha256(raw_seed.encode("utf-8")).hexdigest()[:16]

    all_subtrees: Counter[str] = Counter(current_labels.values())

    # Iterative 1-hop neighborhood aggregation
    for _ in range(iterations):
        next_labels: dict[int, str] = {}
        for node in graph.nodes():
            in_multiset = sorted(current_labels[pred] for pred in graph.predecessors(node))
            out_multiset = sorted(current_labels[succ] for succ in graph.successors(node))
            agg_str = f"{current_labels[node]}|{','.join(in_multiset)}|{','.join(out_multiset)}"
            lbl = hashlib.sha256(agg_str.encode("utf-8")).hexdigest()[:16]
            next_labels[node] = lbl
            all_subtrees[lbl] += 1
        current_labels = next_labels

    final_labels = sorted(current_labels.values())
    top_hash = hashlib.sha256(":".join(final_labels).encode("utf-8")).hexdigest()
    return top_hash, dict(all_subtrees)


def wl_subtree_kernel_similarity(
    subtrees1: Mapping[str, int],
    subtrees2: Mapping[str, int],
) -> float:
    """Compute Weisfeiler-Lehman subtree kernel similarity between two CFGs."""
    if not subtrees1 and not subtrees2:
        return 1.0
    if not subtrees1 or not subtrees2:
        return 0.0

    all_keys = set(subtrees1.keys()) | set(subtrees2.keys())
    dot = sum(subtrees1.get(k, 0) * subtrees2.get(k, 0) for k in all_keys)
    norm1 = math.sqrt(sum(v * v for v in subtrees1.values()))
    norm2 = math.sqrt(sum(v * v for v in subtrees2.values()))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


def compute_md_index(func: Function) -> float:
    """Compute BinDiff-style Matching Degree (MD) index topological invariant.

    Based on Dullien & Rolles (2005): sums edge invariant weights derived from
    predecessor and successor node degrees and edge types.
    """
    if len(func.blocks) <= 1 or not func.edges:
        return 0.0

    graph = build_nx_cfg(func)
    total_md = 0.0

    for edge in func.edges:
        u = edge.src
        v = edge.dst
        if u not in graph or v not in graph:
            continue

        in_u = graph.in_degree(u)
        out_u = graph.out_degree(u)
        in_v = graph.in_degree(v)
        out_v = graph.out_degree(v)
        weight = _EDGE_WEIGHTS.get(edge.edge_type, 1)

        denom = math.sqrt(2.0 * in_u + 3.0 * out_u + 5.0 * in_v + 7.0 * out_v + weight)
        if denom > 0:
            total_md += 1.0 / denom

    return round(total_md, 6)


def md_index_similarity(md1: float, md2: float) -> float:
    """Compute normalized similarity in [0, 1] between two MD indices."""
    if md1 == 0.0 and md2 == 0.0:
        return 1.0
    diff = abs(md1 - md2)
    max_val = max(abs(md1), abs(md2), 1.0)
    sim = 1.0 - (diff / max_val)
    return max(0.0, min(1.0, sim))


def compute_cfg_metrics(func: Function) -> tuple[int, int, int]:
    """Return (block_count, edge_count, cyclomatic_complexity)."""
    v = len(func.blocks)
    e = len(func.edges)
    # Cyclomatic complexity M = E - V + 2 for a single-entry procedure
    cc = max(1, e - v + 2) if v > 0 else 1
    return v, e, cc


def _extract_ascii_string(data: bytes, min_len: int = 3, max_len: int = 128) -> str | None:
    """Extract a clean printable ASCII string from raw bytes up to a null terminator."""
    chars: list[str] = []
    for b in data[:max_len]:
        if b == 0:
            break
        if 32 <= b <= 126 or b in (9, 10, 13):
            chars.append(chr(b))
        else:
            return None
    if len(chars) >= min_len:
        return "".join(chars)
    return None


def compute_constants_and_strings(
    func: Function,
    loaded: LoadedELF | None = None,
) -> tuple[frozenset[int], frozenset[str]]:
    """Extract non-trivial immediate constants and referenced string literals."""
    constants: set[int] = set()
    strings: set[str] = set()

    for block in func.blocks:
        for insn in block.instructions:
            # Rip-relative data reference
            if insn.rip_target is not None and loaded is not None:
                raw = loaded.read_vaddr(insn.rip_target, 64)
                if raw:
                    st = _extract_ascii_string(raw)
                    if st:
                        strings.add(st)
                    elif len(raw) >= 4:
                        # Extract integer constant from .rodata word/dword
                        val = struct.unpack_from("<I", raw, 0)[0]
                        if val not in (0, 0xFFFFFFFF) and val > 255:
                            constants.add(val)

            # Instruction immediate constants
            for imm in (insn.branch_target, insn.call_target):
                if (
                    imm is not None
                    and not (func.addr <= imm < func.addr + func.size)
                    and 255 < imm < 0x10000
                ):
                    constants.add(imm)

    return frozenset(constants), frozenset(strings)


def compute_callee_set(
    func: Function,
    import_map: Mapping[int, str] | None = None,
    sym_map: Mapping[int, str] | None = None,
) -> frozenset[str]:
    """Extract symbolic names of functions called or tail-called by `func`."""
    callees: set[str] = set()
    targets = set(func.call_targets) | set(func.tail_calls)

    for target in targets:
        if import_map and target in import_map:
            callees.add(import_map[target])
        elif sym_map and target in sym_map:
            callees.add(sym_map[target])
        elif target == func.addr:
            callees.add("<SELF>")
        else:
            callees.add(f"sub_{target:x}")

    return frozenset(callees)


def extract_fingerprints(
    func: Function,
    norm_func: NormalizedFunction,
    loaded: LoadedELF | None = None,
    import_map: Mapping[int, str] | None = None,
    sym_map: Mapping[int, str] | None = None,
) -> FunctionFingerprint:
    """Generate all fingerprints for a function."""
    tokens = norm_func.token_sequence
    norm_hash = compute_normalized_hash(tokens)
    token_ngrams = compute_token_ngrams(tokens, n=3)
    mnemonic_hist = compute_mnemonic_histogram(norm_func.instructions)
    wl_cfg_hash, wl_subtrees = compute_wl_cfg_hash(func, iterations=3)
    md_index = compute_md_index(func)
    b_count, e_count, cc = compute_cfg_metrics(func)
    consts, strings = compute_constants_and_strings(func, loaded)
    callees = compute_callee_set(func, import_map, sym_map)

    return FunctionFingerprint(
        func_addr=func.addr,
        func_name=func.name,
        norm_hash=norm_hash,
        token_count=len(tokens),
        token_ngrams=token_ngrams,
        mnemonic_hist=mnemonic_hist,
        wl_cfg_hash=wl_cfg_hash,
        wl_subtrees=wl_subtrees,
        md_index=md_index,
        block_count=b_count,
        edge_count=e_count,
        cyclomatic_complexity=cc,
        constants=consts,
        strings=strings,
        callees=callees,
    )
