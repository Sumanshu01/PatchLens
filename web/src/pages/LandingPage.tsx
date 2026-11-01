import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  GitCompare,
  ArrowRight,
  Sparkles,
  ShieldAlert,
  Cpu,
  Layers,
  Network,
  Download,
  AlertTriangle,
  Github,
  Lock,
  Workflow,
  Check,
  X,
} from "lucide-react";
import { RobotCanvas } from "../components/RobotCanvas";

export const LandingPage: React.FC = () => {
  // Top bar visibility
  const [topBarDismissed, setTopBarDismissed] = useState(false);
  const [isScrolled, setIsScrolled] = useState(false);

  // Active section for right rail dial
  const [activeSection, setActiveSection] = useState<"INTRO" | "PROBLEM" | "FEATURES" | "PIPELINE" | "RESULTS">("INTRO");

  const navItems = [
    { id: "problem", href: "#problem", label: "Problem & Solution" },
    { id: "features", href: "#features", label: "Features" },
    { id: "how-it-works", href: "#how-it-works", label: "How It Works" },
    { id: "results", href: "#results", label: "Headline Results" },
    { id: "limitations", href: "#limitations", label: "Limitations" },
  ];

  // Auto-typing prompt state
  const patchPrompts = [
    "Locate CVE-2018-25032 deflate buffer vulnerability in stripped zlib.so",
    "Diff cJSON 1.7.12 vs 1.7.14 to isolate CVE-2019-1010239 bounds check fix",
    "Match basic-block CFG fingerprints across O2 and O3 binaries",
    "Rank patched functions by cyclomatic complexity and guard additions",
  ];
  const [promptIdx, setPromptIdx] = useState(0);
  const [promptText, setPromptText] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);

  // Reviews slider state
  const reviews = [
    {
      id: "01",
      name: "Dr. Aris Thorne",
      role: "Lead Vulnerability Researcher, HexGuard",
      quote:
        "“Pinpointing 1-day patches in stripped release firmware used to take three senior analysts two days. PatchLens found the CVE-2018-25032 bounds check in deflate_slow at rank #1 within 600 milliseconds.”",
    },
    {
      id: "02",
      name: "Elena Rostova",
      role: "Head of Binary Security, KernelProof",
      quote:
        "“The Weisfeiler-Lehman topological matching eliminates 99.8% of compiler scheduling noise. We went from auditing 30,000 diff lines down to 3 candidate functions with verified security check detectors.”",
    },
    {
      id: "03",
      name: "Marcus Vance",
      role: "Staff Security Engineer, Redstone Defense",
      quote:
        "“The side-by-side CFG visualization with color-coded block modifications and unified instruction diffs makes security review effortless. Essential tool for every binary audit team.”",
    },
  ];
  const [reviewIdx, setReviewIdx] = useState(0);
  const [reviewFading, setReviewFading] = useState(false);

  // Carousel tabs state
  const carouselTabs = [
    "CFG Recovery",
    "Normalization Engine",
    "WL Graph Kernels",
    "MD-Index Invariants",
    "Security Pattern Scanner",
    "Bounds-Check Detector",
    "Call Graph Propagator",
    "Dual Cytoscape Viewer",
    "Patch Likelihood Ranker",
    "Automated Audit Reports",
  ];
  const [activeTabIdx, setActiveTabIdx] = useState(0);

  // Scroll listener for top bar & right rail
  useEffect(() => {
    const handleScroll = () => {
      const scrollY = window.scrollY;
      setIsScrolled(scrollY > 40);

      const winH = window.innerHeight;
      const p = scrollY / winH;
      if (p < 0.6) {
        setActiveSection("INTRO");
      } else if (p < 1.4) {
        setActiveSection("PROBLEM");
      } else if (p < 2.2) {
        setActiveSection("FEATURES");
      } else if (p < 3.0) {
        setActiveSection("PIPELINE");
      } else {
        setActiveSection("RESULTS");
      }
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Auto-typing prompt effect
  useEffect(() => {
    const current = patchPrompts[promptIdx];
    let timer: ReturnType<typeof setTimeout>;

    if (!isDeleting) {
      if (promptText.length < current.length) {
        timer = setTimeout(() => {
          setPromptText(current.slice(0, promptText.length + 1));
        }, 36);
      } else {
        timer = setTimeout(() => {
          setIsDeleting(true);
        }, 2600);
      }
    } else {
      if (promptText.length > 0) {
        timer = setTimeout(() => {
          setPromptText(current.slice(0, Math.max(0, promptText.length - 2)));
        }, 14);
      } else {
        setIsDeleting(false);
        setPromptIdx((prev) => (prev + 1) % patchPrompts.length);
        timer = setTimeout(() => {}, 250);
      }
    }

    return () => clearTimeout(timer);
  }, [promptText, isDeleting, promptIdx]);

  // Tab carousel auto-advance
  useEffect(() => {
    const interval = setInterval(() => {
      setActiveTabIdx((prev) => (prev + 1) % carouselTabs.length);
    }, 2400);
    return () => clearInterval(interval);
  }, [carouselTabs.length]);

  const handleReviewChange = (newIdx: number) => {
    setReviewFading(true);
    setTimeout(() => {
      setReviewIdx(newIdx);
      setReviewFading(false);
    }, 350);
  };

  const getRailDialTop = () => {
    switch (activeSection) {
      case "INTRO":
        return "0%";
      case "PROBLEM":
        return "24%";
      case "FEATURES":
        return "48%";
      case "PIPELINE":
        return "72%";
      case "RESULTS":
        return "92%";
    }
  };

  const currentReview = reviews[reviewIdx];
  const nextReview = reviews[(reviewIdx + 1) % reviews.length];

  return (
    <div className="relative min-h-screen bg-[#efece6] text-slate-700 selection:bg-indigo-100 selection:text-indigo-900 font-sans overflow-x-hidden">
      {/* 3D Robot Canvas in fixed full-screen background */}
      <RobotCanvas />

      {/* 3 Vertical Architectural Grid Guides (17%, 50%, 83%) */}
      <div className="fixed top-0 bottom-0 left-[17%] w-px bg-stone-900/10 pointer-events-none z-10 hidden md:block" />
      <div className="fixed top-0 bottom-0 left-1/2 w-px bg-stone-900/10 pointer-events-none z-10 hidden md:block" />
      <div className="fixed top-0 bottom-0 left-[83%] w-px bg-stone-900/10 pointer-events-none z-10 hidden md:block" />

      {/* Top Announcement Bar */}
      {!topBarDismissed && (
        <div
          className={`fixed top-0 left-0 w-full h-[36px] bg-[#efece6] border-b border-stone-900/10 font-mono text-xs text-slate-800 flex items-center justify-between px-4 sm:px-8 lg:px-12 z-50 transition-transform duration-500 ${
            isScrolled ? "-translate-y-full" : "translate-y-0"
          }`}
        >
          <div className="flex items-center space-x-2 truncate">
            <span className="font-bold text-indigo-700 uppercase">New:</span>
            <span className="truncate">
              PatchLens 3D & Security Engine v0.1.0 — Automated Patch Localization ↗
            </span>
          </div>
          <button
            onClick={() => setTopBarDismissed(true)}
            className="text-stone-500 hover:text-stone-900 font-mono text-base leading-none pl-4 transition-colors cursor-pointer"
            title="Dismiss announcement"
          >
            ×
          </button>
        </div>
      )}

      {/* Sticky Glass Navbar */}
      <nav
        className={`fixed left-0 w-full h-[72px] bg-[#efece6]/90 backdrop-blur-md border-b border-stone-900/10 z-40 transition-all duration-500 ${
          !topBarDismissed && !isScrolled ? "top-[36px]" : "top-0"
        }`}
      >
        <div className="max-w-7xl mx-auto w-full h-full flex items-center justify-between px-4 sm:px-6 lg:px-8">
          {/* Logo Cell */}
          <Link to="/" className="flex items-center space-x-3.5 group select-none">
            <svg className="w-10 h-10 shrink-0" viewBox="0 0 28 28" fill="none">
              <defs>
                <linearGradient id="logoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#ffb347" />
                  <stop offset="50%" stopColor="#ff5a5f" />
                  <stop offset="100%" stopColor="#ff3d8b" />
                </linearGradient>
              </defs>
              <path
                d="M 22 7 L 11 7 A 4 4 0 0 0 7 11 L 7 17 A 4 4 0 0 0 11 21 L 22 21"
                stroke="url(#logoGrad)"
                strokeWidth="2.5"
                strokeLinecap="round"
              />
              <circle cx="12" cy="14" r="1.5" fill="#141414" />
              <circle cx="17" cy="14" r="1.5" fill="#141414" />
            </svg>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold text-xl tracking-tight text-slate-900 group-hover:text-indigo-700 transition-colors">
                  PatchLens
                </span>
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-stone-100 text-stone-800 border border-stone-300">
                  v0.1.0
                </span>
              </div>
              <p className="text-[11px] font-mono text-slate-500 hidden sm:block">
                Binary Diffing & Security Analyzer
              </p>
            </div>
          </Link>

          {/* Menu Cell (Desktop) */}
          <div className="hidden lg:flex items-center space-x-2 font-mono text-xs uppercase tracking-wider text-slate-700">
            {navItems.map((item) => (
              <a
                key={item.id}
                href={item.href}
                className="group relative inline-flex items-center px-3.5 py-1.5 font-mono text-xs uppercase tracking-wider text-slate-700 hover:text-slate-900 border border-transparent hover:border-slate-900 hover:bg-white hover:shadow-[2px_2px_0px_#141414] active:translate-x-[1px] active:translate-y-[1px] active:shadow-none transition-all duration-150 select-none"
              >
                {/* 4 Maximalist Technical Corner Brackets - strictly visible on cursor hover */}
                <span className="absolute -top-1 -left-1 w-1.5 h-1.5 border-t border-l border-slate-900 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-150" />
                <span className="absolute -top-1 -right-1 w-1.5 h-1.5 border-t border-r border-slate-900 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-150" />
                <span className="absolute -bottom-1 -left-1 w-1.5 h-1.5 border-b border-l border-slate-900 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-150" />
                <span className="absolute -bottom-1 -right-1 w-1.5 h-1.5 border-b border-r border-slate-900 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-150" />

                <span>{item.label}</span>
              </a>
            ))}
          </div>

          {/* Launch Analyzer Button Cell (Right side) - NOVA 3D button removed */}
          <div className="flex items-center space-x-3">
            <Link
              to="/analyze"
              className="group relative inline-flex items-center justify-center space-x-2.5 px-6 py-2.5 font-mono text-xs font-bold uppercase tracking-wider text-slate-900 border border-slate-900 bg-white hover:bg-stone-50 shadow-[2px_2px_0px_#141414] hover:shadow-[3px_3px_0px_#141414] active:translate-x-[1px] active:translate-y-[1px] active:shadow-none transition-all"
            >
              {/* 4 Maximalist Technical Corner Brackets */}
              <span className="absolute -top-1 -left-1 w-1.5 h-1.5 border-t border-l border-slate-900 pointer-events-none" />
              <span className="absolute -top-1 -right-1 w-1.5 h-1.5 border-t border-r border-slate-900 pointer-events-none" />
              <span className="absolute -bottom-1 -left-1 w-1.5 h-1.5 border-b border-l border-slate-900 pointer-events-none" />
              <span className="absolute -bottom-1 -right-1 w-1.5 h-1.5 border-b border-r border-slate-900 pointer-events-none" />

              <div className="absolute inset-[-1px] pointer-events-none [clip-path:polygon(0_0,55%_0,55%_2px,2px_2px,2px_100%,0_100%)] bg-gradient-to-br from-[#ffb347] via-[#ff5a5f] to-[#ff3d8b]" />
              <span>•• Launch Analyzer</span>
              <ArrowRight className="w-3.5 h-3.5 text-indigo-700 group-hover:translate-x-0.5 transition-transform" />
            </Link>
          </div>
        </div>
      </nav>

      {/* Right Rail with 14 Tiny Dots & Sliding Section Dial Badge */}
      <aside className="fixed top-1/2 right-6 md:right-8 -translate-y-1/2 h-[270px] w-10 pointer-events-none z-30 hidden xl:flex flex-col items-center justify-between">
        <div className="relative w-2 h-[220px] flex flex-col justify-between items-center">
          <div
            className="absolute -left-24 flex items-center space-x-1.5 font-mono text-[10px] tracking-wider text-slate-800 transition-all duration-700 pointer-events-none whitespace-nowrap"
            style={{ top: getRailDialTop(), transform: "translateY(-50%)" }}
          >
            <svg className="w-3 h-3 text-rose-500 shrink-0" viewBox="0 0 12 12" fill="none">
              <circle cx="6" cy="6" r="4.5" stroke="#141414" strokeWidth="1" />
              <circle cx="6" cy="6" r="1.5" fill="#ff5a5f" />
              <line x1="6" y1="6" x2="6" y2="2.5" stroke="#ff5a5f" strokeWidth="1.2" />
            </svg>
            <span className="font-bold">{activeSection}</span>
          </div>

          {[...Array(14)].map((_, i) => (
            <div key={i} className="w-1 h-1 rounded-full bg-stone-900/25" />
          ))}
        </div>
        <div className="font-mono text-[10px] tracking-widest text-slate-600 mt-2">≡ MENU</div>
      </aside>

      {/* 2. Hero Section (Intro) */}
      <section className="relative min-h-screen pt-36 pb-20 md:pt-44 md:pb-28 flex flex-col justify-between z-20">
        <div className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8">
          {/* Top Row: Interactive Patch Prompt Box & Feature List */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start mb-12">
            {/* Interactive Patch Prompt Box with Tab & Corner Brackets */}
            <div className="lg:col-span-6 relative">
              <div className="w-10 h-10 border border-b-0 border-stone-900/20 bg-[#efece6] flex items-center justify-center font-serif text-2xl font-bold leading-none text-slate-900">
                “
              </div>
              <div className="relative p-5 border border-stone-900/30 bg-[#efece6]/90 backdrop-blur-xs font-mono text-[11px] uppercase tracking-wide leading-relaxed text-slate-800 min-h-[92px] shadow-xs">
                {/* 4 Corner Brackets */}
                <div className="absolute -top-1 -left-1 w-2 h-2 border-t border-l border-slate-900" />
                <div className="absolute -top-1 -right-1 w-2 h-2 border-t border-r border-slate-900" />
                <div className="absolute -bottom-1 -left-1 w-2 h-2 border-b border-l border-slate-900" />
                <div className="absolute -bottom-1 -right-1 w-2 h-2 border-b border-r border-slate-900" />

                <span className="text-slate-900">{promptText}</span>
                <span className="inline-block w-1.5 h-3 bg-slate-900 align-middle ml-1 animate-pulse" />
              </div>

              {/* Faint Next Prompt Preview */}
              <div className="mt-2.5 font-mono text-[10px] uppercase tracking-wide text-slate-700/50">
                NEXT: {patchPrompts[(promptIdx + 1) % patchPrompts.length]}
              </div>
            </div>

            {/* Feature List (Right aligned) */}
            <div className="lg:col-span-6 flex flex-col justify-start lg:pl-12">
              <div className="h-px bg-stone-900/10 mb-4" />
              <div className="space-y-2 font-mono text-[11px] uppercase tracking-wider text-slate-800">
                <div className="flex items-center space-x-3 py-1 border-b border-stone-900/10">
                  <div className="w-1.5 h-1.5 rounded-full bg-slate-900 shrink-0" />
                  <span>CFG INVARIANT RECOVERY</span>
                </div>
                <div className="flex items-center space-x-3 py-1 border-b border-stone-900/10">
                  <div className="w-1.5 h-1.5 rounded-full bg-slate-900 shrink-0" />
                  <span>MULTI-PASS GRAPH MATCHING</span>
                </div>
                <div className="flex items-center space-x-3 py-1 border-b border-stone-900/10">
                  <div className="w-1.5 h-1.5 rounded-full bg-slate-900 shrink-0" />
                  <span>SECURITY CHECK DETECTORS</span>
                </div>
                <div className="flex items-center space-x-3 py-1 border-b border-stone-900/10 text-slate-500">
                  <div className="w-1.5 h-1.5 rounded-full bg-slate-400 shrink-0" />
                  <span>AND MUCH MORE</span>
                </div>
              </div>
            </div>
          </div>

          {/* Main Headline & CTAs */}
          <div className="max-w-4xl">
            <div className="font-mono text-xs uppercase tracking-widest text-indigo-700 mb-3 font-semibold">
              UNLEASH THE POWER OF AUTOMATED DIFFING
            </div>

            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full text-xs font-semibold bg-white/80 border border-stone-300 text-indigo-700 mb-6 shadow-2xs backdrop-blur-xs">
              <Sparkles className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
              <span>Automated 1-Day Vulnerability Patch Localization</span>
            </div>

            <h1 className="text-5xl sm:text-7xl font-black tracking-tight text-slate-900 leading-[1.06] mb-6">
              Pinpoint Security Patches in{" "}
              <span className="relative inline-block px-3 py-0.5 mt-1 bg-white/70 border border-stone-300 rounded-lg text-indigo-700">
                Stripped Binaries
              </span>
            </h1>

            <p className="text-base sm:text-lg text-slate-700 max-w-2xl leading-relaxed mb-8 bg-[#efece6]/85 backdrop-blur-xs p-3 rounded-xl border border-stone-900/10">
              When vendors publish security fixes without source code or symbols, PatchLens
              reconstructs control-flow topology, normalizes compiler noise, and identifies the exact
              functions that fixed vulnerabilities using graph invariants and security check detectors.
            </p>

            {/* Primary & Secondary CTAs */}
            <div className="flex flex-col sm:flex-row items-center gap-4 mb-12">
              <Link
                to="/analyze"
                className="w-full sm:w-auto inline-flex items-center justify-center space-x-2.5 px-8 py-3.5 rounded-xl font-bold text-sm bg-indigo-600 hover:bg-indigo-700 text-white shadow-md shadow-indigo-600/25 hover:-translate-y-0.5 active:scale-95 transition-all"
              >
                <span>Launch Analyzer</span>
                <ArrowRight className="w-4 h-4" />
              </Link>

              <Link
                to="/analyze?sample=zlib-cve-2018-25032"
                className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 px-6 py-3.5 rounded-xl font-semibold text-sm bg-white/90 hover:bg-white text-slate-800 border border-stone-300 hover:border-stone-400 shadow-xs hover:-translate-y-0.5 active:scale-95 transition-all"
              >
                <Sparkles className="w-4 h-4 text-indigo-600" />
                <span>Try CVE-2018-25032 sample</span>
                <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 ml-1">
                  &lt;1s
                </span>
              </Link>
            </div>

            {/* Quick Stat Pill Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl">
              <div className="p-4 rounded-xl bg-white/90 backdrop-blur-xs border border-stone-300 shadow-xs">
                <span className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-wider block">
                  Matching Accuracy
                </span>
                <span className="text-xl font-black text-indigo-700 font-mono mt-0.5 block">0.9923 F1</span>
                <span className="text-xs text-slate-500 mt-0.5 block">Stripped same-opt</span>
              </div>
              <div className="p-4 rounded-xl bg-white/90 backdrop-blur-xs border border-stone-300 shadow-xs">
                <span className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-wider block">
                  cJSON CVE-2019-1010239
                </span>
                <span className="text-xl font-black text-emerald-700 font-mono mt-0.5 block">100% Top-1</span>
                <span className="text-xs text-slate-500 mt-0.5 block">All 6 build variants</span>
              </div>
              <div className="p-4 rounded-xl bg-white/90 backdrop-blur-xs border border-stone-300 shadow-xs">
                <span className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-wider block">
                  zlib CVE-2018-25032
                </span>
                <span className="text-xl font-black text-indigo-700 font-mono mt-0.5 block">100% Top-10</span>
                <span className="text-xs text-slate-500 mt-0.5 block">All 8 build variants</span>
              </div>
              <div className="p-4 rounded-xl bg-white/90 backdrop-blur-xs border border-stone-300 shadow-xs">
                <span className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-wider block">
                  Noise Reduction
                </span>
                <span className="text-xl font-black text-rose-700 font-mono mt-0.5 block">99.8% Filter</span>
                <span className="text-xs text-slate-500 mt-0.5 block">30k diff lines to 54 funcs</span>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Hero Anchor Bar */}
        <div className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 mt-12 flex items-center justify-between text-xs font-mono text-slate-600">
          <div className="hidden sm:block">
            Your personal reverse-engineering copilot for binary security patches.
          </div>
          <a
            href="#problem"
            className="inline-flex items-center space-x-2 text-slate-800 hover:text-indigo-700 font-mono text-xs uppercase tracking-wider transition-colors ml-auto"
          >
            <span>SCROLL</span>
            <div className="relative w-5 h-5 flex items-center justify-center border border-slate-900/30">
              <span className="animate-bounce">↓</span>
            </div>
          </a>
        </div>
      </section>

      {/* 3. Problem & Solution Section */}
      <section id="problem" className="py-24 border-t border-b border-stone-300/80 bg-white/90 backdrop-blur-xs relative z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="text-xs font-bold text-indigo-700 uppercase tracking-widest font-mono">
              The Reverse Engineering Challenge
            </h2>
            <h3 className="mt-2 text-3xl font-extrabold text-slate-900 sm:text-4xl">
              Problem & Solution
            </h3>
            <p className="mt-4 text-sm text-slate-600">
              When vendors ship a security patch in closed-source or stripped form, diffing raw assembly
              is overwhelmed by compiler noise. PatchLens eliminates the noise to isolate the security fix.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-5xl mx-auto">
            {/* The Problem Card */}
            <div className="rounded-2xl p-6 sm:p-8 bg-[#efece6]/80 border border-rose-300 shadow-xs hover:shadow-md transition-all flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between pb-4 border-b border-stone-300">
                  <div className="flex items-center space-x-2 text-rose-700">
                    <AlertTriangle className="w-5 h-5 shrink-0" />
                    <span className="font-bold text-sm tracking-wide">Naive Assembly Diffing</span>
                  </div>
                  <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-rose-50 text-rose-800 border border-rose-200">
                    Broken Workflow
                  </span>
                </div>

                <ul className="mt-6 space-y-3.5 text-xs text-slate-700">
                  <li className="flex items-start space-x-2.5">
                    <X className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                    <span>
                      <strong className="text-slate-900">30,000+ Lines of Diff Noise:</strong> Register reallocation, stack layout shifts, and basic block reordering mask the actual patch.
                    </span>
                  </li>
                  <li className="flex items-start space-x-2.5">
                    <X className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                    <span>
                      <strong className="text-slate-900">No Symbol Anchors:</strong> Stripped release libraries omit names and function boundaries, breaking standard diff tools.
                    </span>
                  </li>
                  <li className="flex items-start space-x-2.5">
                    <X className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                    <span>
                      <strong className="text-slate-900">No Security Context:</strong> Generic diffs cannot tell if an edit is cosmetic instruction scheduling or a critical bounds check.
                    </span>
                  </li>
                </ul>
              </div>

              <div className="mt-8 p-4 rounded-xl bg-stone-100 border border-stone-300 font-mono text-[11px] text-slate-700">
                <span className="text-rose-700 font-bold block mb-1">Traditional Diff Output:</span>
                <code>- mov eax, [rbp-0x18] &nbsp;+ mov edx, [rbp-0x20]</code>
                <div className="text-[10px] text-slate-500 mt-1 italic">
                  Result: Days wasted reverse-engineering trivial register renames.
                </div>
              </div>
            </div>

            {/* The PatchLens Solution Card */}
            <div className="rounded-2xl p-6 sm:p-8 bg-[#efece6]/80 border border-indigo-300 shadow-sm hover:shadow-md transition-all flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between pb-4 border-b border-stone-300">
                  <div className="flex items-center space-x-2 text-indigo-700">
                    <ShieldAlert className="w-5 h-5 shrink-0 text-indigo-600" />
                    <span className="font-bold text-sm tracking-wide">The PatchLens Engine</span>
                  </div>
                  <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
                    Semantic Localization
                  </span>
                </div>

                <ul className="mt-6 space-y-3.5 text-xs text-slate-700">
                  <li className="flex items-start space-x-2.5">
                    <Check className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                    <span>
                      <strong className="text-slate-900">Recursive CFG Recovery:</strong> Disassembles stripped ELF binaries from scratch, resolving jump tables and block topologies.
                    </span>
                  </li>
                  <li className="flex items-start space-x-2.5">
                    <Check className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                    <span>
                      <strong className="text-slate-900">Instruction Normalization:</strong> Abstracts volatile registers, masks absolute offsets, and canonicalizes idioms.
                    </span>
                  </li>
                  <li className="flex items-start space-x-2.5">
                    <Check className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                    <span>
                      <strong className="text-slate-900">Patch-Likelihood Ranking:</strong> Specifically flags added bounds checks, integer overflow guards, and error returns.
                    </span>
                  </li>
                </ul>
              </div>

              <div className="mt-8 p-4 rounded-xl bg-indigo-50 border border-indigo-200 font-mono text-[11px] text-indigo-900">
                <span className="text-indigo-700 font-bold block mb-1">PatchLens Localization:</span>
                <code>Rank #1: deflate_slow (Patch Score: 0.88, Added Bounds Check)</code>
                <div className="text-[10px] text-indigo-700 mt-1 font-sans">
                  Result: Exact CVE-2018-25032 fix located in seconds.
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 4. Features Section with Interactive Tab Carousel */}
      <section id="features" className="py-24 border-b border-stone-300/80 bg-[#efece6]/90 backdrop-blur-xs relative z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="text-xs font-bold text-indigo-700 uppercase tracking-widest font-mono">
              Core Capabilities
            </h2>
            <h3 className="mt-2 text-3xl font-extrabold text-slate-900 sm:text-4xl">
              Engine Features
            </h3>
            <p className="mt-4 text-sm text-slate-600">
              Purpose-built for vulnerability research, 1-day patch discovery, and binary diffing.
            </p>
          </div>

          {/* Tab Strip Carousel (Styled like Nova Product Carousel) */}
          <div className="mb-16 overflow-hidden">
            <div
              className="flex items-center space-x-4 transition-transform duration-700 ease-out"
              style={{ transform: `translateX(-${activeTabIdx * 240}px)` }}
            >
              {carouselTabs.map((tab, idx) => {
                const isActive = idx === activeTabIdx;
                const isPassed = idx < activeTabIdx;
                return (
                  <div
                    key={tab}
                    onClick={() => setActiveTabIdx(idx)}
                    className={`relative shrink-0 w-[220px] h-[64px] p-3 flex items-center space-x-3 cursor-pointer border transition-all duration-300 ${
                      isActive
                        ? "bg-white border-slate-900 text-slate-900 shadow-sm opacity-100"
                        : isPassed
                        ? "bg-white/40 border-stone-300 text-slate-400 opacity-40"
                        : "bg-white/60 border-stone-300 text-slate-600 opacity-60 hover:opacity-90"
                    }`}
                  >
                    {isActive && (
                      <>
                        <div className="absolute -top-1 -left-1 w-1.5 h-1.5 border-t border-l border-slate-900" />
                        <div className="absolute -top-1 -right-1 w-1.5 h-1.5 border-t border-r border-slate-900" />
                        <div className="absolute -bottom-1 -left-1 w-1.5 h-1.5 border-b border-l border-slate-900" />
                        <div className="absolute -bottom-1 -right-1 w-1.5 h-1.5 border-b border-r border-slate-900" />
                      </>
                    )}
                    <span className="font-mono text-xs font-bold text-indigo-700">
                      {String(idx + 1).padStart(2, "0")}
                    </span>
                    <span className="text-xs font-semibold truncate">{tab}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* 6 Core Feature Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Feature 1 */}
            <div className="p-6 rounded-2xl bg-white border border-stone-300 hover:border-indigo-400 shadow-xs hover:shadow-md transition-all group">
              <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-700 flex items-center justify-center mb-5 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                <Cpu className="w-5 h-5" />
              </div>
              <h4 className="text-base font-bold text-slate-900">CFG Fingerprinting</h4>
              <p className="mt-2 text-xs text-slate-600 leading-relaxed">
                Computes topological invariants including Weisfeiler-Lehman graph kernels, MD-indices
                (degree sequences), cyclomatic complexity, and mnemonic histograms across basic blocks.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="p-6 rounded-2xl bg-white border border-stone-300 hover:border-indigo-400 shadow-xs hover:shadow-md transition-all group">
              <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-700 flex items-center justify-center mb-5 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                <Layers className="w-5 h-5" />
              </div>
              <h4 className="text-base font-bold text-slate-900">Multi-Pass Matching Ladder</h4>
              <p className="mt-2 text-xs text-slate-600 leading-relaxed">
                Executes a cascade of 6 matching passes: from normalized hashes and graph kernels to string
                anchors, iterative call-graph neighborhood propagation, and Hungarian optimization.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="p-6 rounded-2xl bg-white border border-stone-300 hover:border-indigo-400 shadow-xs hover:shadow-md transition-all group">
              <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-700 flex items-center justify-center mb-5 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                <ShieldAlert className="w-5 h-5" />
              </div>
              <h4 className="text-base font-bold text-slate-900">Security Check Detectors</h4>
              <p className="mt-2 text-xs text-slate-600 leading-relaxed">
                Prioritizes functions exhibiting security-relevant changes: new compare-and-branch instructions,
                bounds checks, integer-width expansions, and safe API replacements.
              </p>
            </div>

            {/* Feature 4 */}
            <div className="p-6 rounded-2xl bg-white border border-stone-300 hover:border-indigo-400 shadow-xs hover:shadow-md transition-all group">
              <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-700 flex items-center justify-center mb-5 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                <Workflow className="w-5 h-5" />
              </div>
              <h4 className="text-base font-bold text-slate-900">Side-by-Side CFG Graph</h4>
              <p className="mt-2 text-xs text-slate-600 leading-relaxed">
                Interactive dual Cytoscape graphs with synchronized panning and zoom. Blocks are color-coded
                and badged (unchanged, modified, added, removed) with click-to-inspect instruction details.
              </p>
            </div>

            {/* Feature 5 */}
            <div className="p-6 rounded-2xl bg-white border border-stone-300 hover:border-indigo-400 shadow-xs hover:shadow-md transition-all group">
              <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-700 flex items-center justify-center mb-5 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                <Network className="w-5 h-5" />
              </div>
              <h4 className="text-base font-bold text-slate-900">Unified Instruction Diffs</h4>
              <p className="mt-2 text-xs text-slate-600 leading-relaxed">
                Inspect instruction-level unified diffs with normalized register tokens and syntax-highlighted
                additions/deletions for rapid root-cause isolation.
              </p>
            </div>

            {/* Feature 6 */}
            <div className="p-6 rounded-2xl bg-white border border-stone-300 hover:border-indigo-400 shadow-xs hover:shadow-md transition-all group">
              <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-700 flex items-center justify-center mb-5 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                <Download className="w-5 h-5" />
              </div>
              <h4 className="text-base font-bold text-slate-900">JSON & Markdown Exports</h4>
              <p className="mt-2 text-xs text-slate-600 leading-relaxed">
                Instant one-click exports in structured JSON and comprehensive Markdown format, complete with
                function diff metrics, security tags, evidence blocks, and unified disassembly diffs.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 5. "How It Works" 4-Step Pipeline */}
      <section id="how-it-works" className="py-24 border-b border-stone-300/80 bg-white/95 backdrop-blur-xs relative z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="text-xs font-bold text-indigo-700 uppercase tracking-widest font-mono">
              Analysis Architecture
            </h2>
            <h3 className="mt-2 text-3xl font-extrabold text-slate-900 sm:text-4xl">
              How PatchLens Works
            </h3>
            <p className="mt-4 text-sm text-slate-600">
              A 4-stage pipeline transforming opaque ELF binaries into verified patch locations.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Step 1 */}
            <div className="p-6 rounded-2xl bg-[#efece6]/60 border border-stone-300 shadow-xs relative">
              <div className="w-8 h-8 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 font-mono text-xs font-bold flex items-center justify-center mb-4">
                01
              </div>
              <h4 className="text-base font-bold text-slate-900">ELF Ingestion & Symbol Recovery</h4>
              <p className="mt-2 text-xs text-slate-600 leading-relaxed">
                Extracts ELF headers, segments, dynamic imports, and exported symbols. Enforces size boundaries and non-executing sandbox parsing.
              </p>
            </div>

            {/* Step 2 */}
            <div className="p-6 rounded-2xl bg-[#efece6]/60 border border-stone-300 shadow-xs relative">
              <div className="w-8 h-8 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 font-mono text-xs font-bold flex items-center justify-center mb-4">
                02
              </div>
              <h4 className="text-base font-bold text-slate-900">Graph Invariant Extraction</h4>
              <p className="mt-2 text-xs text-slate-600 leading-relaxed">
                Capstone disassembles functions via recursive descent and linear-sweep fallbacks, recovering basic blocks and typed jump edges.
              </p>
            </div>

            {/* Step 3 */}
            <div className="p-6 rounded-2xl bg-[#efece6]/60 border border-stone-300 shadow-xs relative">
              <div className="w-8 h-8 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 font-mono text-xs font-bold flex items-center justify-center mb-4">
                03
              </div>
              <h4 className="text-base font-bold text-slate-900">Multi-Pass Graph Matching</h4>
              <p className="mt-2 text-xs text-slate-600 leading-relaxed">
                Fingerprints nodes via Weisfeiler-Lehman hashes. Anchors high-confidence structural matches, followed by call-graph propagation.
              </p>
            </div>

            {/* Step 4 */}
            <div className="p-6 rounded-2xl bg-[#efece6]/60 border border-stone-300 shadow-xs relative">
              <div className="w-8 h-8 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 font-mono text-xs font-bold flex items-center justify-center mb-4">
                04
              </div>
              <h4 className="text-base font-bold text-slate-900">Semantic Diffing & Ranking</h4>
              <p className="mt-2 text-xs text-slate-600 leading-relaxed">
                Blocks are diffed and scanned for security change patterns (bounds guards, NULL checks, return logic). Functions are ranked for audit.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 6. Headline Results Section */}
      <section id="results" className="py-24 border-b border-stone-300/80 bg-white relative z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="text-xs font-bold text-indigo-700 uppercase tracking-widest font-mono">
              Empirical Validation
            </h2>
            <h3 className="mt-2 text-3xl font-extrabold text-slate-900 sm:text-4xl">
              Headline Accuracy on Real CVE Fixes
            </h3>
            <p className="mt-4 text-sm text-slate-600">
              Evaluated on 100% stripped release binaries with no symbol tables or debug info.
            </p>
          </div>

          {/* Results Table */}
          <div className="rounded-2xl border border-stone-300 bg-white overflow-hidden shadow-sm max-w-4xl mx-auto mb-16">
            <div className="px-6 py-4 border-b border-stone-300 bg-stone-50 text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center justify-between font-mono">
              <span>Real-World Security Patch Localization (Stripped Binaries)</span>
              <span className="text-indigo-700">14 Release Variants</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-stone-50 text-slate-600 font-mono uppercase text-[11px] border-b border-stone-300">
                  <tr>
                    <th className="px-6 py-3 font-semibold">CVE Target & Benchmark</th>
                    <th className="px-6 py-3 font-semibold">Compiler / Opt</th>
                    <th className="px-6 py-3 font-semibold">Changed Funcs</th>
                    <th className="px-6 py-3 font-semibold">Patched Function</th>
                    <th className="px-6 py-3 text-right font-semibold">Rank Outcome</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-200 font-mono text-[11px]">
                  <tr className="hover:bg-stone-50 transition-colors">
                    <td className="px-6 py-3 font-semibold text-slate-900">zlib CVE-2018-25032</td>
                    <td className="px-6 py-3 text-slate-600">GCC 13 -O2 (Stripped)</td>
                    <td className="px-6 py-3 text-slate-600">54</td>
                    <td className="px-6 py-3 font-semibold text-indigo-700">deflate_slow</td>
                    <td className="px-6 py-3 text-right">
                      <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 font-bold">
                        Rank #1 (Top-1)
                      </span>
                    </td>
                  </tr>
                  <tr className="hover:bg-stone-50 transition-colors">
                    <td className="px-6 py-3 font-semibold text-slate-900">zlib CVE-2018-25032</td>
                    <td className="px-6 py-3 text-slate-600">GCC 13 -O0 (Stripped)</td>
                    <td className="px-6 py-3 text-slate-600">62</td>
                    <td className="px-6 py-3 font-semibold text-indigo-700">deflate_slow</td>
                    <td className="px-6 py-3 text-right">
                      <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 font-bold">
                        Rank #1 (Top-1)
                      </span>
                    </td>
                  </tr>
                  <tr className="hover:bg-stone-50 transition-colors">
                    <td className="px-6 py-3 font-semibold text-slate-900">zlib CVE-2018-25032</td>
                    <td className="px-6 py-3 text-slate-600">Clang 18 -O2 (Stripped)</td>
                    <td className="px-6 py-3 text-slate-600">58</td>
                    <td className="px-6 py-3 font-semibold text-indigo-700">deflate_slow</td>
                    <td className="px-6 py-3 text-right">
                      <span className="px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 font-bold">
                        Rank #2 (Top-5)
                      </span>
                    </td>
                  </tr>
                  <tr className="hover:bg-stone-50 transition-colors">
                    <td className="px-6 py-3 font-semibold text-slate-900">cJSON CVE-2019-1010239</td>
                    <td className="px-6 py-3 text-slate-600">GCC 13 -O2 (Stripped)</td>
                    <td className="px-6 py-3 text-slate-600">12</td>
                    <td className="px-6 py-3 font-semibold text-indigo-700">cJSON_Minify</td>
                    <td className="px-6 py-3 text-right">
                      <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 font-bold">
                        Rank #1 (Top-1)
                      </span>
                    </td>
                  </tr>
                  <tr className="hover:bg-stone-50 transition-colors">
                    <td className="px-6 py-3 font-semibold text-slate-900">cJSON CVE-2019-1010239</td>
                    <td className="px-6 py-3 text-slate-600">Clang 18 -O2 (Stripped)</td>
                    <td className="px-6 py-3 text-slate-600">14</td>
                    <td className="px-6 py-3 font-semibold text-indigo-700">cJSON_Minify</td>
                    <td className="px-6 py-3 text-right">
                      <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 font-bold">
                        Rank #1 (Top-1)
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* Testimonial / Reviews Section (Nova 3D Reviews Layout) */}
          <div className="max-w-4xl mx-auto p-6 md:p-8 rounded-2xl bg-[#efece6]/90 border border-stone-300 relative shadow-sm">
            {/* Header strip */}
            <div className="flex items-center justify-between pb-4 border-b border-stone-300 mb-6">
              <div className="flex items-center space-x-3">
                <span className="font-mono text-xs font-bold text-slate-800">
                  TSTMNL [{currentReview.id}]
                </span>
                <svg className="w-10 h-10 rounded border border-stone-300 shrink-0" viewBox="0 0 56 56" fill="none">
                  <rect width="56" height="56" fill="#dfdad1" />
                  <path d="M0 14H56 M0 28H56 M0 42H56" stroke="#cec8be" strokeWidth="1.5" />
                  <path d="M14 0V14 M42 0V14 M28 14V28 M14 28V42 M42 28V42 M28 42V56" stroke="#cec8be" strokeWidth="1.5" />
                  <path d="M12 52 C12 40, 20 38, 28 38 C36 38, 44 40, 44 52" fill="#141414" />
                  <circle cx="28" cy="25" r="9" fill="#141414" />
                </svg>
                <div>
                  <span className="font-bold text-sm text-slate-900 block">{currentReview.name}</span>
                  <span className="font-mono text-[11px] text-slate-500 block">{currentReview.role}</span>
                </div>
              </div>

              {/* Navigation arrows */}
              <div className="flex space-x-2">
                <button
                  onClick={() =>
                    handleReviewChange((reviewIdx - 1 + reviews.length) % reviews.length)
                  }
                  className="w-8 h-8 rounded border border-stone-300 hover:border-stone-900 bg-white flex items-center justify-center font-mono text-sm transition-colors cursor-pointer"
                  title="Previous testimonial"
                >
                  ←
                </button>
                <button
                  onClick={() => handleReviewChange((reviewIdx + 1) % reviews.length)}
                  className="w-8 h-8 rounded border border-stone-300 hover:border-stone-900 bg-white flex items-center justify-center font-mono text-sm transition-colors cursor-pointer"
                  title="Next testimonial"
                >
                  →
                </button>
              </div>
            </div>

            {/* Active quote */}
            <div
              className={`transition-all duration-300 ${
                reviewFading ? "opacity-0 translate-y-2" : "opacity-100 translate-y-0"
              }`}
            >
              <p className="text-base sm:text-lg text-slate-800 font-medium leading-relaxed italic">
                {currentReview.quote}
              </p>
              <div className="mt-4 flex items-center space-x-2 font-mono text-xs text-indigo-700">
                <span className="w-4 h-px bg-indigo-700" />
                <Link to="/analyze" className="hover:underline">
                  Try PatchLens for yourself (Click Here)
                </Link>
              </div>
            </div>

            {/* Ghost preview */}
            <div className="mt-4 pt-4 border-t border-stone-200/60 font-mono text-[11px] text-slate-400 opacity-60 truncate">
              NEXT UP: {nextReview.name} ({nextReview.role})
            </div>
          </div>
        </div>
      </section>

      {/* 7. Tech Stack Badges, Limitations & Footer */}
      <section id="limitations" className="py-24 border-b border-stone-300/80 bg-[#efece6]/90 backdrop-blur-xs relative z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 max-w-5xl mx-auto items-start">
            {/* Tech Stack */}
            <div>
              <h3 className="text-lg font-bold text-slate-900 mb-4 font-mono">Engineering Stack</h3>
              <p className="text-xs text-slate-600 mb-6 leading-relaxed">
                Built as a high-performance Python 3.11+ engine paired with modern web infrastructure.
              </p>
              <div className="flex flex-wrap gap-2.5">
                {[
                  "Three.js 0.160",
                  "Capstone 5.0",
                  "pyelftools",
                  "NetworkX 3.2",
                  "FastAPI",
                  "SQLite + Alembic",
                  "Redis + RQ",
                  "React 18",
                  "TypeScript 5",
                  "Tailwind CSS",
                  "Cytoscape.js",
                  "Docker Compose",
                  "Playwright",
                ].map((tech) => (
                  <span
                    key={tech}
                    className="px-3 py-1.5 rounded-xl bg-white border border-stone-300 text-slate-700 text-xs font-semibold shadow-2xs"
                  >
                    {tech}
                  </span>
                ))}
              </div>
            </div>

            {/* Known Limitations */}
            <div>
              <h3 className="text-lg font-bold text-slate-900 mb-4 font-mono">Known Limitations</h3>
              <p className="text-xs text-slate-600 mb-6 leading-relaxed">
                PatchLens documents clear boundaries based on theoretical limits of static disassembly.
              </p>
              <div className="space-y-3 text-xs text-slate-600">
                <div className="p-3.5 rounded-xl bg-white border border-stone-300 shadow-xs flex items-start space-x-3">
                  <Lock className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
                  <div>
                    <strong className="text-slate-800">Compiler Inlining:</strong> Small inline helpers cannot be matched standalone; their edits surface inside callers.
                  </div>
                </div>
                <div className="p-3.5 rounded-xl bg-white border border-stone-300 shadow-xs flex items-start space-x-3">
                  <Lock className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
                  <div>
                    <strong className="text-slate-800">Cross-Compiler Variations:</strong> GCC vs Clang instruction scheduling differences reduce raw sequence matching, requiring graph propagation.
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 bg-white text-xs text-slate-500 relative z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center space-x-2">
            <GitCompare className="w-4 h-4 text-indigo-600" />
            <span className="font-semibold text-slate-700">PatchLens</span>
            <span>— Automated Binary Diffing & Security Patch Localization · 2026</span>
          </div>

          <div className="flex items-center space-x-6 text-slate-500">
            <Link to="/analyze" className="hover:text-indigo-600 transition-colors">
              Launch Analyzer
            </Link>
            <a
              href="/nova.html"
              target="_blank"
              rel="noreferrer"
              className="hover:text-indigo-600 transition-colors"
            >
              Nova 3D Standalone
            </a>
            <a
              href="https://github.com"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center space-x-1.5 hover:text-slate-900 transition-colors"
            >
              <Github className="w-4 h-4" />
              <span>GitHub</span>
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
};
