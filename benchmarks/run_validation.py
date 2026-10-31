"""Validation suite computing Top-1, Top-5, and Top-10 hit rates across real CVEs."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.cfg import analyze_binary
from core.diff import diff_matched_functions
from core.match import FunctionMatcher
from core.rank import score_and_rank_diffs

CORPUS_DIR = Path(__file__).resolve().parent.parent / "corpus"
ZLIB_DIR = CORPUS_DIR / "binaries"
CJSON_DIR = CORPUS_DIR / "cjson" / "binaries"


@dataclass(frozen=True, slots=True)
class PatchHitResult:
    """Hit-rate evaluation for a binary pair under a real-world CVE."""

    benchmark: str
    scenario: str
    binary_a: str
    binary_b: str
    stripped: bool
    cve_target_functions: tuple[str, ...]
    total_changed_functions: int
    top_ranked_functions: tuple[tuple[int, str, float, bool], ...]
    top_1_hit: bool
    top_5_hit: bool
    top_10_hit: bool
    best_cve_rank: int | None
    best_cve_func: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark": self.benchmark,
            "scenario": self.scenario,
            "binary_a": self.binary_a,
            "binary_b": self.binary_b,
            "stripped": self.stripped,
            "total_changed_functions": self.total_changed_functions,
            "top_1_hit": self.top_1_hit,
            "top_5_hit": self.top_5_hit,
            "top_10_hit": self.top_10_hit,
            "best_cve_rank": self.best_cve_rank,
            "best_cve_func": self.best_cve_func,
            "top_ranked": [
                {
                    "rank": r,
                    "function": fn,
                    "score": round(sc, 4),
                    "is_cve_fix": is_c,
                }
                for r, fn, sc, is_c in self.top_ranked_functions[:10]
            ],
        }


def evaluate_zlib_patch_ranking() -> list[PatchHitResult]:
    """Evaluate PatchLens ranking accuracy on zlib CVE-2018-25032 (1.2.11 vs 1.2.12)."""
    gt_path = CORPUS_DIR / "ground_truth" / "cve_2018_25032.json"
    if not gt_path.is_file():
        return []
    gt_data = json.loads(gt_path.read_text(encoding="utf-8"))
    cve_targets = tuple(gt_data["security_fix_commit"]["modified_functions"])
    cve_set = set(cve_targets)

    variants = [
        ("gcc-O0", False),
        ("gcc-O0", True),
        ("gcc-O2", False),
        ("gcc-O2", True),
        ("gcc-O3", False),
        ("gcc-O3", True),
        ("clang-O2", False),
        ("clang-O2", True),
    ]

    results: list[PatchHitResult] = []

    for variant, stripped in variants:
        tag = "stripped" if stripped else "unstripped"
        b_a_path = ZLIB_DIR / f"libz-1.2.11-{variant}-{tag}.so"
        b_b_path = ZLIB_DIR / f"libz-1.2.12-{variant}-{tag}.so"
        if not b_a_path.is_file() or not b_b_path.is_file():
            continue

        bin_a = analyze_binary(b_a_path)
        bin_b = analyze_binary(b_b_path)
        matcher = FunctionMatcher()
        match_result = matcher.match(bin_a, bin_b)
        diffs = diff_matched_functions(match_result, bin_a, bin_b)
        ranked = score_and_rank_diffs(diffs, bin_b)

        semantic_diffs = [d for d in ranked if d.rank > 0]
        top_ranked_tuples: list[tuple[int, str, float, bool]] = []
        best_rank: int | None = None
        best_func: str | None = None

        for d in semantic_diffs:
            # Map address back to symbol if stripped
            fn = d.name_b
            if stripped:
                # Check symbol from unstripped counterpart if name is sub_...
                u_path = ZLIB_DIR / f"libz-1.2.12-{variant}-unstripped.so"
                from core.eval import extract_ground_truth_symbols

                syms = extract_ground_truth_symbols(u_path)
                fn = syms.get(d.addr_b or 0, d.name_b)

            is_cve = fn in cve_set
            top_ranked_tuples.append((d.rank, fn, d.patch_score, is_cve))
            if is_cve and best_rank is None:
                best_rank = d.rank
                best_func = fn

        top_1 = bool(best_rank == 1)
        top_5 = bool(best_rank is not None and best_rank <= 5)
        top_10 = bool(best_rank is not None and best_rank <= 10)

        results.append(
            PatchHitResult(
                benchmark="zlib-CVE-2018-25032",
                scenario=f"{variant}_{tag}",
                binary_a=b_a_path.name,
                binary_b=b_b_path.name,
                stripped=stripped,
                cve_target_functions=cve_targets,
                total_changed_functions=len(semantic_diffs),
                top_ranked_functions=tuple(top_ranked_tuples),
                top_1_hit=top_1,
                top_5_hit=top_5,
                top_10_hit=top_10,
                best_cve_rank=best_rank,
                best_cve_func=best_func,
            )
        )

    return results


def evaluate_cjson_patch_ranking() -> list[PatchHitResult]:
    """Evaluate PatchLens ranking accuracy on cJSON CVE-2019-1010239 (1.7.11 vs 1.7.12)."""
    cve_target = "cJSON_Minify"
    variants = [
        ("gcc-O0", False),
        ("gcc-O0", True),
        ("gcc-O2", False),
        ("gcc-O2", True),
        ("clang-O2", False),
        ("clang-O2", True),
    ]

    results: list[PatchHitResult] = []

    for variant, stripped in variants:
        tag = "stripped" if stripped else "unstripped"
        b_a_path = CJSON_DIR / f"libcjson-1.7.11-{variant}-{tag}.so"
        b_b_path = CJSON_DIR / f"libcjson-1.7.12-{variant}-{tag}.so"
        if not b_a_path.is_file() or not b_b_path.is_file():
            continue

        bin_a = analyze_binary(b_a_path)
        bin_b = analyze_binary(b_b_path)
        matcher = FunctionMatcher()
        match_result = matcher.match(bin_a, bin_b)
        diffs = diff_matched_functions(match_result, bin_a, bin_b)
        ranked = score_and_rank_diffs(diffs, bin_b)

        semantic_diffs = [d for d in ranked if d.rank > 0]
        top_ranked_tuples: list[tuple[int, str, float, bool]] = []
        best_rank: int | None = None
        best_func: str | None = None

        for d in semantic_diffs:
            fn = d.name_b
            if stripped:
                u_path = CJSON_DIR / f"libcjson-1.7.12-{variant}-unstripped.so"
                from core.eval import extract_ground_truth_symbols

                syms = extract_ground_truth_symbols(u_path)
                fn = syms.get(d.addr_b or 0, d.name_b)

            is_cve = fn == cve_target
            top_ranked_tuples.append((d.rank, fn, d.patch_score, is_cve))
            if is_cve and best_rank is None:
                best_rank = d.rank
                best_func = fn

        top_1 = bool(best_rank == 1)
        top_5 = bool(best_rank is not None and best_rank <= 5)
        top_10 = bool(best_rank is not None and best_rank <= 10)

        results.append(
            PatchHitResult(
                benchmark="cJSON-CVE-2019-1010239",
                scenario=f"{variant}_{tag}",
                binary_a=b_a_path.name,
                binary_b=b_b_path.name,
                stripped=stripped,
                cve_target_functions=(cve_target,),
                total_changed_functions=len(semantic_diffs),
                top_ranked_functions=tuple(top_ranked_tuples),
                top_1_hit=top_1,
                top_5_hit=top_5,
                top_10_hit=top_10,
                best_cve_rank=best_rank,
                best_cve_func=best_func,
            )
        )

    return results


def format_validation_markdown(
    zlib_results: Sequence[PatchHitResult],
    cjson_results: Sequence[PatchHitResult],
) -> str:
    """Format markdown validation summary report."""
    lines: list[str] = [
        "## Real-World Security Patch Localization (Top-k Hit Rates)",
        "",
        "### Case Study 1: zlib 1.2.11 -> 1.2.12 (CVE-2018-25032)",
        "",
        "| Scenario | Stripped | Changed Funcs | Best Patched Func | Best Rank | Top-1 | Top-5 | Top-10 |",  # noqa: E501
        "|---|:---:|---:|---|---:|:---:|:---:|:---:|",
    ]

    for r in zlib_results:
        st_icon = "Yes" if r.stripped else "No"
        t1 = "YES" if r.top_1_hit else "no"
        t5 = "YES" if r.top_5_hit else "no"
        t10 = "YES" if r.top_10_hit else "no"
        b_rank = f"#{r.best_cve_rank}" if r.best_cve_rank is not None else "N/A"
        b_fn = f"`{r.best_cve_func}`" if r.best_cve_func is not None else "none"
        lines.append(
            f"| `{r.scenario}` | {st_icon} | {r.total_changed_functions} | "
            f"{b_fn} | {b_rank} | {t1} | {t5} | {t10} |"
        )

    lines.extend(
        [
            "",
            "### Case Study 2: cJSON 1.7.11 -> 1.7.12 (CVE-2019-1010239 in `cJSON_Minify`)",
            "",
            "| Scenario | Stripped | Changed Funcs | Target Function | Rank | Top-1 | Top-5 | Top-10 |",  # noqa: E501
            "|---|:---:|---:|---|---:|:---:|:---:|:---:|",
        ]
    )

    for r in cjson_results:
        st_icon = "Yes" if r.stripped else "No"
        t1 = "YES" if r.top_1_hit else "no"
        t5 = "YES" if r.top_5_hit else "no"
        t10 = "YES" if r.top_10_hit else "no"
        b_rank = f"#{r.best_cve_rank}" if r.best_cve_rank is not None else "N/A"
        lines.append(
            f"| `{r.scenario}` | {st_icon} | {r.total_changed_functions} | "
            f"`cJSON_Minify` | {b_rank} | {t1} | {t5} | {t10} |"
        )

    return "\n".join(lines)


if __name__ == "__main__":
    zlib_res = evaluate_zlib_patch_ranking()
    cjson_res = evaluate_cjson_patch_ranking()
    print(format_validation_markdown(zlib_res, cjson_res))
