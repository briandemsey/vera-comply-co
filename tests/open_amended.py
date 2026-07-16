"""Open a real Chrome window, walk through Load -> Amend, land on Compliance Overview
with Amended toggle selected showing 31/32. Leave the browser open for Brian."""
import sys
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        user_data_dir=r"C:\Users\BDEMS\AppData\Local\comply_pw_profile",
        headless=False,
        channel="chrome",
        viewport={"width": 1400, "height": 1000},
        args=["--start-maximized"],
    )
    page = browser.pages[0] if browser.pages else browser.new_page()
    page.goto("http://localhost:8501", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2500)

    # Click Load on JKD-JKE
    page.get_by_role("button", name="Load", exact=True).first.click(timeout=10000)
    page.wait_for_timeout(6000)
    print("Loaded JKD-JKE")

    # Advance through Step 3 and 4 so amended report gets computed
    page.get_by_role("button", name="Amend policy →").click(timeout=10000)
    page.wait_for_timeout(3000)
    page.get_by_role("button", name="See rationale →").click(timeout=10000)
    page.wait_for_timeout(5000)
    print("Advanced to Step 4 (amended report computed)")

    # Open Compliance Overview
    sidebar = page.locator('[data-testid="stSidebar"]')
    sidebar.get_by_role("button", name="Compliance Overview", exact=True).click(timeout=10000, force=True)
    page.wait_for_timeout(3000)
    print("On Compliance Overview")

    # Click Amended radio
    page.get_by_text("Amended (after generated additions)").click(timeout=10000)
    page.wait_for_timeout(4000)

    # Read what's on screen
    metrics = page.evaluate("""
() => {
  const arr = Array.from(document.querySelectorAll('[data-testid="stMetricValue"]'));
  return arr.map(e => e.textContent.trim());
}
""")
    print("On-screen metrics:", metrics)
    print("\nBrowser is open at Compliance Overview with Amended toggle selected.")
    print("This is the SAME URL as your Chrome: http://localhost:8501")
    print("Look at the browser window I just opened.")
    print("\nPress Ctrl+C in this terminal when done.")
    try:
        while True:
            page.wait_for_timeout(60000)
    except KeyboardInterrupt:
        pass
    browser.close()
