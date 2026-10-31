import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import React from "react";
import { MemoryRouter } from "react-router-dom";
import { Navbar } from "../components/Navbar";

describe("Navbar component", () => {
  it("renders PatchLens brand title and version", () => {
    render(
      <MemoryRouter>
        <Navbar onNewAnalysis={vi.fn()} hasResult={false} />
      </MemoryRouter>
    );
    expect(screen.getByText("PatchLens")).toBeInTheDocument();
    expect(screen.getByText("v0.1.0")).toBeInTheDocument();
    expect(screen.getByText("Engine Ready")).toBeInTheDocument();
  });

  it("shows New Analysis button only when hasResult is true", () => {
    const { rerender } = render(
      <MemoryRouter>
        <Navbar onNewAnalysis={vi.fn()} hasResult={false} />
      </MemoryRouter>
    );
    expect(screen.queryByText("+ New Analysis")).not.toBeInTheDocument();

    rerender(
      <MemoryRouter>
        <Navbar onNewAnalysis={vi.fn()} hasResult={true} />
      </MemoryRouter>
    );
    expect(screen.getByText("+ New Analysis")).toBeInTheDocument();
  });
});
