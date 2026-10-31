# Blog Post Outline: How We Built PatchLens — Automated Security Patch Localization in Stripped Binaries

## Working Title
**Hunting Vulnerabilities from the Assembly: How PatchLens Pinpoints Security Patches in Stripped Binaries**

---

## 1. Introduction: The N-Day Patch Analysis Problem
- **The Hook**: When a vendor releases a patch without a detailed changelog or CVE write-up, security researchers race to reverse engineer the binary to discover what vulnerability was fixed (1-day analysis).
- **The Challenge**: Release binaries are stripped of debug symbols and function names. Compilers reorder instructions, inline procedures, and change register allocations. Naive textual diffing (`objdump -d` diff) yields 30,000+ lines of pure false-positive address churn.
- **The Thesis**: By combining Weisfeiler-Lehman graph kernels, BinDiff-style topological invariants, and specialized security check detectors, PatchLens cuts through compiler noise and ranks true patch functions directly into the Top 1 to 5.

---

## 2. Foundations: Parsing and CFG Reconstruction
- ELF structure parsing with `pyelftools` and byte disassembly via Capstone.
- Why recursive descent seeded by calls and entry points beats linear sweep for complex jump patterns.
- Reconstructing Control Flow Graphs (CFG) with typed edges: fallthrough, conditional true/false, unconditional jumps, and call branches.
- Handling stripped binaries: discovering prologue heuristics (`push rbp; mov rbp, rsp`) and resolving indirect calls.

---

## 3. The Matching Ladder: How PatchLens Pairs Functions
- **Instruction Normalization**:
  - Masking memory addresses, relative jumps, and large immediates while preserving semantically meaningful small constants.
  - The `RegisterStrategy` abstraction: why `RoleRegisterStrategy` (mapping registers by ABI role: args, return, callee-saved) outperforms exact matching across GCC and Clang.
- **Multi-Pass Confidence Architecture**:
  - Pass 0: Exact symbol names (evaluation ground truth only).
  - Pass 1: Identical normalized instruction sequence hashes.
  - Pass 2: Weisfeiler-Lehman CFG graph hash + identical callee set.
  - Pass 3: Unique string and constant anchors.
  - Pass 4: Fixed-point call-graph neighborhood propagation.
  - Pass 5: Global Hungarian assignment (`scipy.optimize.linear_sum_assignment`) with threshold rejection to prevent forced false matches.

---

## 4. Turning Diffs into Security Findings
- **Cosmetic vs Semantic Classification**: Filtering out register re-allocations and block re-orderings that don't alter logic.
- **Automated Security Check Detectors**:
  - *Added Bounds Check*: New comparison and conditional jump guarding memory access or call.
  - *Added NULL / Error Check*: Pointer validation guarding an error exit path.
  - *Integer Width / Signedness Change*: Register width promotions (`movsxd`) or unsigned comparisons (`jb` vs `jl`).
  - *Replaced Unsafe Calls*: Replacing dangerous APIs (`strcpy` -> `strncpy`).
  - *New Early Exit*: Fast-return logic escaping buffer manipulation loops.
- **Composite Suspiciousness Ranking**: Balancing semantic delta, security pattern density, and call-graph centrality.

---

## 5. Empirical Validation: Proving It on Real CVEs
- **Case Study 1: zlib 1.2.11 -> 1.2.12 (CVE-2018-25032)**:
  - 100% Top-10 hit rate across all 8 variants (-O0, -O2, -O3, GCC, Clang).
  - Honest failure analysis: why full release maintenance edits (`gz_comp`) introduce competing noise and how centrality mitigates it.
- **Case Study 2: cJSON 1.7.11 -> 1.7.12 (CVE-2019-1010239)**:
  - 100% Top-1 hit rate in all 6 variants; `cJSON_Minify` ranks #1 on stripped binaries.
- **Baseline Comparison**:
  - Naive `objdump` diff: 30,867 diff lines vs PatchLens: 54 ranked semantic functions.

---

## 6. The Full-Stack Demo Architecture
- FastAPI asynchronous backend with process-isolated sandboxing and SQLite/Alembic persistence.
- React 18 + Vite + Cytoscape.js web frontend with side-by-side synchronized CFGs, unified instruction diffs, and Match Explorer call graphs.
- Sub-second instant demo loads from pre-seeded SHA-256 result cache.

---

## 7. Key Takeaways & What's Next
- Binary diffing is an interplay between graph invariants and compiler normalization.
- Future roadmap: adding ARM64 architecture support, LLVM IR lifted diffing, and Ghidra plugin interoperability.

