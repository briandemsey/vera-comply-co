"""End-to-end: prove both bugs are dead.

1. Load JKD-JKE → Policy Detail immediately enabled → click it → worked example renders.
2. Toggle Amended in Compliance Overview flips 0/32 → 31/32.

Every assertion is checked from actual page content.
"""
import io, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)


def sidebar_button(page, label):
    """Robust sidebar button locator — scoped to the sidebar container."""
    return page.locator('[data-testid="stSidebar"]').get_by_role("button", name=label, exact=True)


def main() -> int:
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(viewport={"width": 1400, "height": 1000}).new_page()

        # Step A: land on Load & Amend
        page.goto("http://localhost:8501", wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2500)
        page.screenshot(path=str(OUT / "e2e_00_landing.png"), full_page=True)

        # Step B: Click Load (only exact "Load" button in the main area)
        page.get_by_role("button", name="Load", exact=True).first.click(timeout=10000)
        page.wait_for_timeout(6000)  # engine runs
        page.screenshot(path=str(OUT / "e2e_01_analyzed.png"), full_page=True)

        # === BUG 2 CHECK: is Policy Detail immediately enabled? ===
        pd = sidebar_button(page, "Policy Detail")
        pd_disabled = pd.is_disabled()
        print(f"[bug 2] After Load, Policy Detail disabled = {pd_disabled}  (should be False)")
        if pd_disabled:
            errors.append("BUG 2 LIVES: Policy Detail still disabled after Load")

        # Advance through Steps 3 and 4 to force amended computation
        page.get_by_role("button", name="Amend policy →").click(timeout=10000)
        page.wait_for_timeout(3000)
        page.get_by_role("button", name="See rationale →").click(timeout=10000)
        page.wait_for_timeout(5000)  # amended report computes

        # === BUG 2 CHECK CONT: actually open Policy Detail and see the worked example ===
        try:
            pd.click(timeout=10000, force=True)
            page.wait_for_timeout(3000)
            page.screenshot(path=str(OUT / "e2e_02_policy_detail.png"), full_page=True)
            body = page.locator("main").inner_text()
            if "Examination" in body and "Updated language" in body and "Probable-AG test" in body:
                print("[bug 2 OK] Policy Detail renders full worked example")
            elif "Select a policy" in body:
                errors.append("BUG 2 LIVES: Policy Detail says 'Select a policy'")
            else:
                errors.append(f"BUG 2 partial: Policy Detail opened but content unclear: {body[:400]!r}")
        except Exception as e:
            errors.append(f"BUG 2 unclickable: {e}")

        # === BUG 1 CHECK: toggle flips 0/32 → 31/32 in Compliance Overview ===
        sidebar_button(page, "Compliance Overview").click(timeout=10000, force=True)
        page.wait_for_timeout(3000)

        m_orig = page.evaluate("() => Array.from(document.querySelectorAll('[data-testid=\"stMetricValue\"]')).map(e => e.textContent.trim()).join(' | ')")
        print(f"[bug 1] Original metrics: {m_orig}")
        page.screenshot(path=str(OUT / "e2e_03_overview_original.png"), full_page=True)

        # Click Amended radio
        page.get_by_text("Amended (after generated additions)").click(timeout=10000)
        page.wait_for_timeout(4000)
        m_am = page.evaluate("() => Array.from(document.querySelectorAll('[data-testid=\"stMetricValue\"]')).map(e => e.textContent.trim()).join(' | ')")
        print(f"[bug 1] Amended metrics:  {m_am}")
        page.screenshot(path=str(OUT / "e2e_04_overview_amended.png"), full_page=True)

        if m_orig == m_am:
            errors.append(f"BUG 1 LIVES: Toggle did not change metrics; still {m_am}")
        elif "0/32" in m_orig and ("31/32" in m_am or "32/32" in m_am):
            print("[bug 1 OK] Toggle flipped 0/32 → " + m_am.split(" | ")[1])
        else:
            errors.append(f"BUG 1 partial: metrics changed but not as expected: orig={m_orig} amended={m_am}")

        # Toggle back
        page.get_by_text("Original (before amendment)").click(timeout=10000)
        page.wait_for_timeout(3000)
        m_back = page.evaluate("() => Array.from(document.querySelectorAll('[data-testid=\"stMetricValue\"]')).map(e => e.textContent.trim()).join(' | ')")
        print(f"[bug 1] Back to Original:  {m_back}")
        if m_back != m_orig:
            errors.append(f"Toggle back to Original didn't restore: {m_back} (was {m_orig})")

        browser.close()

    if errors:
        print("\n--- FAILURES ---")
        for e in errors:
            print(" ", e)
        return 1
    print("\nBoth bugs are dead. Screenshots in tests/out/e2e_*.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
