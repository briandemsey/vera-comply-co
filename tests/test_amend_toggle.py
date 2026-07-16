"""Verify original vs amended toggle actually flips the verdict.

Walks Load & Amend to Step 3 to trigger amended-report computation, then
opens Compliance Overview, toggles Amended, and captures both screenshots.
"""
import io
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
URL = "http://localhost:8501"


def main() -> int:
    errors: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(viewport={"width": 1400, "height": 1000}).new_page()
        page.on("pageerror", lambda e: errors.append(f"PAGEERROR: {e}"))

        page.goto(URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)

        # Step 1 -> Load JKD-JKE
        page.get_by_role("button", name="Load", exact=True).first.click(timeout=10000)
        page.wait_for_timeout(6000)
        print("[step 2] analyzed original")

        # Step 2 -> Amend
        page.get_by_role("button", name="Amend policy →").click(timeout=10000)
        page.wait_for_timeout(3000)
        print("[step 3] amended")

        # Step 3 -> See rationale (this triggers _ensure_amended_measurement)
        page.get_by_role("button", name="See rationale →").click(timeout=10000)
        page.wait_for_timeout(4000)  # amended measurement runs here
        print("[step 4] rationale (amended report should now exist)")

        # Now go to Compliance Overview
        page.get_by_role("button", name="Compliance Overview").first.click(timeout=5000)
        page.wait_for_timeout(2000)
        page.screenshot(path=str(OUT / "toggle_01_overview_original.png"), full_page=True)

        # Look for the radio toggle
        toggle_visible = page.get_by_text("Measurement view").count() > 0
        print(f"[toggle] radio visible: {toggle_visible}")

        if not toggle_visible:
            errors.append("Radio 'Measurement view' not visible — amended report probably not computed")
        else:
            # Read the current verdict
            verdict_orig = page.evaluate("""
() => {
  const el = document.querySelector('[data-testid="stMetricValue"]');
  const metrics = Array.from(document.querySelectorAll('[data-testid="stMetricValue"]')).map(e => e.textContent.trim());
  return metrics.join(' | ');
}
""")
            print(f"[original metrics] {verdict_orig}")

            # Click the "Amended" radio option
            try:
                page.get_by_text("Amended (after generated additions)").click(timeout=5000)
                page.wait_for_timeout(3000)
                page.screenshot(path=str(OUT / "toggle_02_overview_amended.png"), full_page=True)
                verdict_am = page.evaluate("""
() => {
  const metrics = Array.from(document.querySelectorAll('[data-testid="stMetricValue"]')).map(e => e.textContent.trim());
  return metrics.join(' | ');
}
""")
                print(f"[amended metrics]  {verdict_am}")

                if verdict_orig == verdict_am:
                    errors.append(f"Toggle did not change metrics: still {verdict_am}")
                else:
                    print("[OK] Metrics changed when toggling to Amended")
            except PWTimeout:
                errors.append("Could not click 'Amended' radio option")

        # Also check Load & Amend Step 2 shows the amended block after having visited Step 3
        page.get_by_role("button", name="Load & Amend a Policy").first.click(timeout=5000)
        page.wait_for_timeout(2000)
        page.screenshot(path=str(OUT / "toggle_03_step2_with_amended.png"), full_page=True)

        browser.close()

    if errors:
        print("\n--- ERRORS ---")
        for e in errors:
            print(e)
        return 1
    print("\nAll toggle checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
