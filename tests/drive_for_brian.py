"""Drive Chrome through the full flow, pausing on each screen so Brian can see."""
import sys
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        user_data_dir=r"C:\Users\BDEMS\AppData\Local\comply_pw_profile",
        headless=False,
        channel="chrome",
        viewport={"width": 1500, "height": 1000},
        args=["--start-maximized"],
    )
    page = browser.pages[0] if browser.pages else browser.new_page()

    print("\n=== SCREEN 1: Landing (Load & Amend, Step 1) ===")
    page.goto("http://localhost:8501", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)
    page.wait_for_timeout(4000)  # let Brian see landing

    print("\n=== SCREEN 2: Loading JKD-JKE... ===")
    page.get_by_role("button", name="Load", exact=True).first.click(timeout=10000)
    page.wait_for_timeout(7000)  # engine runs + settle
    print("       Step 2 (Analyze) should be showing — 0/32 red banner")
    page.wait_for_timeout(5000)  # let Brian see Step 2

    print("\n=== SCREEN 3: Amend policy (before/after redline) ===")
    page.get_by_role("button", name="Amend policy →").click(timeout=10000)
    page.wait_for_timeout(4000)
    print("       Step 3 should be showing — Before/After columns")
    page.wait_for_timeout(5000)

    print("\n=== SCREEN 4: Rationale cards ===")
    page.get_by_role("button", name="See rationale →").click(timeout=10000)
    page.wait_for_timeout(6000)  # amended report computes
    print("       Step 4 should be showing — one card per gap with AG rationale")
    page.wait_for_timeout(5000)

    print("\n=== SCREEN 5: Compliance Overview (Original toggle, showing 0/32) ===")
    sidebar = page.locator('[data-testid="stSidebar"]')
    sidebar.get_by_role("button", name="Compliance Overview", exact=True).click(timeout=10000, force=True)
    page.wait_for_timeout(4000)
    print("       Should show Original toggle selected, 0/32, all red")
    page.wait_for_timeout(5000)

    print("\n=== SCREEN 6: Clicking Amended toggle — should flip to 32/32 GREEN ===")
    page.get_by_text("Amended (after generated additions)").click(timeout=10000)
    page.wait_for_timeout(5000)

    metrics = page.evaluate("""
() => Array.from(document.querySelectorAll('[data-testid="stMetricValue"]')).map(e => e.textContent.trim())
""")
    print(f"       On-screen metrics after Amended click: {metrics}")

    if len(metrics) >= 3 and "32/32" in metrics[1] and metrics[2].strip().lower() == "yes":
        print("\n       *** SUCCESS: 32/32 within probable AG test = Yes ***")
    else:
        print(f"\n       *** UNEXPECTED: {metrics}")

    print("\n\nBrowser is open on Compliance Overview with Amended toggle.")
    print("You should see 32/32 and every criterion in green.")
    print("Look at the browser window.")

    try:
        while True:
            page.wait_for_timeout(60000)
    except KeyboardInterrupt:
        pass
    browser.close()
