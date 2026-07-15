# COMPLY-Colorado — Build & Handoff Spec (for Claude Code)

**Status:** Gate 1 complete (criteria + reference prototype). This document hands the build to Claude Code operating inside the existing `vera-comply` repository, to integrate the Colorado product and deploy to Render.

**Prime directive:** COMPLY-Colorado is a *compliance system of record* for a Colorado school district's use of automated decision-making technology under **SB 26-189**. A district (or CASB, on its behalf) supplies its existing policies and procedures; the app examines them against a sourced criteria set, produces a provision-by-provision gap analysis, and generates an AG-calculated policy revision — original language offered for CASB ownership, routed through the FERPA processes the district already runs.

---

## 0. Read first — non-negotiable rules

1. **Never invent citations.** Every requirement surfaced to a user must carry a real statutory hook. The criteria are pre-sourced in `criteria.json`; do not add or alter a criterion without a verifiable hook.
2. **No CSBA language, anywhere.** All model policy language is original work product offered for CASB ownership. Do not import, paraphrase, or seed from CSBA/CSBA-derived policy text. (The existing California app labels model language "CSBA" — that label and any such text must not carry into the Colorado product.)
3. **Spell it "Demsey"** (never "Dempsey") anywhere a name appears.
4. **Attorney-review gate.** Nothing is district-facing until a Colorado education/FERPA attorney reviews it. Build so that review is fast: keep the hook and status tag visible on every requirement.
5. **Keep the stack lean.** This session's workspace → chat files → **Render** → BoardBook. Do **not** add Google Drive/Docs, new SaaS, or new cloud dependencies. If a capability seems to need one, surface it as a decision, don't add it.
6. **Gated go/no-go.** Do not build Gate N+1 content on top of an unapproved Gate N. Surface open decisions (Section 8) to Brian rather than guessing.

---

## 1. What exists today

The deployed app (`vera-comply.onrender.com`) is the **California SB 1288** build. From its UI it has: a left sidebar (brand + "SB 1288 Compliance", Dashboard / District Info, a Policy Sections list A–F); a Dashboard with "X/6 Sections Complete" and six section cards; and a section-detail page with a "Model Policy Language (CSBA)" panel, a "Current Status Assessment" (dropdowns), and a "District-Specific Language" textarea.

**First task in the repo:** inspect and report the actual stack (framework, state/persistence, styling, build, Render config) before changing anything. This spec describes intent and content, not the current implementation, which only you can see.

**Reuse vs. replace:** reuse the shell, routing, styling system, and the section-detail *anatomy* (model-language panel → status assessment → district-specific textarea). Replace the *content model* and the section taxonomy per Section 3–4.

---

## 2. Source of truth: the criteria data

- `criteria.json` — the machine-readable Gate 1 Criteria Matrix: **38 criteria** across **6 policy modules (A–F)** plus a cross-cutting **X (Enforcement & Risk, context only — not a section)**. Each criterion: `id, module, term, hook, statement, source, status (Statutory|Provisional|Contested), artifact, verify_note`. Each module: `name, hook, model_language`.
- `COMPLY-Colorado_Criteria_Matrix.md` — human-readable copy for review.
- `comply-colorado-prototype.html` — the **reference implementation** of the pages (self-contained; criteria embedded as a JS const). Treat it as the visual/interaction spec, not production code.

The app must **render from the criteria data**, never hard-code requirements in views. When the AG publishes rules (due 2027-01-01), updating `criteria.json` must flow through to every screen and to the export.

---

## 3. Section taxonomy (the swap from SB 1288)

The six sections change from the California topic themes to the **SB 26-189 statutory modules**:

| Module | Section title | Statutory basis |
|---|---|---|
| A | ADMT Inventory | C.R.S. 6-1-1701(2), 1703 |
| B | Classification & FERPA Crosswalk | 6-1-1701(15); FERPA; C.R.S. 22-16 |
| C | Notice & Parent Access | 6-1-1704 |
| D | Recordkeeping | 6-1-1703; C.R.S. 22-16 |
| E | Procurement & Vendor Management | 6-1-1702; FERPA; C.R.S. 22-16; READ Act |
| F | Human Review & Oversight | 6-1-1701(15); 6-1-1705 |

X (Enforcement & Risk) is **not** a section card; surface it as the dashboard risk banner and in the export's risk memo.

---

## 4. Pages & components (see prototype for the realized look)

- **Shell:** sidebar brand "VERA Comply / SB 26-189 Compliance · Colorado"; nav Dashboard, District Info, the six section buttons, Gap Analysis & Revision. A persistent status chip: *"AG rulemaking in progress — provisional items flagged."*
- **Dashboard:** title "SB 26-189 Compliance Dashboard"; **criteria-based** progress ("N of 34 requirements addressed", where 34 = the A–F criteria; X excluded); six module cards each showing title, statutory hook, one-line description, `addressed/total` count, and status; a fixed **Enforcement & risk** banner (X1–X4); a "Generate Revision" affordance (enabled once ≥1 addressed).
- **District Info:** district name; **FERPA-subject** flag (governs which safe-harbor language appears throughout); **policy source** = BoardBook import | Document upload. This drives the examination.
- **Section detail:** header + statutory basis; **Model Policy Language** panel labeled *"original, offered for CASB ownership (draft)"*; a **Requirement Assessment** list — one row per criterion showing statement, hook, a status badge (Statutory/Provisional/Contested), an inline FERPA note where the hook is a FERPA safe harbor (1704(9)/1705(2)) or FERPA reg (99.31/99.20-.21), and a status selector (Not addressed / Partially addressed / Addressed); a **District-Specific Language** textarea.
- **Gap Analysis & Revision:** per module, Missing / Partial / Addressed roll-up, each item linked to its criterion id + hook; a **Revision export** (Gate 2 — see §5).

---

## 5. Beyond the prototype (production capabilities)

The prototype is stateless and in-memory. Production adds:

1. **Persistence** — per-district saved state (criterion statuses, district-specific language, District Info). Backend/DB choice is an open decision (§8); keep it inside the existing Render footprint.
2. **Examination ingestion** — accept district policies via **BoardBook import** or **document upload**, and match provisions to criteria to pre-populate status. *Automation level is an open decision* (automated classification vs. attorney-in-the-loop). Until decided, ship manual status entry (as in the prototype) and treat automated matching as a later increment.
3. **Revision/export generator** (Gate 2) — produce the amended + gap-fill policy document from module `model_language` + district-specific language, with provisional/contested items flagged and a risk memo (X). Output as **Markdown/HTML/PDF** — not a Google Doc. This is the deliverable the whole flow exists to produce.
4. **Multi-tenant / white-label** — if CASB-branded, per-district tenancy and CASB-level admin. Open decision (§8).

---

## 6. Build sequence (gates)

- **Gate 1 — Criteria (done):** `criteria.json`, matrix, prototype.
- **Gate 2 — Content + export:** finalize/attorney-pass the six modules' original language and per-criterion artifact templates; build the revision/export generator.
- **Gate 3 — App integration + deploy:** wire criteria data + persistence into the real app; keep the look; Render staging → attorney review → prod.

Do Gate 3 integration and Gate 2 export as separate reviewable increments; don't fuse them.

---

## 7. Test plan (five layers)

1. **Traceability (automated):** assert every criterion's SB 26-189 hook exists in the enacted text and that FERPA/22-16/READ-Act hooks resolve to real provisions. (Passing as of Gate 1.) Wire this as a CI check so no criterion ships without a live hook.
2. **Coverage:** every deployer duty in the act maps to ≥1 criterion and ≥1 module; every module card is backed by criteria; no orphan views.
3. **Functional/unit:** test the status → progress → gap-analysis logic and the export generator (counts, groupings, provisional flags, FERPA-note triggering).
4. **Adversarial review:** a fresh reviewer (subagent or attorney) attacks the Matrix — a criterion with no basis, a duty with no criterion, a "provisional" dressed as settled. Run before each release.
5. **End-to-end acceptance:** run a **real Colorado district's** published policies through the examination; confirm the gaps COMPLY flags are the gaps a FERPA/education attorney would flag. This is the acceptance bar and the Yennie demo. Then: Render **staging** deploy → attorney review → prod.

---

## 8. Open decisions — surface to Brian, do not guess

1. **Examination automation:** automated policy-to-criteria classification vs. attorney-in-the-loop (affects trust, cost, and liability).
2. **BoardBook ingestion:** API/export integration vs. document upload.
3. **Persistence/backend:** which store, within the Render footprint.
4. **Tenancy:** single-district vs. CASB multi-tenant white-label.
5. **Naming:** "VERA Comply" app brand vs. "COMPLY-Colorado" product; subdomain `vera-comply-co`.
6. **FERPA safe-harbor granularity:** treat as a **per-covered-ADMT** determination (current build) — confirm.

---

## 9. Handoff bundle

- `criteria.json` — data source of truth (38 criteria, 6 modules + X).
- `COMPLY-Colorado_Criteria_Matrix.md` — reviewable matrix.
- `comply-colorado-prototype.html` — reference implementation of the pages.
- `COMPLY-Colorado_Handoff_Spec.md` — this document.

*Not legal advice. Provisional/Contested criteria must be reconciled against the Colorado Attorney General's final rules before district-facing use.*
