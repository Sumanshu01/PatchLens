import os
import shutil

with open('ibm300.b64', 'r', encoding='utf-8') as f:
    ibm300 = f.read().strip()
with open('ibm400.b64', 'r', encoding='utf-8') as f:
    ibm400 = f.read().strip()
with open('ibm500.b64', 'r', encoding='utf-8') as f:
    ibm500 = f.read().strip()
with open('schibsted.b64', 'r', encoding='utf-8') as f:
    schibsted = f.read().strip()

html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NOVA AGENT — Thinking Machines</title>
  
  <style>
    @font-face {{
      font-family: 'IBM Plex Mono';
      font-weight: 300;
      font-style: normal;
      font-display: swap;
      src: url('data:font/woff2;base64,{ibm300}') format('woff2');
    }}
    @font-face {{
      font-family: 'IBM Plex Mono';
      font-weight: 400;
      font-style: normal;
      font-display: swap;
      src: url('data:font/woff2;base64,{ibm400}') format('woff2');
    }}
    @font-face {{
      font-family: 'IBM Plex Mono';
      font-weight: 500;
      font-style: normal;
      font-display: swap;
      src: url('data:font/woff2;base64,{ibm500}') format('woff2');
    }}
    @font-face {{
      font-family: 'Schibsted Grotesk';
      font-weight: 400 500;
      font-style: normal;
      font-display: swap;
      src: url('data:font/woff2;base64,{schibsted}') format('woff2');
    }}

    :root {{
      --bg: #efece6;
      --text: #141414;
      --dim: rgba(20, 20, 20, 0.5);
      --grid: rgba(20, 20, 20, 0.09);
      --brand-gradient: conic-gradient(from 200deg, #ffb347, #ff8a3d 18%, #ff5a5f 34%, #ff3d8b 50%, #ff5a5f 66%, #ff8a3d 82%, #ffb347);
      --linear-brand: linear-gradient(135deg, #ffb347, #ff8a3d, #ff5a5f, #ff3d8b);
      --col: 17%;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
    }}

    html, body {{
      width: 100%;
      min-height: 100%;
      background-color: var(--bg);
      color: var(--text);
      font-family: 'Schibsted Grotesk', -apple-system, BlinkMacSystemFont, sans-serif;
      overflow-x: hidden;
      scroll-behavior: smooth;
    }}

    /* Fullscreen Three.js canvas */
    #robot-canvas {{
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      pointer-events: none;
      z-index: 1;
    }}

    /* Grid guides */
    .grid-guide {{
      position: fixed;
      top: 0;
      bottom: 0;
      width: 1px;
      background: var(--grid);
      pointer-events: none;
      z-index: 2;
    }}
    .guide-left {{ left: 17%; }}
    .guide-center {{ left: 50%; }}
    .guide-right {{ left: 83%; }}

    /* Top bar */
    .top-bar {{
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 30px;
      background: var(--bg);
      border-bottom: 1px solid var(--grid);
      font-family: 'IBM Plex Mono', monospace;
      font-size: 11px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 17%;
      z-index: 60;
      transition: transform 0.5s cubic-bezier(0.6, 0, 0.2, 1);
    }}
    .top-bar.hidden {{
      transform: translateY(-100%);
    }}
    .top-bar-content strong {{
      font-weight: 500;
    }}
    .top-bar-close {{
      background: none;
      border: none;
      font-family: 'IBM Plex Mono', monospace;
      font-size: 16px;
      color: var(--text);
      cursor: pointer;
      line-height: 1;
      padding: 0 4px;
    }}

    /* Navigation */
    .navbar {{
      position: fixed;
      top: 30px;
      left: 0;
      width: 100%;
      height: 52px;
      background: rgba(239, 236, 230, 0.86);
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
      border-bottom: 1px solid var(--grid);
      display: grid;
      grid-template-columns: 17% 1fr 12% 17%;
      align-items: stretch;
      z-index: 50;
      transition: top 0.5s cubic-bezier(0.6, 0, 0.2, 1);
    }}
    .navbar.scrolled-up {{
      top: 0;
    }}

    .nav-logo-cell {{
      display: flex;
      align-items: center;
      padding-left: 28px;
      gap: 12px;
    }}
    .nav-logo-icon {{
      width: 27px;
      height: 27px;
      flex-shrink: 0;
    }}
    .nav-logo-text {{
      font-family: 'Schibsted Grotesk', sans-serif;
      font-size: 18px;
      font-weight: 500;
      letter-spacing: -0.01em;
    }}

    .nav-menu {{
      display: flex;
      align-items: center;
      gap: 22px;
      font-family: 'IBM Plex Mono', monospace;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      padding-left: 24px;
    }}
    .nav-menu a {{
      color: var(--text);
      text-decoration: none;
      transition: opacity 0.2s;
    }}
    .nav-menu a:hover {{
      opacity: 0.7;
    }}

    .nav-pad-cell {{
      display: flex;
      align-items: center;
      justify-content: center;
      border-left: 1px solid var(--grid);
      border-right: 1px solid var(--grid);
      font-family: 'IBM Plex Mono', monospace;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .nav-pad-cell a {{
      color: var(--text);
      text-decoration: none;
    }}

    .nav-btn-cell {{
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 0 16px;
    }}

    .launch-btn {{
      position: relative;
      height: 30px;
      padding: 0 16px;
      background: transparent;
      color: var(--text);
      font-family: 'IBM Plex Mono', monospace;
      font-size: 11px;
      font-weight: 500;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      border: 1px solid rgba(20, 20, 20, 0.22);
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      text-decoration: none;
    }}
    .launch-btn::after {{
      content: '';
      position: absolute;
      inset: -1px;
      background: linear-gradient(135deg, #ff8a3d, #ff5a5f, #ff3d8b);
      clip-path: polygon(0 0, 58% 0, 58% 2px, 2px 2px, 2px 100%, 0 100%);
      pointer-events: none;
    }}

    /* Right rail */
    .right-rail {{
      position: fixed;
      top: 50%;
      right: 32px;
      transform: translateY(-50%);
      height: 270px;
      width: 40px;
      z-index: 40;
      pointer-events: none;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: space-between;
    }}
    .dots-track {{
      position: relative;
      width: 6px;
      height: 230px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      align-items: center;
    }}
    .rail-dot {{
      width: 3px;
      height: 3px;
      border-radius: 50%;
      background: rgba(20, 20, 20, 0.25);
    }}
    .rail-dial-badge {{
      position: absolute;
      right: 18px;
      top: 0%;
      display: flex;
      align-items: center;
      gap: 6px;
      font-family: 'IBM Plex Mono', monospace;
      font-size: 10px;
      letter-spacing: 0.06em;
      color: var(--text);
      white-space: nowrap;
      transition: top 0.7s cubic-bezier(0.2, 0.8, 0.2, 1);
      transform: translateY(-50%);
    }}
    .rail-dial-icon {{
      width: 12px;
      height: 12px;
    }}
    .rail-menu-label {{
      font-family: 'IBM Plex Mono', monospace;
      font-size: 10px;
      letter-spacing: 0.06em;
      color: var(--text);
      margin-top: 10px;
      cursor: pointer;
      pointer-events: auto;
    }}

    /* Reveal animations */
    .rv {{
      opacity: 0;
      transform: translateY(26px);
      transition: opacity 1s cubic-bezier(0.2, 0.7, 0.2, 1), transform 1s cubic-bezier(0.2, 0.7, 0.2, 1);
    }}
    .rv.rv-visible {{
      opacity: 1;
      transform: translateY(0);
    }}
    .rv-d1 {{ transition-delay: 0.1s; }}
    .rv-d2 {{ transition-delay: 0.2s; }}
    .rv-d3 {{ transition-delay: 0.3s; }}
    .rv-d4 {{ transition-delay: 0.4s; }}

    /* Section layout */
    section {{
      position: relative;
      width: 100%;
      height: 100vh;
      overflow: hidden;
      z-index: 10;
    }}

    /* SECTION 1: INTRO */
    #section-intro {{
      height: 100vh;
    }}

    /* Prompt box */
    .prompt-box-wrapper {{
      position: absolute;
      left: 17%;
      top: 30%;
      width: 24.4%;
    }}
    .prompt-tab {{
      width: 42px;
      height: 42px;
      border: 1px solid var(--grid);
      border-bottom: none;
      background: var(--bg);
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: serif;
      font-size: 26px;
      font-weight: 700;
      line-height: 1;
    }}
    .prompt-box {{
      position: relative;
      width: 100%;
      border: 1px solid rgba(20, 20, 20, 0.28);
      background: rgba(239, 236, 230, 0.88);
      padding: 16px;
      font-family: 'IBM Plex Mono', monospace;
      font-size: 11px;
      text-transform: uppercase;
      line-height: 1.45;
      letter-spacing: 0.04em;
      min-height: 90px;
    }}
    /* Corner brackets */
    .corner-bracket {{
      position: absolute;
      width: 7px;
      height: 7px;
      border-color: #141414;
      border-style: solid;
      border-radius: 1px;
      pointer-events: none;
    }}
    .cb-tl {{ top: -4px; left: -4px; border-width: 1px 0 0 1px; }}
    .cb-tr {{ top: -4px; right: -4px; border-width: 1px 1px 0 0; }}
    .cb-bl {{ bottom: -4px; left: -4px; border-width: 0 0 1px 1px; }}
    .cb-br {{ bottom: -4px; right: -4px; border-width: 0 1px 1px 0; }}

    .prompt-typing-text {{
      display: inline;
    }}
    .prompt-caret {{
      display: inline-block;
      width: 6px;
      height: 11px;
      background: #141414;
      vertical-align: middle;
      margin-left: 2px;
      animation: blink 0.9s infinite step-start;
    }}
    @keyframes blink {{
      0%, 50% {{ opacity: 1; }}
      51%, 100% {{ opacity: 0; }}
    }}
    .prompt-faint-next {{
      margin-top: 10px;
      font-family: 'IBM Plex Mono', monospace;
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: rgba(20, 20, 20, 0.35);
      line-height: 1.4;
    }}

    /* Hairline from prompt box to right guide */
    .prompt-rule {{
      position: absolute;
      left: calc(17% + 24.4%);
      right: 17%;
      top: 30%;
      height: 1px;
      background: var(--grid);
      pointer-events: none;
    }}

    /* Feature list */
    .feature-list {{
      position: absolute;
      top: calc(30% + 1px);
      right: 17%;
      width: 23%;
      display: flex;
      flex-direction: column;
    }}
    .feature-row {{
      height: 21px;
      position: relative;
      display: flex;
      align-items: center;
      border-bottom: 1px solid var(--grid);
      font-family: 'IBM Plex Mono', monospace;
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      padding-left: 32px;
    }}
    .feature-row.dim {{
      color: var(--dim);
    }}
    .feature-row::before {{
      content: '';
      position: absolute;
      left: 18%;
      width: 3px;
      height: 3px;
      border-radius: 50%;
      background: #141414;
    }}
    .feature-row.dim::before {{
      background: var(--dim);
    }}

    /* Bottom left intro headline */
    .intro-bottom-left {{
      position: absolute;
      bottom: 8%;
      left: 17%;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}
    .unleash-tag {{
      font-family: 'IBM Plex Mono', monospace;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--text);
    }}
    .intro-headline {{
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}
    .headline-box {{
      position: relative;
      display: inline-block;
      width: fit-content;
      padding: 6px 24px;
      font-size: clamp(42px, 5.25vw, 92px);
      font-weight: 400;
      letter-spacing: -0.02em;
      line-height: 1.05;
      background: rgba(239, 236, 230, 0.4);
    }}
    .box-border-svg {{
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
    }}

    /* Subline */
    .intro-subline {{
      position: absolute;
      bottom: 3.6%;
      left: calc(62% + 18px);
      font-size: 14.5px;
      color: var(--text);
      max-width: 280px;
      line-height: 1.4;
      background: rgba(239, 236, 230, 0.85);
      padding: 4px 8px;
    }}

    /* Bottom rule */
    .intro-bottom-rule {{
      position: absolute;
      left: 50%;
      right: 0;
      bottom: 14%;
      height: 1px;
      background: var(--grid);
      pointer-events: none;
    }}

    /* Scroll link */
    .intro-scroll-link {{
      position: absolute;
      bottom: 3.6%;
      right: 17%;
      display: flex;
      align-items: center;
      gap: 8px;
      font-family: 'IBM Plex Mono', monospace;
      font-size: 11px;
      letter-spacing: 0.06em;
      color: var(--text);
      text-decoration: none;
      cursor: pointer;
    }}
    .scroll-arrow-box {{
      position: relative;
      width: 22px;
      height: 22px;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .bob-arrow {{
      animation: arrowBob 2s infinite ease-in-out;
    }}
    @keyframes arrowBob {{
      0%, 100% {{ transform: translateY(0); }}
      50% {{ transform: translateY(4px); }}
    }}

    /* SECTION 2: PRODUCT */
    #section-product {{
      height: 100vh;
    }}
    .tab-carousel-strip {{
      position: absolute;
      top: 14%;
      left: 17%;
      height: 74px;
      display: flex;
      align-items: center;
      gap: 20px;
      transition: transform 0.9s cubic-bezier(0.65, 0, 0.2, 1);
    }}
    .carousel-tab {{
      width: 33vw;
      height: 64px;
      display: flex;
      align-items: center;
      border: 1px solid transparent;
      padding: 0 16px;
      gap: 16px;
      position: relative;
      opacity: 0.14;
      transition: opacity 0.6s ease, border-color 0.6s ease;
      background: rgba(239, 236, 230, 0.8);
      flex-shrink: 0;
    }}
    .carousel-tab.passed {{
      opacity: 0;
    }}
    .carousel-tab.active {{
      opacity: 1;
      border: 1px solid var(--text);
    }}
    .carousel-tab-num {{
      width: 68px;
      font-family: 'IBM Plex Mono', monospace;
      font-size: 13px;
      letter-spacing: 0.05em;
      flex-shrink: 0;
    }}
    .carousel-tab-label {{
      font-family: 'Schibsted Grotesk', sans-serif;
      font-size: 18px;
      font-weight: 500;
      white-space: nowrap;
    }}

    .product-bottom-left {{
      position: absolute;
      bottom: 8%;
      left: 17%;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}
    .product-dots {{
      font-family: 'IBM Plex Mono', monospace;
      font-size: 14px;
      letter-spacing: 0.2em;
    }}
    .product-headline {{
      font-size: clamp(30px, 3.05vw, 54px);
      font-weight: 400;
      letter-spacing: -0.02em;
      line-height: 1.15;
    }}
    .gateway-box {{
      display: inline-block;
      border: 1px solid var(--text);
      border-radius: 8px;
      padding: 4px 20px;
      margin-bottom: 6px;
      background: rgba(239, 236, 230, 0.88);
    }}

    /* SECTION 3: REVIEWS */
    #section-reviews {{
      height: 100vh;
    }}
    .review-header-strip {{
      position: absolute;
      top: 14%;
      left: 17%;
      right: 17%;
      height: 60px;
      border-bottom: 1px solid var(--grid);
      display: flex;
      align-items: center;
      gap: 18px;
    }}
    .tstmnl-tag {{
      font-family: 'IBM Plex Mono', monospace;
      font-size: 11px;
      letter-spacing: 0.05em;
    }}
    .review-avatar-svg {{
      width: 56px;
      height: 56px;
      border-radius: 6px;
      overflow: hidden;
      border: 1px solid var(--grid);
      flex-shrink: 0;
    }}
    .review-author-info {{
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 15px;
      font-weight: 500;
    }}
    .review-author-dot {{
      width: 4px;
      height: 4px;
      border-radius: 50%;
      background: #141414;
    }}
    .review-author-role {{
      font-family: 'IBM Plex Mono', monospace;
      font-size: 11px;
      color: var(--dim);
      letter-spacing: 0.04em;
    }}

    .review-quote-wrapper {{
      position: absolute;
      top: 26%;
      left: 17%;
      width: 23vw;
      display: flex;
      flex-direction: column;
      gap: 24px;
      transition: opacity 0.45s ease, transform 0.45s ease;
    }}
    .review-quote-wrapper.fading {{
      opacity: 0;
      transform: translateY(10px);
    }}
    .review-quote-text {{
      font-size: clamp(20px, 2.3vw, 40px);
      line-height: 1.19;
      font-weight: 400;
      letter-spacing: -0.01em;
      background: rgba(239, 236, 230, 0.88);
      padding: 6px 10px;
    }}
    .try-yourself-link {{
      display: flex;
      align-items: center;
      gap: 12px;
      font-family: 'IBM Plex Mono', monospace;
      font-size: 11px;
      letter-spacing: 0.05em;
      color: var(--text);
      text-decoration: none;
      background: rgba(239, 236, 230, 0.88);
      padding: 4px 8px;
      width: fit-content;
    }}
    .try-yourself-link::before {{
      content: '';
      display: inline-block;
      width: 24px;
      height: 1px;
      background: var(--text);
    }}

    .review-arrows {{
      position: absolute;
      bottom: 8%;
      left: 17%;
      display: flex;
      gap: 16px;
    }}
    .arrow-btn {{
      width: 38px;
      height: 38px;
      border: 1px solid var(--text);
      background: transparent;
      font-size: 16px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: background 0.2s;
    }}
    .arrow-btn:hover {{
      background: rgba(20, 20, 20, 0.06);
    }}

    .review-ghost {{
      position: absolute;
      top: 26%;
      left: 85%;
      width: 22vw;
      font-size: clamp(20px, 2.3vw, 40px);
      line-height: 1.19;
      opacity: 0.10;
      pointer-events: none;
    }}

    /* Footer */
    footer {{
      position: relative;
      height: 30vh;
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: 'IBM Plex Mono', monospace;
      font-size: 12px;
      letter-spacing: 0.08em;
      color: var(--dim);
      border-top: 1px solid var(--grid);
      background: var(--bg);
      z-index: 10;
    }}

    /* Mobile responsive (<= 900px) */
    @media (max-width: 900px) {{
      .grid-guide.guide-left,
      .grid-guide.guide-right,
      .nav-menu,
      .nav-pad-cell,
      .right-rail,
      .feature-list,
      .review-ghost,
      .prompt-rule,
      .intro-bottom-rule {{
        display: none !important;
      }}

      .top-bar {{
        padding: 0 16px;
      }}

      .navbar {{
        grid-template-columns: 1fr auto;
        padding: 0 16px;
      }}
      .nav-logo-cell {{
        padding-left: 0;
      }}

      .prompt-box-wrapper {{
        left: 16px !important;
        right: 16px !important;
        width: auto !important;
        top: 18% !important;
      }}

      .intro-bottom-left {{
        left: 16px !important;
        bottom: 16px !important;
      }}
      .intro-scroll-link {{
        right: 16px !important;
        bottom: 16px !important;
      }}
      .intro-subline {{
        left: 16px !important;
        bottom: 120px !important;
      }}

      .tab-carousel-strip {{
        left: 16px !important;
      }}
      .carousel-tab {{
        width: 80vw !important;
      }}
      .product-bottom-left {{
        left: 16px !important;
        bottom: 24px !important;
      }}

      .review-header-strip {{
        left: 16px !important;
        right: 16px !important;
      }}
      .review-quote-wrapper {{
        left: 16px !important;
        width: calc(100% - 32px) !important;
        top: 24% !important;
      }}
      .review-arrows {{
        left: 16px !important;
        bottom: 24px !important;
      }}
    }}
  </style>

  <script type="importmap">
  {{
    "imports": {{
      "three": "https://unpkg.com/three@0.160.0/build/three.module.js",
      "three/addons/": "https://unpkg.com/three@0.160.0/examples/jsm/"
    }}
  }}
  </script>
</head>
<body>

  <!-- Fullscreen WebGL Canvas -->
  <canvas id="robot-canvas"></canvas>

  <!-- 3 Grid Guides -->
  <div class="grid-guide guide-left"></div>
  <div class="grid-guide guide-center"></div>
  <div class="grid-guide guide-right"></div>

  <!-- Top Bar -->
  <div class="top-bar" id="top-bar">
    <div class="top-bar-content">
      <strong>New:</strong> Nova Agent V1 Is Here - The Home for On-chain AI Agents ↗
    </div>
    <button class="top-bar-close" id="top-bar-close">×</button>
  </div>

  <!-- Navigation -->
  <nav class="navbar" id="navbar">
    <div class="nav-logo-cell">
      <svg class="nav-logo-icon" viewBox="0 0 28 28">
        <defs>
          <linearGradient id="navLogoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#ffb347" />
            <stop offset="50%" stop-color="#ff5a5f" />
            <stop offset="100%" stop-color="#ff3d8b" />
          </linearGradient>
        </defs>
        <path d="M 22 7 L 11 7 A 4 4 0 0 0 7 11 L 7 17 A 4 4 0 0 0 11 21 L 22 21" fill="none" stroke="url(#navLogoGrad)" stroke-width="2.5" stroke-linecap="round"/>
        <circle cx="12" cy="14" r="1.5" fill="#141414"/>
        <circle cx="17" cy="14" r="1.5" fill="#141414"/>
      </svg>
      <span class="nav-logo-text">NOVA AGENT</span>
    </div>

    <div class="nav-menu">
      <a href="#solutions">Solutions▾</a>
      <a href="#pricing">Pricing</a>
      <a href="#learn">Learn▾</a>
      <a href="#nova">$NOVA▾</a>
      <a href="#community">Community▾</a>
      <a href="#contact">Contact us</a>
    </div>

    <div class="nav-pad-cell">
      <a href="#">Nova Pad ↗</a>
    </div>

    <div class="nav-btn-cell">
      <a href="#section-product" class="launch-btn">•• LAUNCH NOVA</a>
    </div>
  </nav>

  <!-- Right Rail -->
  <aside class="right-rail">
    <div class="dots-track">
      <div class="rail-dial-badge" id="rail-dial">
        <svg class="rail-dial-icon" viewBox="0 0 12 12" fill="none">
          <circle cx="6" cy="6" r="4.5" stroke="#141414" stroke-width="1"/>
          <circle cx="6" cy="6" r="1.5" fill="#ff5a5f"/>
          <line x1="6" y1="6" x2="6" y2="2.5" stroke="#ff5a5f" stroke-width="1.2"/>
        </svg>
        <span id="rail-label">INTRO</span>
      </div>
      <div class="rail-dot"></div>
      <div class="rail-dot"></div>
      <div class="rail-dot"></div>
      <div class="rail-dot"></div>
      <div class="rail-dot"></div>
      <div class="rail-dot"></div>
      <div class="rail-dot"></div>
      <div class="rail-dot"></div>
      <div class="rail-dot"></div>
      <div class="rail-dot"></div>
      <div class="rail-dot"></div>
      <div class="rail-dot"></div>
      <div class="rail-dot"></div>
      <div class="rail-dot"></div>
    </div>
    <div class="rail-menu-label">≡ MENU</div>
  </aside>

  <!-- SECTION 1: INTRO -->
  <section id="section-intro">
    <div class="prompt-box-wrapper rv">
      <div class="prompt-tab">“</div>
      <div class="prompt-box">
        <div class="corner-bracket cb-tl"></div>
        <div class="corner-bracket cb-tr"></div>
        <div class="corner-bracket cb-bl"></div>
        <div class="corner-bracket cb-br"></div>
        <span class="prompt-typing-text" id="typing-prompt"></span><span class="prompt-caret"></span>
      </div>
      <div class="prompt-faint-next" id="faint-next">NEXT: AUDIT THIS CONTRACT FOR REENTRANCY VULNERABILITIES.</div>
    </div>

    <div class="prompt-rule"></div>

    <div class="feature-list rv rv-d1">
      <div class="feature-row">DEVELOPMENT</div>
      <div class="feature-row">MARKET ANALYSIS</div>
      <div class="feature-row">AI TRADING</div>
      <div class="feature-row dim">AND MUCH MORE</div>
    </div>

    <div class="intro-bottom-left rv rv-d2">
      <div class="unleash-tag">UNLEASH THE POWER OF</div>
      <div class="intro-headline">
        <div class="headline-box thinking-box">
          <svg class="box-border-svg" preserveAspectRatio="none" viewBox="0 0 100 100">
            <defs>
              <linearGradient id="thinkGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#ff8a3d" />
                <stop offset="50%" stop-color="#ff5a5f" />
                <stop offset="100%" stop-color="#ff3d8b" />
              </linearGradient>
            </defs>
            <polygon points="1,1 99,1 99,78 82,99 1,99" fill="none" stroke="url(#thinkGrad)" stroke-width="2" vector-effect="non-scaling-stroke" />
          </svg>
          Thinking
        </div>
        <div class="headline-box machines-box">
          <svg class="box-border-svg" preserveAspectRatio="none" viewBox="0 0 100 100">
            <defs>
              <linearGradient id="machGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#ffb347" />
                <stop offset="50%" stop-color="#ff8a3d" />
                <stop offset="100%" stop-color="#ff5a5f" />
              </linearGradient>
            </defs>
            <rect x="1" y="1" width="98" height="98" fill="none" stroke="url(#machGrad)" stroke-width="2" vector-effect="non-scaling-stroke" />
          </svg>
          Machines
        </div>
      </div>
    </div>

    <div class="intro-subline rv rv-d3">
      Your personal expert in all crypto & blockchain related topics.
    </div>

    <div class="intro-bottom-rule"></div>

    <a href="#section-product" class="intro-scroll-link rv rv-d3">
      <span>SCROLL</span>
      <div class="scroll-arrow-box">
        <div class="corner-bracket cb-tl"></div>
        <div class="corner-bracket cb-tr"></div>
        <div class="corner-bracket cb-bl"></div>
        <div class="corner-bracket cb-br"></div>
        <span class="bob-arrow">↓</span>
      </div>
    </a>
  </section>

  <!-- SECTION 2: PRODUCT -->
  <section id="section-product">
    <div class="tab-carousel-strip" id="carousel-strip">
      <!-- 10 tabs generated dynamically -->
    </div>

    <div class="product-bottom-left rv">
      <div class="product-dots">··</div>
      <div class="product-headline">
        <div class="gateway-box">Your Gateway</div>
        <div>To Web3 AI</div>
      </div>
    </div>
  </section>

  <!-- SECTION 3: REVIEWS -->
  <section id="section-reviews">
    <div class="review-header-strip rv">
      <span class="tstMNL-tag">TSTMNL [<span id="review-num">01</span>]</span>
      <svg class="review-avatar-svg" viewBox="0 0 56 56" fill="none">
        <rect width="56" height="56" fill="#dfdad1"/>
        <path d="M0 14H56 M0 28H56 M0 42H56" stroke="#cec8be" stroke-width="1.5"/>
        <path d="M14 0V14 M42 0V14 M28 14V28 M14 28V42 M42 28V42 M28 42V56" stroke="#cec8be" stroke-width="1.5"/>
        <path d="M12 52 C12 40, 20 38, 28 38 C36 38, 44 40, 44 52" fill="#141414"/>
        <circle cx="28" cy="25" r="9" fill="#141414"/>
      </svg>
      <div class="review-author-info">
        <span id="review-author-name">Ilan Brooks</span>
        <div class="review-author-dot"></div>
        <span class="review-author-role" id="review-author-role">Founder of Halden Capital</span>
      </div>
    </div>

    <div class="review-quote-wrapper rv rv-d1" id="quote-wrapper">
      <div class="review-quote-text" id="quote-text">
        “Smart contract auditing has always been a bottleneck for our startups, Nova Agent solves this problem in seconds.”
      </div>
      <a href="#section-product" class="try-yourself-link">Try for yourself (Click Here)</a>
    </div>

    <div class="review-arrows rv rv-d2">
      <button class="arrow-btn" id="prev-review-btn">←</button>
      <button class="arrow-btn" id="next-review-btn">→</button>
    </div>

    <div class="review-ghost" id="ghost-quote">
      “Nova Agent is a vital asset for Web3 investors, simplifying the research process effortlessly.”
    </div>
  </section>

  <!-- FOOTER -->
  <footer>
    NOVA AGENT · 2026
  </footer>

  <!-- Three.js App Code -->
  <script type="module">
    import * as THREE from 'three';
    import {{ RoundedBoxGeometry }} from 'three/addons/geometries/RoundedBoxGeometry.js';
    import {{ RoomEnvironment }} from 'three/addons/environments/RoomEnvironment.js';

    /* --- THREE.JS SCENE SETUP --- */
    const canvas = document.getElementById('robot-canvas');
    const renderer = new THREE.WebGLRenderer({{ canvas, antialias: true, alpha: true }});
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.05;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    const scene = new THREE.Scene();

    // Camera (30 deg FOV)
    const camera = new THREE.PerspectiveCamera(30, window.innerWidth / window.innerHeight, 0.1, 100);
    camera.position.set(0, 1.1, 11.6);

    // Environment map
    const pmremGenerator = new THREE.PMREMGenerator(renderer);
    pmremGenerator.compileEquirectangularShader();
    const roomEnv = new RoomEnvironment();
    scene.environment = pmremGenerator.fromScene(roomEnv, 0.04).texture;

    // Lights
    const hemiLight = new THREE.HemisphereLight(0xfff6ee, 0xd9d2c8, 0.7);
    scene.add(hemiLight);

    const keyLight = new THREE.DirectionalLight(0xfff3e6, 1.7);
    keyLight.position.set(-3, 5, 4);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.width = 1024;
    keyLight.shadow.mapSize.height = 1024;
    keyLight.shadow.radius = 6;
    keyLight.shadow.bias = -0.0005;
    keyLight.shadow.camera.near = 1;
    keyLight.shadow.camera.far = 20;
    keyLight.shadow.camera.left = -3;
    keyLight.shadow.camera.right = 3;
    keyLight.shadow.camera.top = 4;
    keyLight.shadow.camera.bottom = -4;
    scene.add(keyLight);

    const rimLight = new THREE.DirectionalLight(0xfff0e6, 1.2);
    rimLight.position.set(4, 2, -4);
    scene.add(rimLight);

    const fillLight = new THREE.PointLight(0xff9a6a, 2.2, 6);
    fillLight.position.set(-3.2, 1.2, 0.6);
    scene.add(fillLight);

    /* --- MATERIALS --- */
    const shellMat = new THREE.MeshPhysicalMaterial({{
      color: 0xeeebe6,
      roughness: 0.38,
      clearcoat: 0.45,
      clearcoatRoughness: 0.3
    }});

    const shellLightMat = new THREE.MeshPhysicalMaterial({{
      color: 0xf8f6f2,
      roughness: 0.34,
      clearcoat: 0.45,
      clearcoatRoughness: 0.3
    }});

    const jointsMat = new THREE.MeshPhysicalMaterial({{
      color: 0x1b1b1f,
      roughness: 0.55,
      metalness: 0.3
    }});

    const deepDarkMat = new THREE.MeshPhysicalMaterial({{
      color: 0x0f0f12,
      roughness: 0.7,
      metalness: 0.1
    }});

    const pedestalMat = new THREE.MeshPhysicalMaterial({{
      color: 0x2a2928,
      roughness: 0.9
    }});

    // Conic gradient for ring
    const ringCanvas = document.createElement('canvas');
    ringCanvas.width = 512;
    ringCanvas.height = 512;
    const ringCtx = ringCanvas.getContext('2d');
    const conic = ringCtx.createConicGradient(200 * Math.PI / 180, 256, 256);
    conic.addColorStop(0, '#ffb347');
    conic.addColorStop(0.18, '#ff8a3d');
    conic.addColorStop(0.34, '#ff5a5f');
    conic.addColorStop(0.50, '#ff3d8b');
    conic.addColorStop(0.66, '#ff5a5f');
    conic.addColorStop(0.82, '#ff8a3d');
    conic.addColorStop(1.0, '#ffb347');
    ringCtx.fillStyle = conic;
    ringCtx.fillRect(0, 0, 512, 512);

    const ringTexture = new THREE.CanvasTexture(ringCanvas);
    ringTexture.colorSpace = THREE.SRGBColorSpace;

    const ringMat = new THREE.MeshPhysicalMaterial({{
      map: ringTexture,
      emissive: new THREE.Color(0xffffff),
      emissiveMap: ringTexture,
      emissiveIntensity: 0.22,
      roughness: 0.5,
      clearcoat: 0.35
    }});

    // Face Screen Canvas
    const faceCanvas = document.createElement('canvas');
    faceCanvas.width = 512;
    faceCanvas.height = 512;
    const faceCtx = faceCanvas.getContext('2d');
    const faceTexture = new THREE.CanvasTexture(faceCanvas);
    faceTexture.colorSpace = THREE.SRGBColorSpace;

    const screenMat = new THREE.MeshPhysicalMaterial({{
      color: 0x050508,
      roughness: 0.15,
      clearcoat: 1.0,
      clearcoatRoughness: 0.1,
      emissive: new THREE.Color(0xffffff),
      emissiveMap: faceTexture,
      emissiveIntensity: 1.6
    }});

    /* --- ROBOT GEOMETRY HIERARCHY --- */
    const robotRoot = new THREE.Group();
    scene.add(robotRoot);

    const robotBodyGroup = new THREE.Group();
    robotRoot.add(robotBodyGroup);

    // Pedestal (receives shadow)
    const pedestal = new THREE.Mesh(
      new THREE.BoxGeometry(1.7, 1.6, 1.7),
      pedestalMat
    );
    pedestal.position.set(0, -2.22, 0);
    pedestal.receiveShadow = true;
    robotRoot.add(pedestal);

    // Legs
    function createLeg(xSide) {{
      const legGroup = new THREE.Group();
      legGroup.position.set(xSide * 0.35, -0.65, 0);

      // Hip ball
      const hip = new THREE.Mesh(new THREE.SphereGeometry(0.14, 20, 20), jointsMat);
      hip.position.set(0, 0, 0);
      hip.castShadow = true;
      legGroup.add(hip);

      // Leg block
      const leg = new THREE.Mesh(new RoundedBoxGeometry(0.30, 0.58, 0.32, 3, 0.08), shellMat);
      leg.position.set(0, -0.32, 0);
      leg.castShadow = true;
      legGroup.add(leg);

      // Ankle
      const ankle = new THREE.Mesh(new THREE.SphereGeometry(0.12, 16, 16), jointsMat);
      ankle.position.set(0, -0.65, 0);
      ankle.castShadow = true;
      legGroup.add(ankle);

      // Foot
      const foot = new THREE.Mesh(new RoundedBoxGeometry(0.34, 0.18, 0.54, 3, 0.06), shellLightMat);
      foot.position.set(0, -0.76, 0.1);
      foot.castShadow = true;
      legGroup.add(foot);

      return legGroup;
    }}
    robotBodyGroup.add(createLeg(-1));
    robotBodyGroup.add(createLeg(1));

    // Torso
    const torsoMesh = new THREE.Mesh(
      new RoundedBoxGeometry(1.22, 1.12, 0.92, 4, 0.24),
      shellMat
    );
    torsoMesh.position.set(0, 0.16, 0);
    torsoMesh.castShadow = true;
    robotBodyGroup.add(torsoMesh);

    // Chest-top slab
    const chestSlab = new THREE.Mesh(
      new RoundedBoxGeometry(0.96, 0.22, 0.68, 3, 0.06),
      shellLightMat
    );
    chestSlab.position.set(0, 0.62, 0.06);
    chestSlab.castShadow = true;
    robotBodyGroup.add(chestSlab);

    // LEDs on chest
    const ledColors = [0xff8a3d, 0xff5a5f, 0xff3d8b];
    [-0.16, 0, 0.16].forEach((x, idx) => {{
      const led = new THREE.Mesh(
        new THREE.SphereGeometry(0.032, 16, 16),
        new THREE.MeshBasicMaterial({{ color: ledColors[idx] }})
      );
      led.position.set(x, 0.44, 0.48);
      robotBodyGroup.add(led);
    }});

    // Two dark vertical slots with lips
    [-0.22, 0.22].forEach(x => {{
      const slot = new THREE.Mesh(
        new RoundedBoxGeometry(0.06, 0.26, 0.04, 2, 0.02),
        jointsMat
      );
      slot.position.set(x, 0.12, 0.47);
      robotBodyGroup.add(slot);

      const lip = new THREE.Mesh(
        new THREE.TorusGeometry(0.045, 0.018, 12, 16, Math.PI),
        jointsMat
      );
      lip.position.set(x, 0.25, 0.47);
      lip.rotation.z = Math.PI;
      robotBodyGroup.add(lip);
    }});

    // Pelvis
    const pelvis = new THREE.Mesh(
      new RoundedBoxGeometry(0.85, 0.28, 0.7, 3, 0.1),
      jointsMat
    );
    pelvis.position.set(0, -0.44, 0);
    robotBodyGroup.add(pelvis);

    // Arms
    const leftArmGroup = new THREE.Group();
    const rightArmGroup = new THREE.Group();

    function assembleArm(group, side) {{
      group.position.set(side * 0.72, 0.54, 0);
      group.rotation.z = side * 0.16;

      const shoulder = new THREE.Mesh(new THREE.SphereGeometry(0.16, 20, 20), jointsMat);
      shoulder.castShadow = true;
      group.add(shoulder);

      const upperArm = new THREE.Mesh(new RoundedBoxGeometry(0.22, 0.46, 0.22, 3, 0.06), shellMat);
      upperArm.position.set(0, -0.26, 0);
      upperArm.castShadow = true;
      group.add(upperArm);

      const elbow = new THREE.Mesh(new THREE.SphereGeometry(0.13, 16, 16), jointsMat);
      elbow.position.set(0, -0.52, 0);
      elbow.castShadow = true;
      group.add(elbow);

      const forearm = new THREE.Group();
      forearm.position.set(0, -0.52, 0);
      forearm.rotation.x = -0.35;

      const armLower = new THREE.Mesh(new RoundedBoxGeometry(0.20, 0.40, 0.20, 3, 0.06), shellMat);
      armLower.position.set(0, -0.22, 0);
      armLower.castShadow = true;
      forearm.add(armLower);

      const hand = new THREE.Mesh(new RoundedBoxGeometry(0.18, 0.18, 0.22, 3, 0.05), shellLightMat);
      hand.position.set(0, -0.46, 0.02);
      hand.castShadow = true;
      forearm.add(hand);

      const thumb = new THREE.Mesh(new RoundedBoxGeometry(0.06, 0.09, 0.12, 2, 0.02), shellLightMat);
      thumb.position.set(side * -0.09, -0.44, 0.06);
      forearm.add(thumb);

      group.add(forearm);
      group.forearmRef = forearm;
    }}
    assembleArm(leftArmGroup, -1);
    assembleArm(rightArmGroup, 1);
    robotBodyGroup.add(leftArmGroup);
    robotBodyGroup.add(rightArmGroup);

    // Neck
    const neck = new THREE.Mesh(
      new THREE.CylinderGeometry(0.26, 0.26, 0.24, 24),
      jointsMat
    );
    neck.position.set(0, 0.78, 0);
    robotBodyGroup.add(neck);

    // Head pivot group at y .78
    const headPivot = new THREE.Group();
    headPivot.position.set(0, 0.78, 0);
    robotBodyGroup.add(headPivot);

    const headCenterGroup = new THREE.Group();
    headCenterGroup.position.set(0, 0.78, 0);
    headPivot.add(headCenterGroup);

    // Skull
    const skull = new THREE.Mesh(
      new RoundedBoxGeometry(1.5, 1.42, 1.3, 4, 0.2),
      shellMat
    );
    skull.castShadow = true;
    headCenterGroup.add(skull);

    // Dark back block with scattered circuit bars
    const darkBackBlock = new THREE.Mesh(
      new RoundedBoxGeometry(1.28, 1.14, 0.9, 3, 0.1),
      deepDarkMat
    );
    darkBackBlock.position.set(0, 0, -0.26);
    headCenterGroup.add(darkBackBlock);

    // ~26 circuit bars
    const barGeo1 = new THREE.BoxGeometry(0.04, 0.04, 0.12);
    const barGeo2 = new THREE.BoxGeometry(0.12, 0.04, 0.04);
    for (let i = 0; i < 26; i++) {{
      const isTop = i > 16;
      const bar = new THREE.Mesh(isTop ? barGeo1 : barGeo2, jointsMat);
      if (!isTop) {{
        bar.position.set(
          (Math.random() - 0.5) * 1.1,
          (Math.random() - 0.5) * 0.95,
          -0.72
        );
      }} else {{
        bar.position.set(
          (Math.random() - 0.5) * 1.0,
          0.58,
          -0.2 - Math.random() * 0.4
        );
      }}
      headCenterGroup.add(bar);
    }}

    // Extruded rounded-rect frame with conic gradient UV remapping
    function createRoundedRectShape(w, h, r) {{
      const s = new THREE.Shape();
      const x = -w / 2, y = -h / 2;
      s.moveTo(x + r, y);
      s.lineTo(x + w - r, y);
      s.quadraticCurveTo(x + w, y, x + w, y + r);
      s.lineTo(x + w, y + h - r);
      s.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
      s.lineTo(x + r, y + h);
      s.quadraticCurveTo(x, y + h, x, y + h - r);
      s.lineTo(x, y + r);
      s.quadraticCurveTo(x, y, x + r, y);
      return s;
    }}

    const outerFrame = createRoundedRectShape(1.5, 1.44, 0.3);
    const innerFrameHole = new THREE.Path();
    const iw = 1.08, ih = 1.02, ir = 0.2;
    const ix = -iw / 2, iy = -ih / 2;
    innerFrameHole.moveTo(ix + ir, iy);
    innerFrameHole.lineTo(ix + iw - ir, iy);
    innerFrameHole.quadraticCurveTo(ix + iw, iy, ix + iw, iy + ir);
    innerFrameHole.lineTo(ix + iw, iy + ih - ir);
    innerFrameHole.quadraticCurveTo(ix + iw, iy + ih, ix + iw - ir, iy + ih);
    innerFrameHole.lineTo(ix + ir, iy + ih);
    innerFrameHole.quadraticCurveTo(ix, iy + ih, ix, iy + ih - ir);
    innerFrameHole.lineTo(ix, iy + ir);
    innerFrameHole.quadraticCurveTo(ix, iy, ix + ir, iy);
    outerFrame.holes.push(innerFrameHole);

    const ringGeo = new THREE.ExtrudeGeometry(outerFrame, {{
      depth: 0.1,
      bevelEnabled: true,
      bevelSegments: 4,
      steps: 1,
      bevelSize: 0.03,
      bevelThickness: 0.03
    }});
    ringGeo.center();

    // Remap UVs
    ringGeo.computeBoundingBox();
    const rMin = ringGeo.boundingBox.min;
    const rMax = ringGeo.boundingBox.max;
    const rxSpan = rMax.x - rMin.x;
    const rySpan = rMax.y - rMin.y;
    const pos = ringGeo.attributes.position;
    const uvs = ringGeo.attributes.uv;
    for (let i = 0; i < pos.count; i++) {{
      const u = (pos.getX(i) - rMin.x) / rxSpan;
      const v = (pos.getY(i) - rMin.y) / rySpan;
      uvs.setXY(i, u, v);
    }}
    uvs.needsUpdate = true;

    const ringMesh = new THREE.Mesh(ringGeo, ringMat);
    ringMesh.position.set(0, 0, 0.60);
    headCenterGroup.add(ringMesh);

    // Bezel: inner shell-light frame at z .62
    const bezelOuter = createRoundedRectShape(1.10, 1.04, 0.2);
    const bezelHole = new THREE.Path();
    const bw = 0.92, bh = 0.86, br = 0.1;
    const bx = -bw / 2, by = -bh / 2;
    bezelHole.moveTo(bx + br, by);
    bezelHole.lineTo(bx + bw - br, by);
    bezelHole.quadraticCurveTo(bx + bw, by, bx + bw, by + br);
    bezelHole.lineTo(bx + bw, by + bh - br);
    bezelHole.quadraticCurveTo(bx + bw, by + bh, bx + bw - br, by + bh);
    bezelHole.lineTo(bx + br, by + bh);
    bezelHole.quadraticCurveTo(bx, by + bh, bx, by + bh - br);
    bezelHole.lineTo(bx, by + br);
    bezelHole.quadraticCurveTo(bx, by, bx + br, by);
    bezelOuter.holes.push(bezelHole);

    const bezelGeo = new THREE.ExtrudeGeometry(bezelOuter, {{
      depth: 0.04,
      bevelEnabled: false
    }});
    bezelGeo.center();
    const bezelMesh = new THREE.Mesh(bezelGeo, shellLightMat);
    bezelMesh.position.set(0, 0, 0.62);
    headCenterGroup.add(bezelMesh);

    // Screen: rounded plate .9 x .84 at z .66
    const screenMesh = new THREE.Mesh(
      new RoundedBoxGeometry(0.9, 0.84, 0.04, 3, 0.08),
      screenMat
    );
    screenMesh.position.set(0, 0, 0.66);
    headCenterGroup.add(screenMesh);

    // Ears: cylinder r .22 on both sides with caps
    const earGeo = new THREE.CylinderGeometry(0.22, 0.22, 0.18, 24);
    earGeo.rotateZ(Math.PI / 2);

    const leftEar = new THREE.Mesh(earGeo, shellMat);
    leftEar.position.set(-0.82, 0, 0);
    headCenterGroup.add(leftEar);

    const rightEar = new THREE.Mesh(earGeo, shellMat);
    rightEar.position.set(0.82, 0, 0);
    headCenterGroup.add(rightEar);

    // Dark cable loop on right ear
    const cableGeo = new THREE.TorusGeometry(0.24, 0.04, 16, 32, Math.PI);
    const cableMesh = new THREE.Mesh(cableGeo, jointsMat);
    cableMesh.position.set(0.88, -0.16, 0);
    cableMesh.rotation.y = Math.PI / 2;
    headCenterGroup.add(cableMesh);


    /* --- FACE SCREEN ANIMATION (Eyes + Quote) --- */
    let eyeAlpha = 1.0;
    let quoteAlpha = 0.0;
    let isBlinking = false;
    let blinkStartTime = 0;
    let nextBlinkTime = performance.now() + 3000;

    function renderFaceCanvas(now) {{
      faceCtx.fillStyle = '#060608';
      faceCtx.fillRect(0, 0, 512, 512);

      // Check blink
      if (!isBlinking && now >= nextBlinkTime) {{
        isBlinking = true;
        blinkStartTime = now;
      }}
      let vScale = 1.0;
      if (isBlinking) {{
        const progress = (now - blinkStartTime) / 180; // 0.18s
        if (progress >= 1.0) {{
          isBlinking = false;
          nextBlinkTime = now + 2500 + Math.random() * 3000;
        }} else {{
          const squash = Math.sin(progress * Math.PI);
          vScale = 1.0 - 0.9 * squash; // squashes to 10%
        }}
      }}

      // Eyes rendering
      if (eyeAlpha > 0.01) {{
        faceCtx.save();
        faceCtx.globalAlpha = eyeAlpha;
        faceCtx.fillStyle = '#ffffff';
        faceCtx.shadowColor = '#ffffff';
        faceCtx.shadowBlur = 18;

        // Left eye at (196, 262)
        faceCtx.beginPath();
        faceCtx.ellipse(196, 262, 30, Math.max(1, 38 * vScale), 0, 0, Math.PI * 2);
        faceCtx.fill();

        // Right eye at (316, 252)
        faceCtx.beginPath();
        faceCtx.ellipse(316, 252, 30, Math.max(1, 38 * vScale), 0, 0, Math.PI * 2);
        faceCtx.fill();

        faceCtx.restore();
      }}

      // Quote mode rendering
      if (quoteAlpha > 0.01) {{
        faceCtx.save();
        faceCtx.globalAlpha = quoteAlpha;
        faceCtx.fillStyle = '#ffffff';
        faceCtx.shadowColor = '#ffffff';
        faceCtx.shadowBlur = 18;
        faceCtx.font = '900 560px "Arial Black", sans-serif';
        faceCtx.textAlign = 'center';
        faceCtx.textBaseline = 'middle';
        faceCtx.fillText('“', 256, 400);
        faceCtx.restore();
      }}

      faceTexture.needsUpdate = true;
    }}

    /* --- CAMERA INTERPOLATION & MOTION --- */
    let smoothP = 0;
    let targetCursorX = 0;
    let targetCursorY = 0;
    let cursorX = 0;
    let cursorY = 0;

    window.addEventListener('mousemove', (e) => {{
      targetCursorX = (e.clientX / window.innerWidth) * 2 - 1;
      targetCursorY = (e.clientY / window.innerHeight) * 2 - 1;
    }});

    function easeInOutCubic(t) {{
      return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    }}

    const clock = new THREE.Clock();

    /* --- RIGHT RAIL LOGIC --- */
    const railDial = document.getElementById('rail-dial');
    const railLabel = document.getElementById('rail-label');

    function updateRightRail(p) {{
      if (!railDial || !railLabel) return;
      if (p < 0.5) {{
        railDial.style.top = '0%';
        railLabel.textContent = 'INTRO';
      }} else if (p < 1.5) {{
        railDial.style.top = '31%';
        railLabel.textContent = 'PRODUCT';
      }} else {{
        railDial.style.top = '62%';
        railLabel.textContent = 'REVIEWS';
      }}
    }}

    function animate() {{
      requestAnimationFrame(animate);
      const now = performance.now();
      const time = clock.getElapsedTime();

      // Scroll parameter p in [0, 2]
      const rawP = Math.min(2, Math.max(0, window.scrollY / window.innerHeight));
      smoothP += (rawP - smoothP) * 0.08;

      // Pointer smoothing (6%)
      cursorX += (targetCursorX - cursorX) * 0.06;
      cursorY += (targetCursorY - cursorY) * 0.06;

      // Face mode toggle at 1.55
      const targetIsQuote = smoothP > 1.55;
      if (targetIsQuote) {{
        quoteAlpha = Math.min(1.0, quoteAlpha + 0.05);
        eyeAlpha = Math.max(0.0, eyeAlpha - 0.05);
      }} else {{
        eyeAlpha = Math.min(1.0, eyeAlpha + 0.05);
        quoteAlpha = Math.max(0.0, quoteAlpha - 0.05);
      }}
      renderFaceCanvas(now);

      // Camera & Pose interpolation
      // Intro: z 11.6, y 1.1, look y 0.55, body yaw -0.42, head yaw -0.6, pitch 0.16, roll 0.22
      // Product/Reviews: z 6.9, y 1.95, look y 1.72, body yaw -0.2, head yaw -0.06, pitch 0.04, roll 0
      const blend = easeInOutCubic(Math.min(1.0, smoothP));

      let camZ = 11.6 + (6.9 - 11.6) * blend;
      let camY = 1.1 + (1.95 - 1.1) * blend;
      let lookY = 0.55 + (1.72 - 0.55) * blend;

      if (window.innerWidth <= 900) {{
        camZ *= 1.25;
      }}

      // Apply pointer parallax to camera
      camera.position.x = cursorX * 0.25;
      camera.position.y = camY - cursorY * 0.1;
      camera.position.z = camZ;
      camera.lookAt(0, lookY, 0);

      // Body yaw
      const baseBodyYaw = -0.42 + (-0.2 - (-0.42)) * blend;
      robotBodyGroup.rotation.y = baseBodyYaw + cursorX * 0.12;

      // Head rotations
      const baseHeadYaw = -0.6 + (-0.06 - (-0.6)) * blend;
      const baseHeadPitch = 0.16 + (0.04 - 0.16) * blend;
      const baseHeadRoll = 0.22 + (0 - 0.22) * blend;

      headPivot.rotation.y = baseHeadYaw + cursorX * 0.45;
      headPivot.rotation.x = baseHeadPitch + cursorY * 0.18 + Math.sin(0.9 * time) * 0.02;
      headPivot.rotation.z = baseHeadRoll + Math.sin(0.7 * time) * 0.02;

      // Idle oscillations
      robotBodyGroup.position.y = Math.sin(1.4 * time) * 0.02;
      leftArmGroup.rotation.x = Math.sin(1.4 * time - 0.5) * 0.05;
      rightArmGroup.rotation.x = Math.sin(1.4 * time + 0.5) * 0.05;
      if (leftArmGroup.forearmRef) {{
        leftArmGroup.forearmRef.rotation.x = -0.35 + Math.sin(1.4 * time) * 0.06;
      }}
      if (rightArmGroup.forearmRef) {{
        rightArmGroup.forearmRef.rotation.x = -0.35 + Math.sin(1.4 * time + 0.5) * 0.06;
      }}

      renderer.render(scene, camera);

      // Update right rail dial
      updateRightRail(smoothP);
    }}
    animate();

    window.addEventListener('resize', () => {{
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    }});

    /* --- TOP BAR & NAVBAR SCROLL BEHAVIOR --- */
    const topBar = document.getElementById('top-bar');
    const navbar = document.getElementById('navbar');
    const topBarClose = document.getElementById('top-bar-close');

    let topBarDismissed = false;
    topBarClose.addEventListener('click', () => {{
      topBarDismissed = true;
      topBar.classList.add('hidden');
      navbar.classList.add('scrolled-up');
    }});

    window.addEventListener('scroll', () => {{
      if (!topBarDismissed) {{
        if (window.scrollY > 40) {{
          topBar.classList.add('hidden');
          navbar.classList.add('scrolled-up');
        }} else {{
          topBar.classList.remove('hidden');
          navbar.classList.remove('scrolled-up');
        }}
      }}
    }});

    /* --- AUTO-TYPING PROMPT BOX --- */
    const prompts = [
      "Create a smart contract for a token named NOVA on Ethereum.",
      "Explain what a smart contract does in simple terms.",
      "Audit this contract for reentrancy vulnerabilities.",
      "What is the market sentiment on BTC today?"
    ];

    let promptIdx = 0;
    let charIdx = 0;
    let isDeleting = false;
    const typingEl = document.getElementById('typing-prompt');
    const faintNextEl = document.getElementById('faint-next');

    function updatePromptLoop() {{
      const current = prompts[promptIdx];
      const nextPrompt = prompts[(promptIdx + 1) % prompts.length];
      faintNextEl.textContent = 'NEXT: ' + nextPrompt;

      if (!isDeleting) {{
        charIdx++;
        typingEl.textContent = current.slice(0, charIdx);
        if (charIdx >= current.length) {{
          // Hold for 2.6s
          setTimeout(() => {{
            isDeleting = true;
            updatePromptLoop();
          }}, 2600);
          return;
        }}
        setTimeout(updatePromptLoop, 38);
      }} else {{
        charIdx = Math.max(0, charIdx - 2);
        typingEl.textContent = current.slice(0, charIdx);
        if (charIdx <= 0) {{
          isDeleting = false;
          promptIdx = (promptIdx + 1) % prompts.length;
          // Wait 250ms before typing next
          setTimeout(updatePromptLoop, 250);
          return;
        }}
        setTimeout(updatePromptLoop, 14);
      }}
    }}
    updatePromptLoop();

    /* --- SECTION 2 TAB CAROUSEL --- */
    const tabLabels = [
      "AI Chatbot",
      "NFT Generator",
      "Smart-contract generator",
      "Blockchain & market analytics",
      "AI Trading assistant",
      "Code auditor",
      "Chart & technical analysis",
      "Crypto news AI",
      "Smart-contract auditor",
      "AI Chatbot"
    ];

    const strip = document.getElementById('carousel-strip');
    tabLabels.forEach((label, i) => {{
      const tab = document.createElement('div');
      tab.className = 'carousel-tab' + (i === 0 ? ' active' : '');
      const numStr = String(i + 1).padStart(2, '0');
      tab.innerHTML = `
        <div class="corner-bracket cb-tl"></div>
        <div class="corner-bracket cb-tr"></div>
        <div class="corner-bracket cb-bl"></div>
        <div class="corner-bracket cb-br"></div>
        <div class="carousel-tab-num">${{numStr}}</div>
        <div class="carousel-tab-label">${{label}}</div>
      `;
      strip.appendChild(tab);
    }});

    let currentTabIndex = 0;
    setInterval(() => {{
      currentTabIndex = (currentTabIndex + 1) % tabLabels.length;
      strip.style.transform = `translateX(-${{currentTabIndex * 34}}vw)`;
      const tabs = strip.querySelectorAll('.carousel-tab');
      tabs.forEach((t, idx) => {{
        t.classList.remove('active', 'passed');
        if (idx === currentTabIndex) {{
          t.classList.add('active');
        }} else if (idx < currentTabIndex) {{
          t.classList.add('passed');
        }}
      }});
    }}, 2400);

    /* --- SECTION 3 REVIEWS SLIDER --- */
    const reviews = [
      {{
        id: "01",
        name: "Ilan Brooks",
        role: "Founder of Halden Capital",
        quote: "“Smart contract auditing has always been a bottleneck for our startups, Nova Agent solves this problem in seconds.”"
      }},
      {{
        id: "02",
        name: "Rhea Okafor",
        role: "Co-founder of Tessel Network",
        quote: "“Nova Agent is a vital asset for Web3 investors, simplifying the research process effortlessly.”"
      }},
      {{
        id: "03",
        name: "Mara Elling",
        role: "CTO at Northline Labs",
        quote: "“The fastest way we have found to go from an idea to a deployable token contract.”"
      }}
    ];

    let reviewIdx = 0;
    const reviewNumEl = document.getElementById('review-num');
    const authorNameEl = document.getElementById('review-author-name');
    const authorRoleEl = document.getElementById('review-author-role');
    const quoteWrapper = document.getElementById('quote-wrapper');
    const quoteTextEl = document.getElementById('quote-text');
    const ghostQuoteEl = document.getElementById('ghost-quote');

    function showReview(idx) {{
      quoteWrapper.classList.add('fading');
      setTimeout(() => {{
        reviewIdx = idx;
        const cur = reviews[reviewIdx];
        const nxt = reviews[(reviewIdx + 1) % reviews.length];

        reviewNumEl.textContent = cur.id;
        authorNameEl.textContent = cur.name;
        authorRoleEl.textContent = cur.role;
        quoteTextEl.textContent = cur.quote;
        ghostQuoteEl.textContent = nxt.quote;

        quoteWrapper.classList.remove('fading');
      }}, 450);
    }}

    document.getElementById('prev-review-btn').addEventListener('click', () => {{
      showReview((reviewIdx - 1 + reviews.length) % reviews.length);
    }});
    document.getElementById('next-review-btn').addEventListener('click', () => {{
      showReview((reviewIdx + 1) % reviews.length);
    }});

    /* --- INTERSECTION OBSERVER REVEAL --- */
    const observer = new IntersectionObserver((entries) => {{
      entries.forEach(entry => {{
        if (entry.isIntersecting) {{
          entry.target.querySelectorAll('.rv').forEach(el => {{
            el.classList.add('rv-visible');
          }});
        }}
      }});
    }}, {{ threshold: 0.15 }});

    document.querySelectorAll('section').forEach(sec => observer.observe(sec));
  </script>
</body>
</html>
'''

with open('nova_agent.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

os.makedirs('web/public', exist_ok=True)
shutil.copy('nova_agent.html', 'web/public/nova.html')

print("Generated nova_agent.html and copied to web/public/nova.html successfully!")

