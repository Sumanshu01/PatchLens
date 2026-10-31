"""Multi-pass, confidence-scored function matching engine for binary diffing."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
from scipy.optimize import linear_sum_assignment

from core.fingerprint import (
    FunctionFingerprint,
    extract_fingerprints,
    md_index_similarity,
    mnemonic_cosine_similarity,
    ngram_jaccard_similarity,
    wl_subtree_kernel_similarity,
)
from core.loader import LoadedELF
from core.models import Binary, Function
from core.normalize import (
    InstructionNormalizer,
    NormalizedFunction,
    RegisterStrategy,
    RoleRegisterStrategy,
)


@dataclass(frozen=True, slots=True)
class FunctionMatch:
    """A matched pair of functions from two binaries."""

    addr_a: int
    addr_b: int
    name_a: str
    name_b: str
    pass_name: str
    confidence: float
    similarity: float

    def to_dict(self) -> dict[str, object]:
        return {
            "addr_a": self.addr_a,
            "addr_b": self.addr_b,
            "name_a": self.name_a,
            "name_b": self.name_b,
            "pass_name": self.pass_name,
            "confidence": round(self.confidence, 4),
            "similarity": round(self.similarity, 4),
        }


@dataclass(frozen=True, slots=True)
class MatchResult:
    """Complete result of binary diff function matching."""

    matches: tuple[FunctionMatch, ...]
    unmatched_a: tuple[int, ...]
    unmatched_b: tuple[int, ...]
    pass_counts: dict[str, int]

    @property
    def total_matches(self) -> int:
        return len(self.matches)

    @property
    def added_count(self) -> int:
        """Count of functions present in binary B but not binary A."""
        return len(self.unmatched_b)

    @property
    def removed_count(self) -> int:
        """Count of functions present in binary A but not binary B."""
        return len(self.unmatched_a)

    def get_match_by_a(self, addr_a: int) -> FunctionMatch | None:
        for m in self.matches:
            if m.addr_a == addr_a:
                return m
        return None

    def get_match_by_b(self, addr_b: int) -> FunctionMatch | None:
        for m in self.matches:
            if m.addr_b == addr_b:
                return m
        return None


def _set_jaccard(s1: frozenset[object], s2: frozenset[object]) -> float:
    """Compute Jaccard similarity between two sets."""
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    intersection = len(s1 & s2)
    union = len(s1 | s2)
    return intersection / union if union > 0 else 0.0


def compute_composite_similarity(
    fp_a: FunctionFingerprint,
    fp_b: FunctionFingerprint,
    weights: Mapping[str, float] | None = None,
) -> float:
    """Compute composite similarity score in [0.0, 1.0] across all fingerprint signals."""
    w = {
        "mnemonic": 0.25,
        "wl_subtrees": 0.25,
        "md_index": 0.15,
        "callees": 0.15,
        "strings_consts": 0.10,
        "ngrams": 0.10,
    }
    if weights:
        w.update(weights)

    sim_mnem = mnemonic_cosine_similarity(fp_a.mnemonic_hist, fp_b.mnemonic_hist)
    sim_wl = wl_subtree_kernel_similarity(fp_a.wl_subtrees, fp_b.wl_subtrees)
    sim_md = md_index_similarity(fp_a.md_index, fp_b.md_index)
    sim_callees = _set_jaccard(fp_a.callees, fp_b.callees)

    # Combined strings & constants Jaccard
    s_const = _set_jaccard(fp_a.constants, fp_b.constants)
    s_str = _set_jaccard(fp_a.strings, fp_b.strings)
    sim_str_const = (s_str * 0.7 + s_const * 0.3) if (fp_a.strings or fp_b.strings) else s_const

    sim_ngram = ngram_jaccard_similarity(fp_a.token_ngrams, fp_b.token_ngrams)

    total_score = (
        w["mnemonic"] * sim_mnem
        + w["wl_subtrees"] * sim_wl
        + w["md_index"] * sim_md
        + w["callees"] * sim_callees
        + w["strings_consts"] * sim_str_const
        + w["ngrams"] * sim_ngram
    )
    return max(0.0, min(1.0, total_score))


class FunctionMatcher:
    """Configurable, multi-pass function matching engine."""

    ALL_PASSES: tuple[str, ...] = (
        "pass0_symbol_exact",
        "pass1_normalized_exact",
        "pass2_cfg_structural",
        "pass3_string_constant_anchor",
        "pass4_callgraph_propagation",
        "pass5_global_hungarian",
    )

    DEFAULT_STRIPPED_PASSES: tuple[str, ...] = (
        "pass1_normalized_exact",
        "pass2_cfg_structural",
        "pass3_string_constant_anchor",
        "pass4_callgraph_propagation",
        "pass5_global_hungarian",
    )

    def __init__(
        self,
        enabled_passes: Sequence[str] | None = None,
        register_strategy: RegisterStrategy | None = None,
        hungarian_threshold: float = 0.52,
        propagation_threshold: float = 0.65,
        anchor_threshold: float = 0.60,
        weights: Mapping[str, float] | None = None,
    ) -> None:
        self.enabled_passes = tuple(enabled_passes or self.DEFAULT_STRIPPED_PASSES)
        self.register_strategy = register_strategy or RoleRegisterStrategy()
        self.hungarian_threshold = hungarian_threshold
        self.propagation_threshold = propagation_threshold
        self.anchor_threshold = anchor_threshold
        self.weights = dict(weights) if weights else None
        self.normalizer = InstructionNormalizer(register_strategy=self.register_strategy)

    def _prepare_data(
        self,
        binary: Binary,
        loaded: LoadedELF | None,
        use_symbols: bool,
    ) -> tuple[
        dict[int, Function],
        dict[int, NormalizedFunction],
        dict[int, FunctionFingerprint],
        dict[int, set[int]],
        dict[int, set[int]],
    ]:
        """Precompute normalized functions, fingerprints, and call graph adjacency."""
        import_map = {imp.plt_addr: imp.name for imp in binary.imports if imp.plt_addr != 0}
        sym_map = (
            {s.addr: s.name for s in binary.symbols if s.sym_type == "STT_FUNC"}
            if use_symbols
            else {}
        )

        func_dict: dict[int, Function] = {f.addr: f for f in binary.functions}
        norm_dict: dict[int, NormalizedFunction] = {}
        fp_dict: dict[int, FunctionFingerprint] = {}
        callers: dict[int, set[int]] = defaultdict(set)
        callees: dict[int, set[int]] = defaultdict(set)

        for f in binary.functions:
            nf = self.normalizer.normalize_function(f, import_map=import_map, func_name_map=sym_map)
            norm_dict[f.addr] = nf
            fp = extract_fingerprints(
                f,
                nf,
                loaded=loaded,
                import_map=import_map,
                sym_map=sym_map,
            )
            fp_dict[f.addr] = fp

            # Track callers and callees inside the binary
            for tgt in set(f.call_targets) | set(f.tail_calls):
                if tgt in func_dict:
                    callees[f.addr].add(tgt)
                    callers[tgt].add(f.addr)

        return func_dict, norm_dict, fp_dict, callers, callees

    def match(
        self,
        binary_a: Binary,
        binary_b: Binary,
        loaded_a: LoadedELF | None = None,
        loaded_b: LoadedELF | None = None,
        use_symbols: bool = False,
    ) -> MatchResult:
        """Run multi-pass matching between binary_a and binary_b."""
        funcs_a, _norms_a, fps_a, callers_a, callees_a = self._prepare_data(
            binary_a, loaded_a, use_symbols
        )
        funcs_b, _norms_b, fps_b, callers_b, callees_b = self._prepare_data(
            binary_b, loaded_b, use_symbols
        )

        unmatched_a = set(funcs_a.keys())
        unmatched_b = set(funcs_b.keys())
        matches: list[FunctionMatch] = []
        pass_counts: Counter[str] = Counter()

        def _record_match(
            addr_a: int,
            addr_b: int,
            pass_name: str,
            confidence: float,
            similarity: float,
        ) -> None:
            matches.append(
                FunctionMatch(
                    addr_a=addr_a,
                    addr_b=addr_b,
                    name_a=funcs_a[addr_a].name,
                    name_b=funcs_b[addr_b].name,
                    pass_name=pass_name,
                    confidence=confidence,
                    similarity=similarity,
                )
            )
            unmatched_a.remove(addr_a)
            unmatched_b.remove(addr_b)
            pass_counts[pass_name] += 1

        # -------------------------------------------------------------
        # PASS 0: Exact Symbol Name Match (Ground truth / Unstripped only)
        # -------------------------------------------------------------
        if "pass0_symbol_exact" in self.enabled_passes and use_symbols:
            name_to_b: dict[str, int] = {}
            for addr_b in sorted(unmatched_b):
                name = funcs_b[addr_b].name
                if not name.startswith("sub_"):
                    name_to_b.setdefault(name, addr_b)

            for addr_a in sorted(unmatched_a):
                name = funcs_a[addr_a].name
                if not name.startswith("sub_") and name in name_to_b:
                    addr_b = name_to_b[name]
                    if addr_b in unmatched_b:
                        sim = compute_composite_similarity(
                            fps_a[addr_a], fps_b[addr_b], self.weights
                        )
                        _record_match(addr_a, addr_b, "pass0_symbol_exact", 1.0, sim)

        # -------------------------------------------------------------
        # PASS 1: Identical Normalized Instruction Hash
        # -------------------------------------------------------------
        if "pass1_normalized_exact" in self.enabled_passes:
            hash_map_b: dict[str, list[int]] = defaultdict(list)
            for b in unmatched_b:
                hash_map_b[fps_b[b].norm_hash].append(b)

            for a in sorted(unmatched_a):
                if a not in unmatched_a:
                    continue
                h = fps_a[a].norm_hash
                b_cands = [b for b in hash_map_b.get(h, []) if b in unmatched_b]
                if len(b_cands) == 1:
                    b_match = b_cands[0]
                    conf = 0.99 if fps_a[a].token_count >= 2 else 0.95
                    _record_match(a, b_match, "pass1_normalized_exact", conf, 1.0)
                elif len(b_cands) > 1:
                    # Break ties using callee sets and call-graph structure
                    best_b = None
                    best_sim = -1.0
                    for cand_b in b_cands:
                        sim = compute_composite_similarity(fps_a[a], fps_b[cand_b], self.weights)
                        if sim > best_sim:
                            best_sim = sim
                            best_b = cand_b
                    if best_b is not None and best_sim >= 0.90:
                        _record_match(a, best_b, "pass1_normalized_exact", 0.96, 1.0)

        # -------------------------------------------------------------
        # PASS 2: Identical WL CFG Hash + Same Callee Set
        # -------------------------------------------------------------
        if "pass2_cfg_structural" in self.enabled_passes:
            cfg_map_b: dict[tuple[str, frozenset[str]], list[int]] = defaultdict(list)
            for b in unmatched_b:
                fp = fps_b[b]
                if fp.block_count >= 2 or fp.callees:
                    cfg_map_b[(fp.wl_cfg_hash, fp.callees)].append(b)

            for a in sorted(unmatched_a):
                if a not in unmatched_a:
                    continue
                fp_a = fps_a[a]
                if fp_a.block_count < 2 and not fp_a.callees:
                    continue
                key = (fp_a.wl_cfg_hash, fp_a.callees)
                b_cands = [b for b in cfg_map_b.get(key, []) if b in unmatched_b]
                if len(b_cands) == 1:
                    cand_b = b_cands[0]
                    sim = compute_composite_similarity(fp_a, fps_b[cand_b], self.weights)
                    if sim >= 0.75:
                        conf = min(0.95, sim)
                        _record_match(a, cand_b, "pass2_cfg_structural", conf, sim)

        # -------------------------------------------------------------
        # PASS 3: Unique String & Constant Anchors
        # -------------------------------------------------------------
        if "pass3_string_constant_anchor" in self.enabled_passes:
            # Frequency of strings and constants across unmatched functions
            str_counts_a = Counter(s for a in unmatched_a for s in fps_a[a].strings)
            str_counts_b = Counter(s for b in unmatched_b for s in fps_b[b].strings)
            const_counts_a = Counter(c for a in unmatched_a for c in fps_a[a].constants)
            const_counts_b = Counter(c for b in unmatched_b for c in fps_b[b].constants)

            for a in sorted(unmatched_a):
                if a not in unmatched_a:
                    continue
                fp_a = fps_a[a]

                # Check for rare shared string (appears at most once in A and once in B)
                best_match = None
                best_score = -1.0
                unique_shared_strings = {
                    s for s in fp_a.strings if str_counts_a[s] == 1 and str_counts_b.get(s, 0) == 1
                }
                if unique_shared_strings:
                    for b in unmatched_b:
                        if unique_shared_strings & fps_b[b].strings:
                            sim = compute_composite_similarity(fp_a, fps_b[b], self.weights)
                            if sim > best_score:
                                best_score = sim
                                best_match = b

                if best_match is not None and best_score >= self.anchor_threshold:
                    conf = min(0.92, max(0.85, best_score))
                    _record_match(
                        a,
                        best_match,
                        "pass3_string_constant_anchor",
                        conf,
                        best_score,
                    )
                    continue

                # Check for unique constants set overlap
                unique_shared_consts = {
                    c
                    for c in fp_a.constants
                    if const_counts_a[c] == 1 and const_counts_b.get(c, 0) == 1
                }
                if len(unique_shared_consts) >= 2:
                    for b in unmatched_b:
                        shared = unique_shared_consts & fps_b[b].constants
                        if len(shared) >= 2:
                            sim = compute_composite_similarity(fp_a, fps_b[b], self.weights)
                            if sim > best_score and sim >= 0.70:
                                best_score = sim
                                best_match = b

                if best_match is not None and best_score >= self.anchor_threshold:
                    conf = min(0.90, max(0.82, best_score))
                    _record_match(
                        a,
                        best_match,
                        "pass3_string_constant_anchor",
                        conf,
                        best_score,
                    )

        # -------------------------------------------------------------
        # PASS 4: Call-Graph Fixed-Point Propagation
        # -------------------------------------------------------------
        if "pass4_callgraph_propagation" in self.enabled_passes:
            max_prop_rounds = 10
            for _ in range(max_prop_rounds):
                new_matches: list[tuple[int, int, float, float]] = []
                matched_pairs = [(m.addr_a, m.addr_b) for m in matches]

                # Evaluate caller and callee neighbors of all current matched pairs
                candidate_scores: dict[tuple[int, int], float] = {}

                for m_a, m_b in matched_pairs:
                    # Callee-to-callee propagation
                    unmatched_callees_a = [c for c in callees_a.get(m_a, ()) if c in unmatched_a]
                    unmatched_callees_b = [c for c in callees_b.get(m_b, ()) if c in unmatched_b]

                    for u in unmatched_callees_a:
                        for v in unmatched_callees_b:
                            pair = (u, v)
                            if pair not in candidate_scores:
                                sim = compute_composite_similarity(fps_a[u], fps_b[v], self.weights)
                                candidate_scores[pair] = sim

                    # Caller-to-caller propagation
                    unmatched_callers_a = [p for p in callers_a.get(m_a, ()) if p in unmatched_a]
                    unmatched_callers_b = [q for q in callers_b.get(m_b, ()) if q in unmatched_b]

                    for p in unmatched_callers_a:
                        for q in unmatched_callers_b:
                            pair = (p, q)
                            if pair not in candidate_scores:
                                sim = compute_composite_similarity(fps_a[p], fps_b[q], self.weights)
                                candidate_scores[pair] = sim

                # Select mutually highest-scoring pairs with distinctness margin
                a_to_cands: dict[int, list[tuple[int, float]]] = defaultdict(list)
                b_to_cands: dict[int, list[tuple[int, float]]] = defaultdict(list)
                for (u, v), score in candidate_scores.items():
                    if (
                        u in unmatched_a
                        and v in unmatched_b
                        and score >= self.propagation_threshold
                    ):
                        a_to_cands[u].append((v, score))
                        b_to_cands[v].append((u, score))

                for u, cands in a_to_cands.items():
                    cands.sort(key=lambda x: x[1], reverse=True)
                    best_v, best_s = cands[0]
                    # Margin check against second best candidate
                    margin = (best_s - cands[1][1]) if len(cands) > 1 else 0.10
                    if margin >= 0.04:
                        v_cands = sorted(b_to_cands[best_v], key=lambda x: x[1], reverse=True)
                        if v_cands[0][0] == u:
                            conf = min(0.92, max(0.78, best_s))
                            new_matches.append((u, best_v, conf, best_s))

                if not new_matches:
                    break

                for u, v, conf, sim in new_matches:
                    if u in unmatched_a and v in unmatched_b:
                        _record_match(u, v, "pass4_callgraph_propagation", conf, sim)

        # -------------------------------------------------------------
        # PASS 5: Global Hungarian Assignment
        # -------------------------------------------------------------
        if "pass5_global_hungarian" in self.enabled_passes and unmatched_a and unmatched_b:
            sorted_u_a = sorted(unmatched_a)
            sorted_u_b = sorted(unmatched_b)
            n_rows = len(sorted_u_a)
            n_cols = len(sorted_u_b)

            sim_matrix = np.zeros((n_rows, n_cols), dtype=np.float64)
            for i, a in enumerate(sorted_u_a):
                for j, b in enumerate(sorted_u_b):
                    sim_matrix[i, j] = compute_composite_similarity(
                        fps_a[a], fps_b[b], self.weights
                    )

            cost_matrix = 1.0 - sim_matrix
            row_ind, col_ind = linear_sum_assignment(cost_matrix)

            for i, j in zip(row_ind, col_ind, strict=False):
                sim = float(sim_matrix[i, j])
                if sim >= self.hungarian_threshold:
                    a = sorted_u_a[i]
                    b = sorted_u_b[j]
                    conf = min(0.88, sim)
                    _record_match(a, b, "pass5_global_hungarian", conf, sim)

        return MatchResult(
            matches=tuple(matches),
            unmatched_a=tuple(sorted(unmatched_a)),
            unmatched_b=tuple(sorted(unmatched_b)),
            pass_counts=dict(pass_counts),
        )
