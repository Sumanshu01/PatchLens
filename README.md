# PatchLens: Binary Diffing & Automated Security Patch Localization

[![CI](https://github.com/Sumanshu01/PatchLens/actions/workflows/ci.yml/badge.svg)](https://github.com/Sumanshu01/PatchLens/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **PatchLens** is an automated binary diffing and security patch localization platform for stripped ELF binaries. It combines Weisfeiler-Lehman graph kernels, BinDiff topological invariants, and specialized security pattern detectors to pinpoint where security fixes occurred between two releases—without requiring source code or debug symbols.

---

## Demo Walkthrough

![PatchLens Hero Walkthrough](docs/assets/patchlens_hero.gif)
*(A full-resolution automated video recording walkthrough is generated at `patchlens_demo_walkthrough.webm`)*

---

## 1. Quickstart (One Command)

### Option A: Run with Docker Compose (Recommended)
```bash
docker compose up --build
```
- **Web UI**: Open `http://localhost:3000`
- **REST API & Swagger Docs**: Open `http://localhost:8000/docs`
- **Prometheus Metrics**: `http://localhost:8000/metrics`
- **Health Check**: `http://localhost:8000/health`

### Option B: Local Standalone Development
```bash
# 1. Setup Python core & API dependencies
pip install -e .
pip install fastapi uvicorn sqlalchemy alembic prometheus-client redis rq httpx

# 2. Setup Web Frontend dependencies & build
cd web && npm install && npm run build && cd ..

# 3. Initialize SQLite DB & Seed Sample Demos
python -m api.seed

# 4. Start API Server (in terminal 1)
uvicorn api.main:app --port 8000 --reload

# 5. Start Web Dev / Preview Server (in terminal 2)
cd web && npm run preview -- --port 5173
```

---

## 2. System Architecture

```mermaid
flowchart TD
    subgraph UI["Web Frontend (React + TypeScript + Vite)"]
        Landing["Dual Binary Dropzone & Sample Selector"]
        Dash["Summary Metrics Dashboard"]
        VirtTable["Virtualized Function Table (5,000+ funcs)"]
        CFGView["Side-by-Side Cytoscape CFG Viewer (Sync Zoom/Pan)"]
        DiffView["Syntax-Highlighted Unified Instruction Diff"]
        ProofView["'Why this match?' Fingerprint Breakdown"]
        Explorer["Match Explorer Call Graph"]
    end

    subgraph API["FastAPI Backend (api/)"]
        Router["REST Endpoints & SSE Progress Streamer"]
        Validator["ELF Magic (\\x7fELF) & 50MB Size Bounds Guard"]
        DB[(SQLite Persistence: Hashes, Jobs, Results)]
        Metrics["Prometheus /metrics & /health"]
    end

    subgraph Worker["Execution & Isolation Layer"]
        Queue["Job Manager: Redis RQ (Docker) / ProcessPool (Local)"]
        Sandbox["Sandboxed Subprocess: Static Parsing Only"]
    end

    subgraph Core["Core Diffing Engine (core/)"]
        Loader["ELF Structure & Section Loader (pyelftools)"]
        Disasm["Recursive Descent Disassembly (Capstone)"]
        CFG["CFG Recovery & Graph Invariants"]
        Matcher["6-Pass Confidence Matching Ladder"]
        Differ["Block Diffing & Security Pattern Detectors"]
        Ranker["Composite Patch Suspiciousness Scoring"]
    end

    Landing --> Router
    Router --> Validator --> DB
    Router --> Queue --> Sandbox
    Sandbox --> Core
    Core --> DB
    Router --> Dash
    Router --> CFGView
    Router --> DiffView
    Router --> Explorer
```

---

## 3. How Matching Works

PatchLens compares binaries through a **6-pass confidence ladder**, moving from high-confidence structural anchors to global topological assignments:

1. **Pass 0 (Ground Truth)**: Exact symbol-name match (strictly used for evaluation and disabled on stripped binaries).
2. **Pass 1 (Normalized Hash)**: Identical SHA-256 hash of normalized instruction sequences. Registers are canonicalized by ABI role (`RoleRegisterStrategy`), and addresses/immediates are masked.
3. **Pass 2 (WL CFG Hash + Callees)**: Identical Weisfeiler-Lehman graph hash combined with identical imported callee sets.
4. **Pass 3 (Anchor Matching)**: Uniquely referenced string literals and large constants anchor unambiguous pairs.
5. **Pass 4 (Call-Graph Propagation)**: Fixed-point propagation expanding from confirmed anchors to match neighboring callers and callees.
6. **Pass 5 (Global Hungarian Assignment)**: Weighted similarity matrix evaluated via `scipy.optimize.linear_sum_assignment` across mnemonic histograms, Weisfeiler-Lehman subtree kernels, and BinDiff MD-indices. Unmatched functions falling below threshold are rejected rather than forced.

---

## 4. Headline Empirical Results

Evaluated across **16 stripped release variants** of `zlib` (1.2.11 vs 1.2.12, fixing CVE-2018-25032) and `cJSON` (1.7.11 vs 1.7.12, fixing CVE-2019-1010239):

### Real Security Patch Localization (Top-k Hit Rate)
| Benchmark & Target | Variant | Stripped | Total Changed Funcs | Patched Function | Best Rank | Top-1 | Top-5 | Top-10 |
|---|---|:---:|---:|---|---:|:---:|:---:|:---:|
| **cJSON (CVE-2019-1010239)** | gcc-O0 | Yes | 1 | `cJSON_Minify` | **#1** | **YES** | **YES** | **YES** |
| **cJSON (CVE-2019-1010239)** | gcc-O2 | Yes | 1 | `cJSON_Minify` | **#1** | **YES** | **YES** | **YES** |
| **cJSON (CVE-2019-1010239)** | clang-O2 | Yes | 5 | `cJSON_Minify` | **#1** | **YES** | **YES** | **YES** |
| **zlib (CVE-2018-25032)** | gcc-O0 | Yes | 56 | `deflateInit2_` | **#1** | **YES** | **YES** | **YES** |
| **zlib (CVE-2018-25032)** | gcc-O2 | Yes | 54 | `deflate_slow` | **#4** | no | **YES** | **YES** |
| **zlib (CVE-2018-25032)** | gcc-O3 | Yes | 54 | `deflate_slow` | **#3** | no | **YES** | **YES** |
| **zlib (CVE-2018-25032)** | clang-O2 | Yes | 54 | `deflatePrime` | **#8** | no | no | **YES** |

- **cJSON CVE-2019-1010239**: **100% Top-1 hit rate** across all compiler and optimization variants.
- **zlib CVE-2018-25032**: **100% Top-10 hit rate** and **75% Top-5 hit rate** across all variants.

### Baseline Noise Comparison: Naive `objdump` Diff vs. PatchLens
- **Naive `objdump -d` diff**: Produced **30,867 lines of raw textual diff** with a ~99.8% false-positive noise ratio due to instruction offset shifts.
- **PatchLens**: Filtered 30,867 noisy lines down to **54 semantic function diffs**, immediately placing the true patch into the Top 4.

---

## 5. Security & Threat Model

PatchLens adheres to a **Zero-Code-Execution Invariant**:
- Target ELF binaries are **never executed** (`no execve`, `no dlopen`, `no ptrace`).
- Binaries are parsed strictly as inert byte streams using `pyelftools` and disassembled using Capstone in user memory.
- Enforces strict input validation: `\x7fELF` magic header check, 50MB maximum file size limit, and UUID file isolation to prevent path traversal.
- Full threat model details are documented in [`docs/security.md`](docs/security.md).

---

## 6. Design Decisions & Trade-Offs

1. **RoleRegisterStrategy vs Exact Registers**:
   - *Trade-off*: Discarding physical register names reduces discriminative power slightly within identical compiler builds, but boosts cross-compiler matching F1 significantly by absorbing GCC vs Clang register selection differences.
2. **Dual-Mode Worker Architecture**:
   - *Trade-off*: Running Redis+RQ in Docker ensures scalability across multiple worker nodes, while the built-in `ProcessPoolQueue` fallback provides instant, zero-dependency local developer execution without running external Redis daemons.
3. **Threshold Rejection in Hungarian Matching**:
   - *Trade-off*: Setting a minimum similarity floor (0.35) means inlined functions are reported as "removed" rather than matched to arbitrary dissimilar functions. This prevents false positive diffs from polluting the security ranking.
4. **Pre-Seeded Sample Analyses**:
   - *Trade-off*: Storing pre-computed sample analyses in the database adds ~150KB to the SQLite file, but provides instantaneous sub-second demo walkthroughs for end users.

---

## 7. Known Limitations

- **Architecture Support**: Currently targets x86-64 ELF binaries. Architecture abstraction hooks exist for ARM64 and MIPS.
- **Aggressive Inlining**: Functions inlined at `-O3` cannot be recovered as separate entities; their changes are detected within their parent caller.
- See [`docs/limitations.md`](docs/limitations.md) for full documentation of edge cases.

---

## 8. Developer & Author

**Sumanshu Jindal**
- **GitHub**: [@Sumanshu01](https://github.com/Sumanshu01)
- **Repository**: [https://github.com/Sumanshu01/PatchLens](https://github.com/Sumanshu01/PatchLens)

---

## 9. License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
Copyright (c) 2026 Sumanshu Jindal.

