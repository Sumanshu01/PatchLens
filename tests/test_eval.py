"""Unit and integration tests for core/eval.py matching evaluation harness."""

from __future__ import annotations

from pathlib import Path

from core.eval import evaluate_matcher_on_pair, extract_ground_truth_symbols
from core.match import FunctionMatcher

CORPUS_BIN_DIR = Path(__file__).resolve().parent.parent / "corpus" / "binaries"


def test_extract_ground_truth_symbols(zlib_1211_gcc_o2_unstripped: Path) -> None:
    symbols = extract_ground_truth_symbols(zlib_1211_gcc_o2_unstripped)
    assert len(symbols) > 80
    sym_values = set(symbols.values())
    assert "adler32" in sym_values
    assert "deflate" in sym_values
    assert "inflate" in sym_values


def test_same_opt_matching_f1_ge_095(
    zlib_1211_gcc_o2_stripped: Path,
    zlib_1211_gcc_o2_unstripped: Path,
) -> None:
    matcher = FunctionMatcher()
    res = evaluate_matcher_on_pair(
        scenario_name="same_opt_test",
        split="tuning",
        stripped_a_path=zlib_1211_gcc_o2_stripped,
        unstripped_a_path=zlib_1211_gcc_o2_unstripped,
        stripped_b_path=zlib_1211_gcc_o2_stripped,
        unstripped_b_path=zlib_1211_gcc_o2_unstripped,
        matcher=matcher,
    )

    assert res.f1 >= 0.95, f"Expected F1 >= 0.95, got {res.f1:.4f}"
    assert res.precision >= 0.95
    assert res.recall >= 0.95
    assert len(res.pass_breakdown) > 0

    # Ensure to_dict works cleanly
    d = res.to_dict()
    assert d["scenario_name"] == "same_opt_test"
    assert d["f1"] == round(res.f1, 4)


def test_markdown_formatting_helpers(
    zlib_1211_gcc_o2_stripped: Path,
    zlib_1211_gcc_o2_unstripped: Path,
) -> None:
    from core.eval import format_ablation_markdown, format_results_markdown

    res = evaluate_matcher_on_pair(
        scenario_name="dummy_scenario",
        split="tuning",
        stripped_a_path=zlib_1211_gcc_o2_stripped,
        unstripped_a_path=zlib_1211_gcc_o2_unstripped,
        stripped_b_path=zlib_1211_gcc_o2_stripped,
        unstripped_b_path=zlib_1211_gcc_o2_unstripped,
    )
    md = format_results_markdown([res], [res])
    assert "dummy_scenario" in md
    assert "Tuning Set Results" in md

    ablation_data = {
        "full_model": {
            "same_opt": 1.0,
            "patch_same_opt": 0.98,
            "cross_opt": 0.70,
            "cross_compiler": 0.85,
            "mean_f1": 0.88,
        },
        "no_pass1": {
            "same_opt": 0.90,
            "patch_same_opt": 0.85,
            "cross_opt": 0.65,
            "cross_compiler": 0.80,
            "mean_f1": 0.80,
        },
    }
    ab_md = format_ablation_markdown(ablation_data)
    assert "full_model" in ab_md
    assert "no_pass1" in ab_md
