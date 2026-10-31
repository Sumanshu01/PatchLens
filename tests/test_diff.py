"""Unit tests for diffing, security detectors, patch ranking, and analysis caching."""

from __future__ import annotations

from pathlib import Path

from core.cache import AnalysisCache
from core.detectors import (
    AddedBoundsCheckDetector,
    AddedNullErrorCheckDetector,
    IntegerWidthSignednessDetector,
    NewEarlyExitDetector,
    ReplacedUnsafeCallDetector,
    SecurityTag,
    run_all_detectors,
)
from core.diff import (
    BlockChangeType,
    ChangeClassification,
    FunctionDiff,
    FunctionDiffer,
    diff_matched_functions,
)
from core.match import FunctionMatch, MatchResult
from core.models import Architecture, BasicBlock, Binary, Function, Instruction
from core.rank import compute_callgraph_centrality, score_and_rank_diffs


def _create_simple_func(
    addr: int,
    name: str,
    mnemonics: tuple[str, ...],
    callees: tuple[int, ...] = (),
) -> Function:
    insns = []
    curr = addr
    for m in mnemonics:
        insns.append(
            Instruction(
                addr=curr,
                size=4,
                mnemonic=m,
                op_str="",
                raw_bytes=b"\x90\x90\x90\x90",
            )
        )
        curr += 4
    bb = BasicBlock(addr, curr, tuple(insns), ())
    return Function(
        addr=addr,
        size=curr - addr,
        name=name,
        is_symbol_backed=True,
        blocks=(bb,),
        edges=(),
        call_targets=callees,
    )


def test_function_classification_identical_and_semantic() -> None:
    differ = FunctionDiffer()

    # Identical function pair
    f1 = _create_simple_func(0x1000, "func1", ("mov", "add", "ret"))
    f2 = _create_simple_func(0x2000, "func1", ("mov", "add", "ret"))
    b_diffs, _raw_matches = differ.diff_basic_blocks(f1, f2)
    assert len(b_diffs) == 1
    assert b_diffs[0].change_type == BlockChangeType.UNCHANGED

    # Semantic change: added comparison / different instruction count
    f3 = _create_simple_func(0x1000, "func1", ("mov", "ret"))
    f4 = _create_simple_func(0x2000, "func1", ("mov", "cmp", "je", "ret"))
    b_diffs_sem, _raw_matches_sem = differ.diff_basic_blocks(f3, f4)
    assert any(bd.change_type == BlockChangeType.MODIFIED for bd in b_diffs_sem)


def test_detectors_bounds_and_null_checks() -> None:
    # Function A without bounds check
    bb_a = BasicBlock(
        0x1000,
        0x1008,
        (
            Instruction(0x1000, 4, "mov", "eax, [rdi]", b"\x90\x90\x90\x90"),
            Instruction(0x1004, 4, "ret", "", b"\xc3"),
        ),
        (),
    )
    fa = Function(0x1000, 8, "f_vuln", True, (bb_a,), ())

    # Function B with newly added bounds check guarding memory read
    bb_b = BasicBlock(
        0x2000,
        0x200C,
        (
            Instruction(0x2000, 4, "cmp", "rdi, 100", b"\x90\x90\x90\x90"),
            Instruction(0x2004, 4, "ja", "0x200c", b"\x90\x90\x90\x90", branch_target=0x200C),
            Instruction(0x2008, 4, "mov", "eax, [rdi]", b"\x90\x90\x90\x90"),
        ),
        (),
    )
    fb = Function(0x2000, 12, "f_safe", True, (bb_b,), ())

    bounds_detector = AddedBoundsCheckDetector()
    tags = bounds_detector.detect(fa, fb, [(bb_a, bb_b)], frozenset(), frozenset())
    assert len(tags) >= 1
    assert tags[0].tag_type == "added_bounds_check"
    assert "bounds" in tags[0].description.lower()

    # Null check detector
    bb_null = BasicBlock(
        0x3000,
        0x3008,
        (
            Instruction(0x3000, 4, "test", "rdi, rdi", b"\x90\x90\x90\x90"),
            Instruction(0x3004, 4, "je", "0x3010", b"\x90\x90\x90\x90", branch_target=0x3010),
        ),
        (),
    )
    fb_null = Function(0x3000, 8, "f_null", True, (bb_null,), ())
    null_detector = AddedNullErrorCheckDetector()
    null_tags = null_detector.detect(fa, fb_null, [(bb_a, bb_null)], frozenset(), frozenset())
    assert len(null_tags) >= 1
    assert null_tags[0].tag_type == "added_null_error_check"


def test_detectors_integer_width_and_unsafe_calls() -> None:
    # Integer width extension (movsxd)
    bb_a = BasicBlock(
        0x1000, 0x1004, (Instruction(0x1000, 4, "mov", "eax, edi", b"\x90\x90\x90\x90"),), ()
    )
    bb_b = BasicBlock(
        0x2000, 0x2004, (Instruction(0x2000, 4, "movsxd", "rax, edi", b"\x90\x90\x90\x90"),), ()
    )
    fa = Function(0x1000, 4, "f_a", True, (bb_a,), ())
    fb = Function(0x2000, 4, "f_b", True, (bb_b,), ())

    width_detector = IntegerWidthSignednessDetector()
    w_tags = width_detector.detect(fa, fb, [(bb_a, bb_b)], frozenset(), frozenset())
    assert len(w_tags) >= 1
    assert w_tags[0].tag_type == "integer_width_signedness"

    # Replaced unsafe call
    unsafe_detector = ReplacedUnsafeCallDetector()
    call_tags = unsafe_detector.detect(
        fa, fb, [(bb_a, bb_b)], frozenset({"strcpy"}), frozenset({"strncpy"})
    )
    assert len(call_tags) == 1
    assert call_tags[0].tag_type == "replaced_unsafe_call"
    assert "strncpy" in call_tags[0].description


def test_detectors_new_early_exit() -> None:
    bb_b_ret = BasicBlock(0x2010, 0x2014, (Instruction(0x2010, 4, "ret", "", b"\xc3"),), ())
    bb_b_main = BasicBlock(0x2000, 0x2008, (Instruction(0x2000, 4, "nop", "", b"\x90"),), ())
    fb = Function(0x2000, 20, "f_exit", True, (bb_b_main, bb_b_ret), ())
    fa = Function(0x1000, 8, "f_orig", True, (bb_b_main,), ())

    exit_detector = NewEarlyExitDetector()
    exit_tags = exit_detector.detect(fa, fb, [(None, bb_b_ret)], frozenset(), frozenset())
    assert len(exit_tags) == 1
    assert exit_tags[0].tag_type == "new_early_exit"


def test_rank_and_centrality() -> None:
    f1 = _create_simple_func(0x1000, "core_func", ("mov", "ret"), callees=(0x2000, 0x3000))
    f2 = _create_simple_func(0x2000, "helper_1", ("mov", "ret"))
    f3 = _create_simple_func(0x3000, "helper_2", ("mov", "ret"))

    bin_mock = Binary(
        path="/tmp/test.so",
        sha256="0" * 64,
        arch=Architecture.X86_64,
        bits=64,
        endian="little",
        is_pie=True,
        is_stripped=True,
        entry_point=0x1000,
        sections=(),
        symbols=(),
        imports=(),
        functions=(f1, f2, f3),
    )

    centrality = compute_callgraph_centrality(bin_mock)
    assert len(centrality) == 3
    assert centrality[0x1000] >= 0.0

    # Test score_and_rank_diffs on semantic diffs
    bb_mod = BasicBlock(
        0x1000, 0x1008, (Instruction(0x1000, 4, "add", "eax, 1", b"\x90\x90\x90\x90"),), ()
    )
    f_mod = Function(0x1000, 8, "core_func", True, (bb_mod,), ())
    f_diff = FunctionDiffer().diff_basic_blocks(f1, f_mod)[0]
    func_diff = FunctionDiff(
        func_a=f1,
        func_b=f_mod,
        similarity=0.75,
        classification=ChangeClassification.CHANGED_SEMANTIC,
        block_diffs=f_diff,
        security_tags=(SecurityTag("added_bounds_check", "test", 0.9, (0x1000,), (0x1000,), "ev"),),
    )
    ranked = score_and_rank_diffs([func_diff], bin_mock)
    assert len(ranked) == 1
    assert ranked[0].rank == 1
    assert ranked[0].patch_score > 0.0
    assert ranked[0].to_dict()["rank"] == 1


def test_diff_matched_functions_pipeline() -> None:
    f_a1 = _create_simple_func(0x1000, "func_same", ("mov", "ret"))
    f_a2 = _create_simple_func(0x2000, "func_removed", ("nop", "ret"))
    f_b1 = _create_simple_func(0x1000, "func_same", ("mov", "ret"))
    f_b2 = _create_simple_func(0x3000, "func_added", ("xor", "ret"))

    bin_a = Binary(
        path="/tmp/bin_a.so",
        sha256="1" * 64,
        arch=Architecture.X86_64,
        bits=64,
        endian="little",
        is_pie=True,
        is_stripped=True,
        entry_point=0x1000,
        sections=(),
        symbols=(),
        imports=(),
        functions=(f_a1, f_a2),
    )
    bin_b = Binary(
        path="/tmp/bin_b.so",
        sha256="2" * 64,
        arch=Architecture.X86_64,
        bits=64,
        endian="little",
        is_pie=True,
        is_stripped=True,
        entry_point=0x1000,
        sections=(),
        symbols=(),
        imports=(),
        functions=(f_b1, f_b2),
    )

    match_result = MatchResult(
        matches=(FunctionMatch(0x1000, 0x1000, "func_same", "func_same", "pass1", 1.0, 1.0),),
        unmatched_a=(0x2000,),
        unmatched_b=(0x3000,),
        pass_counts={"pass1": 1},
    )

    diffs = diff_matched_functions(match_result, bin_a, bin_b)
    assert len(diffs) == 3
    classifications = {d.classification for d in diffs}
    assert ChangeClassification.IDENTICAL in classifications
    assert ChangeClassification.REMOVED in classifications
    assert ChangeClassification.ADDED in classifications

    all_tags = run_all_detectors(
        f_a1, f_b1, [(f_a1.blocks[0], f_b1.blocks[0])], frozenset(), frozenset()
    )
    assert isinstance(all_tags, tuple)


def test_analysis_cache(tmp_path: Path, zlib_1211_gcc_o2_stripped: Path) -> None:
    cache = AnalysisCache(cache_dir=tmp_path / "cache")
    cache.clear()

    # Test get_or_analyze
    b = cache.get_or_analyze(zlib_1211_gcc_o2_stripped)
    assert b is not None
    # Second call hits cache
    b2 = cache.get_or_analyze(zlib_1211_gcc_o2_stripped)
    assert b2 is b


def test_regression_cjson_patch_ranking_top1() -> None:
    """Regression test locking in 100% Top-1 hit rate on cJSON CVE-2019-1010239."""
    corpus_cjson = Path(__file__).resolve().parent.parent / "corpus" / "cjson" / "binaries"
    bin_a_path = corpus_cjson / "libcjson-1.7.11-gcc-O2-stripped.so"
    bin_b_path = corpus_cjson / "libcjson-1.7.12-gcc-O2-stripped.so"
    if not bin_a_path.is_file() or not bin_b_path.is_file():
        return

    from core.cfg import analyze_binary
    from core.diff import diff_matched_functions
    from core.eval import extract_ground_truth_symbols
    from core.match import FunctionMatcher
    from core.rank import score_and_rank_diffs

    bin_a = analyze_binary(bin_a_path)
    bin_b = analyze_binary(bin_b_path)
    matcher = FunctionMatcher()
    match_result = matcher.match(bin_a, bin_b)
    diffs = diff_matched_functions(match_result, bin_a, bin_b)
    ranked = score_and_rank_diffs(diffs, bin_b)

    semantic = [d for d in ranked if d.rank > 0]
    assert len(semantic) >= 1
    # Check that rank #1 corresponds to cJSON_Minify
    u_path = corpus_cjson / "libcjson-1.7.12-gcc-O2-unstripped.so"
    syms = extract_ground_truth_symbols(u_path)
    top_1_name = syms.get(semantic[0].addr_b or 0, semantic[0].name_b)
    assert semantic[0].rank == 1
    assert top_1_name == "cJSON_Minify"


def test_regression_zlib_patch_ranking_top5(zlib_1211_gcc_o2_stripped: Path) -> None:
    """Regression test locking in Top-5 hit rate on zlib CVE-2018-25032."""
    bin_b_path = zlib_1211_gcc_o2_stripped.parent / "libz-1.2.12-gcc-O2-stripped.so"
    if not bin_b_path.is_file():
        return

    from core.cfg import analyze_binary
    from core.diff import diff_matched_functions
    from core.eval import extract_ground_truth_symbols
    from core.match import FunctionMatcher
    from core.rank import score_and_rank_diffs

    bin_a = analyze_binary(zlib_1211_gcc_o2_stripped)
    bin_b = analyze_binary(bin_b_path)
    matcher = FunctionMatcher()
    match_result = matcher.match(bin_a, bin_b)
    diffs = diff_matched_functions(match_result, bin_a, bin_b)
    ranked = score_and_rank_diffs(diffs, bin_b)

    semantic = [d for d in ranked if d.rank > 0]
    u_path = bin_b_path.parent / "libz-1.2.12-gcc-O2-unstripped.so"
    syms = extract_ground_truth_symbols(u_path)

    cve_functions = {
        "compress_block",
        "deflateCopy",
        "deflateInit2_",
        "deflatePrime",
        "deflate_fast",
        "deflate_huff",
        "deflate_rle",
        "deflate_slow",
        "init_block",
    }

    # Verify that a CVE function is within Top 5
    top_5_names = [syms.get(d.addr_b or 0, d.name_b) for d in semantic[:5]]
    assert any(fn in cve_functions for fn in top_5_names)
