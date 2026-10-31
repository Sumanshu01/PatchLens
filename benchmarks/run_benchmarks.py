"""Performance profiling and benchmarking for PatchLens diffing stages."""

from __future__ import annotations

import json
import time
import tracemalloc
from pathlib import Path
from typing import Any

from core.cache import AnalysisCache
from core.cfg import recover_all_functions
from core.diff import diff_matched_functions
from core.disasm import disassemble_text
from core.fingerprint import extract_fingerprints
from core.loader import load_elf
from core.match import FunctionMatcher
from core.normalize import InstructionNormalizer
from core.rank import score_and_rank_diffs

CORPUS_DIR = Path(__file__).resolve().parent.parent / "corpus"
ZLIB_BIN_A = CORPUS_DIR / "binaries" / "libz-1.2.11-gcc-O2-stripped.so"
ZLIB_BIN_B = CORPUS_DIR / "binaries" / "libz-1.2.12-gcc-O2-stripped.so"


def profile_pipeline_stages(bin_a_path: Path, bin_b_path: Path) -> dict[str, Any]:
    """Profile runtime and peak memory for each analysis and diffing stage."""
    tracemalloc.start()
    stages: dict[str, float] = {}

    # Stage 1: Load ELF
    t0 = time.perf_counter()
    loaded_a = load_elf(bin_a_path)
    loaded_b = load_elf(bin_b_path)
    stages["load_elf"] = time.perf_counter() - t0

    # Stage 2: Capstone Disassembly
    t0 = time.perf_counter()
    disasm_a = disassemble_text(loaded_a)
    disasm_b = disassemble_text(loaded_b)
    stages["disassemble"] = time.perf_counter() - t0

    # Stage 3: CFG Recovery
    t0 = time.perf_counter()
    funcs_a = recover_all_functions(loaded_a, disasm_a)
    funcs_b = recover_all_functions(loaded_b, disasm_b)
    b_a = loaded_a.binary
    b_b = loaded_b.binary
    bin_obj_a = type(b_a)(
        path=b_a.path,
        sha256=b_a.sha256,
        arch=b_a.arch,
        bits=b_a.bits,
        endian=b_a.endian,
        is_pie=b_a.is_pie,
        is_stripped=b_a.is_stripped,
        entry_point=b_a.entry_point,
        sections=b_a.sections,
        symbols=b_a.symbols,
        imports=b_a.imports,
        functions=funcs_a,
    )
    bin_obj_b = type(b_b)(
        path=b_b.path,
        sha256=b_b.sha256,
        arch=b_b.arch,
        bits=b_b.bits,
        endian=b_b.endian,
        is_pie=b_b.is_pie,
        is_stripped=b_b.is_stripped,
        entry_point=b_b.entry_point,
        sections=b_b.sections,
        symbols=b_b.symbols,
        imports=b_b.imports,
        functions=funcs_b,
    )
    stages["cfg_recovery"] = time.perf_counter() - t0

    # Stage 4: Normalization and Fingerprinting
    t0 = time.perf_counter()
    normalizer = InstructionNormalizer()
    for f in funcs_a:
        nf = normalizer.normalize_function(f)
        extract_fingerprints(f, nf, loaded=loaded_a)
    for f in funcs_b:
        nf = normalizer.normalize_function(f)
        extract_fingerprints(f, nf, loaded=loaded_b)
    stages["fingerprinting"] = time.perf_counter() - t0

    # Stage 5: Multi-Pass Function Matching
    t0 = time.perf_counter()
    matcher = FunctionMatcher()
    match_result = matcher.match(bin_obj_a, bin_obj_b, loaded_a, loaded_b, use_symbols=False)
    stages["function_matching"] = time.perf_counter() - t0

    # Stage 6: Block-Level Diffing and Security Pattern Detection
    t0 = time.perf_counter()
    diffs = diff_matched_functions(match_result, bin_obj_a, bin_obj_b, loaded_a, loaded_b)
    stages["block_diff_and_detect"] = time.perf_counter() - t0

    # Stage 7: Patch Likelihood Ranking
    t0 = time.perf_counter()
    score_and_rank_diffs(diffs, bin_obj_b)
    stages["ranking"] = time.perf_counter() - t0

    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    total_time = sum(stages.values())

    return {
        "binary_a": bin_a_path.name,
        "binary_b": bin_b_path.name,
        "total_functions": len(funcs_a) + len(funcs_b),
        "stages_seconds": {k: round(v, 4) for k, v in stages.items()},
        "total_seconds": round(total_time, 4),
        "peak_memory_mb": round(peak / (1024 * 1024), 2),
    }


def benchmark_caching_speedup(bin_a_path: Path, bin_b_path: Path) -> dict[str, Any]:
    """Measure speedup gained by sha256-keyed analysis caching."""
    cache = AnalysisCache(cache_dir=Path(".patchlens_cache_benchmark"))
    cache.clear()

    # Cold run
    t0 = time.perf_counter()
    b_a_cold = cache.get_or_analyze(bin_a_path)
    b_b_cold = cache.get_or_analyze(bin_b_path)
    matcher = FunctionMatcher()
    m_cold = matcher.match(b_a_cold, b_b_cold)
    diffs_cold = diff_matched_functions(m_cold, b_a_cold, b_b_cold)
    score_and_rank_diffs(diffs_cold, b_b_cold)
    cold_time = time.perf_counter() - t0

    # Warm run (cached binary models)
    t0 = time.perf_counter()
    b_a_warm = cache.get_or_analyze(bin_a_path)
    b_b_warm = cache.get_or_analyze(bin_b_path)
    m_warm = matcher.match(b_a_warm, b_b_warm)
    diffs_warm = diff_matched_functions(m_warm, b_a_warm, b_b_warm)
    score_and_rank_diffs(diffs_warm, b_b_warm)
    warm_time = time.perf_counter() - t0

    cache.clear()

    speedup = cold_time / warm_time if warm_time > 0 else 1.0
    return {
        "cold_seconds": round(cold_time, 4),
        "warm_seconds": round(warm_time, 4),
        "speedup_factor": round(speedup, 2),
    }


if __name__ == "__main__":
    if ZLIB_BIN_A.is_file() and ZLIB_BIN_B.is_file():
        profile = profile_pipeline_stages(ZLIB_BIN_A, ZLIB_BIN_B)
        print("Pipeline Stages Profile:", json.dumps(profile, indent=2))

        caching = benchmark_caching_speedup(ZLIB_BIN_A, ZLIB_BIN_B)
        print("Caching Benchmark:", json.dumps(caching, indent=2))
