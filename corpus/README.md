# PatchLens Benchmark Corpus (`zlib` 1.2.11 & 1.2.12 — CVE-2018-25032)

This directory contains the reproducible build pipeline and ground-truth metadata for evaluating **PatchLens** on **CVE-2018-25032** (a heap buffer overflow / out-of-bounds write in `zlib`'s `trees.c` / `deflate.c` fixed in `zlib 1.2.12` via commit `5c44459c3b28a9bd3283aaceab7c615f8020c531`).

## Build Matrix (16 ELF Shared Libraries)

`corpus/build.py` clones the official upstream `madler/zlib` repository, checks out tags `v1.2.11` and `v1.2.12`, and builds `libz.so` across four compiler/optimization configurations, each emitted in both **unstripped** (with `.symtab` DWARF/symbol ground truth) and **stripped** (`strip --strip-all`) forms:

| Version | Variant | Compiler & Flags | Unstripped Binary | Stripped Binary |
|---|---|---|---|---|
| `1.2.11` | `gcc-O0` | `gcc -O0 -g -fPIC -shared` | `libz-1.2.11-gcc-O0-unstripped.so` | `libz-1.2.11-gcc-O0-stripped.so` |
| `1.2.11` | `gcc-O2` | `gcc -O2 -g -fPIC -shared` | `libz-1.2.11-gcc-O2-unstripped.so` | `libz-1.2.11-gcc-O2-stripped.so` |
| `1.2.11` | `gcc-O3` | `gcc -O3 -g -fPIC -shared` | `libz-1.2.11-gcc-O3-unstripped.so` | `libz-1.2.11-gcc-O3-stripped.so` |
| `1.2.11` | `clang-O2` | `clang -O2 -g -fPIC -shared` | `libz-1.2.11-clang-O2-unstripped.so` | `libz-1.2.11-clang-O2-stripped.so` |
| `1.2.12` | `gcc-O0` | `gcc -O0 -g -fPIC -shared` | `libz-1.2.12-gcc-O0-unstripped.so` | `libz-1.2.12-gcc-O0-stripped.so` |
| `1.2.12` | `gcc-O2` | `gcc -O2 -g -fPIC -shared` | `libz-1.2.12-gcc-O2-unstripped.so` | `libz-1.2.12-gcc-O2-stripped.so` |
| `1.2.12` | `gcc-O3` | `gcc -O3 -g -fPIC -shared` | `libz-1.2.12-gcc-O3-unstripped.so` | `libz-1.2.12-gcc-O3-stripped.so` |
| `1.2.12` | `clang-O2` | `clang -O2 -g -fPIC -shared` | `libz-1.2.12-clang-O2-unstripped.so` | `libz-1.2.12-clang-O2-stripped.so` |

## Rebuilding the Corpus

From the repository root:

```bash
python -m corpus.build
# or via Make:
make corpus
```

On Linux, `corpus/build.py` invokes `gcc`, `clang`, and `strip` directly. On Windows, it transparently delegates ELF compilation and stripping to WSL (`wsl bash -c ...`).

## Output Artifacts

- `corpus/binaries/*.so`: All 16 compiled ELF shared libraries.
- `corpus/manifest.json`: SHA-256 checksums, byte sizes, compiler version strings, and exact build commands for every binary.
- `corpus/ground_truth/cve_2018_25032.json` & `corpus/ground_truth/README.md`: Ground-truth list of modified functions programmatically extracted from `git diff v1.2.11 v1.2.12` and commit `5c44459c3b28a9bd3283aaceab7c615f8020c531`.

