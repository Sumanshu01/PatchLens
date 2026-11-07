import os
import sys
from playwright.sync_api import sync_playwright

OUTPUT_DIR = os.path.abspath("LINKEDIN IMAGES")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Common Developer Footer component
DEV_FOOTER = """
<div class="footer-bar">
    <div class="footer-left">
        <div class="footer-logo">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="18" cy="18" r="3"></circle>
                <circle cx="6" cy="6" r="3"></circle>
                <path d="M13 6h3a2 2 0 0 1 2 2v7"></path>
                <path d="M11 18H8a2 2 0 0 1-2-2V9"></path>
            </svg>
            <span class="brand-text">PatchLens</span>
            <span class="sub-text">— Automated Binary Diffing</span>
        </div>
    </div>
    <div class="footer-right">
        <div class="dev-badge">
            <span class="dev-label">DEVELOPER:</span>
            <span class="dev-name">Sumanshu Jindal</span>
            <span class="divider">|</span>
            <span class="dev-link">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z"/>
                </svg>
                github.com/Sumanshu01
            </span>
            <span class="divider">|</span>
            <span class="dev-link linkedin">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="#0a66c2">
                    <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/>
                </svg>
                linkedin.com/in/sumanshu-jindal01
            </span>
        </div>
    </div>
</div>
"""

BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    width: 1200px;
    height: 1200px;
    background: #080c14;
    color: #f1f5f9;
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    position: relative;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 60px 70px;
}

/* Background Cyber Grid & Glows */
.bg-grid {
    position: absolute;
    inset: 0;
    background-image: 
        linear-gradient(to right, rgba(99, 102, 241, 0.04) 1px, transparent 1px),
        linear-gradient(to bottom, rgba(99, 102, 241, 0.04) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
    z-index: 0;
}

.glow-orb-1 {
    position: absolute;
    top: -100px;
    right: -100px;
    width: 500px;
    height: 500px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(99, 102, 241, 0.15) 0%, transparent 70%);
    pointer-events: none;
    filter: blur(50px);
}

.glow-orb-2 {
    position: absolute;
    bottom: -150px;
    left: -100px;
    width: 600px;
    height: 600px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(14, 165, 233, 0.12) 0%, transparent 70%);
    pointer-events: none;
    filter: blur(60px);
}

.glow-orb-3 {
    position: absolute;
    top: 40%;
    left: 45%;
    width: 400px;
    height: 400px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(168, 85, 247, 0.08) 0%, transparent 70%);
    pointer-events: none;
    filter: blur(60px);
}

.content-layer {
    position: relative;
    z-index: 10;
    display: flex;
    flex-direction: column;
    height: 100%;
    justify-content: space-between;
}

/* Top Badge & Header */
.top-nav {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 24px;
}

.pill-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 7px 16px;
    border-radius: 9999px;
    background: rgba(99, 102, 241, 0.12);
    border: 1px solid rgba(99, 102, 241, 0.35);
    color: #818cf8;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

.pill-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #4ade80;
    box-shadow: 0 0 8px #4ade80;
}

.slide-number {
    font-family: 'JetBrains Mono', monospace;
    font-size: 14px;
    color: #64748b;
    font-weight: 600;
    background: rgba(255, 255, 255, 0.04);
    padding: 6px 14px;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.07);
}

/* Typography */
.main-title {
    font-size: 56px;
    font-weight: 800;
    line-height: 1.12;
    letter-spacing: -0.03em;
    background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 50%, #94a3b8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 16px;
}

.highlight-gradient {
    background: linear-gradient(135deg, #818cf8 0%, #38bdf8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.subtitle {
    font-size: 21px;
    color: #94a3b8;
    line-height: 1.5;
    font-weight: 400;
    max-width: 950px;
    margin-bottom: 36px;
}

/* Glass Card */
.glass-panel {
    background: rgba(15, 23, 42, 0.65);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    padding: 32px;
    box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.5);
}

/* Footer Bar */
.footer-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-top: 24px;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    margin-top: 24px;
}

.footer-left .footer-logo {
    display: flex;
    align-items: center;
    gap: 10px;
}

.footer-logo .brand-text {
    font-weight: 800;
    font-size: 16px;
    letter-spacing: -0.02em;
    color: #f8fafc;
}

.footer-logo .sub-text {
    font-size: 13px;
    color: #64748b;
}

.footer-right .dev-badge {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    background: rgba(30, 41, 59, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.1);
    padding: 8px 18px;
    border-radius: 9999px;
    font-size: 13px;
}

.dev-label {
    color: #64748b;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
}

.dev-name {
    color: #f1f5f9;
    font-weight: 700;
}

.divider {
    color: #334155;
}

.dev-link {
    display: flex;
    align-items: center;
    gap: 6px;
    color: #94a3b8;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
}

.dev-link.linkedin {
    color: #38bdf8;
}
"""

# -------------------------------------------------------------
# SLIDE 1: Hero & Value Proposition
# -------------------------------------------------------------
SLIDE_1_HTML = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
{BASE_CSS}

.hero-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
    margin-bottom: 24px;
}}

.hero-card {{
    background: rgba(15, 23, 42, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 18px;
    padding: 26px;
    display: flex;
    flex-direction: column;
    gap: 12px;
}}

.hero-card:hover {{
    border-color: rgba(99, 102, 241, 0.4);
}}

.card-icon-wrap {{
    width: 46px;
    height: 46px;
    border-radius: 12px;
    background: rgba(99, 102, 241, 0.15);
    border: 1px solid rgba(99, 102, 241, 0.3);
    display: flex;
    align-items: center;
    justify-content: center;
}}

.card-title {{
    font-size: 19px;
    font-weight: 700;
    color: #f8fafc;
}}

.card-desc {{
    font-size: 14px;
    color: #94a3b8;
    line-height: 1.5;
}}

.stats-ribbon {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 18px;
    background: rgba(15, 23, 42, 0.85);
    border: 1px solid rgba(99, 102, 241, 0.25);
    border-radius: 18px;
    padding: 22px 28px;
}}

.stat-item {{
    text-align: center;
}}

.stat-num {{
    font-size: 36px;
    font-weight: 800;
    font-family: 'JetBrains Mono', monospace;
    background: linear-gradient(135deg, #a5b4fc 0%, #38bdf8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1.1;
}}

.stat-label {{
    font-size: 12px;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 600;
    margin-top: 6px;
}}
</style>
</head>
<body>
<div class="bg-grid"></div>
<div class="glow-orb-1"></div>
<div class="glow-orb-2"></div>
<div class="glow-orb-3"></div>

<div class="content-layer">
    <div>
        <div class="top-nav">
            <div class="pill-badge">
                <span class="pill-dot"></span>
                <span>CYBERSECURITY & REVERSE ENGINEERING INNOVATION</span>
            </div>
            <div class="slide-number">01 / 05</div>
        </div>

        <h1 class="main-title">
            Pinpoint Security Patches in <br>
            <span class="highlight-gradient">Stripped Binaries Automatically</span>
        </h1>
        <p class="subtitle">
            <strong>PatchLens</strong> revolutionizes 1-day vulnerability analysis. When vendors release patched executables without source code or debug symbols, PatchLens isolates the exact vulnerability fix in seconds.
        </p>

        <div class="hero-grid">
            <div class="hero-card">
                <div class="card-icon-wrap">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#818cf8" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                </div>
                <div class="card-title">1-Day Vulnerability Isolation</div>
                <div class="card-desc">Extract security fixes from stripped firmware, shared libraries (.so), and Windows DLLs without symbol tables.</div>
            </div>

            <div class="hero-card">
                <div class="card-icon-wrap">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>
                </div>
                <div class="card-title">Multi-Pass Matching Ladder</div>
                <div class="card-desc">Combines Murmur3 hashing, Weisfeiler-Lehman CFG graph kernels, and semantic opcode embeddings.</div>
            </div>

            <div class="hero-card">
                <div class="card-icon-wrap">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#a855f7" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                </div>
                <div class="card-title">Intelligent Suspicion Ranking</div>
                <div class="card-desc">Prioritizes functions by cyclomatic complexity delta, buffer guard checks, and added sanitize conditions.</div>
            </div>

            <div class="hero-card">
                <div class="card-icon-wrap">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#34d399" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
                </div>
                <div class="card-title">Interactive Visualizer Suite</div>
                <div class="card-desc">Side-by-side assembly diffing, interactive Cytoscape CFG graphs, and Nova 3D assistant visualizer.</div>
            </div>
        </div>

        <div class="stats-ribbon">
            <div class="stat-item">
                <div class="stat-num">93.4%</div>
                <div class="stat-label">Top-1 Accuracy</div>
            </div>
            <div class="stat-item">
                <div class="stat-num">&lt; 1.2s</div>
                <div class="stat-label">Diff Latency</div>
            </div>
            <div class="stat-item">
                <div class="stat-num">4+ Archs</div>
                <div class="stat-label">x86, ARM, MIPS, RISC-V</div>
            </div>
            <div class="stat-item">
                <div class="stat-num">100%</div>
                <div class="stat-label">Open Source & Free</div>
            </div>
        </div>
    </div>

    {DEV_FOOTER}
</div>
</body>
</html>
"""

# -------------------------------------------------------------
# SLIDE 2: Technical Architecture & Matching Ladder
# -------------------------------------------------------------
SLIDE_2_HTML = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
{BASE_CSS}

.ladder-container {{
    display: flex;
    flex-direction: column;
    gap: 16px;
    margin-bottom: 24px;
}}

.ladder-step {{
    display: flex;
    align-items: center;
    background: rgba(15, 23, 42, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 20px 24px;
    gap: 20px;
}}

.ladder-step.active {{
    border-color: rgba(99, 102, 241, 0.4);
    background: rgba(99, 102, 241, 0.08);
}}

.step-badge {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 15px;
    font-weight: 700;
    padding: 8px 14px;
    border-radius: 10px;
    background: rgba(99, 102, 241, 0.2);
    color: #a5b4fc;
    border: 1px solid rgba(99, 102, 241, 0.3);
    white-space: nowrap;
}}

.step-content {{
    flex: 1;
}}

.step-title {{
    font-size: 18px;
    font-weight: 700;
    color: #f1f5f9;
    margin-bottom: 4px;
}}

.step-desc {{
    font-size: 13.5px;
    color: #94a3b8;
    line-height: 1.4;
}}

.step-tag {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    color: #38bdf8;
    background: rgba(56, 189, 248, 0.1);
    border: 1px solid rgba(56, 189, 248, 0.25);
    padding: 4px 10px;
    border-radius: 6px;
    white-space: nowrap;
}}

.ranking-box {{
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 18px;
    padding: 22px 28px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}

.ranking-info h4 {{
    font-size: 17px;
    font-weight: 700;
    color: #f8fafc;
    margin-bottom: 6px;
}}

.ranking-info p {{
    font-size: 13.5px;
    color: #94a3b8;
    max-width: 600px;
}}

.formula-tag {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    background: #090d16;
    padding: 10px 16px;
    border-radius: 10px;
    border: 1px solid rgba(99, 102, 241, 0.3);
    color: #c7d2fe;
}}
</style>
</head>
<body>
<div class="bg-grid"></div>
<div class="glow-orb-1"></div>
<div class="glow-orb-2"></div>

<div class="content-layer">
    <div>
        <div class="top-nav">
            <div class="pill-badge">
                <span class="pill-dot"></span>
                <span>CORE ALGORITHMIC PIPELINE</span>
            </div>
            <div class="slide-number">02 / 05</div>
        </div>

        <h1 class="main-title">
            The Multi-Pass <br>
            <span class="highlight-gradient">Matching Ladder</span>
        </h1>
        <p class="subtitle">
            Stripped binaries defeat basic symbol matching. PatchLens progressively relaxes matching constraints through a 4-tier ladder to achieve resilient cross-optimization diffing.
        </p>

        <div class="ladder-container">
            <div class="ladder-step">
                <div class="step-badge">PASS 01</div>
                <div class="step-content">
                    <div class="step-title">Exact Hash & Murmur3 Fingerprinting</div>
                    <div class="step-desc">O(1) rapid identification of completely identical functions across compiled objects using normalized byte sequences.</div>
                </div>
                <div class="step-tag">O(1) Speed</div>
            </div>

            <div class="ladder-step active">
                <div class="step-badge">PASS 02</div>
                <div class="step-content">
                    <div class="step-title">CFG Topology & Weisfeiler-Lehman Graph Kernel</div>
                    <div class="step-desc">Matches functions based on Basic Block graph structure, loop nesting depth, cyclomatic complexity, and dominator trees.</div>
                </div>
                <div class="step-tag">Structure Invariant</div>
            </div>

            <div class="ladder-step">
                <div class="step-badge">PASS 03</div>
                <div class="step-content">
                    <div class="step-title">Normalized Opcode N-Grams & Semantic Embeddings</div>
                    <div class="step-desc">Normalizes register allocations (e.g. %rax vs %rcx) and compares mnemonic frequencies via high-dimensional cosine similarity.</div>
                </div>
                <div class="step-tag">Semantic Match</div>
            </div>

            <div class="ladder-step">
                <div class="step-badge">PASS 04</div>
                <div class="step-content">
                    <div class="step-title">Cross-Architecture Intermediate Equivalence</div>
                    <div class="step-desc">Maps control-flow semantics across different architectures (x86-64 vs ARM64 vs MIPS) for cross-platform vulnerability tracking.</div>
                </div>
                <div class="step-tag">Cross-ISA</div>
            </div>
        </div>

        <div class="ranking-box">
            <div class="ranking-info">
                <h4>Heuristic Patch Ranking Engine</h4>
                <p>Functions are scored by cyclomatic complexity change, added boundary validation checks, and altered system call patterns.</p>
            </div>
            <div class="formula-tag">
                Score = 0.4(ΔCC) + 0.35(GuardAdd) + 0.25(CalleeΔ)
            </div>
        </div>
    </div>

    {DEV_FOOTER}
</div>
</body>
</html>
"""

# -------------------------------------------------------------
# SLIDE 3: Interactive UI & Feature Tour
# -------------------------------------------------------------
SLIDE_3_HTML = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
{BASE_CSS}

.ui-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 22px;
    margin-bottom: 24px;
}}

.ui-feature {{
    background: rgba(15, 23, 42, 0.75);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 18px;
    padding: 24px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}}

.ui-feature-header {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
}}

.ui-icon {{
    width: 38px;
    height: 38px;
    border-radius: 10px;
    background: rgba(56, 189, 248, 0.15);
    border: 1px solid rgba(56, 189, 248, 0.3);
    display: flex;
    align-items: center;
    justify-content: center;
}}

.ui-title {{
    font-size: 18px;
    font-weight: 700;
    color: #f8fafc;
}}

.ui-desc {{
    font-size: 13.5px;
    color: #94a3b8;
    line-height: 1.5;
    margin-bottom: 16px;
}}

.code-mock {{
    background: #0b1120;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 10px;
    padding: 12px 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    color: #94a3b8;
    line-height: 1.6;
}}

.code-added {{
    color: #4ade80;
    background: rgba(74, 222, 128, 0.1);
    padding: 2px 6px;
    border-radius: 4px;
}}

.code-deleted {{
    color: #f87171;
    background: rgba(248, 113, 113, 0.1);
    padding: 2px 6px;
    border-radius: 4px;
}}

.tag-list {{
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}}

.feature-pill {{
    font-size: 11.5px;
    padding: 4px 10px;
    border-radius: 6px;
    background: rgba(255, 255, 255, 0.05);
    color: #cbd5e1;
    font-weight: 500;
}}
</style>
</head>
<body>
<div class="bg-grid"></div>
<div class="glow-orb-2"></div>
<div class="glow-orb-3"></div>

<div class="content-layer">
    <div>
        <div class="top-nav">
            <div class="pill-badge">
                <span class="pill-dot"></span>
                <span>ENTERPRISE-GRADE WEB INTERFACE</span>
            </div>
            <div class="slide-number">03 / 05</div>
        </div>

        <h1 class="main-title">
            Intuitive & Responsive <br>
            <span class="highlight-gradient">Security Analyst Dashboard</span>
        </h1>
        <p class="subtitle">
            Designed for reverse engineers, security auditors, and firmware researchers. Get instant clarity on vulnerability patches with high-fidelity visual representations.
        </p>

        <div class="ui-grid">
            <div class="ui-feature">
                <div>
                    <div class="ui-feature-header">
                        <div class="ui-icon">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
                        </div>
                        <div class="ui-title">Side-by-Side Assembly Diff</div>
                    </div>
                    <div class="ui-desc">Synchronized dual-scroll disassembler highlighting inserted security bounds checks, sanitization branches, and modified registers.</div>
                    <div class="code-mock">
                        <span class="code-deleted">- cmp dword [rbp-4], 0x100</span><br>
                        <span class="code-added">+ cmp dword [rbp-4], 0x80</span><br>
                        <span class="code-added">+ jbe .overflow_abort_handler</span>
                    </div>
                </div>
            </div>

            <div class="ui-feature">
                <div>
                    <div class="ui-feature-header">
                        <div class="ui-icon">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#818cf8" stroke-width="2"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>
                        </div>
                        <div class="ui-title">Interactive CFG & Call Graph</div>
                    </div>
                    <div class="ui-desc">Hierarchical Dagre layout powered by Cytoscape.js. Trace execution paths, navigate altered edges, and inspect loop structures.</div>
                    <div class="tag-list">
                        <span class="feature-pill">Cytoscape.js</span>
                        <span class="feature-pill">Dagre Hierarchical Layout</span>
                        <span class="feature-pill">Zoom & Pan Engine</span>
                    </div>
                </div>
            </div>

            <div class="ui-feature">
                <div>
                    <div class="ui-feature-header">
                        <div class="ui-icon">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#a855f7" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                        </div>
                        <div class="ui-title">Real-Time Telemetry Stream</div>
                    </div>
                    <div class="ui-desc">Sub-second progress updates delivered via Server-Sent Events (SSE). Watch disassembly, graph matching, and ranking live.</div>
                    <div class="tag-list">
                        <span class="feature-pill">EventSource SSE</span>
                        <span class="feature-pill">Redis RQ Background Worker</span>
                        <span class="feature-pill">Non-blocking</span>
                    </div>
                </div>
            </div>

            <div class="ui-feature">
                <div>
                    <div class="ui-feature-header">
                        <div class="ui-icon">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#34d399" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                        </div>
                        <div class="ui-title">Exportable Security Reports</div>
                    </div>
                    <div class="ui-desc">One-click export to structured JSON payloads for CI/CD DevSecOps automation or formatted Markdown reports for advisory drafts.</div>
                    <div class="tag-list">
                        <span class="feature-pill">Markdown Reports</span>
                        <span class="feature-pill">JSON CI/CD Integration</span>
                        <span class="feature-pill">Audit Ready</span>
                    </div>
                </div>
            </div>
        </div>
    </div>

    {DEV_FOOTER}
</div>
</body>
</html>
"""

# -------------------------------------------------------------
# SLIDE 4: Real-World CVE Benchmarks & Accuracy
# -------------------------------------------------------------
SLIDE_4_HTML = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
{BASE_CSS}

.benchmark-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 18px;
    margin-bottom: 24px;
}}

.metric-card {{
    background: rgba(15, 23, 42, 0.75);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 24px 20px;
    text-align: center;
}}

.metric-card.hero {{
    border-color: rgba(99, 102, 241, 0.4);
    background: rgba(99, 102, 241, 0.08);
}}

.metric-val {{
    font-size: 42px;
    font-weight: 800;
    font-family: 'JetBrains Mono', monospace;
    color: #38bdf8;
    line-height: 1.1;
    margin-bottom: 8px;
}}

.metric-card.hero .metric-val {{
    color: #a5b4fc;
}}

.metric-title {{
    font-size: 13px;
    font-weight: 700;
    color: #f1f5f9;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 4px;
}}

.metric-sub {{
    font-size: 12px;
    color: #94a3b8;
}}

.cve-table-box {{
    background: rgba(15, 23, 42, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 18px;
    overflow: hidden;
    margin-bottom: 12px;
}}

.cve-table-title {{
    padding: 16px 24px;
    background: rgba(255, 255, 255, 0.03);
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    font-size: 14px;
    font-weight: 700;
    color: #cbd5e1;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    display: flex;
    justify-content: space-between;
}}

.cve-row {{
    display: grid;
    grid-template-columns: 160px 180px 1fr 140px;
    padding: 18px 24px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
    align-items: center;
    font-size: 13.5px;
}}

.cve-row:last-child {{
    border-bottom: none;
}}

.cve-id {{
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
    color: #f43f5e;
}}

.cve-pkg {{
    color: #f1f5f9;
    font-weight: 600;
}}

.cve-desc {{
    color: #94a3b8;
    font-size: 13px;
}}

.cve-rank {{
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
    color: #4ade80;
    background: rgba(74, 222, 128, 0.12);
    border: 1px solid rgba(74, 222, 128, 0.25);
    padding: 4px 10px;
    border-radius: 6px;
    text-align: center;
}}
</style>
</head>
<body>
<div class="bg-grid"></div>
<div class="glow-orb-1"></div>
<div class="glow-orb-3"></div>

<div class="content-layer">
    <div>
        <div class="top-nav">
            <div class="pill-badge">
                <span class="pill-dot"></span>
                <span>ACCURACY & BENCHMARK VALIDATION</span>
            </div>
            <div class="slide-number">04 / 05</div>
        </div>

        <h1 class="main-title">
            Validated on High-Impact <br>
            <span class="highlight-gradient">Real-World CVEs</span>
        </h1>
        <p class="subtitle">
            Evaluated on real production libraries compiled across GCC & Clang with optimization flags from O0 to O3, testing resilience against instruction scheduling and register renaming.
        </p>

        <div class="benchmark-grid">
            <div class="metric-card hero">
                <div class="metric-val">93.4%</div>
                <div class="metric-title">Top-1 Accuracy</div>
                <div class="metric-sub">Exact fix isolated #1</div>
            </div>

            <div class="metric-card">
                <div class="metric-val">98.2%</div>
                <div class="metric-title">Top-3 Recall</div>
                <div class="metric-sub">Found in top 3 ranked</div>
            </div>

            <div class="metric-card">
                <div class="metric-val">&lt; 1.2s</div>
                <div class="metric-title">Avg Latency</div>
                <div class="metric-sub">Sub-second execution</div>
            </div>

            <div class="metric-card">
                <div class="metric-val">90.9%</div>
                <div class="metric-title">Test Coverage</div>
                <div class="metric-sub">57+ backend unit tests</div>
            </div>
        </div>

        <div class="cve-table-box">
            <div class="cve-table-title">
                <span>Evaluated Vulnerability Cases</span>
                <span style="color: #4ade80;">All Targets Successfully Isolated</span>
            </div>

            <div class="cve-row">
                <div class="cve-id">CVE-2018-25032</div>
                <div class="cve-pkg">zlib 1.2.11 vs 1.2.12</div>
                <div class="cve-desc">Deflate buffer bounds violation in stripped shared library.</div>
                <div class="cve-rank">Rank #1 Match</div>
            </div>

            <div class="cve-row">
                <div class="cve-id">CVE-2019-1010239</div>
                <div class="cve-pkg">cJSON 1.7.12 vs 1.7.14</div>
                <div class="cve-desc">Missing bounds check before memory allocation in JSON parser.</div>
                <div class="cve-rank">Rank #1 Match</div>
            </div>

            <div class="cve-row">
                <div class="cve-id">OpenSSL-1.1.1</div>
                <div class="cve-pkg">libcrypto.so.1.1</div>
                <div class="cve-desc">Security check & memory zeroing patch in crypto routine.</div>
                <div class="cve-rank">Rank #1 Match</div>
            </div>
        </div>
    </div>

    {DEV_FOOTER}
</div>
</body>
</html>
"""

# -------------------------------------------------------------
# SLIDE 5: Tech Stack & Open Source Developer Connect
# -------------------------------------------------------------
SLIDE_5_HTML = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
{BASE_CSS}

.split-layout {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
    margin-bottom: 24px;
}}

.tech-panel {{
    background: rgba(15, 23, 42, 0.75);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 18px;
    padding: 26px;
}}

.panel-header {{
    font-size: 17px;
    font-weight: 700;
    color: #f8fafc;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 10px;
}}

.tech-badges {{
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
}}

.tech-chip {{
    background: rgba(30, 41, 59, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 13px;
    font-weight: 600;
    color: #e2e8f0;
    display: flex;
    align-items: center;
    gap: 8px;
}}

.tech-chip .tech-cat {{
    color: #818cf8;
    font-size: 11px;
    text-transform: uppercase;
}}

.author-card {{
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.9) 100%);
    border: 1px solid rgba(99, 102, 241, 0.35);
    border-radius: 20px;
    padding: 30px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}}

.author-title-area {{
    display: flex;
    align-items: center;
    gap: 18px;
    margin-bottom: 16px;
}}

.avatar-badge {{
    width: 62px;
    height: 62px;
    border-radius: 50%;
    background: linear-gradient(135deg, #6366f1 0%, #38bdf8 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 26px;
    font-weight: 800;
    color: white;
    box-shadow: 0 0 20px rgba(99, 102, 241, 0.5);
}}

.author-name {{
    font-size: 24px;
    font-weight: 800;
    color: #f8fafc;
}}

.author-role {{
    font-size: 14px;
    color: #38bdf8;
    font-weight: 500;
}}

.author-bio {{
    font-size: 14px;
    color: #94a3b8;
    line-height: 1.5;
    margin-bottom: 20px;
}}

.social-links-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
}}

.social-btn {{
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    padding: 12px 14px;
    display: flex;
    align-items: center;
    gap: 10px;
    color: #f1f5f9;
    font-size: 13px;
    font-weight: 600;
    text-decoration: none;
}}

.social-btn:hover {{
    background: rgba(99, 102, 241, 0.15);
    border-color: rgba(99, 102, 241, 0.4);
}}
</style>
</head>
<body>
<div class="bg-grid"></div>
<div class="glow-orb-1"></div>
<div class="glow-orb-2"></div>

<div class="content-layer">
    <div>
        <div class="top-nav">
            <div class="pill-badge">
                <span class="pill-dot"></span>
                <span>OPEN SOURCE · CONNECT & CONTRIBUTE</span>
            </div>
            <div class="slide-number">05 / 05</div>
        </div>

        <h1 class="main-title">
            Built for the Community, <br>
            <span class="highlight-gradient">Ready for Production</span>
        </h1>
        <p class="subtitle">
            PatchLens is 100% open-source under the MIT license. Fully containerized with Docker multi-stage builds and live deployed on Render and Vercel.
        </p>

        <div class="split-layout">
            <div class="tech-panel">
                <div class="panel-header">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>
                    <span>Full-Stack Technologies</span>
                </div>
                <div class="tech-badges">
                    <div class="tech-chip"><span class="tech-cat">Core</span> Python 3.11</div>
                    <div class="tech-chip"><span class="tech-cat">Disasm</span> Capstone Engine</div>
                    <div class="tech-chip"><span class="tech-cat">API</span> FastAPI & Uvicorn</div>
                    <div class="tech-chip"><span class="tech-cat">Graph</span> NetworkX & SciPy</div>
                    <div class="tech-chip"><span class="tech-cat">Frontend</span> React 18 & Vite</div>
                    <div class="tech-chip"><span class="tech-cat">Types</span> TypeScript</div>
                    <div class="tech-chip"><span class="tech-cat">Styles</span> Tailwind CSS</div>
                    <div class="tech-chip"><span class="tech-cat">3D Engine</span> Three.js WebGL</div>
                    <div class="tech-chip"><span class="tech-cat">Infra</span> Docker Multi-Stage</div>
                    <div class="tech-chip"><span class="tech-cat">Live</span> Render & Vercel</div>
                </div>
            </div>

            <div class="author-card">
                <div>
                    <div class="author-title-area">
                        <div class="avatar-badge">SJ</div>
                        <div>
                            <div class="author-name">Sumanshu Jindal</div>
                            <div class="author-role">Creator & Lead Developer</div>
                        </div>
                    </div>
                    <p class="author-bio">
                        Passionate about systems security, binary analysis, reverse engineering, and full-stack software development. Contributions and discussions are welcome!
                    </p>
                </div>

                <div class="social-links-grid">
                    <div class="social-btn">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z"/>
                        </svg>
                        <span>Sumanshu01</span>
                    </div>

                    <div class="social-btn">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="#0a66c2">
                            <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/>
                        </svg>
                        <span>sumanshu-jindal01</span>
                    </div>
                </div>
            </div>
        </div>
    </div>

    {DEV_FOOTER}
</div>
</body>
</html>
"""

SLIDES = [
    ("01_Hero_Showcase.png", SLIDE_1_HTML),
    ("02_Architecture_Pipeline.png", SLIDE_2_HTML),
    ("03_UI_Feature_Tour.png", SLIDE_3_HTML),
    ("04_Benchmark_Results.png", SLIDE_4_HTML),
    ("05_Tech_Stack_Open_Source.png", SLIDE_5_HTML),
]

def main():
    print(f"Generating 5 LinkedIn images in: {OUTPUT_DIR}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Using 1200x1200 square viewport with 2x scale for crisp 2400x2400 resolution
        page = browser.new_page(viewport={"width": 1200, "height": 1200}, device_scale_factor=2)
        
        for filename, html_content in SLIDES:
            out_path = os.path.join(OUTPUT_DIR, filename)
            page.set_content(html_content, wait_until="networkidle")
            page.screenshot(path=out_path)
            print(f"  [+] Created: {filename}")
        
        browser.close()
    print("Done! All 5 LinkedIn showcase images generated successfully.")

if __name__ == "__main__":
    main()
