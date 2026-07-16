"""Walk the app like a user, capture what's on screen at every step."""
import io, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
OUT = Path(__file__).parent / "walk"
OUT.mkdir(exist_ok=True)


def sidebar_button(page, label):
    return page.locator('[data-testid="stSidebar"]').get_by_role("button", name=label, exact=True)


def snap(page, name, note):
    path = OUT / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"  [{name}] {note}  ->  {path.name}")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(viewport={"width": 1400, "height": 1100}).new_page()

        # 1. Land
        page.goto("http://localhost:8501", wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2500)
        snap(page, "01_land", "Landing page (should be Load & Amend Step 1)")

        # 2. Click Load on JKD-JKE
        print("\n> Click 'Load' on JKD-JKE.md")
        page.get_by_role("button", name="Load", exact=True).first.click(timeout=10000)
        page.wait_for_timeout(6000)
        snap(page, "02_step2", "Step 2 (Analyze) should show 0/32 red banner")

        # 3. Verify Policy Detail is enabled
        pd = sidebar_button(page, "Policy Detail")
        print(f"\n> Policy Detail button disabled = {pd.is_disabled()}  (want False)")

        # 4. Click Policy Detail from sidebar
        print("\n> Click 'Policy Detail' in sidebar")
        pd.click(timeout=10000, force=True)
        page.wait_for_timeout(3000)
        snap(page, "03_policy_detail", "Policy Detail — should show worked example (Examination, gap, Updated language, AG test)")

        # 5. Back to Load & Amend Step 2, then Amend, then Rationale
        print("\n> Back to Load & Amend, advance to Step 3, then Step 4")
        sidebar_button(page, "Load & Amend a Policy").click(timeout=10000, force=True)
        page.wait_for_timeout(2500)
        page.get_by_role("button", name="Amend policy →").click(timeout=10000)
        page.wait_for_timeout(3000)
        snap(page, "04_step3", "Step 3 (Amend) — before/after redline")

        page.get_by_role("button", name="See rationale →").click(timeout=10000)
        page.wait_for_timeout(5000)  # amended report computes here
        snap(page, "05_step4", "Step 4 (Rationale) — rationale cards")

        # 6. Compliance Overview
        print("\n> Click 'Compliance Overview'")
        sidebar_button(page, "Compliance Overview").click(timeout=10000, force=True)
        page.wait_for_timeout(3000)
        snap(page, "06_overview_original", "Compliance Overview default (Original)")

        # 7. Click Amended radio
        print("\n> Toggle to 'Amended'")
        page.get_by_text("Amended (after generated additions)").click(timeout=10000)
        page.wait_for_timeout(4000)
        snap(page, "07_overview_amended", "Compliance Overview after clicking Amended (should be 31/32 with green ✅)")

        # 8. Gap Analysis
        print("\n> Click 'Gap Analysis & Revision'")
        sidebar_button(page, "Gap Analysis & Revision").click(timeout=10000, force=True)
        page.wait_for_timeout(3000)
        snap(page, "08_gap", "Gap Analysis view (Amended state persists)")

        browser.close()
    print("\nDone. Screenshots in tests/walk/*.png")


if __name__ == "__main__":
    main()
