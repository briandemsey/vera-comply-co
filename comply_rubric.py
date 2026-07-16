#!/usr/bin/env python3
"""COMPLY-Colorado measurable rubric: turns each criterion into a test.

Each A-F criterion gains:
  pass_condition      - what must be present in a district policy to satisfy it
  evidence_required   - the kind of provision text that proves it
  measurement_method  - how the engine detects it
  cues                - concept groups (lists of synonyms); a group is 'met' if any synonym appears
  gap_labels          - human phrase per concept group (used to state what is missing)
  revision            - original gap-fill language (offered for CASB ownership) that satisfies the test
ag_test_tier is derived from the criterion's status:
  Statutory  -> passes now (hard pass/fail; defensible today)
  Provisional-> built to the expected rule (subject to the AG's final rules)
  Contested  -> defensible position taken (flagged for AG reconciliation)
"""
import json, os
_HERE = os.path.dirname(os.path.abspath(__file__))
def _load_base():
    d = json.load(open(os.path.join(_HERE, "criteria.json")))
    C = [(c["id"], c["module"], c["term"], c["hook"], c["statement"],
          c["source"], c["status"], c["artifact"], c.get("verify_note","")) for c in d["criteria"]]
    MODULES = {k: (v["name"], v["hook"], v["model_language"]) for k, v in d["modules"].items()}
    return C, MODULES
C, MODULES = _load_base()

TIER = {
 "Statutory":   {"tier":"Statutory",  "pass_semantics":"Hard requirement — must fully pass; defensible today.", "must_pass":True},
 "Provisional": {"tier":"Provisional","pass_semantics":"Built to the standard we expect the AG to set; subject to final rules.", "must_pass":True},
 "Contested":   {"tier":"Contested",  "pass_semantics":"Defensible reading taken where commenters/AG framing disagree; flagged for reconciliation.", "must_pass":False},
}
# status field on each criterion may read e.g. "Statutory" / "Provisional" / "Contested"
def tier_for(status):
    key = "Statutory" if status.startswith("Stat") else "Provisional" if status.startswith("Prov") else "Contested"
    return TIER[key]

# id -> test spec.  cues: list of groups; group met if any term (substring, case-insensitive) present.
TESTS = {
 "A1":{"pass":"Policy requires the district to identify and inventory every automated decision-making technology it uses that generates predictions, recommendations, classifications, rankings, or scores used to make, guide, or assist a decision about an individual.",
   "evid":"An inventory/identification obligation naming automated or algorithmic systems.","meth":"Detect an inventory duty AND reference to automated/algorithmic decision systems.",
   "cues":[["inventory","identify","catalog","register","maintain a list","list of"],["automated decision","admt","algorithm","artificial intelligence","ai system","ai tool","predictive","scoring system","machine learning"]],
   "labels":["an inventory/identification duty","reference to automated decision systems"],
   "rev":"The District shall identify and maintain an inventory of every automated decision-making technology it uses to make, guide, or assist a decision about a student."},
 "A2":{"pass":"Policy provides a method to determine which systems are 'covered' — i.e., materially influence a consequential decision (a non-de-minimis factor affecting the outcome).",
   "evid":"A materiality/coverage determination step.","meth":"Detect a materiality test tied to consequential decisions.",
   "cues":[["materially influence","material factor","non-de-minimis","affects the decision","significant factor","relied upon"],["consequential decision","covered system","covered admt"]],
   "labels":["a materiality test","tie to consequential decisions"],
   "rev":"For each system, the District shall determine whether it materially influences a consequential decision, and if so treat it as a covered system under this policy."},
 "A3":{"pass":"Policy scopes which education decisions are consequential (enrollment or an education opportunity) and distinguishes routine academic administration and classroom personalization that are excluded.",
   "evid":"An education-domain scope statement with the routine-administration carve-out.","meth":"Detect education consequential-decision scoping.",
   "cues":[["consequential decision","materially influence"],["education","enrollment","placement","eligibility","gifted","special education","discipline","opportunity"]],
   "labels":["a consequential-decision definition","the education decisions in scope"],
   "rev":"Consequential decisions in education include enrollment and education opportunities such as placement, eligibility, and program access; routine academic administration and classroom personalization that do not materially influence such decisions are excluded."},
 "A4":{"pass":"Policy flags predictive screeners (including SB 25-200 / READ Act dyslexia screeners) as candidate covered systems pending a materiality analysis.",
   "evid":"Named treatment of screeners/predictive assessments as candidate ADMT.","meth":"Detect screener + coverage treatment.",
   "cues":[["screener","screening","dyslexia","read act","interim assessment","predictive assessment","risk score"],["covered","admt","automated","materially"]],
   "labels":["identification of predictive screeners","their treatment as candidate covered systems"],
   "rev":"Universal screeners that produce predictive scores or classifications about students, including READ Act dyslexia screeners, shall be evaluated as candidate covered systems."},
 "A5":{"pass":"Policy requires the inventory to be maintained as a current register and re-reviewed on developer material updates.",
   "evid":"An ongoing-maintenance / update obligation for the inventory.","meth":"Detect maintenance cadence + update trigger.",
   "cues":[["maintain","update","current","annually","periodically","review the inventory","keep up to date"],["inventory","register","list"]],
   "labels":["an inventory-maintenance duty","a review/update trigger"],
   "rev":"The District shall keep the inventory current and re-review each system upon notice of a material update or modification from its developer."},

 "B1":{"pass":"Policy classifies each covered system by decision type and covered domain.",
   "evid":"A classification/categorization step per system.","meth":"Detect classification tied to decision type/domain.",
   "cues":[["classif","categor","characteriz"],["decision type","covered domain","domain","use case"]],
   "labels":["a classification step","classification by decision type or domain"],
   "rev":"For each covered system, the District shall classify the decision type and the covered domain it affects."},
 "B2":{"pass":"Policy establishes that the district is subject to FERPA, conditioning the Part-17 FERPA safe harbors.",
   "evid":"A statement of FERPA applicability.","meth":"Detect FERPA applicability language.",
   "cues":[["ferpa","family educational rights and privacy"]],
   "labels":["a statement of FERPA applicability"],
   "rev":"The District is an educational agency subject to the Family Educational Rights and Privacy Act (FERPA); FERPA processes are used to satisfy the notice and correction duties of this policy where available."},
 "B3":{"pass":"Policy determines, per covered system, whether notice/disclosure is satisfied through the district's FERPA notices and student-record access procedures.",
   "evid":"A per-system FERPA notice safe-harbor determination.","meth":"Detect FERPA-notice routing tied to systems.",
   "cues":[["ferpa notice","annual notice","student record access"],["notice","disclos"]],
   "labels":["FERPA notice procedures","their use to satisfy ADMT notice"],
   "rev":"For each covered system, the District shall determine whether the notice and disclosure duties are satisfied through its existing FERPA notices and student-record access procedures."},
 "B4":{"pass":"Policy determines, per covered system, whether correction and human review are satisfied through existing student-record inspection/review/amendment and district appeal processes.",
   "evid":"A per-system FERPA rights safe-harbor determination.","meth":"Detect FERPA amendment/appeal routing.",
   "cues":[["inspect","review","amend"],["student record","education record"],["appeal","complaint"]],
   "labels":["record inspection/amendment procedures","a district appeal/complaint process"],
   "rev":"For each covered system, correction and human-review duties shall be satisfied through the District's student-record inspection, review, and amendment procedures and its complaint or appeal process."},
 "B5":{"pass":"Policy requires each vendor system to fit the FERPA school-official exception: legitimate educational interest, institutional function, district direct control, and use/re-disclosure limits.",
   "evid":"School-official-exception conditions in vendor terms.","meth":"Detect school-official exception controls.",
   "cues":[["school official","legitimate educational interest"],["direct control","under the control","control over"],["re-disclos","redisclos","use and re-disclosure","not use for any other"]],
   "labels":["the school-official / legitimate-educational-interest basis","district direct control","use and re-disclosure limits"],
   "rev":"Each vendor system that accesses education records shall qualify under the FERPA school-official exception, with a legitimate educational interest, the District's direct control over records, and binding use and re-disclosure limits."},
 "B6":{"pass":"Policy binds vendors as 'school service contract providers' under the Colorado Student Data Transparency and Security Act (C.R.S. 22-16).",
   "evid":"22-16 school-service-contract-provider obligations in vendor terms.","meth":"Detect 22-16 provider binding.",
   "cues":[["school service contract provider","student data transparency","22-16","student data privacy"],["provider","vendor","contract"]],
   "labels":["reference to Colorado student-data law (22-16)","binding vendors as school service contract providers"],
   "rev":"Vendors handling student data shall be bound as school service contract providers under the Colorado Student Data Transparency and Security Act (C.R.S. 22-16)."},

 "C1":{"pass":"Policy requires clear and conspicuous notice before a covered system is used to materially influence a consequential decision.",
   "evid":"A pre-use notice duty.","meth":"Detect notice + before/prior + clarity.",
   "cues":[["notice","inform","notif"],["before","prior to","in advance"],["clear and conspicuous","conspicuous","plain"]],
   "labels":["a notice duty","that notice precedes the decision","a clear-and-conspicuous standard"],
   "rev":"Before a covered system is used to materially influence a consequential decision affecting a student, the District shall provide clear and conspicuous notice to the affected consumer."},
 "C2":{"pass":"Policy allows compliance via a prominent public notice reasonably accessible at points of interaction.",
   "evid":"A public-posting notice option.","meth":"Detect public/posted notice.",
   "cues":[["public notice","posted","website","publicly available","prominent"],["notice","point of interaction","point of contact"]],
   "labels":["a public/posted notice option","accessibility at points of interaction"],
   "rev":"The District may satisfy the notice duty through a prominent public notice reasonably accessible at points of consumer interaction."},
 "C3":{"pass":"Policy requires, within 30 days of an adverse outcome, a plain-language description, the system's role, a process to request information, and an explanation of consumer rights.",
   "evid":"A 30-day post-adverse-outcome disclosure with the required elements.","meth":"Detect adverse + 30 days + explanation.",
   "cues":[["adverse"],["30 day","thirty day","within 30","within thirty"],["plain language","description","explain","role of","how to request","rights"]],
   "labels":["an adverse-outcome trigger","the 30-day timeframe","the required disclosure elements"],
   "rev":"Within thirty days after an adverse outcome materially influenced by a covered system, the District shall provide a plain-language description of the decision, the system's role, a simple process to request further information, and an explanation of the consumer's rights."},
 "C4":{"pass":"Policy routes notice and disclosure through FERPA notices and student-record access procedures.",
   "evid":"FERPA-routed notice/disclosure.","meth":"Detect FERPA + notice routing.",
   "cues":[["ferpa"],["notice","disclos","student record"]],
   "labels":["FERPA processes","their use for notice and disclosure"],
   "rev":"Notice and post-adverse-outcome disclosures shall be delivered through the District's FERPA notices and student-record access procedures, including notice to a parent, guardian, or eligible student."},
 "C5":{"pass":"Policy makes notices reasonably accessible to consumers with disabilities and limited English proficiency.",
   "evid":"Accessibility and language-access provisions.","meth":"Detect accessibility + language access.",
   "cues":[["accessib","disabilit","ada","assistive"],["language","english proficiency","translat","primary language"]],
   "labels":["disability accessibility","language access for limited-English proficiency"],
   "rev":"Notices and disclosures shall be reasonably accessible to consumers with disabilities and available to consumers with limited English proficiency in a language they understand."},
 "C6":{"pass":"Policy provides parent/guardian/eligible-student access to, and a mechanism to request correction of, personal data.",
   "evid":"Parent/eligible-student access and correction rights.","meth":"Detect parent access + correction.",
   "cues":[["parent","guardian","eligible student"],["access","inspect","review"],["correct","amend","request change"]],
   "labels":["parent/guardian/eligible-student access","a correction mechanism"],
   "rev":"A parent, guardian, or eligible student may access the personal data used in a decision and request correction of materially inaccurate data through the District's established process."},

 "D1":{"pass":"Policy requires retaining records for at least three years after each consequential decision.",
   "evid":"A 3-year (or longer) retention obligation tied to decisions.","meth":"Detect retention + three years.",
   "cues":[["retain","retention","keep","preserve"],["three year","3 year","3-year","36 month"]],
   "labels":["a records-retention duty","the three-year minimum"],
   "rev":"The District shall retain, for at least three years after each consequential decision, records reasonably necessary to demonstrate compliance with this policy."},
 "D2":{"pass":"Policy specifies records include system version identifiers, changelogs, and documentation of material mitigation changes.",
   "evid":"A record-contents specification.","meth":"Detect versioning/changelog record contents.",
   "cues":[["version","changelog","identifier","system version"],["record","document","log"]],
   "labels":["specified record contents","version identifiers / changelogs"],
   "rev":"Retained records shall include covered-system version identifiers, changelogs, and documentation of material mitigation changes."},
 "D3":{"pass":"Policy maintains a data-security policy and vendor data-destruction consistent with C.R.S. 22-16.",
   "evid":"Security and destruction provisions.","meth":"Detect security + destruction.",
   "cues":[["security","safeguard","protect","encrypt"],["destr","dispos","delete","purge"]],
   "labels":["a data-security policy","data-destruction practices"],
   "rev":"The District shall maintain a data-security policy and require vendor data destruction consistent with the Colorado Student Data Transparency and Security Act."},
 "D4":{"pass":"Policy ensures records are sufficient to demonstrate compliance to the Attorney General.",
   "evid":"A demonstrate-compliance/audit-readiness provision.","meth":"Detect compliance-evidence readiness.",
   "cues":[["demonstrate compliance","audit","evidence of compliance","upon request"],["record","documentation"]],
   "labels":["a demonstrate-compliance duty","audit-ready records"],
   "rev":"Records shall be organized and sufficient to demonstrate compliance to the Attorney General upon request."},

 "E1":{"pass":"Policy requires obtaining developer documentation: intended and known-harmful uses, training-data categories, known limitations, and use/monitoring/human-review instructions.",
   "evid":"A developer-documentation intake requirement.","meth":"Detect developer documentation intake.",
   "cues":[["developer","vendor documentation","documentation from"],["intended use","known limitation","training data","instructions","harmful use"]],
   "labels":["a developer-documentation intake duty","the required documentation elements"],
   "rev":"Before deploying a covered system, the District shall obtain the developer's documentation of intended and known-harmful uses, training-data categories, known limitations, and instructions for appropriate use, monitoring, and human review."},
 "E2":{"pass":"Vendor contracts impose district direct control and purpose-limitation / no-reuse / no-resale on records.",
   "evid":"Direct-control and purpose-limitation clauses.","meth":"Detect control + purpose limits.",
   "cues":[["direct control","under the control","control over"],["purpose","use only","not reuse","no resale","not sell","re-disclos"]],
   "labels":["district direct control","purpose-limitation / no-reuse terms"],
   "rev":"Vendor contracts shall place education records under the District's direct control and limit their use to the contracted purpose, prohibiting reuse, resale, or re-disclosure."},
 "E3":{"pass":"Vendor contracts meet 22-16 transparency, use-limitation, security, and destruction duties.",
   "evid":"22-16 contract terms.","meth":"Detect 22-16 provider contract terms.",
   "cues":[["school service contract","22-16","student data transparency"],["security","destr","use limit","transparen"]],
   "labels":["reference to 22-16 provider duties","transparency/security/destruction terms"],
   "rev":"Vendor contracts shall satisfy the transparency, use-limitation, security, and destruction duties required of school service contract providers under C.R.S. 22-16."},
 "E4":{"pass":"Procurement screens predictive screeners against the READ Act §1209(2.5) technical criteria (validity, classification accuracy, public technical manual, cutoff points).",
   "evid":"A screener-validity procurement gate.","meth":"Detect validity screening for screeners.",
   "cues":[["validity","reliab","classification accuracy","technical manual","normed","cutoff"],["screener","assessment","vendor","predictive"]],
   "labels":["a validity/technical-criteria gate","its application to screeners"],
   "rev":"Before adopting a screener or predictive assessment, the District shall verify it meets the READ Act technical criteria, including validity, classification accuracy, and a public technical manual with research-based cutoff points."},
 "E5":{"pass":"Contracts do not indemnify against Colorado Anti-Discrimination Act liability from covered-system decisions.",
   "evid":"An indemnification-limitation provision.","meth":"Detect indemnification + anti-discrimination.",
   "cues":[["indemnif","hold harmless","defend"],["discrimination","anti-discrimination","civil rights"]],
   "labels":["attention to indemnification clauses","the anti-discrimination carve-out"],
   "rev":"No contract shall indemnify, defend, or hold harmless a party against liability under the Colorado Anti-Discrimination Act arising from a covered-system decision; such terms are void as against public policy."},
 "E6":{"pass":"Policy processes developer notices of material updates and triggers re-inventory and re-classification.",
   "evid":"An update-handling procedure.","meth":"Detect update notice + re-assessment.",
   "cues":[["update","modif","new version","release notes","patch"],["re-inventory","re-assess","re-evaluat","re-classif","review"]],
   "labels":["handling of developer update notices","a re-inventory/re-classification trigger"],
   "rev":"On receiving a developer notice of a material update or modification, the District shall re-inventory and re-classify the affected system."},

 "F1":{"pass":"Policy designates a trained human reviewer with explicit authority to approve, modify, or override a consequential decision materially influenced by a covered system, who does not default to the output.",
   "evid":"A reviewer with named override authority, training, and non-deference.","meth":"Detect reviewer + override authority + training + non-default.",
   "cues":[["reviewer","review","human review","official","designat","responsible"],["override","overturn","reverse","modify","authority to approve","final authority"],["train","qualified","competent"],["not default","independent judgment","not rely solely","shall not defer","own determination"]],
   "labels":["a designated reviewer","authority to approve, modify, or override","reviewer training","non-deference to the system output"],
   "rev":"A consequential decision materially influenced by a covered system shall be reviewed by a designated, trained District official who has authority to approve, modify, or override the decision and who does not default to the system's output."},
 "F2":{"pass":"Policy requires the reviewer to consider primary evidence, be trained, and not default to the system output.",
   "evid":"Reviewer-quality conditions.","meth":"Detect primary evidence + training + non-default.",
   "cues":[["primary evidence","underlying evidence","original record","source material"],["train","qualified"],["not default","independent","not rely solely"]],
   "labels":["consideration of primary evidence","reviewer training","non-deference to the output"],
   "rev":"The reviewer shall consider the relevant available primary evidence, be trained to conduct the review, and shall not default to the system's output."},
 "F3":{"pass":"Policy gives the reviewer access to understand the system's intended use, material limitations, input categories, and principal factors.",
   "evid":"Reviewer information-access conditions.","meth":"Detect access to system understanding.",
   "cues":[["intended use","limitation","input","principal factor","how the system works","material limitation"],["understand","access to information","provided with"]],
   "labels":["reviewer access to system information","understanding of use/limitations/factors"],
   "rev":"The reviewer shall have access to information sufficient to understand the system's intended use, material limitations, categories of inputs, and the principal factors used to generate its output."},
 "F4":{"pass":"Policy provides, on an adverse outcome, an opportunity for meaningful human review and reconsideration to the extent commercially reasonable.",
   "evid":"An adverse-outcome reconsideration right.","meth":"Detect adverse + human reconsideration.",
   "cues":[["adverse"],["reconsider","re-examine","review again","appeal"],["human","person","official"]],
   "labels":["an adverse-outcome trigger","a human reconsideration opportunity"],
   "rev":"On an adverse outcome, the affected consumer shall have an opportunity for meaningful human review and reconsideration of the decision, to the extent commercially reasonable."},
 "F5":{"pass":"Policy provides correction of factually inaccurate personal data (not opinions, predictions, scores, or protected evaluations).",
   "evid":"A data-correction right with the evaluation carve-out.","meth":"Detect correction of inaccurate data.",
   "cues":[["correct","amend","rectif","fix"],["inaccurate","incorrect","erroneous","personal data"]],
   "labels":["a data-correction right","its focus on factually inaccurate data"],
   "rev":"A consumer may request correction of factually incorrect or materially inaccurate personal data used in a decision; correction of opinions, predictions, scores, or protected evaluations is not required."},
 "F6":{"pass":"Policy routes correction and human review through FERPA amendment and district complaint/appeal processes.",
   "evid":"FERPA-routed correction/review.","meth":"Detect FERPA amendment/appeal routing for review.",
   "cues":[["ferpa","student record","education record"],["amend","correct","review","appeal","complaint"]],
   "labels":["FERPA amendment/appeal processes","their use for correction and review"],
   "rev":"Correction and human-review requests shall be handled through the District's FERPA student-record amendment and complaint or appeal processes."},
 "F7":{"pass":"Policy documents internal audits (e.g., a planted-error catch-rate program) evidencing that reviewers do not default to the system output.",
   "evid":"An oversight-audit program.","meth":"Detect audit/monitoring of reviewer performance.",
   "cues":[["audit","monitor","quality assurance","catch rate","spot check","sampl"],["review","oversight","reviewer","human review"]],
   "labels":["an oversight-audit program","its focus on reviewer performance"],
   "rev":"The District shall periodically audit its human-review process — for example, by measuring how often reviewers catch known errors — to demonstrate that reviewers do not default to the system's output."},

 # X: context only, not measured against district policy
 "X1":{"context":True},"X2":{"context":True},"X3":{"context":True},"X4":{"context":True},
}

def build_rubric():
    out=[]
    for cid,mod,term,hook,stmt,src,status,artifact,verify in C:
        t=TESTS.get(cid,{})
        tier=tier_for(status)
        item={"id":cid,"module":mod,"module_name":MODULES[mod][0],"term":term,"hook":hook,
              "statement":stmt,"source":src,"status":status,"artifact":artifact,"verify_note":verify,
              "ag_test_tier":tier["tier"],"pass_semantics":tier["pass_semantics"],"must_pass":tier["must_pass"],
              "context_only":bool(t.get("context"))}
        if not t.get("context"):
            item.update({"pass_condition":t.get("pass",""),"evidence_required":t.get("evid",""),
                         "measurement_method":t.get("meth",""),"cues":t.get("cues",[]),
                         "gap_labels":t.get("labels",[]),"revision":t.get("rev","")})
        out.append(item)
    return out

if __name__=="__main__":
    import json
    r=build_rubric()
    json.dump({"criteria":r},open("/home/claude/criteria_rubric.json","w"),indent=2)
    measured=[x for x in r if not x["context_only"]]
    print(f"rubric: {len(r)} criteria, {len(measured)} measurable, {len(r)-len(measured)} context-only")
