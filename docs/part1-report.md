# PatchLens — Part 1 Analysis Report

## 1. Overview

Part 1 of **PatchLens** implements the binary analysis foundation for x86-64 ELF binaries:
- **ELF Loader (`core/loader.py`)**: Extracts architecture (`EM_X86_64` / `EM_AARCH64`), sections, `.symtab` and `.dynsym` symbols, PLT/GOT relocations mapped to `.plt.sec`/`.plt` stub addresses, and `R_*_RELATIVE` relocation addends into `.text`.
- **Recursive-Descent Disassembler (`core/disasm.py`)**: Uses Capstone to trace reachable execution paths from symbol seeds, entry points, relocation targets, and direct `call rel32` targets, followed by a linear-sweep fallback with inter-function NOP/trap padding skipping and prologue detection (`endbr64`, `push rbp; mov rbp, rsp`, callee-save pushes, `sub rsp, imm`).
- **Function & CFG Recovery (`core/cfg.py`)**: Partitions `.text` into functions, detects basic block leaders, builds per-function `networkx.DiGraph` instances with typed edges (`fallthrough`, `jump`, `conditional-true`, `conditional-false`, `call`), classifies inter-procedural jumps as tail calls, and recovers PIC `.rodata` switch jump tables (including LICM-hoisted table base `lea` instructions).

---

## 2. Corpus & Ground Truth Summary (`zlib 1.2.11` vs `1.2.12`)

The benchmark corpus in `corpus/binaries/` comprises **16 ELF shared libraries** compiled from upstream `madler/zlib` tags `v1.2.11` and `v1.2.12` using `gcc 15.2.0` (`-O0`, `-O2`, `-O3`) and `clang 21.1.8` (`-O2`), each produced in both unstripped (`.symtab` preserved) and stripped (`strip --strip-all`) variants.

### Function Recovery Accuracy (Unstripped vs. Stripped)

| Binary Variant (`zlib 1.2.11` / `1.2.12`) | `.symtab` `STT_FUNC` Count in `.text` | Recovered Functions (Unstripped) | Unstripped Delta | Recovered Functions (Stripped) | Stripped Delta |
|---|---:|---:|---:|---:|---:|
| `1.2.11 gcc -O0` | 133 | 133 | 0.00% | 133 | 0.00% |
| `1.2.11 gcc -O2` | 112 | 112 | 0.00% | 111 | -0.89% |
| `1.2.11 gcc -O3` | 108 | 108 | 0.00% | 107 | -0.93% |
| `1.2.11 clang -O2` | 107 | 107 | 0.00% | 106 | -0.93% |
| `1.2.12 gcc -O0` | 145 | 145 | 0.00% | 145 | 0.00% |
| `1.2.12 gcc -O2` | 117 | 117 | 0.00% | 116 | -0.85% |
| `1.2.12 gcc -O3` | 109 | 109 | 0.00% | 108 | -0.92% |
| `1.2.12 clang -O2` | 109 | 109 | 0.00% | 108 | -0.92% |

- Across all 8 unstripped builds, recovered function counts match `.symtab`'s unique `STT_FUNC` addresses in `.text` within **0.00%** (well within the `<5%` acceptance threshold).
- Across all 8 stripped builds (`.symtab` completely removed), hybrid recursive descent + `call` target discovery + `R_X86_64_RELATIVE` table seeding + prologue heuristics recover **>99%** of ground-truth functions (missing at most 1 CRT or tail-called helper per optimized binary).

---

## 3. CFG Sanity & `objdump` Parity Verification

1. **Reachability & Zero Dangling Edges**:
   - Verified across every recovered function in both unstripped and stripped `zlib` binaries:
     - `100%` of basic blocks in `func.blocks` are reachable from `func.addr` in `build_nx_cfg(func)`.
     - `0` dangling edges exist (`all(e.src in block_starts and e.dst in block_starts for e in func.edges)`).
2. **`objdump -d` Basic Block Boundary Parity**:
   - Verified exact basic-block start and end address parity against `objdump -d` on 3 hand-picked `zlib` functions (`adler32`, `compress2`, and `_tr_flush_block`).

---

## 4. Known Failure Cases & Takeaways for Part 2

1. **Aggressive Inlining at `-O2`/`-O3`**:
   - Between `-O0` (133–145 functions) and `-O2`/`-O3` (107–117 functions), both GCC and Clang inline ~25–35 internal `static` helper functions (such as `pqdownheap`, `send_tree`, `scan_tree`, `bi_windup`, and `flush_pending` in `trees.c` / `deflate.c`) directly into their callers (`build_tree`, `_tr_flush_block`, `deflate`).
   - Consequently, in Part 2 cross-optimization matching (`-O0` vs `-O2`), those inlined static functions in `-O0` have **no standalone counterpart** in `-O2` and must be left unmatched (reported as removed/inlined) rather than forcibly paired with unrelated functions.
2. **Tail-Call Optimization on Wrapper Functions**:
   - Thin API wrappers (such as `adler32` tail-calling `adler32_z` via `jmp adler32_z`, or `crc32` tail-calling `crc32_z`) compile to a single basic block ending in an inter-procedural `jmp` (`Function.tail_calls`) rather than a `call` + `ret`. Part 2's call-graph propagation and callee-set extraction should include both `call_targets` and `tail_calls` so wrapper-to-implementation edges are preserved across optimization levels.
3. **Switch Jump Tables in State Machines (`inflate`, `inflateBack`)**:
   - Large state-machine functions (`inflate` has >150 basic blocks) rely on PIC `.rodata` jump tables where LICM hoists `lea reg, [rip + table]` to the function header. Resolving these tables is critical for accurate CFG structural hashing (Weisfeiler-Lehman) and MD-index computation in Part 2.

