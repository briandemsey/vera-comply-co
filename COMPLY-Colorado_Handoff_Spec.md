# COMPLY-Colorado — Build & Handoff Spec (Policy-First) — for Claude Code

**Supersedes** the earlier criterion-first spec. The product is **policy-first**: a district uploads its policy manual, gets an initial report that examines every policy and flags the ones subject to SB 26-189, then works them one at a time (examine → update language → test), with everything saved per district and visible to CASB across districts.

**One-line product:** *Upload your policies → see which are subject to SB 26-189 → update each in-scope policy to AI-aware language → test each revision against the probable AG standard.*

The intelligence is proven on a real district (Poudre School District — 185 policies classified, 84 in scope, 6 fully worked). Claude Code's job is to wrap the deployed, persistent, multi-tenant product around that intelligence — not to re-derive the SB 26-189 judgment.

---

## 0. Read first — non-negotiable rules

1. **Never invent citations.** Every requirement and every statutory reference must trace to real text. The rubric (`criteria_rubric.json`) is pre-sourced; do not add or alter a criterion or a statutory cite without a verifiable hook.
2. **No CSBA language.** All model/updated policy language is original work product offered for CASB ownership. Never import or seed from CSBA/CSBA-derived text.
3. **Spell it "Demsey"** (never "Dempsey").
4. **Attorney-review gate.** No scope verdict, updated language, or AG-test result is district-facing until a Colorado education/FERPA attorney reviews it. Build the human-in-the-loop confirm step as first-class (see the checklist / per-policy confirm).
5. **Keep the stack lean.** Workspace → **Render** → BoardBook/Diligent. Do **not** add Google Drive/Docs or new SaaS. Surface a need as a decision, don't add a dependency.
6. **Gated go/no-go.** Don't build Gate N+1 on an unapproved Gate N. Surface open decisions (§8) rather than guessing.

---

## 1. What exists today

The deployed Colorado app (`vera-comply-co.onrender.com`) is a **Streamlit (Python)** app — currently descriptive/self-report. **First task in the repo:** inspect and report the actual stack (framework, state/persistence, styling, Render config, auth) before changing anything. This spec is intent and content; the repo is the ground truth only you can see.

Streamlit is fine for the engine and a pilot; a multi-tenant persistent portal pushes its edges — see §8 decision 4.

---

## 2. The product flow (policy-first)

1. **Upload.** District uploads its policy manual (PDF / DOCX / TXT — the engine parses all three). Split the manual into **individual policies** (by heading/code structure). District Info: name, FERPA-subject flag, source (upload / BoardBook / Diligent export).
2. **Initial Report (policy-indexed triage).** For each policy: **subject to review?** (yes/no), applicable modules (A–F), priority (High/Med/Low), one-line rationale. Summary tiles (N examined / subject / high / not subject), a "recommended to address first" list, and a **checklist mode** where a district official confirms each scope verdict (this doubles as the human-in-the-loop attestation).
3. **Per-policy loop.** Select an in-scope policy →
   - **Examine** — what content is subject to SB 26-189 and why.
   - **Applicable requirements** — the modules/criteria it implicates.
   - **Current gap** — what the policy is missing.
   - **Updated language** — original, AI-aware language to add (offered for CASB ownership).
   - **Probable-AG test** — the applicable requirements with confidence tiers (Statutory / Provisional / Contested) and a within/not-within verdict.
   - **Confirm / edit** — attorney or admin accepts or edits before it's final.
4. **Persistence.** Save per district: uploaded policies, scope verdicts + confirmations, generated revisions + edits, test results, progress.
5. **CASB view.** Multi-tenant admin dashboard: every district, its scope counts, and how far each is through its in-scope policies.

`comply_policy_prototype.html` in the bundle is the **reference implementation** of steps 2–3 (report + per-policy detail + checklist), rendered from the real Poudre data. Treat it as the visual/interaction spec, not production code.

---

## 3. The intelligence (built and proven here — two layers)

**Layer 1 — the rubric (the 34 SB 26-189 requirements as tests).**
- `criteria.json` — base criteria (38: 34 measurable across modules A–F, plus 4 X context).
- `comply_rubric.py` → `criteria_rubric.json` — each criterion as a test: `pass_condition`, `evidence_required`, `measurement_method`, detection `cues`, `ag_test_tier`, and original gap-fill `revision` language.
- Modules: A ADMT Inventory · B Classification & FERPA Crosswalk · C Notice & Parent Access · D Recordkeeping · E Procurement & Vendor Management · F Human Review & Oversight.

**Layer 2 — the policy-level logic (the policy-first shape).**
- **Scope classifier** — for each policy, determine `subject_to_review`, `applicable_modules`, `priority`, `rationale`. Output schema is `policies_scope.json`:
  ```
  {"code","title","subject_to_review":bool,"applicable_modules":["A".."F"],
   "rationale":"one sentence","priority":"High|Medium|Low"}
  ```
  Rule: a policy is subject to review if it governs a **consequential decision** about a student (enrollment, placement, gifted/special-ed, discipline, suspension/expulsion, screening/testing, grading, class rank, graduation, eligibility) or staff (hiring, evaluation, discipline, dismissal), **or** governs student/personal data, records, technology, monitoring, or a human-review/appeal/correction process the Act regulates. Not in scope: purely administrative/fiscal/facilities/operational matters with no person-decision and no personal-data/technology content.
- **Per-policy examine/revise/test** — for an in-scope policy, produce the examination, the updated AI-aware language, and the probable-AG test against the applicable modules. `policy_details.json` (embedded as `DETAILS` in `build_prototype.py`) has **six fully worked examples** (`JKD-JKE`, `JLDAC`, `JRA-JRC`, `JS`, `GDQD`, `IKC`) showing the target quality and structure: `{examination, gap, updated, test:[[module,tier,satisfied]...]}`.

**The judge/classifier is an LLM with the attorney in the loop.** A transparent cue-based heuristic exists in `comply_engine.py` for offline runs; production swaps in the LLM classifier/judge (the interface is `judge()` and the scope classifier). The scope classification and per-policy generation in the prototype were produced by exactly this LLM pass over the real corpus.

---

## 4. Pages & components

- **Shell:** VERA Comply / "SB 26-189 Compliance · Colorado"; persistent chip "AG rulemaking in progress — provisional items flagged."
- **Upload + District Info** (§2.1).
- **Initial Report** (§2.2) — tiles, recommended-first, policy table (code, title, scope badge, priority, modules, rationale), checklist/confirm mode. See prototype.
- **Policy Detail** (§2.3) — the five-part examine→requirements→gap→updated-language→AG-test view, plus confirm/edit. See prototype.
- **CASB Admin** — fleet dashboard across districts (§2.5).
- **Persistence** beneath all of it (§2.4).

---

## 5. Build sequence (gates)

- **Gate 1 — Intelligence (proven here):** rubric + scope classifier + per-policy examine/revise/test, demonstrated on Poudre. Artifacts in the bundle.
- **Gate 2 — Wire into the app:** upload → split into policies → scope-classify → Initial Report → per-policy loop, with the LLM classifier/judge and the attorney-confirm step. Swap the heuristic for the LLM interface. Keep the prototype's look.
- **Gate 3 — Deployed product:** per-district persistence, accounts, CASB multi-tenant/admin view, deploy to Render (staging → attorney review → prod).

Do Gate 2 (per-policy intelligence in-app) and Gate 3 (persistence/tenancy/deploy) as separate reviewable increments.

---

## 6. Test plan

1. **Scope-classification accuracy** — the `subject_to_review` calls and priorities must hold up to an attorney's read; spot-check a sample each release, and treat the checklist confirmations as the ground-truth feedback loop.
2. **Per-policy revision correctness** — updated language actually satisfies the applicable requirements; AG-test tiers are honest (Statutory defensible; Provisional/Contested flagged, never asserted as guaranteed approval).
3. **Traceability (CI)** — every criterion's SB 26-189 hook resolves in the enacted text; FERPA/22-16/READ-Act hooks resolve. No criterion ships without a live hook.
4. **Functional / persistence** — upload→split→report→per-policy→save/reload; multi-tenant isolation.
5. **End-to-end acceptance** — run the **Poudre fixture** (in the bundle) end to end: report → work an in-scope policy → attorney reviews the generated revision. This is the acceptance bar and the CASB/Yennie demo. Then Render staging → attorney review → prod.

---

## 7. Handoff bundle

- `criteria.json`, `criteria_rubric.json` — the 34-requirement rubric (source of truth).
- `comply_rubric.py`, `comply_engine.py` — rubric + engine (parse/chunk/measure/score/revise; LLM-judge interface with heuristic stand-in).
- `policies_scope.json` — scope-classifier output over the real Poudre manual (185 policies) + schema.
- `build_prototype.py` (contains `DETAILS`, the 6 worked policy examples) — schema + reference content for per-policy examine/revise/test.
- `comply_policy_prototype.html` — reference implementation of the Initial Report + per-policy loop + checklist.
- `streamlit_app.py` — earlier upload→measure Streamlit prototype (starting point for Gate 2).
- **Poudre corpus** (`corpus/*.txt`, `Poudre_Policy_Compendium.docx`) — the end-to-end test fixture.

---

## 8. Open decisions — surface to Brian, do not guess

1. **LLM classifier/judge** — model choice and the attorney-in-the-loop confirm workflow (who confirms, when).
2. **Scope threshold calibration** — how inclusive "subject to review" should be (current pass leans inclusive; the checklist lets the district narrow).
3. **Per-policy generation** — generate updated language on-demand per policy, or batch all in-scope at upload.
4. **Persistence / backend & tenancy** — store, and single-district vs CASB multi-tenant white-label; auth. (Stay within the Render footprint.)
5. **Manual splitting** — how to reliably split an uploaded manual into individual policies (heading/code detection; BoardBook/Diligent export structure).
6. **Naming** — "VERA Comply" app vs "COMPLY-Colorado" product; subdomain.
7. **FERPA safe-harbor granularity** — per-covered-ADMT determination (current) — confirm.

*Not legal advice. Provisional/Contested items must be reconciled against the Colorado Attorney General's final rules before district-facing use.*
