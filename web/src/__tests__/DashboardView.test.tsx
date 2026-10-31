import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import React from "react";
import { DashboardView } from "../components/DashboardView";
import { AnalysisResult } from "../types";

vi.mock("@tanstack/react-virtual", () => ({
  useVirtualizer: (opts: any) => ({
    getTotalSize: () => opts.count * 58,
    getVirtualItems: () =>
      Array.from({ length: opts.count }).map((_, i) => ({
        index: i,
        start: i * 58,
        size: 58,
      })),
  }),
}));

const mockResult: AnalysisResult = {
  id: 1,
  job_id: "test-job",
  pair_hash: "abcd1234abcd1234",
  summary: {
    total_functions_a: 100,
    total_functions_b: 102,
    matched_count: 98,
    unmatched_a_count: 2,
    unmatched_b_count: 4,
    identical_count: 80,
    changed_cosmetic_count: 8,
    changed_semantic_count: 10,
    top_patch_candidates_count: 5,
  },
  ranked_diffs: [
    {
      rank: 1,
      patch_score: 1.25,
      classification: "changed-semantic",
      addr_a: 0x1000,
      addr_b: 0x2000,
      name_a: "vuln_func",
      name_b: "fixed_func",
      similarity: 0.75,
      matched_pass: "pass2_cfg_structural",
      confidence: 0.9,
      security_tags: [
        {
          tag_type: "added_bounds_check",
          description: "Added bounds check on buffer",
          confidence: 0.95,
          block_ids_a: [0x1000],
          block_ids_b: [0x2000],
          evidence: "cmp rdi, 100",
        },
      ],
      block_diffs_count: 3,
      snippet_diff: "--- bb_0x1000\n+++ bb_0x2000\n@@ -1 +1 @@\n-nop\n+cmp rdi, 100",
    },
  ],
  callgraph: { nodes: [], edges: [] },
};

describe("DashboardView component", () => {
  it("renders summary cards and functions table", () => {
    render(
      <DashboardView
        result={mockResult}
        onSelectFunction={vi.fn()}
        onToggleCallGraph={vi.fn()}
        showCallGraph={false}
      />
    );

    expect(screen.getByText("Diff Results & Security Localization")).toBeInTheDocument();
    expect(screen.getByText("Semantic Changes")).toBeInTheDocument();
    expect(screen.getByText("10")).toBeInTheDocument();
    expect(screen.getByText("vuln_func")).toBeInTheDocument();
    expect(screen.getByText("fixed_func")).toBeInTheDocument();
  });
});

