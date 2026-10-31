import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import React from "react";
import { UploadView } from "../components/UploadView";

// Mock API
vi.mock("../api", () => ({
  getSampleCases: vi.fn().mockResolvedValue([
    {
      id: "zlib-cve-2018-25032",
      title: "zlib 1.2.11 -> 1.2.12 (CVE-2018-25032)",
      description: "Test CVE",
      cve: "CVE-2018-25032",
      binary_a_name: "libz-1.2.11.so",
      binary_b_name: "libz-1.2.12.so",
      pair_hash: "hash",
      result_id: 1,
    },
  ]),
  uploadBinary: vi.fn(),
  startAnalysis: vi.fn(),
}));

describe("UploadView component", () => {
  it("renders upload zones and sample buttons", async () => {
    render(<UploadView onAnalysisStarted={vi.fn()} onSampleSelected={vi.fn()} />);

    expect(screen.getByText(/Pinpoint Security Patches/i)).toBeInTheDocument();
    expect(screen.getByText(/1. Baseline Binary/i)).toBeInTheDocument();
    expect(screen.getByText(/2. Patched Binary/i)).toBeInTheDocument();
    expect(await screen.findByText(/zlib 1.2.11 -> 1.2.12/i)).toBeInTheDocument();
  });
});

