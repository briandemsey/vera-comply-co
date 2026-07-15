"""VERA Comply — SB 26-189 Compliance (Colorado)

Streamlit port of comply-colorado-prototype_1.html.
Renders entirely from criteria.json; never hard-code requirements.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import streamlit as st

DATA_PATH = Path(__file__).parent / "criteria.json"
ORDER = ["A", "B", "C", "D", "E", "F"]
STATUS_OPTIONS = ["Not addressed", "Partially addressed", "Addressed"]
FERPA_HOOK_RE = re.compile(r"1704\(9\)|1705\(2\)|99\.31|99\.20")

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


@st.cache_data
def load_data() -> dict:
    with DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def init_state(criteria: list[dict]) -> None:
    if "status" not in st.session_state:
        st.session_state.status = {c["id"]: "Not addressed" for c in criteria}
    if "district_name" not in st.session_state:
        st.session_state.district_name = ""
    if "district_ferpa" not in st.session_state:
        st.session_state.district_ferpa = "Yes"
    if "district_source" not in st.session_state:
        st.session_state.district_source = "BoardBook import"
    if "view" not in st.session_state:
        st.session_state.view = "dash"
    if "dsl" not in st.session_state:
        st.session_state.dsl = {m: "" for m in ORDER}


def inject_css() -> None:
    st.markdown(
        f"""
        <style>
        .block-container {{padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1000px;}}
        [data-testid="stSidebar"] {{background: {RAIL}; border-right: 1px solid {LINE};}}
        [data-testid="stSidebar"] .stButton > button {{
            width: 100%; text-align: left; background: {NAVY}; color: #fff;
            border: none; border-radius: 6px; padding: 9px 12px; margin-bottom: 6px;
            font-size: 13px;
        }}
        [data-testid="stSidebar"] .stButton > button:hover {{opacity: .92;}}
        h1 {{color: {NAVY}; font-size: 27px; margin: 4px 0;}}
        h2 {{color: {NAVY};}}
        h3 {{color: {NAVY};}}
        .sub {{color: {MUTED}; margin: 0 0 18px;}}
        .pill {{
            display: inline-block; font-size: 11px; padding: 3px 9px; border-radius: 20px;
            background: {PROVBG}; color: {PROV}; border: 1px solid #e6cf93; margin-bottom: 14px;
        }}
        .brand {{color: {NAVY}; font-weight: 700; font-size: 19px; text-align: center;}}
        .brand small {{display: block; color: {MUTED}; font-weight: 500; font-size: 12px; margin-top: 3px;}}
        .card {{
            border: 1.5px solid {NAVY}; border-radius: 9px; padding: 16px; background: #fff;
            margin-bottom: 14px;
        }}
        .card h3 {{margin: 0; font-size: 17px;}}
        .card .hook {{font-size: 11.5px; color: {MUTED}; font-family: ui-monospace, Menlo, monospace;}}
        .card .desc {{font-size: 13px; color: #33414f; margin-top: 6px;}}
        .card .meta {{font-size: 12.5px; margin-top: 6px;}}
        .cnt {{font-weight: 700;}}
        .badge {{
            font-size: 10.5px; font-weight: 700; padding: 2px 7px; border-radius: 4px;
            text-transform: uppercase; letter-spacing: .03em;
        }}
        .b-Statutory {{background: {STATBG}; color: {STAT};}}
        .b-Provisional {{background: {PROVBG}; color: {PROV};}}
        .b-Contested {{background: {CONTBG}; color: {CONT};}}
        .model {{
            background: #eef4fb; border: 1px solid #cfe0f2; border-radius: 8px;
            padding: 16px; color: {NAVY2}; font-size: 14px; line-height: 1.5; margin: 6px 0 22px;
        }}
        .model .lbl {{
            font-size: 11px; text-transform: uppercase; letter-spacing: .05em;
            color: {MUTED}; font-weight: 700; margin-bottom: 8px;
        }}
        .crit {{border: 1px solid {LINE}; border-radius: 8px; padding: 14px 16px; margin-bottom: 12px;}}
        .crit .top {{display: flex; justify-content: space-between; gap: 12px; align-items: flex-start;}}
        .crit .id {{font-family: ui-monospace, Menlo, monospace; font-weight: 700; color: {NAVY};}}
        .crit .stmt {{margin: 6px 0; font-size: 13.5px;}}
        .crit .hook {{font-size: 11.5px; color: {MUTED}; font-family: ui-monospace, Menlo, monospace;}}
        .ferpa {{
            font-size: 12px; color: {STAT}; background: {STATBG}; padding: 6px 10px;
            border-radius: 5px; margin-top: 8px; display: inline-block;
        }}
        .risk {{
            border-left: 4px solid {NAVY}; background: #f6f9fc; padding: 12px 16px;
            margin: 8px 0 24px; font-size: 12.5px; color: #33414f;
        }}
        .note {{
            font-size: 12px; color: {MUTED}; margin-top: 22px;
            border-top: 1px solid {LINE}; padding-top: 12px;
        }}
        .tag-Not {{color: {CONT};}}
        .tag-Part {{color: {PROV};}}
        .tag-Add {{color: {STAT};}}
        </style>
        """,
        unsafe_allow_html=True,
    )


def sidebar(modules: dict) -> None:
    with st.sidebar:
        st.markdown(
            '<div class="brand">VERA Comply<small>SB 26-189 Compliance · Colorado</small></div>',
            unsafe_allow_html=True,
        )
        st.markdown("---")
        if st.button("Dashboard", key="nav_dash"):
            st.session_state.view = "dash"
        if st.button("District Info", key="nav_district"):
            st.session_state.view = "district"
        st.markdown("---")
        st.markdown(
            f'<div style="font-size:12px;font-weight:700;color:{MUTED};margin:6px 4px">POLICY SECTIONS</div>',
            unsafe_allow_html=True,
        )
        for m in ORDER:
            if st.button(f"{m}: {modules[m]['name']}", key=f"nav_{m}"):
                st.session_state.view = m
        st.markdown("---")
        if st.button("Gap Analysis & Revision", key="nav_gap"):
            st.session_state.view = "gap"


def module_counts(criteria: list[dict], m: str) -> tuple[int, int, int]:
    cs = [c for c in criteria if c["module"] == m]
    add = sum(1 for c in cs if st.session_state.status[c["id"]] == "Addressed")
    part = sum(1 for c in cs if st.session_state.status[c["id"]] == "Partially addressed")
    return len(cs), add, part


def overall_progress(criteria: list[dict]) -> tuple[int, int, int]:
    all_c = [c for c in criteria if c["module"] in ORDER]
    add = sum(1 for c in all_c if st.session_state.status[c["id"]] == "Addressed")
    pct = round(100 * add / len(all_c)) if all_c else 0
    return add, len(all_c), pct


SHORT_DESC = {
    "A": "Inventory every covered AI decision system.",
    "B": "Classify each system and crosswalk it to FERPA safe harbors.",
    "C": "Notice families and disclose adverse outcomes — via FERPA.",
    "D": "Retain three-year decision records (no FERPA analog).",
    "E": "Gate vendors on FERPA, Colorado data law, and screener validity.",
    "F": "Ensure a trained human can override every covered decision.",
}


def view_dash(criteria: list[dict], modules: dict) -> None:
    logo = Path(__file__).parent / "assets" / "casb_logo_sharp.png"
    if logo.exists():
        st.image(str(logo), width=260)
    st.markdown('<div class="pill">AG rulemaking in progress — provisional items flagged</div>', unsafe_allow_html=True)
    st.markdown("# SB 26-189 Compliance Dashboard")
    st.markdown('<p class="sub">Colorado school-district deployer compliance for automated decision-making technology.</p>', unsafe_allow_html=True)

    add, total, pct = overall_progress(criteria)
    st.markdown(
        f'<div style="font-size:18px;font-weight:600">Compliance Progress: {add} of {total} requirements addressed</div>',
        unsafe_allow_html=True,
    )
    st.progress(pct / 100 if total else 0)

    st.markdown(
        '<div class="risk"><b>Enforcement &amp; risk context:</b> Part 17 is enforced solely by the '
        'Attorney General with no private right of action (§6-1-1706, 1709); a 60-day cure applies '
        'unless knowing/repeated (repeals 2030). Residual private exposure runs through the Colorado '
        'Anti-Discrimination Act (§6-1-1707). Effective Jan 1, 2027.</div>',
        unsafe_allow_html=True,
    )

    st.markdown("## Policy Sections")
    cols = st.columns(3)
    for i, m in enumerate(ORDER):
        md = modules[m]
        t, addm, partm = module_counts(criteria, m)
        state = "Addressed" if addm == t else ("In progress" if addm + partm > 0 else "Incomplete")
        with cols[i % 3]:
            st.markdown(
                f'<div class="card"><h3>{m} — {md["name"]}</h3>'
                f'<div class="hook">{md["hook"]}</div>'
                f'<div class="desc">{SHORT_DESC[m]}</div>'
                f'<div class="meta"><span class="cnt">{addm}/{t}</span> requirements addressed · {state}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button(f"Edit Section {m}", key=f"edit_{m}"):
                st.session_state.view = m
                st.rerun()


def view_district() -> None:
    st.markdown("# District Info")
    st.markdown('<p class="sub">Context that drives the examination of your policies.</p>', unsafe_allow_html=True)

    st.session_state.district_name = st.text_input("District name", value=st.session_state.district_name)
    st.session_state.district_ferpa = st.selectbox(
        "Subject to FERPA?",
        options=["Yes", "No"],
        index=["Yes", "No"].index(st.session_state.district_ferpa),
    )
    st.session_state.district_source = st.selectbox(
        "How do your policies and procedures reach us?",
        options=["BoardBook import", "Document upload"],
        index=["BoardBook import", "Document upload"].index(st.session_state.district_source),
    )
    st.markdown(
        '<div class="note">FERPA-subject status governs which safe-harbor language appears throughout your sections.</div>',
        unsafe_allow_html=True,
    )


def ferpa_note(hook: str) -> str:
    if FERPA_HOOK_RE.search(hook):
        return f'<div class="ferpa">Satisfiable through your existing FERPA process — {hook}</div>'
    return ""


def view_section(m: str, criteria: list[dict], modules: dict) -> None:
    md = modules[m]
    st.markdown('<div class="pill">AG rulemaking in progress — provisional items flagged</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="color:{NAVY};font-size:24px;font-weight:600">Section {m}: {md["name"]}</div>', unsafe_allow_html=True)
    st.markdown(f'<p class="sub">Statutory basis: {md["hook"]}</p>', unsafe_allow_html=True)

    st.markdown(
        f'<div class="model"><div class="lbl">Model Policy Language — original, offered for CASB ownership (draft)</div>{md["model_language"]}</div>',
        unsafe_allow_html=True,
    )

    st.markdown("### Requirement Assessment")
    for c in [c for c in criteria if c["module"] == m]:
        cid = c["id"]
        st.markdown(
            f'<div class="crit">'
            f'<div class="top"><span class="id">{cid} · {c["term"]}</span>'
            f'<span class="badge b-{c["status"]}">{c["status"]}</span></div>'
            f'<div class="stmt">{c["statement"]}</div>'
            f'<div class="hook">{c["hook"]}</div>'
            f'{ferpa_note(c["hook"])}'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.session_state.status[cid] = st.selectbox(
            f"Status for {cid}",
            options=STATUS_OPTIONS,
            index=STATUS_OPTIONS.index(st.session_state.status[cid]),
            key=f"sel_{cid}",
            label_visibility="collapsed",
        )

    st.session_state.dsl[m] = st.text_area(
        "District-Specific Language (optional)",
        value=st.session_state.dsl[m],
        placeholder="Customize the model language for your district…",
        height=100,
    )
    st.markdown(
        '<div class="note">Model language is original work product offered for CASB ownership. '
        'Provisional and Contested items are subject to the Attorney General’s final rules.</div>',
        unsafe_allow_html=True,
    )


def view_gap(criteria: list[dict], modules: dict) -> None:
    st.markdown("# Gap Analysis & Revision")
    st.markdown(
        '<p class="sub">Where your policies and procedures stand against SB 26-189, provision by provision.</p>',
        unsafe_allow_html=True,
    )

    for m in ORDER:
        cs = [c for c in criteria if c["module"] == m]
        miss = [c for c in cs if st.session_state.status[c["id"]] == "Not addressed"]
        part = [c for c in cs if st.session_state.status[c["id"]] == "Partially addressed"]
        add = [c for c in cs if st.session_state.status[c["id"]] == "Addressed"]

        st.markdown(f'<h4 style="color:{NAVY};margin:16px 0 6px">{m} — {modules[m]["name"]}</h4>', unsafe_allow_html=True)
        lines = []
        if miss:
            joined = "; ".join(f'{c["id"]} {c["term"]} [{c["hook"]}]' for c in miss)
            lines.append(f'<li class="tag-Not"><b>Missing ({len(miss)}):</b> {joined}</li>')
        if part:
            joined = "; ".join(f'{c["id"]} {c["term"]}' for c in part)
            lines.append(f'<li class="tag-Part"><b>Partial ({len(part)}):</b> {joined}</li>')
        if add:
            joined = ", ".join(c["id"] for c in add)
            lines.append(f'<li class="tag-Add"><b>Addressed ({len(add)}):</b> {joined}</li>')
        if not cs:
            lines.append("<li>—</li>")
        st.markdown(f'<ul style="margin:0 0 6px;padding-left:20px">{"".join(lines)}</ul>', unsafe_allow_html=True)

    addv, totalv, _ = overall_progress(criteria)
    unmet = totalv - addv
    st.markdown(
        f'<div class="risk">Revision export (stub): COMPLY would now amend the {unmet} unmet items '
        'and generate original policy language — routed through your FERPA processes — producing an '
        'AG-calculated revision offered for CASB ownership. Wiring this export to a document generator '
        'is a Gate 2 build step.</div>',
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(page_title="VERA Comply — SB 26-189 (Colorado)", layout="wide")
    data = load_data()
    criteria = data["criteria"]
    modules = data["modules"]

    init_state(criteria)
    inject_css()
    sidebar(modules)

    v = st.session_state.view
    if v == "dash":
        view_dash(criteria, modules)
    elif v == "district":
        view_district()
    elif v == "gap":
        view_gap(criteria, modules)
    elif v in ORDER:
        view_section(v, criteria, modules)
    else:
        view_dash(criteria, modules)


if __name__ == "__main__":
    main()
