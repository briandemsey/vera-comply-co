"""Smoke test: walk Load & Amend JKD-JKE from Step 1 -> Step 4.

Run: python tests/test_load_amend.py
Requires: streamlit already running on http://localhost:8501
"""
import io
import sys
from pathlib import Path

# force stdout to UTF-8 so the arrow chars in button names print without dying
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
URL = "http://localhost:8501"

def main() -> int:
    errors: list[str] = []
    console_errors: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1400, "height": 900})
        page = ctx.new_page()

        page.on("console", lambda m: console_errors.append(f"[{m.type}] {m.text}") if m.type in ("error", "warning") else None)
        page.on("pageerror", lambda e: errors.append(f"PAGEERROR: {e}"))

        try:
            page.goto(URL, wait_until="networkidle", timeout=30000)
        except PWTimeout:
            errors.append("Timed out loading http://localhost:8501")
            print("\n".join(errors))
            return 1

        # Streamlit needs a moment to finish rendering after networkidle
        page.wait_for_timeout(1500)
        page.screenshot(path=str(OUT / "01_landing.png"), full_page=True)
        print(f"[step 1] landing loaded, title='{page.title()}'")

        # Step 1: click the exact "Load" button next to the JKD-JKE row.
        # Multiple buttons contain the word "Load" (sidebar "Load & Amend a Policy",
        # sample-policy row "Load"). We want the row-level one — filter to exact match.
        try:
            page.get_by_role("button", name="Load", exact=True).first.click(timeout=10000)
        except PWTimeout:
            errors.append("Could not find exact 'Load' button on Step 1")
            page.screenshot(path=str(OUT / "01_landing_ERROR.png"), full_page=True)
            print("\n".join(errors))
            return 1

        page.wait_for_timeout(6000)  # give the engine a few seconds to run
        page.screenshot(path=str(OUT / "02_analyze.png"), full_page=True)
        print("[step 2] analyzed")

        # Click "Amend policy →"
        try:
            page.get_by_role("button", name="Amend policy →").click(timeout=10000)
        except PWTimeout:
            errors.append("Could not find 'Amend policy →' button on Step 2")
            page.screenshot(path=str(OUT / "02_analyze_ERROR.png"), full_page=True)

        page.wait_for_timeout(2000)
        page.screenshot(path=str(OUT / "03_amend.png"), full_page=True)
        print("[step 3] amended")

        try:
            page.get_by_role("button", name="See rationale →").click(timeout=10000)
        except PWTimeout:
            errors.append("Could not find 'See rationale →' button on Step 3")
            page.screenshot(path=str(OUT / "03_amend_ERROR.png"), full_page=True)

        page.wait_for_timeout(2000)
        page.screenshot(path=str(OUT / "04_rationale.png"), full_page=True)
        print("[step 4] rationale shown")

        # Check the four unlocked sidebar buttons (Initial Report, Policy Detail, Compliance Overview, Gap)
        # Policy Detail should still be disabled (no policy selected)
        for label, should_be_enabled in [
            ("Initial Report", True),
            ("Compliance Overview", True),
            ("Gap Analysis & Revision", True),
        ]:
            btn = page.get_by_role("button", name=label).first
            try:
                is_disabled = btn.is_disabled(timeout=3000)
            except PWTimeout:
                errors.append(f"Sidebar button not found: {label}")
                continue
            state = "disabled" if is_disabled else "enabled"
            expected = "enabled" if should_be_enabled else "disabled"
            marker = "OK" if state == expected else "MISMATCH"
            print(f"[{marker}] sidebar '{label}' is {state} (expected {expected})")
            if state != expected:
                errors.append(f"Sidebar '{label}' should be {expected}, is {state}")

        # Click Initial Report and screenshot
        try:
            page.get_by_role("button", name="Initial Report").first.click(timeout=5000)
            page.wait_for_timeout(1500)
            page.screenshot(path=str(OUT / "05_initial_report.png"), full_page=True)
            print("[view] Initial Report opened")
        except PWTimeout:
            errors.append("Could not open Initial Report from sidebar")

        # Compliance Overview
        try:
            page.get_by_role("button", name="Compliance Overview").first.click(timeout=5000)
            page.wait_for_timeout(1500)
            page.screenshot(path=str(OUT / "06_overview.png"), full_page=True)
            print("[view] Compliance Overview opened")
        except PWTimeout:
            errors.append("Could not open Compliance Overview")

        # Gap Analysis
        try:
            page.get_by_role("button", name="Gap Analysis & Revision").first.click(timeout=5000)
            page.wait_for_timeout(1500)
            page.screenshot(path=str(OUT / "07_gap.png"), full_page=True)
            print("[view] Gap Analysis & Revision opened")
        except PWTimeout:
            errors.append("Could not open Gap Analysis & Revision")

        browser.close()

    print("\n--- console warnings/errors ---")
    for m in console_errors[:20]:
        print(m)
    if errors:
        print("\n--- ERRORS ---")
        for e in errors:
            print(e)
        return 1
    print("\nAll steps completed without errors.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
