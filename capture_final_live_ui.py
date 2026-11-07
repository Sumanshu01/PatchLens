import os
import time
from playwright.sync_api import sync_playwright

OUTPUT_DIR = os.path.abspath("LINKEDIN IMAGES")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def capture_live():
    print(f"Capturing REAL LIVE UI images into: {OUTPUT_DIR}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1600, "height": 1000},
            device_scale_factor=1.5
        )
        page = context.new_page()

        # 1. Landing Page with 3D Robot Canvas
        print("  [1/5] Capturing Landing Page with 3D Robot...")
        page.goto("http://localhost:5173/", wait_until="networkidle")
        time.sleep(3)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "01_Live_Landing_Hero_3D.png"))
        print("    -> 01_Live_Landing_Hero_3D.png")

        # 2. Security Localization Dashboard
        print("  [2/5] Capturing Full Security Localization Dashboard...")
        page.goto("http://localhost:5173/analyze?sample=zlib-cve-2018-25032", wait_until="networkidle")
        page.wait_for_selector("button:has-text('DIFF VIEW')", timeout=30000)
        time.sleep(2)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "02_Live_Security_Localization_Dashboard.png"))
        print("    -> 02_Live_Security_Localization_Dashboard.png")

        # 3. Side-by-Side CFG Graph Modal
        print("  [3/5] Capturing Side-by-Side Control Flow Graph (CFG)...")
        page.click("button:has-text('DIFF VIEW')")
        time.sleep(2.5)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "03_Live_SideBySide_CFG_Graph.png"))
        print("    -> 03_Live_SideBySide_CFG_Graph.png")

        # 4. Instruction-Level Disassembly Diff Tab
        print("  [4/5] Capturing Instruction-Level Disassembly Diff...")
        page.click("button:has-text('Instruction-Level Diff')")
        time.sleep(2)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "04_Live_Instruction_Assembly_Diff.png"))
        print("    -> 04_Live_Instruction_Assembly_Diff.png")

        # 5. Interactive Call Graph View
        print("  [5/5] Capturing Interactive Topological Call Graph...")
        # Reload dashboard cleanly
        page.goto("http://localhost:5173/analyze?sample=zlib-cve-2018-25032", wait_until="networkidle")
        page.wait_for_selector("button:has-text('MATCH EXPLORER')", timeout=30000)
        time.sleep(1)
        page.click("button:has-text('MATCH EXPLORER')")
        time.sleep(3)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "05_Live_Topological_CallGraph.png"))
        print("    -> 05_Live_Topological_CallGraph.png")

        browser.close()
    print("Done! All 5 real live UI images captured successfully.")

if __name__ == "__main__":
    capture_live()
