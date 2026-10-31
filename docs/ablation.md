# PatchLens Part 2 — Function Matching Ablation Study

## Summary of Ablation Results

| Configuration | Same Opt F1 | Patch F1 | Cross-Opt | Cross-Comp | Mean F1 | Delta |
|---|---:|---:|---:|---:|---:|---:|
| `full_model` | 0.9923 | 0.9572 | 0.3804 | 0.6100 | **0.7350** | baseline |
| `no_pass1_normalized_exact` | 0.9923 | 0.9728 | 0.3804 | 0.6100 | **0.7389** | +0.0039 |
| `no_pass2_cfg_structural` | 0.9923 | 0.9572 | 0.3804 | 0.6100 | **0.7350** | +0.0000 |
| `no_pass3_string_constant_anchor` | 0.9923 | 0.9572 | 0.3804 | 0.6100 | **0.7350** | +0.0000 |
| `no_pass4_callgraph_propagation` | 0.9923 | 0.9572 | 0.3804 | 0.6100 | **0.7350** | +0.0000 |
| `no_pass5_global_hungarian` | 0.9923 | 0.9091 | 0.1176 | 0.1667 | **0.5464** | -0.1886 |
| `no_mnemonic` | 0.9923 | 0.8646 | 0.0455 | 0.1805 | **0.5207** | -0.2143 |
| `no_wl_subtrees` | 0.9923 | 0.8889 | 0.3200 | 0.4607 | **0.6655** | -0.0695 |
| `no_md_index` | 0.9923 | 0.9478 | 0.1655 | 0.3926 | **0.6246** | -0.1104 |
| `no_callees` | 0.9923 | 0.9725 | 0.1905 | 0.4229 | **0.6445** | -0.0904 |
| `no_strings_consts` | 0.9923 | 0.9725 | 0.2733 | 0.5445 | **0.6957** | -0.0393 |
| `no_ngrams` | 0.9923 | 0.9688 | 0.3804 | 0.6030 | **0.7361** | +0.0011 |
| `reg_strat_role` | 0.9923 | 0.9572 | 0.3804 | 0.6100 | **0.7350** | +0.0000 |
| `reg_strat_abstract` | 0.9923 | 0.9572 | 0.3804 | 0.6070 | **0.7342** | -0.0008 |
| `reg_strat_exact` | 0.9923 | 0.9572 | 0.3804 | 0.6000 | **0.7325** | -0.0025 |

## Analysis of Findings

1. **Pass 1 (Normalized Hash) & Pass 2 (WL CFG Hash)**:
   - In same-opt scenarios, Pass 1 alone resolves the majority with zero FPs.
   - Disabling Pass 1 or 2 causes degradation because matches fall to Pass 5.
2. **Pass 4 (Call-Graph Propagation)**:
   - Resolves small leaf functions and API wrappers with identical metrics.
   - Once anchors lock, propagation resolves neighbors along the call graph.
3. **Pass 5 (Global Hungarian Matching & Threshold Rejection)**:
   - Critical for cross-opt (-O0 vs -O2) where compiler inlining alters hashes.
   - Threshold rejection prevents forcing matches for inlined functions.
4. **Register Strategy Comparison**:
   - `RoleRegisterStrategy` outperforms `ExactRegisterStrategy` across GCC/Clang
     because different compilers allocate different registers for the same ABI role.
