"""VERA Comply — SB 26-189 Compliance (Colorado) — policy-first.

Upload -> Initial Report (per-policy scope triage) -> Policy Detail
(examine, gap, updated language, probable-AG test) -> Compliance Overview
(criterion rollup) -> Gap Analysis & Revision export.
"""

from __future__ import annotations

import io
import json
import os
import re
import tempfile
from pathlib import Path

import streamlit as st

from comply_engine import chunk_text, judge, parse_document, run, score
from comply_rubric import build_rubric

HERE = Path(__file__).parent
SCOPE_FIXTURE = HERE / "policies_scope.json"
DETAILS_FIXTURE = HERE / "policy_details.json"
FIXTURE_MD = HERE / "fixture" / "Poudre_Policy_Compendium.md"
SAMPLE_POLICIES_DIR = HERE / "sample_policies"
LOGO = HERE / "assets" / "casb_logo_sharp.png"

MODULE_ORDER = ["A", "B", "C", "D", "E", "F"]
MODULE_NAMES = {
    "A": "ADMT Inventory",
    "B": "Classification & FERPA Crosswalk",
    "C": "Notice & Parent Access",
    "D": "Recordkeeping",
    "E": "Procurement & Vendor Management",
    "F": "Human Review & Oversight",
}

NAVY = "#1f3b63"
NAVY2 = "#2a4d7a"
RAIL = "#eef1f5"
LINE = "#d7dee8"
INK = "#1c2431"
MUTED = "#5b6b7f"
STAT = "#2f6b3d"
PROV = "#8a6d1a"
CONT = "#8a2f2f"
STATBG = "#e4ecf5"
PROVBG = "#fff3d6"
CONTBG = "#f7dede"


def inject_css() -> None:
    st.markdown(
        f"""
        <style>
        .block-container {{padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1100px;}}
        [data-testid="stSidebar"] {{background: {RAIL}; border-right: 1px solid {LINE};}}
        [data-testid="stSidebar"] .stButton > button {{
            width: 100%; text-align: left; background: {NAVY}; color: #fff;
            border: none; border-radius: 6px; padding: 9px 12px; margin-bottom: 6px;
            font-size: 13px;
        }}
        h1 {{color: {NAVY}; font-size: 27px; margin: 4px 0;}}
        h2, h3 {{color: {NAVY};}}
        .sub {{color: {MUTED}; margin: 0 0 18px;}}
        .pill {{
            display: inline-block; font-size: 11px; padding: 3px 9px; border-radius: 20px;
            background: {PROVBG}; color: {PROV}; border: 1px solid #e6cf93; margin-bottom: 14px;
        }}
        .brand {{color: {NAVY}; font-weight: 700; font-size: 19px; text-align: center;}}
        .brand small {{display: block; color: {MUTED}; font-weight: 500; font-size: 12px; margin-top: 3px;}}
        .tile {{
            border: 1.5px solid {NAVY}; border-radius: 9px; padding: 14px 16px; background: #fff;
            text-align: center;
        }}
        .tile .n {{font-size: 30px; font-weight: 700; color: {NAVY};}}
        .tile .lbl {{font-size: 12px; color: {MUTED}; text-transform: uppercase; letter-spacing: .05em;}}
        .badge {{
            font-size: 10.5px; font-weight: 700; padding: 2px 7px; border-radius: 4px;
            text-transform: uppercase; letter-spacing: .03em;
        }}
        .b-High {{background: {CONTBG}; color: {CONT};}}
        .b-Medium {{background: {PROVBG}; color: {PROV};}}
        .b-Low {{background: {STATBG}; color: {STAT};}}
        .b-Statutory {{background: {STATBG}; color: {STAT};}}
        .b-Provisional {{background: {PROVBG}; color: {PROV};}}
        .b-Contested {{background: {CONTBG}; color: {CONT};}}
        .b-Addressed {{background: {STATBG}; color: {STAT};}}
        .b-Partial {{background: {PROVBG}; color: {PROV};}}
        .b-NotAddressed {{background: {CONTBG}; color: {CONT};}}
        .polcard {{
            border: 1px solid {LINE}; border-radius: 8px; padding: 12px 14px;
            margin-bottom: 10px; background: #fff;
        }}
        .polcard .code {{font-family: ui-monospace, Menlo, monospace; font-weight: 700; color: {NAVY};}}
        .polcard .rat {{font-size: 12.5px; color: #33414f; margin-top: 4px;}}
        .polcard .mods {{font-size: 11.5px; color: {MUTED}; margin-top: 4px;}}
        .ev {{background: #f6f9fc; border-left: 3px solid #cfe0f2; padding: 10px 14px; margin: 8px 0; border-radius: 4px; font-size: 13px;}}
        .rev {{background: #eef4fb; border: 1px solid #cfe0f2; border-radius: 6px; padding: 10px 14px; margin: 8px 0; color: {NAVY}; font-size: 13px;}}
        .model {{background: #eef4fb; border: 1px solid #cfe0f2; border-radius: 8px; padding: 14px; color: {NAVY2}; font-size: 14px; line-height: 1.5; margin: 6px 0 18px;}}
        .model .lbl {{font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: {MUTED}; font-weight: 700; margin-bottom: 6px;}}
        .verdict-ok {{background: {STATBG}; color: {STAT}; padding: 12px 16px; border-radius: 8px; font-weight: 700; margin: 10px 0;}}
        .verdict-no {{background: {CONTBG}; color: {CONT}; padding: 12px 16px; border-radius: 8px; font-weight: 700; margin: 10px 0;}}
        .note {{font-size: 12px; color: {MUTED}; margin-top: 22px; border-top: 1px solid {LINE}; padding-top: 12px;}}
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_state() -> None:
    ss = st.session_state
    ss.setdefault("view", "load_amend")
    ss.setdefault("district_name", "")
    ss.setdefault("district_ferpa", "Yes")
    ss.setdefault("district_source", "Document upload")
    ss.setdefault("report", None)  # whole-manual measurement (Poudre demo / uploaded manual)
    ss.setdefault("report_amended", None)  # whole-manual measurement after amendment
    ss.setdefault("scope", None)   # list of per-policy scope dicts
    ss.setdefault("details", None) # dict of code -> worked policy detail
    ss.setdefault("selected_policy", None)
    ss.setdefault("scope_confirmed", {})
    # Single-policy Load & Amend state
    ss.setdefault("la_policy_text", None)     # original policy text loaded
    ss.setdefault("la_policy_name", None)     # display name/filename
    ss.setdefault("la_policy_code", None)     # e.g. JKD-JKE (from filename or extracted)
    ss.setdefault("la_report", None)          # engine report on the single policy (original)
    ss.setdefault("la_report_amended", None)  # engine report after amendment splice
    ss.setdefault("la_amended_text", None)    # the spliced amended policy text
    ss.setdefault("la_step", 1)               # 1 load, 2 analyze, 3 amend, 4 rationale
    ss.setdefault("show_amended", False)      # global toggle: original vs amended measurement


def _active_report() -> dict | None:
    """The measurement report to render in the four manual-views.

    Prefers whole-manual report over single-policy, and respects the amended
    toggle so views flip between "before" and "after" measurement.
    """
    ss = st.session_state
    if ss.report is not None:
        if ss.show_amended and ss.report_amended is not None:
            return ss.report_amended
        return ss.report
    if ss.la_report is not None:
        if ss.show_amended and ss.la_report_amended is not None:
            return ss.la_report_amended
        return ss.la_report
    return None


def _ensure_amended_measurement() -> None:
    """Compute the amended-policy measurement lazily, once per amendment change.

    Also lazily computes la_report if a policy is loaded but hasn't been measured yet,
    so views like Compliance Overview work even if the user skipped Step 2.
    """
    ss = st.session_state
    # Compute the original single-policy report if a policy is loaded but not yet measured
    if ss.la_policy_text is not None and ss.la_report is None:
        ss.la_report = _measure_single_policy(ss.la_policy_text)
    # Compute the amended single-policy report
    if ss.la_report is not None and ss.la_report_amended is None and ss.la_policy_text is not None:
        original_report = ss.la_report
        gaps = [r for r in original_report["results"]
                if not r["context_only"] and r["measured"]["status"] != "Addressed"]
        additions = _build_additions_block(gaps)
        amended_text = ss.la_policy_text.rstrip() + "\n\n" + additions
        ss.la_amended_text = amended_text
        ss.la_report_amended = _measure_single_policy(amended_text)


def _render_amended_toggle() -> None:
    """Show the original/amended radio when an amended measurement exists."""
    ss = st.session_state
    have_amended = (ss.la_report_amended is not None) or (ss.report_amended is not None)
    if not have_amended:
        return

    options = ["Original (before amendment)", "Amended (after generated additions)"]
    # Seed the widget's own key so its state is the source of truth, not ss.show_amended
    if "_amend_toggle" not in ss:
        ss["_amend_toggle"] = options[1 if ss.show_amended else 0]

    def _on_change():
        ss.show_amended = ss["_amend_toggle"].startswith("Amended")

    st.radio(
        "Measurement view",
        options=options,
        horizontal=True,
        key="_amend_toggle",
        on_change=_on_change,
    )


def _active_scope() -> list[dict] | None:
    """The per-policy triage list, or a synthetic single-entry list built from the
    loaded single policy so Initial Report / Policy Detail have something to show.
    """
    ss = st.session_state
    if ss.scope is not None:
        return ss.scope
    if ss.la_report is not None and ss.la_policy_code:
        rep = ss.la_report
        addressed_modules = sorted({r["module"] for r in rep["results"]
                                    if not r["context_only"] and r["measured"]["status"] == "Addressed"})
        s = rep["score"]
        rationale = (
            f"Single policy loaded via Load & Amend. Rubric measurement: "
            f"{s['must_pass_addressed']}/{s['must_pass_total']} must-pass requirements addressed."
        )
        return [{
            "code": ss.la_policy_code,
            "title": ss.la_policy_name or ss.la_policy_code,
            "subject_to_review": True,
            "applicable_modules": addressed_modules or MODULE_ORDER,
            "rationale": rationale,
            "priority": "High" if not s["within_probable_ag_test"] else "Medium",
        }]
    return None


def sidebar() -> None:
    ss = st.session_state
    manual_loaded = _active_report() is not None or ss.la_policy_text is not None
    scope_loaded = _active_scope() is not None or ss.la_policy_code is not None
    policy_selected = ss.selected_policy is not None

    with st.sidebar:
        st.markdown(
            '<div class="brand">VERA Comply<small>SB 26-189 Compliance · Colorado</small></div>',
            unsafe_allow_html=True,
        )
        st.markdown("---")

        # Always-available entry points
        for label, key in [
            ("Load & Amend a Policy", "load_amend"),
            ("Upload Manual", "upload"),
        ]:
            if st.button(label, key=f"nav_{key}"):
                st.session_state.view = key

        st.markdown("---")
        st.markdown(
            f'<div style="font-size:11px;color:{MUTED};text-transform:uppercase;letter-spacing:.05em;margin:6px 4px">Manual views</div>',
            unsafe_allow_html=True,
        )
        # Disabled unless a manual has been loaded
        st.button("Initial Report",         key="nav_report",   disabled=not (manual_loaded or scope_loaded),
                  on_click=lambda: st.session_state.__setitem__("view", "report"))
        st.button("Policy Detail",          key="nav_detail",   disabled=not (scope_loaded and policy_selected),
                  on_click=lambda: st.session_state.__setitem__("view", "detail"))
        st.button("Compliance Overview",    key="nav_overview", disabled=not manual_loaded,
                  on_click=lambda: st.session_state.__setitem__("view", "overview"))
        st.button("Gap Analysis & Revision",key="nav_gap",      disabled=not manual_loaded,
                  on_click=lambda: st.session_state.__setitem__("view", "gap"))

        if not manual_loaded:
            st.caption("Load a manual to unlock these views.")

        st.markdown("---")
        st.caption(
            "AG rulemaking in progress. Provisional and Contested items are shown as built "
            "to the expected standard, subject to the AG's final rules — never as guaranteed approval."
        )


def load_poudre_fixture() -> None:
    """Load the built-in Poudre demo — scope + details + engine measurement."""
    st.session_state.district_name = "Poudre School District"
    st.session_state.district_ferpa = "Yes"
    st.session_state.district_source = "Poudre fixture (demo)"
    with st.spinner("Loading Poudre demo — 185 policies, measuring against the rubric..."):
        st.session_state.scope = json.loads(SCOPE_FIXTURE.read_text(encoding="utf-8"))
        st.session_state.details = json.loads(DETAILS_FIXTURE.read_text(encoding="utf-8"))["worked_policies"]
        st.session_state.report = run(str(FIXTURE_MD))
    st.session_state.view = "report"


def process_upload(uploaded) -> None:
    suffix = os.path.splitext(uploaded.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.read())
        path = tmp.name
    try:
        with st.spinner(f"Examining {uploaded.name} against SB 26-189..."):
            st.session_state.report = run(path)
        st.session_state.scope = None
        st.session_state.details = None
        st.session_state.district_source = f"Upload: {uploaded.name}"
        st.session_state.view = "report"
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def view_upload() -> None:
    if LOGO.exists():
        st.image(str(LOGO), width=260)
    st.markdown('<div class="pill">AG rulemaking in progress — provisional items flagged</div>', unsafe_allow_html=True)
    st.markdown("# Upload & District Info")
    st.markdown(
        '<p class="sub">Upload your policy manual and we\'ll examine every policy against SB 26-189 — '
        'telling you which are subject to review, where the gaps are, and what language would close them.</p>',
        unsafe_allow_html=True,
    )

    col_a, col_b = st.columns(2)
    with col_a:
        st.session_state.district_name = st.text_input("District name", value=st.session_state.district_name)
    with col_b:
        st.session_state.district_ferpa = st.selectbox(
            "Subject to FERPA?", ["Yes", "No"],
            index=["Yes", "No"].index(st.session_state.district_ferpa),
        )

    st.markdown("### Provide your policy manual")
    up = st.file_uploader(
        "Upload PDF, DOCX, TXT, or MD",
        type=["pdf", "docx", "txt", "md"],
        help="We split the manual into individual policies, classify each for SB 26-189 scope, and measure the manual as a whole against the 34 rubric requirements.",
    )
    if up is not None:
        process_upload(up)
        st.rerun()

    st.markdown("---")
    st.markdown("### Or try the Poudre demo")
    st.caption("Real Colorado district manual: 185 policies, 84 in-scope, 6 fully worked. Loads the reference measurement instantly.")
    if st.button("Load Poudre demo", type="primary"):
        load_poudre_fixture()
        st.rerun()


def view_report() -> None:
    ss = st.session_state
    rep = _active_report()
    scope = _active_scope()
    if rep is None and scope is None:
        st.info("Load a policy on **Load & Amend a Policy**, or a whole manual on **Upload Manual**.")
        return

    st.markdown('<div class="pill">AG rulemaking in progress — provisional items flagged</div>', unsafe_allow_html=True)
    st.markdown(f"# Initial Report — {ss.district_name or 'District'}")
    single_note = " · single-policy view" if ss.report is None and ss.la_report is not None else ""
    st.markdown(f'<p class="sub">Source: {ss.district_source}{single_note}</p>', unsafe_allow_html=True)

    # Manual-level score (from engine)
    if rep is not None:
        s = rep["score"]
        ok = s["within_probable_ag_test"]
        verdict_class = "verdict-ok" if ok else "verdict-no"
        verdict_text = (
            "Within the probable AG test on all must-pass requirements."
            if ok
            else f"Not yet within the probable AG test — {len(s['failing'])} must-pass requirements unmet."
        )
        st.markdown(f'<div class="{verdict_class}">{verdict_text}</div>', unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f'<div class="tile"><div class="n">{rep["provisions"]}</div><div class="lbl">Provisions examined</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="tile"><div class="n">{s["must_pass_addressed"]}/{s["must_pass_total"]}</div><div class="lbl">Must-pass addressed</div></div>', unsafe_allow_html=True)
        by_tier = s["by_tier"]
        stat = by_tier.get("Statutory", {"addressed": 0, "total": 0})
        prov = by_tier.get("Provisional", {"addressed": 0, "total": 0})
        c3.markdown(f'<div class="tile"><div class="n">{stat["addressed"]}/{stat["total"]}</div><div class="lbl">Statutory</div></div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="tile"><div class="n">{prov["addressed"]}/{prov["total"]}</div><div class="lbl">Provisional</div></div>', unsafe_allow_html=True)
        st.markdown("")

    # Per-policy scope table (from scope fixture, or synthetic single-item when only a single policy is loaded)
    if scope is not None:
        subj = [p for p in scope if p.get("subject_to_review")]
        high = [p for p in subj if p.get("priority") == "High"]
        st.markdown(f"### Per-policy triage — {len(subj)} in scope out of {len(scope)}")
        st.caption(f"{len(high)} High priority. Click a code to open its Policy Detail.")

        # High-priority first
        priority_order = {"High": 0, "Medium": 1, "Low": 2}
        subj_sorted = sorted(subj, key=lambda p: (priority_order.get(p.get("priority"), 3), p.get("code", "")))

        # Filter
        show_only_subject = st.checkbox("Show only in-scope policies", value=True)
        show = subj_sorted if show_only_subject else sorted(scope, key=lambda p: (0 if p.get("subject_to_review") else 1, priority_order.get(p.get("priority"), 3), p.get("code", "")))

        for p in show[:200]:
            code = p.get("code", "")
            title = p.get("title", "")
            pri = p.get("priority", "Low")
            mods = p.get("applicable_modules") or []
            rat = p.get("rationale", "")
            worked = code in (ss.details or {})
            open_label = "Open" + (" (worked example)" if worked else "")
            cols = st.columns([1, 4, 1, 1])
            with cols[0]:
                st.markdown(f'<span class="badge b-{pri}">{pri}</span>', unsafe_allow_html=True)
            with cols[1]:
                st.markdown(
                    f'<div class="polcard"><span class="code">{code}</span> · <b>{title}</b>'
                    f'<div class="rat">{rat}</div>'
                    f'<div class="mods">Modules: {", ".join(mods) if mods else "—"}</div></div>',
                    unsafe_allow_html=True,
                )
            with cols[2]:
                confirmed = ss.scope_confirmed.get(code, None)
                if confirmed is True:
                    st.caption("✓ confirmed")
                elif confirmed is False:
                    st.caption("✗ rejected")
                else:
                    if st.button("Confirm", key=f"conf_{code}"):
                        ss.scope_confirmed[code] = True
                        st.rerun()
            with cols[3]:
                if st.button(open_label, key=f"open_{code}"):
                    ss.selected_policy = code
                    ss.view = "detail"
                    st.rerun()

    else:
        st.info(
            "This upload was measured but per-policy triage requires either the Poudre demo or a policy-manifest "
            "input. The manual was scored against the rubric — see Compliance Overview for the criterion-level view."
        )


def view_detail() -> None:
    ss = st.session_state
    scope = _active_scope()
    if ss.selected_policy is None or scope is None:
        st.info("Select a policy from **Initial Report** to open its detail.")
        return

    code = ss.selected_policy
    scope_row = next((p for p in scope if p.get("code") == code), None)
    # Prefer already-loaded details (from Poudre demo); otherwise read from disk so
    # single-policy Load & Amend entries can still surface worked examples.
    details_map = ss.details
    if details_map is None and DETAILS_FIXTURE.exists():
        try:
            details_map = json.loads(DETAILS_FIXTURE.read_text(encoding="utf-8")).get("worked_policies", {})
        except Exception:
            details_map = {}
    detail = (details_map or {}).get(code)

    if scope_row is None:
        st.error(f"Policy {code} not found.")
        return

    st.markdown('<div class="pill">AG rulemaking in progress — provisional items flagged</div>', unsafe_allow_html=True)
    st.markdown(f"# {code} — {scope_row.get('title','')}")
    pri = scope_row.get("priority", "Low")
    mods = scope_row.get("applicable_modules") or []
    st.markdown(
        f'<p class="sub"><span class="badge b-{pri}">{pri}</span> · Applicable modules: {", ".join(mods) if mods else "—"}</p>',
        unsafe_allow_html=True,
    )

    st.markdown("### Rationale for scope")
    st.write(scope_row.get("rationale", ""))

    if detail is None:
        # No stored worked example — render the same before/after + rationale from the engine
        # so any loaded single policy gets the full end-to-end story here.
        if ss.la_policy_text is None or ss.la_policy_code != code:
            st.info(
                "No worked example is stored for this policy, and no single-policy text is loaded "
                "to generate one on the fly. Load a policy on **Load & Amend a Policy**."
            )
            return
        _ensure_amended_measurement()
        original = ss.la_policy_text
        rep = ss.la_report
        gaps = [r for r in rep["results"] if not r["context_only"] and r["measured"]["status"] != "Addressed"]
        additions = _build_additions_block(gaps)
        amended = original.rstrip() + "\n\n" + additions

        st.caption(
            "Generated on-the-fly examination for this policy (no attorney-reviewed worked example on file). "
            "Below is the before/after redline plus per-criterion rationale — the same output you get from "
            "the Load & Amend flow."
        )

        s = rep["score"]
        st.markdown(
            f"**Examination summary:** {rep['provisions']} provisions in the loaded policy. "
            f"Rubric measurement: {s['must_pass_addressed']}/{s['must_pass_total']} must-pass requirements addressed as loaded."
        )

        st.markdown("### Before / After")
        col_b, col_a = st.columns(2)
        with col_b:
            st.markdown("**Before**")
            st.markdown(
                f'<div style="max-height:500px;overflow:auto;border:1px solid {LINE};'
                f'border-radius:6px;padding:12px;background:#fafbfd;font-size:12.5px;'
                f'white-space:pre-wrap;font-family:ui-monospace,Menlo,monospace">{_escape(original)}</div>',
                unsafe_allow_html=True,
            )
        with col_a:
            st.markdown("**After**")
            before_len = len(original.rstrip())
            after_original = _escape(amended[:before_len])
            after_additions = _escape(amended[before_len:])
            st.markdown(
                f'<div style="max-height:500px;overflow:auto;border:1px solid {LINE};'
                f'border-radius:6px;padding:12px;background:#fafbfd;font-size:12.5px;'
                f'white-space:pre-wrap;font-family:ui-monospace,Menlo,monospace">'
                f'{after_original}'
                f'<span style="background:#e4f3e8;border-left:3px solid {STAT};'
                f'display:block;padding:8px 10px;margin-top:8px">{after_additions}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.download_button(
            "Download amended policy (Markdown)",
            data=amended,
            file_name=f"{code}_amended.md",
            mime="text/markdown",
            key=f"det_download_{code}",
        )

        if gaps:
            st.markdown("### Why each insertion was added + AG rationale")
            st.caption(
                f"{len(gaps)} insertion(s). Each block explains what was missing, why the generated "
                "language closes the gap, and the AG's likely rationale for accepting it."
            )
            for r in gaps:
                mm = r["measured"]
                tier = r["ag_test_tier"]
                tier_note = {
                    "Statutory": "Hard statutory requirement — defensible on the enacted text of SB 26-189 today. An AG enforcement action would be unlikely to succeed against this insertion because it directly implements the statute.",
                    "Provisional": "This requirement will be shaped by AG rules due 2027-01-01. The inserted language is built to the standard the AG is most likely to set. Risk: final rules could tighten wording — flag for reconciliation on 2027-01-01.",
                    "Contested": "Live battleground where commenters and the AG's framing disagree. The insertion takes the defensible broader-reading approach so the district is over-covered rather than under. Flagged for reconciliation against final rules.",
                }.get(tier, "")
                gap_labels = mm.get("gap") or []
                evidence_summary = (
                    f'The existing policy mentions "{(mm["evidence"]["text"][:180] + "...") if mm["evidence"] and len(mm["evidence"]["text"]) > 180 else (mm["evidence"]["text"] if mm["evidence"] else "")}" but does not fully satisfy the requirement.'
                    if mm["evidence"]
                    else "The existing policy contains no provision addressing this requirement."
                )
                st.markdown(
                    f'''
<div style="border:1px solid {LINE};border-radius:8px;padding:14px 16px;margin:10px 0;background:#fff">
<div style="display:flex;justify-content:space-between;align-items:center">
<div><span style="font-family:ui-monospace,Menlo,monospace;font-weight:700;color:{NAVY}">{r["id"]} · {r["term"]}</span></div>
<div><span class="badge b-{tier}">{tier}</span></div>
</div>
<div style="font-size:11.5px;color:{MUTED};font-family:ui-monospace,Menlo,monospace;margin:4px 0 10px">{r["hook"]}</div>
<div style="margin-bottom:8px"><b>What was missing.</b> {evidence_summary} {("Specifically missing: " + "; ".join(gap_labels) + ".") if gap_labels else ""}</div>
<div style="margin-bottom:8px"><b>Why the after-language was added.</b> Satisfies the criterion's pass condition — {r.get("pass_condition","")}.</div>
<div style="background:#eef4fb;border:1px solid #cfe0f2;border-radius:6px;padding:10px 12px;margin:8px 0;color:{NAVY};font-size:13px">
<b>Inserted language.</b> "{r.get("revision","")}"
</div>
<div style="margin-bottom:8px"><b>AG rationale for approval.</b> {tier_note}</div>
</div>
                    ''',
                    unsafe_allow_html=True,
                )
        else:
            st.success("No gaps detected against the rubric — nothing to amend.")

        st.markdown("### Confirm / edit")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Confirm this examination and revision", type="primary", key=f"det_conf_{code}"):
                ss.scope_confirmed[code] = True
                st.success("Confirmed. This policy is now marked attorney-reviewed for the acceptance record.")
        with col2:
            st.text_area("Attorney note (optional)", key=f"det_note_{code}", height=80)
        return

    st.markdown("### Examination")
    st.write(detail.get("examination", ""))

    st.markdown("### Current gap")
    st.write(detail.get("gap", ""))

    st.markdown("### Updated language — original, offered for CASB ownership")
    st.markdown(f'<div class="model"><div class="lbl">Proposed insertion</div>{detail.get("updated","")}</div>', unsafe_allow_html=True)

    st.markdown("### Probable-AG test")
    test = detail.get("test", [])
    if test:
        for mod, tier, satisfied in test:
            mark = "✓" if satisfied else "✗"
            st.markdown(
                f'<div style="margin:4px 0"><span class="badge b-{tier}">{tier}</span> '
                f'&nbsp;<b>Module {mod}</b> — {MODULE_NAMES.get(mod,"")} &nbsp;{mark}</div>',
                unsafe_allow_html=True,
            )
    st.caption(
        "Statutory items must fully pass and are defensible today. Provisional items are built to the standard "
        "we expect the AG to set. Contested items are the defensible reading pending final rules."
    )

    st.markdown("### Confirm / edit")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Confirm this examination and revision", type="primary", key=f"det_conf_{code}"):
            ss.scope_confirmed[code] = True
            st.success("Confirmed. This policy is now marked attorney-reviewed for the acceptance record.")
    with col2:
        st.text_area("Attorney note (optional)", key=f"det_note_{code}", height=80)


def view_overview() -> None:
    ss = st.session_state
    _ensure_amended_measurement()
    rep = _active_report()
    if rep is None:
        st.info("Load a policy on **Load & Amend a Policy**, or a whole manual on **Upload Manual**.")
        return

    st.markdown('<div class="pill">AG rulemaking in progress — provisional items flagged</div>', unsafe_allow_html=True)
    st.markdown("# Compliance Overview")
    single_note = " · single-policy view" if ss.report is None and ss.la_report is not None else ""
    st.markdown(
        f'<p class="sub">Criterion-level rollup across the 34 measurable requirements. The auditor view.{single_note}</p>',
        unsafe_allow_html=True,
    )

    _render_amended_toggle()

    s = rep["score"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Provisions examined", rep["provisions"])
    c2.metric("Must-pass addressed", f"{s['must_pass_addressed']}/{s['must_pass_total']}")
    c3.metric("Within probable AG test", "Yes" if s["within_probable_ag_test"] else "Not yet")

    # Group results by module
    results = [r for r in rep["results"] if not r["context_only"]]
    by_module: dict[str, list] = {}
    for r in results:
        by_module.setdefault(r["module"], []).append(r)

    for m in MODULE_ORDER:
        if m not in by_module:
            continue
        rows = by_module[m]
        addressed = sum(1 for r in rows if r["measured"]["status"] == "Addressed")
        st.markdown(f"### {m} — {MODULE_NAMES[m]}  ·  {addressed}/{len(rows)} addressed")
        for r in rows:
            mm = r["measured"]
            st_status = mm["status"]
            badge_class = "b-Addressed" if st_status == "Addressed" else ("b-Partial" if st_status == "Partial" else "b-NotAddressed")
            icon = {"Addressed": "✅", "Partial": "🟡", "Not addressed": "🔴"}.get(st_status, "•")
            with st.expander(f"{icon} {r['id']} · {r['term']} — {st_status}  ·  [{r['ag_test_tier']}]"):
                st.caption(f"{r['hook']} · {r['pass_semantics']}")
                if mm["evidence"]:
                    st.markdown(
                        f'<div class="ev"><b>{mm["evidence"]["heading"]}</b> — "{mm["evidence"]["text"][:600]}"</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown('<div class="ev">No matching provision found in the uploaded manual.</div>', unsafe_allow_html=True)
                if mm["gap"]:
                    st.markdown(f"**Gap:** missing {'; '.join(mm['gap'])}.")
                else:
                    st.markdown("**Fully satisfied.**")
                if r.get("revision"):
                    st.markdown(
                        f'<div class="rev"><b>Generated revision</b> (re-measured: {r.get("remeasured","")})<br>"{r["revision"]}"</div>',
                        unsafe_allow_html=True,
                    )


def view_gap() -> None:
    ss = st.session_state
    _ensure_amended_measurement()
    rep = _active_report()
    if rep is None:
        st.info("Load a policy on **Load & Amend a Policy**, or a whole manual on **Upload Manual**.")
        return

    st.markdown("# Gap Analysis & Revision")
    single_note = " · single-policy view" if ss.report is None and ss.la_report is not None else ""
    st.markdown(
        f'<p class="sub">Every must-pass gap and the generated original language that closes it. '
        f'Export the full report as HTML for attorney review.{single_note}</p>',
        unsafe_allow_html=True,
    )

    _render_amended_toggle()

    results = [r for r in rep["results"] if not r["context_only"]]
    gaps = [r for r in results if r["measured"]["status"] != "Addressed"]
    st.markdown(f"**{len(gaps)} gaps** identified across {len(results)} measurable requirements.")

    for m in MODULE_ORDER:
        mod_gaps = [r for r in gaps if r["module"] == m]
        if not mod_gaps:
            continue
        st.markdown(f"### {m} — {MODULE_NAMES[m]}  ·  {len(mod_gaps)} gap(s)")
        for r in mod_gaps:
            mm = r["measured"]
            st.markdown(f"**{r['id']} · {r['term']}** — {mm['status']}  ·  `{r['hook']}`")
            if mm["gap"]:
                st.caption(f"Missing: {'; '.join(mm['gap'])}")
            if r.get("revision"):
                st.markdown(f'<div class="rev">{r["revision"]}</div>', unsafe_allow_html=True)

    from comply_engine import render_html
    html = render_html(rep, district=ss.district_name or "District")
    st.download_button(
        "Download full measurement report (HTML)",
        data=html,
        file_name=f"comply_colorado_report_{re.sub(r'[^A-Za-z0-9]+','_', ss.district_name or 'district').lower()}.html",
        mime="text/html",
    )


def _measure_single_policy(text: str) -> dict:
    """Run the rubric against a single policy's text and return the report dict."""
    rubric = build_rubric()
    provisions = chunk_text(text)
    results = []
    for c in rubric:
        row = {k: c[k] for k in ("id", "module", "module_name", "term", "hook", "status",
                                 "ag_test_tier", "pass_semantics", "must_pass", "context_only")}
        if c["context_only"]:
            row["measured"] = {"status": "context", "evidence": None, "gap": []}
            results.append(row)
            continue
        row["pass_condition"] = c["pass_condition"]
        row["revision"] = c["revision"]
        m = judge(c, provisions)
        row["measured"] = m
        if m["status"] != "Addressed":
            rem = judge(c, [{"heading": "Proposed revision", "text": c["revision"]}])
            row["remeasured"] = rem["status"]
        results.append(row)
    return {"provisions": len(provisions), "score": score(results), "results": results}


def _list_sample_policies() -> list[Path]:
    if not SAMPLE_POLICIES_DIR.exists():
        return []
    return sorted([p for p in SAMPLE_POLICIES_DIR.iterdir()
                   if p.is_file() and p.suffix.lower() in {".md", ".txt", ".pdf", ".docx"}])


def _reset_load_amend() -> None:
    for k in ("la_policy_text", "la_policy_name", "la_policy_code",
              "la_report", "la_report_amended", "la_amended_text",
              "selected_policy"):
        st.session_state[k] = None
    st.session_state.la_step = 1
    st.session_state.show_amended = False
    if "_amend_toggle" in st.session_state:
        del st.session_state["_amend_toggle"]


def view_load_amend() -> None:
    if LOGO.exists():
        st.image(str(LOGO), width=260)
    st.markdown('<div class="pill">AG rulemaking in progress — provisional items flagged</div>', unsafe_allow_html=True)
    st.markdown("# Load & Amend a Policy")
    st.markdown(
        '<p class="sub">Single-policy workflow: <b>Load → Analyze → Amend (before/after) → Rationale</b>. '
        'This is what you do for one policy end to end; the batch view runs it across a priority list.</p>',
        unsafe_allow_html=True,
    )

    # Progress indicator
    steps = ["1. Load", "2. Analyze", "3. Amend", "4. Rationale"]
    cur = st.session_state.la_step
    cols = st.columns(4)
    for i, s in enumerate(steps, start=1):
        marker = "●" if i == cur else ("✓" if i < cur else "○")
        style = f"color:{NAVY};font-weight:700" if i == cur else (f"color:{STAT}" if i < cur else f"color:{MUTED}")
        cols[i - 1].markdown(f'<div style="{style};font-size:14px">{marker} {s}</div>', unsafe_allow_html=True)
    st.markdown("---")

    # ---------- Step 1: Load ----------
    if cur == 1:
        st.markdown("### Step 1 — Load a policy")

        samples = _list_sample_policies()
        if samples:
            st.markdown("**Sample policies** (extracted from real Colorado district manuals)")
            for p in samples:
                col1, col2 = st.columns([4, 1])
                col1.markdown(f"`{p.name}` — {p.stat().st_size / 1024:.1f} KB")
                if col2.button("Load", key=f"la_load_{p.name}"):
                    text = parse_document(str(p))
                    st.session_state.la_policy_text = text
                    st.session_state.la_policy_name = p.name
                    stem = p.stem
                    st.session_state.la_policy_code = stem
                    # Auto-select for Policy Detail so it unlocks without going via Initial Report
                    st.session_state.selected_policy = stem
                    st.session_state.la_step = 2
                    st.rerun()
            st.markdown("---")

        st.markdown("### Or upload your own single policy (PDF / DOCX / TXT / MD)")
        up = st.file_uploader("Single-policy upload", type=["pdf", "docx", "txt", "md"], key="la_upload")
        if up is not None:
            suffix = os.path.splitext(up.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(up.read())
                path = tmp.name
            try:
                text = parse_document(path)
            finally:
                try:
                    os.unlink(path)
                except OSError:
                    pass
            st.session_state.la_policy_text = text
            st.session_state.la_policy_name = up.name
            code = os.path.splitext(up.name)[0]
            st.session_state.la_policy_code = code
            st.session_state.selected_policy = code
            st.session_state.la_step = 2
            st.rerun()
        return

    # From step 2 onward we need a loaded policy
    if st.session_state.la_policy_text is None:
        st.warning("No policy loaded. Go back to Step 1.")
        if st.button("← Back to Load"):
            _reset_load_amend()
            st.rerun()
        return

    # Sticky header showing which policy is loaded
    st.markdown(
        f"**Loaded:** `{st.session_state.la_policy_name}` &nbsp;·&nbsp; "
        f"{len(st.session_state.la_policy_text):,} characters",
        unsafe_allow_html=True,
    )
    if st.button("Load a different policy", key="la_change"):
        _reset_load_amend()
        st.rerun()
    st.markdown("")

    # ---------- Step 2: Analyze ----------
    if cur == 2:
        st.markdown("### Step 2 — Analyze against SB 26-189")
        if st.session_state.la_report is None:
            with st.spinner("Chunking policy into provisions and measuring against 34 rubric requirements..."):
                st.session_state.la_report = _measure_single_policy(st.session_state.la_policy_text)
        rep = st.session_state.la_report
        s = rep["score"]

        st.markdown(f"**Provisions found:** {rep['provisions']}")
        st.markdown(f"**Must-pass requirements addressed:** {s['must_pass_addressed']} of {s['must_pass_total']}")

        verdict = (
            '<div class="verdict-ok">Within the probable AG test on all must-pass requirements.</div>'
            if s["within_probable_ag_test"]
            else f'<div class="verdict-no">Not yet within the probable AG test — {len(s["failing"])} must-pass requirements unmet.</div>'
        )
        st.markdown(verdict, unsafe_allow_html=True)

        # If we've been to Step 3+ already, show the after-amendment score too
        if st.session_state.la_report_amended is not None:
            s2 = st.session_state.la_report_amended["score"]
            st.markdown("**After amendment (generated additions applied):**")
            st.markdown(f"Must-pass requirements addressed: {s2['must_pass_addressed']} of {s2['must_pass_total']}")
            amended_verdict = (
                '<div class="verdict-ok">Amended policy is within the probable AG test on all must-pass requirements.</div>'
                if s2["within_probable_ag_test"]
                else f'<div class="verdict-no">Amended policy still unmet on {len(s2["failing"])} must-pass requirements — {", ".join(s2["failing"])}.</div>'
            )
            st.markdown(amended_verdict, unsafe_allow_html=True)

        # Per-module breakdown
        results = [r for r in rep["results"] if not r["context_only"]]
        by_module: dict[str, list] = {}
        for r in results:
            by_module.setdefault(r["module"], []).append(r)
        for m in MODULE_ORDER:
            if m not in by_module:
                continue
            rows = by_module[m]
            addr = sum(1 for r in rows if r["measured"]["status"] == "Addressed")
            partial = sum(1 for r in rows if r["measured"]["status"] == "Partial")
            missing = sum(1 for r in rows if r["measured"]["status"] == "Not addressed")
            st.markdown(
                f'**{m} — {MODULE_NAMES[m]}**  ·  '
                f'<span style="color:{STAT}">{addr} addressed</span>  ·  '
                f'<span style="color:{PROV}">{partial} partial</span>  ·  '
                f'<span style="color:{CONT}">{missing} missing</span>',
                unsafe_allow_html=True,
            )
        st.markdown("")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back", key="la_back_2"):
                st.session_state.la_step = 1
                st.rerun()
        with col2:
            if st.button("Amend policy →", type="primary", key="la_next_2"):
                st.session_state.la_step = 3
                st.rerun()
        return

    # ---------- Step 3: Amend (before / after) ----------
    if cur == 3:
        st.markdown("### Step 3 — Amend the policy")
        rep = st.session_state.la_report
        gaps = [r for r in rep["results"] if not r["context_only"] and r["measured"]["status"] != "Addressed"]

        original = st.session_state.la_policy_text
        additions_block = _build_additions_block(gaps)
        amended = original.rstrip() + "\n\n" + additions_block

        st.caption(
            "Before is your policy exactly as loaded. After splices in original AI-aware language "
            "(offered for CASB ownership) at the end of the policy — every insertion tagged with the "
            "criterion ID and statutory hook it satisfies. This is the redline the attorney reviews."
        )

        col_b, col_a = st.columns(2)
        with col_b:
            st.markdown('**Before**')
            st.markdown(
                f'<div style="max-height:600px;overflow:auto;border:1px solid {LINE};'
                f'border-radius:6px;padding:12px;background:#fafbfd;font-size:12.5px;'
                f'white-space:pre-wrap;font-family:ui-monospace,Menlo,monospace">{_escape(original)}</div>',
                unsafe_allow_html=True,
            )
        with col_a:
            st.markdown('**After**')
            # Highlight the additions block with a green left border
            before_len = len(original.rstrip())
            after_original = _escape(amended[:before_len])
            after_additions = _escape(amended[before_len:])
            st.markdown(
                f'<div style="max-height:600px;overflow:auto;border:1px solid {LINE};'
                f'border-radius:6px;padding:12px;background:#fafbfd;font-size:12.5px;'
                f'white-space:pre-wrap;font-family:ui-monospace,Menlo,monospace">'
                f'{after_original}'
                f'<span style="background:#e4f3e8;border-left:3px solid {STAT};'
                f'display:block;padding:8px 10px;margin-top:8px">{after_additions}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown("")
        st.download_button(
            "Download amended policy (Markdown)",
            data=amended,
            file_name=f"{st.session_state.la_policy_code}_amended.md",
            mime="text/markdown",
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back", key="la_back_3"):
                st.session_state.la_step = 2
                st.rerun()
        with col2:
            if st.button("See rationale →", type="primary", key="la_next_3"):
                st.session_state.la_step = 4
                st.rerun()
        return

    # ---------- Step 4: Rationale ----------
    if cur == 4:
        st.markdown("### Step 4 — Why the after policy was created + AG rationale for approval")
        rep = st.session_state.la_report
        gaps = [r for r in rep["results"] if not r["context_only"] and r["measured"]["status"] != "Addressed"]

        if not gaps:
            st.success("No gaps found. The policy as loaded is within the probable AG test on all must-pass requirements.")
        else:
            st.caption(
                f"{len(gaps)} insertion(s) were made. Each block below explains, for one insertion: "
                "what was missing, why the language was added, and the AG's likely rationale for accepting it."
            )

            for r in gaps:
                mm = r["measured"]
                tier = r["ag_test_tier"]
                tier_note = {
                    "Statutory": "This is a hard statutory requirement — defensible on the enacted text of SB 26-189 today. An AG enforcement action would be unlikely to succeed against this insertion because it directly implements the statute.",
                    "Provisional": "This requirement will be shaped by AG rules due 2027-01-01. The inserted language is built to the standard the AG is most likely to set, based on the statutory text and the AG's stated rulemaking considerations. Risk: final rules could tighten the wording — flag for reconciliation on 2027-01-01.",
                    "Contested": "This item is a live battleground where commenters and the AG's framing disagree. The insertion takes the defensible broader-reading approach so the district is over-covered rather than under. Flagged for reconciliation against final rules.",
                }.get(tier, "")

                gap_labels = mm.get("gap") or []
                evidence_summary = (
                    f'The existing policy mentions "{(mm["evidence"]["text"][:180] + "...") if mm["evidence"] and len(mm["evidence"]["text"]) > 180 else (mm["evidence"]["text"] if mm["evidence"] else "")}" but does not fully satisfy the requirement.'
                    if mm["evidence"]
                    else "The existing policy contains no provision addressing this requirement."
                )

                st.markdown(
                    f'''
<div style="border:1px solid {LINE};border-radius:8px;padding:14px 16px;margin:10px 0;background:#fff">
<div style="display:flex;justify-content:space-between;align-items:center">
<div><span style="font-family:ui-monospace,Menlo,monospace;font-weight:700;color:{NAVY}">{r["id"]} · {r["term"]}</span></div>
<div><span class="badge b-{tier}">{tier}</span></div>
</div>
<div style="font-size:11.5px;color:{MUTED};font-family:ui-monospace,Menlo,monospace;margin:4px 0 10px">{r["hook"]}</div>

<div style="margin-bottom:8px"><b>What was missing.</b> {evidence_summary}
{"Specifically missing: " + "; ".join(gap_labels) + "." if gap_labels else ""}
</div>

<div style="margin-bottom:8px"><b>Why the after-language was added.</b> The insertion satisfies the criterion's pass condition — {r.get("pass_condition","")} — by adding original, AI-aware language that maps directly to the statutory hook.</div>

<div style="background:#eef4fb;border:1px solid #cfe0f2;border-radius:6px;padding:10px 12px;margin:8px 0;color:{NAVY};font-size:13px">
<b>Inserted language.</b> "{r.get("revision","")}"
</div>

<div style="margin-bottom:8px"><b>AG rationale for approval.</b> {tier_note}</div>

<div style="font-size:12px;color:{MUTED};border-top:1px solid {LINE};padding-top:8px;margin-top:8px">
<b>Semantics:</b> {r["pass_semantics"]}
</div>
</div>
                    ''',
                    unsafe_allow_html=True,
                )

        st.markdown("")
        st.markdown(
            f'<div class="note">Not legal advice. Provisional and Contested items must be reconciled against the '
            f'Colorado Attorney General\'s final rules before district-facing use. Every insertion above must be '
            f'attorney-reviewed before it enters your board policy.</div>',
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back", key="la_back_4"):
                st.session_state.la_step = 3
                st.rerun()
        with col2:
            if st.button("Load another policy", key="la_restart"):
                _reset_load_amend()
                st.rerun()
        return


def _escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _build_additions_block(gaps: list[dict]) -> str:
    if not gaps:
        return ""
    lines = ["", "---", "", "## Additions to satisfy SB 26-189 (offered for CASB ownership)", ""]
    by_module: dict[str, list] = {}
    for r in gaps:
        by_module.setdefault(r["module"], []).append(r)
    for m in MODULE_ORDER:
        if m not in by_module:
            continue
        lines.append(f"### Module {m} — {MODULE_NAMES[m]}")
        lines.append("")
        for r in by_module[m]:
            lines.append(f"**[{r['id']} · {r['term']} · {r['ag_test_tier']} · {r['hook']}]**")
            lines.append("")
            lines.append(r.get("revision", ""))
            lines.append("")
    return "\n".join(lines)


def main() -> None:
    st.set_page_config(page_title="VERA Comply — SB 26-189 (Colorado)", layout="wide")
    inject_css()
    init_state()
    sidebar()

    v = st.session_state.view
    if v == "load_amend":
        view_load_amend()
    elif v == "upload":
        view_upload()
    elif v == "report":
        view_report()
    elif v == "detail":
        view_detail()
    elif v == "overview":
        view_overview()
    elif v == "gap":
        view_gap()
    else:
        view_load_amend()


if __name__ == "__main__":
    main()
