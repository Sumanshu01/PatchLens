import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import React from "react";
import { MemoryRouter, Routes, Route, useLocation } from "react-router-dom";
import { LandingPage } from "../pages/LandingPage";

// Helper component to display current route location for testing router transitions
const LocationDisplay: React.FC = () => {
  const location = useLocation();
  return (
    <div data-testid="location-display">
      {location.pathname}
      {location.search}
    </div>
  );
};

describe("LandingPage component", () => {
  it("renders the hero heading, tagline, and navigation sections", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <LandingPage />
      </MemoryRouter>
    );

    expect(
      screen.getByRole("heading", { name: /Pinpoint Security Patches in Stripped Binaries/i })
    ).toBeInTheDocument();
    expect(screen.getByText(/Automated 1-Day Vulnerability Patch Localization/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Problem & Solution/i })).toBeInTheDocument();
    expect(screen.getByText(/CFG Fingerprinting/i)).toBeInTheDocument();
    expect(screen.getByText(/Multi-Pass Matching Ladder/i)).toBeInTheDocument();
    expect(screen.getByText(/Headline Accuracy on Real CVE Fixes/i)).toBeInTheDocument();
  });

  it("has primary and secondary CTA links with correct target attributes", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <LandingPage />
      </MemoryRouter>
    );

    // Primary CTA buttons (both navbar and hero)
    const launchButtons = screen.getAllByRole("link", { name: /Launch Analyzer/i });
    expect(launchButtons.length).toBeGreaterThanOrEqual(2);
    launchButtons.forEach((btn) => {
      expect(btn).toHaveAttribute("href", "/analyze");
    });

    // Secondary CTA button for CVE sample
    const sampleCta = screen.getByRole("link", { name: /Try CVE-2018-25032 sample/i });
    expect(sampleCta).toBeInTheDocument();
    expect(sampleCta).toHaveAttribute("href", "/analyze?sample=zlib-cve-2018-25032");
  });

  it("navigates to /analyze when primary 'Launch Analyzer' CTA is clicked", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route
            path="/analyze"
            element={
              <div>
                <h1>Analyzer View</h1>
                <LocationDisplay />
              </div>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    // Click the hero CTA
    const heroLaunchBtn = screen.getAllByRole("link", { name: /Launch Analyzer/i })[1];
    fireEvent.click(heroLaunchBtn);

    expect(screen.getByRole("heading", { name: "Analyzer View" })).toBeInTheDocument();
    expect(screen.getByTestId("location-display")).toHaveTextContent("/analyze");
  });

  it("navigates to /analyze?sample=zlib-cve-2018-25032 when secondary CTA is clicked", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route
            path="/analyze"
            element={
              <div>
                <h1>Analyzer View</h1>
                <LocationDisplay />
              </div>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    const sampleBtn = screen.getByRole("link", { name: /Try CVE-2018-25032 sample/i });
    fireEvent.click(sampleBtn);

    expect(screen.getByRole("heading", { name: "Analyzer View" })).toBeInTheDocument();
    expect(screen.getByTestId("location-display")).toHaveTextContent(
      "/analyze?sample=zlib-cve-2018-25032"
    );
  });
});
