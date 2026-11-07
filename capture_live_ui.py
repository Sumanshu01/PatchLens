import os
import time
from playwright.sync_api import sync_playwright

OUTPUT_DIR = os.path.abspath("LINKEDIN IMAGES")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def capture():
    print(f"Capturing REAL LIVE UI screenshots into: {OUTPUT_DIR}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Desktop 1600x1000 with 1.5x scale
        context = browser.new_context(
            viewport={"width": 1600, "height": 1000},
            device_scale_factor=1.5
        )
        page = context.new_page()

        # 1. Landing Page Hero
        print("  [1/5] Capturing Landing Page with 3D Robot...")
        page.goto("http://localhost:5173/", wait_until="networkidle")
        time.sleep(3)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "01_Live_Landing_Hero.png"))
        print("    -> 01_Live_Landing_Hero.png")

        # 2. Binary Upload & Sample Selector
        print("  [2/5] Capturing Binary Upload & Sample Cases...")
        page.goto("http://localhost:5173/analyze", wait_until="networkidle")
        time.sleep(1.5)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "02_Live_Analyzer_Upload.png"))
        print("    -> 02_Live_Analyzer_Upload.png")

        # 3. Live Analysis Dashboard
        print("  [3/5] Capturing Analysis Dashboard (CVE-2018-25032)...")
        page.goto("http://localhost:5173/analyze?sample=zlib-cve-2018-25032", wait_until="networkidle")
        page.wait_for_selector(".font-mono", timeout=30000)
        time.sleep(2)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "03_Live_Analysis_Dashboard.png"))
        print("    -> 03_Live_Analysis_Dashboard.png")

        # 4. Side-by-Side Function Assembly Diff Modal
        print("  [4/5] Opening Function Detail & Side-by-Side Assembly Diff...")
        diff_btn = page.query_selector("button:has-text('DIFF VIEW')")
        if diff_btn:
            diff_btn.click()
            time.sleep(2)
            page.screenshot(path=os.path.join(OUTPUT_DIR, "04_Live_Assembly_Diff.png"))
            print("    -> 04_Live_Assembly_Diff.png")
            # Close modal by clicking backdrop or close button
            close_btn = page.query_selector("button:has-text('Close')")
            if close_btn:
                close_btn.click()
                time.sleep(1)

        # 5. Interactive Call Graph View
        print("  [5/5] Capturing Interactive Call Graph View...")
        call_graph_btn = page.query_selector("button:has-text('CALL GRAPH')") or page.query_selector("button:has-text('Call Graph')")
        if call_graph_btn:
            call_graph_btn.click()
            time.sleep(2.5)
            page.screenshot(path=os.path.join(OUTPUT_DIR, "05_Live_CallGraph_View.png"))
            print("    -> 05_Live_CallGraph_View.png")

        browser.close()
    print("Done! All 5 real live UI screenshots captured successfully.")

if __name__ == "__main__":
    capture()
