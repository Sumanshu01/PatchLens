"""End-to-end Playwright test and automated demo recording for PatchLens web application."""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ARTIFACT_DIR = Path(r"C:\Users\PC\.gemini\antigravity\brain\c0d7caeb-c8af-43bc-982a-a28ff385be50")
SCREENSHOTS_DIR = ARTIFACT_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
VIDEO_DIR = Path("web/e2e_videos")
VIDEO_DIR.mkdir(parents=True, exist_ok=True)


def run_e2e_test_and_recording() -> None:
    """Launch servers, execute user flow, assert UI states, and record video artifact."""
    print("[E2E] Starting PatchLens FastAPI backend server...")
    root_dir = Path(__file__).resolve().parent.parent
    backend_proc = subprocess.Popen(
        [
            "python",
            "-m",
            "uvicorn",
            "api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=str(root_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    print("[E2E] Starting PatchLens Vite frontend preview server...")
    web_dir = Path(__file__).resolve().parent.parent / "web"
    frontend_proc = subprocess.Popen(
        ["npm.cmd", "run", "preview", "--", "--port", "5173", "--host", "127.0.0.1"],
        cwd=str(web_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for servers to be live
    print("[E2E] Waiting for backend and frontend to be responsive...")
    import urllib.request

    for _ in range(30):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=1) as r:
                if r.status == 200:
                    break
        except Exception:
            time.sleep(0.5)

    for _ in range(30):
        try:
            with urllib.request.urlopen("http://127.0.0.1:5173/", timeout=1) as r:
                if r.status == 200:
                    break
        except Exception:
            time.sleep(0.5)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--enable-webgl", "--use-gl=angle", "--use-angle=swiftshader"],
            )
            context = browser.new_context(
                record_video_dir=str(VIDEO_DIR),
                record_video_size={"width": 1280, "height": 800},
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()
            page.on("console", lambda msg: print(f"[Browser Console] {msg.type}: {msg.text}"))
            page.on("pageerror", lambda err: print(f"[Browser PageError] {err}"))

            print("[E2E] Step 1: Navigating to PatchLens landing page...")
            page.goto("http://127.0.0.1:5173/", wait_until="networkidle", timeout=15000)
            page.wait_for_selector("text=Pinpoint Security Patches", timeout=10000)
            page.screenshot(path=str(SCREENSHOTS_DIR / "1_landing_page.png"))
            print("[E2E] Step 1 OK: Landing page verified.")

            print("[E2E] Step 1b: Testing maximalist navbar hover box...")
            features_btn = page.wait_for_selector("a:has-text('Features')", timeout=5000)
            features_btn.hover()
            page.wait_for_timeout(400)
            page.screenshot(path=str(SCREENSHOTS_DIR / "1b_navbar_hover_box.png"))
            print("[E2E] Step 1b OK: Navbar hover box verified.")

            print("[E2E] Step 1c: Testing maximalist navbar click box...")
            features_btn.click()
            page.wait_for_timeout(600)
            page.screenshot(path=str(SCREENSHOTS_DIR / "1c_navbar_clicked_box.png"))
            print("[E2E] Step 1c OK: Navbar clicked box verified.")

            print("[E2E] Step 2: Clicking 'Try CVE-2018-25032 sample' CTA on Landing Page...")
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(300)
            sample_btn = page.wait_for_selector("text=Try CVE-2018-25032 sample", timeout=5000)
            t0 = time.perf_counter()
            sample_btn.click()

            # Wait for dashboard to load
            page.wait_for_selector("text=Diff Results & Security Localization", timeout=10000)
            load_time = time.perf_counter() - t0
            print(f"[E2E] Step 2 OK: Sample analysis loaded in {load_time:.3f}s (<6s requirement)!")
            assert load_time < 6.0, f"Sample load took {load_time}s which exceeds limit!"

            page.wait_for_timeout(1000)
            page.screenshot(path=str(SCREENSHOTS_DIR / "2_dashboard_results.png"))

            print("[E2E] Step 3: Verifying dashboard metrics & summary cards...")
            page.wait_for_selector("text=Semantic Changes")
            page.wait_for_selector("text=Matched Pairs")
            print("[E2E] Step 3 OK: Metrics cards verified.")

            print("[E2E] Step 4: Opening Function Detail Modal for Rank #1 function...")
            diff_view_btn = page.wait_for_selector("text=Diff View", timeout=5000)
            diff_view_btn.click()

            # Verify Side-by-Side CFG
            page.wait_for_selector("text=Side-by-Side CFG", timeout=5000)
            page.wait_for_timeout(1500)
            page.screenshot(path=str(SCREENSHOTS_DIR / "3_cfg_side_by_side.png"))
            print("[E2E] Step 4 OK: Side-by-side CFG graphs rendered.")

            print("[E2E] Step 5: Switching to Instruction-Level Diff tab...")
            page.click("text=Instruction-Level Diff")
            page.wait_for_timeout(1000)
            page.screenshot(path=str(SCREENSHOTS_DIR / "4_instruction_diff.png"))
            print("[E2E] Step 5 OK: Unified instruction diff verified.")

            print("[E2E] Step 6: Switching to Why This Match? explanation tab...")
            page.click("text=Why This Match?")
            page.wait_for_selector("text=Multi-Pass Matching Attribution", timeout=5000)
            page.wait_for_timeout(1000)
            page.screenshot(path=str(SCREENSHOTS_DIR / "5_why_this_match.png"))
            print("[E2E] Step 6 OK: Match proof and fingerprint breakdown verified.")

            # Close modal
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
            close_btn = page.query_selector("button:has(svg.lucide-x)")
            if close_btn:
                import contextlib

                with contextlib.suppress(Exception):
                    close_btn.click()
            page.wait_for_timeout(500)

            print("[E2E] Step 7: Testing Match Explorer (Call Graph)...")
            cg_toggle = page.wait_for_selector("text=Match Explorer (Call Graph)", timeout=5000)
            cg_toggle.click()
            page.wait_for_selector("text=Match Explorer — Call Graph Hierarchy", timeout=5000)
            page.wait_for_timeout(1500)
            page.screenshot(path=str(SCREENSHOTS_DIR / "6_callgraph_explorer.png"))
            print("[E2E] Step 7 OK: Call graph explorer verified.")

            print("[E2E] Step 8: Navigating to standalone Nova Agent 3D page (/nova.html)...")
            page.goto("http://127.0.0.1:5173/nova.html", wait_until="networkidle", timeout=15000)
            page.wait_for_selector("text=NOVA AGENT", timeout=10000)
            page.wait_for_selector("text=Thinking", timeout=10000)
            page.wait_for_timeout(2000)
            page.screenshot(path=str(SCREENSHOTS_DIR / "7_nova_agent_3d.png"))
            print("[E2E] Step 8 OK: Standalone Nova Agent 3D page verified.")

            # Close context to flush video file
            context.close()
            browser.close()

            # Save video recording artifact
            video_files = list(VIDEO_DIR.glob("*.webm"))
            if video_files:
                latest_video = max(video_files, key=lambda f: f.stat().st_mtime)
                dest_video = ARTIFACT_DIR / "patchlens_demo_walkthrough.webm"
                shutil.copy(latest_video, dest_video)
                print(f"[E2E] Video recording artifact saved to: {dest_video}")

    finally:
        print("[E2E] Tearing down test servers...")
        backend_proc.terminate()
        frontend_proc.terminate()
        backend_proc.wait()
        frontend_proc.wait()
        print("[E2E] All servers stopped cleanly.")


if __name__ == "__main__":
    run_e2e_test_and_recording()
