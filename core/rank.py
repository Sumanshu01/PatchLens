"""Patch-likelihood ranking scoring changed functions by semantic delta and security tags."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import networkx as nx

from core.diff import ChangeClassification, FunctionDiff
from core.models import Binary

_TAG_WEIGHTS: dict[str, float] = {
    "added_bounds_check": 1.0,
    "added_null_error_check": 0.8,
    "integer_width_signedness": 0.8,
    "replaced_unsafe_call": 0.9,
    "new_early_exit": 0.6,
}


def compute_callgraph_centrality(binary: Binary) -> dict[int, float]:
    """Compute normalized degree centrality on the binary's inter-procedural call graph."""
    if not binary.functions:
        return {}

    g: nx.DiGraph[int] = nx.DiGraph()
    func_addrs = {f.addr for f in binary.functions}
    for addr in func_addrs:
        g.add_node(addr)

    for f in binary.functions:
        for tgt in set(f.call_targets) | set(f.tail_calls):
            if tgt in func_addrs:
                g.add_edge(f.addr, tgt)

    try:
        raw_centrality = nx.degree_centrality(g)
    except Exception:
        raw_centrality = {addr: 0.0 for addr in func_addrs}

    max_val = max(raw_centrality.values()) if raw_centrality else 1.0
    if max_val <= 0:
        max_val = 1.0

    return {addr: score / max_val for addr, score in raw_centrality.items()}


def score_and_rank_diffs(
    diffs: Sequence[FunctionDiff],
    binary_b: Binary | None = None,
    weights: Mapping[str, float] | None = None,
) -> tuple[FunctionDiff, ...]:
    """Calculate patch-likelihood score for changed functions and return sorted by rank."""
    w_sem = weights.get("w_sem", 0.35) if weights else 0.35
    w_sec = weights.get("w_sec", 0.50) if weights else 0.50
    w_cent = weights.get("w_cent", 0.15) if weights else 0.15

    centrality_map = compute_callgraph_centrality(binary_b) if binary_b else {}

    scored_diffs: list[FunctionDiff] = []

    for d in diffs:
        if d.classification != ChangeClassification.CHANGED_SEMANTIC:
            # Identical or cosmetic changes have 0 patch score
            scored_diffs.append(
                FunctionDiff(
                    func_a=d.func_a,
                    func_b=d.func_b,
                    similarity=d.similarity,
                    classification=d.classification,
                    block_diffs=d.block_diffs,
                    security_tags=d.security_tags,
                    patch_score=0.0,
                    rank=0,
                )
            )
            continue

        sem_delta = 1.0 - d.similarity

        tag_score = 0.0
        for tag in d.security_tags:
            w = _TAG_WEIGHTS.get(tag.tag_type, 0.5)
            tag_score += w * tag.confidence

        cent = centrality_map.get(d.addr_b or 0, 0.0)

        # Composite patch score
        patch_score = w_sem * sem_delta + w_sec * min(2.0, tag_score) + w_cent * cent

        scored_diffs.append(
            FunctionDiff(
                func_a=d.func_a,
                func_b=d.func_b,
                similarity=d.similarity,
                classification=d.classification,
                block_diffs=d.block_diffs,
                security_tags=d.security_tags,
                patch_score=round(patch_score, 4),
                rank=0,
            )
        )

    # Sort candidates by descending patch score
    semantic_changed = [
        d for d in scored_diffs if d.classification == ChangeClassification.CHANGED_SEMANTIC
    ]
    other_diffs = [
        d for d in scored_diffs if d.classification != ChangeClassification.CHANGED_SEMANTIC
    ]

    semantic_changed.sort(key=lambda x: x.patch_score, reverse=True)

    ranked_results: list[FunctionDiff] = []
    for idx, d in enumerate(semantic_changed):
        ranked_results.append(
            FunctionDiff(
                func_a=d.func_a,
                func_b=d.func_b,
                similarity=d.similarity,
                classification=d.classification,
                block_diffs=d.block_diffs,
                security_tags=d.security_tags,
                patch_score=d.patch_score,
                rank=idx + 1,
            )
        )

    ranked_results.extend(other_diffs)
    return tuple(ranked_results)
