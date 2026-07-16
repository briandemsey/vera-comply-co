#!/usr/bin/env python3
"""COMPLY-Colorado measurement engine.

Pipeline: ingest -> chunk (provisions) -> measure (status + cited evidence + gap)
          -> score against probable-AG tiers -> generate revision -> re-measure -> report.

The measure() judge here is a transparent CUE-BASED heuristic so the whole loop runs
offline and deterministically for the demo. In production the same interface is served
by an LLM judge with the attorney in the loop; swap judge_status()/find_evidence().
"""
import json, re, html, sys, os
from comply_rubric import build_rubric

# ---------- Layer 1: ingest + chunk ----------
def parse_document(path):
    ext=os.path.splitext(path)[1].lower()
    if ext in (".txt",".md"): return open(path,encoding="utf-8").read()
    if ext==".pdf":
        try:
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                return "\n".join((p.extract_text() or "") for p in pdf.pages)
        except Exception as e: raise RuntimeError(f"PDF parse needs pdfplumber: {e}")
    if ext==".docx":
        try:
            from docx import Document
            return "\n".join(p.text for p in Document(path).paragraphs)
        except Exception as e: raise RuntimeError(f"DOCX parse needs python-docx: {e}")
    raise ValueError(f"Unsupported file type: {ext}")

def chunk_text(text):
    """Split a policy manual into addressable provisions by heading/paragraph."""
    provisions=[]; heading="(preamble)"; buf=[]
    def flush():
        t=" ".join(buf).strip()
        if t: provisions.append({"heading":heading,"text":t})
    for raw in text.splitlines():
        line=raw.strip()
        if not line:
            flush(); buf=[]; continue
        # treat short ALL-CAPS / 'Section'/'Policy'/numbered lines as headings
        if (len(line)<80 and (line.isupper() or re.match(r'^(section|policy|article|part)\b',line,re.I)
                              or re.match(r'^([A-Z]\.|\d+(\.\d+)*\.?)\s+\S',line))):
            flush(); buf=[]; heading=line; continue
        buf.append(line)
    flush()
    return provisions

# ---------- Layer 2: measure ----------
def group_hit(text, group):
    # Normalize hyphens and multi-space in BOTH the text and the cue terms so
    # "student record" matches "student-record" and vice versa.
    def norm(s):
        return s.lower().replace("-", " ").replace("  ", " ")
    t = norm(text)
    return any(norm(term) in t for term in group)

def judge(crit, provisions):
    """Return status, evidence provision(s), and unmet gap labels for one criterion."""
    cues=crit.get("cues",[]); labels=crit.get("gap_labels",[])
    if not cues: return {"status":"n/a","evidence":None,"gap":[]}
    anchor=cues[0]
    relevant=[p for p in provisions if group_hit(p["text"],anchor)]
    if not relevant:
        return {"status":"Not addressed","evidence":None,"gap":labels[:]}
    met=[any(group_hit(p["text"],g) for p in relevant) for g in cues]
    best=max(relevant,key=lambda p:sum(1 for g in cues if group_hit(p["text"],g)))
    def lbl(i): return labels[i] if i < len(labels) else f'"{cues[i][0]}"'
    gap=[lbl(i) for i,ok in enumerate(met) if not ok]
    status="Addressed" if all(met) else "Partial"
    return {"status":status,"evidence":{"heading":best["heading"],"text":best["text"]},"gap":gap}

# ---------- Layer 3: score against probable AG test ----------
def score(results):
    measured=[r for r in results if not r["context_only"]]
    must=[r for r in measured if r["must_pass"]]
    passed=[r for r in must if r["measured"]["status"]=="Addressed"]
    failing=[r for r in must if r["measured"]["status"]!="Addressed"]
    by_tier={}
    for r in measured:
        t=r["ag_test_tier"]; d=by_tier.setdefault(t,{"total":0,"addressed":0})
        d["total"]+=1; d["addressed"]+= (r["measured"]["status"]=="Addressed")
    return {"within_probable_ag_test": len(failing)==0,
            "must_pass_total":len(must),"must_pass_addressed":len(passed),
            "failing":[r["id"] for r in failing],"by_tier":by_tier}

# ---------- orchestration: measure -> revise -> re-measure ----------
def run(policy_path):
    rubric=build_rubric()
    provisions=chunk_text(parse_document(policy_path))
    results=[]
    for c in rubric:
        row={k:c[k] for k in ("id","module","module_name","term","hook","status",
                              "ag_test_tier","pass_semantics","must_pass","context_only")}
        if c["context_only"]:
            row["measured"]={"status":"context","evidence":None,"gap":[]}
            results.append(row); continue
        row["pass_condition"]=c["pass_condition"]
        m=judge(c,provisions); row["measured"]=m
        if m["status"]!="Addressed":
            row["revision"]=c["revision"]
            rem=judge(c,[{"heading":"Proposed revision","text":c["revision"]}])
            row["remeasured"]=rem["status"]
        results.append(row)
    return {"provisions":len(provisions),"score":score(results),"results":results}

# ---------- report rendering ----------
def render_html(report, district="Sample District"):
    s=report["score"]; ok=s["within_probable_ag_test"]
    def esc(x): return html.escape(x or "")
    badge={"Statutory":"#2f6b3d","Provisional":"#8a6d1a","Contested":"#8a2f2f"}
    stbg={"Addressed":"#e4f3e8","Partial":"#fff3d6","Not addressed":"#f7dede","context":"#eef1f5"}
    stfg={"Addressed":"#2f6b3d","Partial":"#8a6d1a","Not addressed":"#8a2f2f","context":"#5b6b7f"}
    rows=""
    cur=None
    for r in report["results"]:
        if r["context_only"]: continue
        if r["module"]!=cur:
            cur=r["module"]; rows+=f'<h2>{esc(r["module"])} — {esc(r["module_name"])}</h2>'
        m=r["measured"]; st=m["status"]
        ev = f'<div class="ev"><span class="evh">{esc(m["evidence"]["heading"])}</span> “{esc(m["evidence"]["text"])}”</div>' if m["evidence"] else '<div class="ev none">No matching provision found in the uploaded policy.</div>'
        gap = ('<div class="gap"><b>Gap:</b> missing '+esc("; ".join(m["gap"]))+'.</div>') if m["gap"] else '<div class="gap ok">Fully satisfied.</div>'
        rev=""
        if st!="Addressed":
            rev=(f'<div class="rev"><b>Generated revision</b> <span class="pill">re-measured: {esc(r.get("remeasured",""))}</span><br>“{esc(r.get("revision",""))}”</div>')
        rows+=(f'<div class="crit"><div class="top"><span class="id">{esc(r["id"])} · {esc(r["term"])}</span>'
               f'<span class="tier" style="color:{badge.get(r["ag_test_tier"],"#333")}">{esc(r["ag_test_tier"])}</span></div>'
               f'<div class="hook">{esc(r["hook"])} · <i>{esc(r["pass_semantics"])}</i></div>'
               f'<div class="status" style="background:{stbg.get(st)};color:{stfg.get(st)}">Measured: {esc(st)}</div>'
               f'{ev}{gap}{rev}</div>')
    tiers="".join(f'<span class="tstat">{esc(t)}: {d["addressed"]}/{d["total"]}</span>' for t,d in s["by_tier"].items())
    verdict=('<span class="ok">WITHIN the probable AG test</span>' if ok else
             f'<span class="no">NOT YET within the probable AG test — {len(s["failing"])} must-pass items unmet</span>')
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>COMPLY-Colorado Measurement Report</title>
<style>body{{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#1c2431;max-width:920px;margin:24px auto;padding:0 18px;line-height:1.45}}
h1{{color:#1f3b63;margin-bottom:2px}}h2{{color:#1f3b63;border-bottom:2px solid #e7ecf2;padding-bottom:4px;margin-top:28px}}
.sub{{color:#5b6b7f;margin-top:0}}
.summary{{border:1px solid #d7dee8;border-radius:10px;padding:16px 18px;margin:16px 0;background:#f8fafc}}
.summary .v{{font-size:18px;font-weight:700;margin-bottom:6px}}
.ok{{color:#2f6b3d}}.no{{color:#8a2f2f}}
.tstat{{display:inline-block;background:#eef4fb;border:1px solid #cfe0f2;border-radius:20px;padding:3px 10px;margin:4px 6px 0 0;font-size:12.5px;color:#1f3b63}}
.crit{{border:1px solid #e2e8f0;border-radius:9px;padding:13px 15px;margin:11px 0}}
.top{{display:flex;justify-content:space-between;gap:10px}}
.id{{font-weight:700;color:#1f3b63}}.tier{{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.03em}}
.hook{{font-size:11.5px;color:#5b6b7f;font-family:ui-monospace,Menlo,monospace;margin:2px 0 8px}}
.status{{display:inline-block;font-weight:700;font-size:12.5px;padding:3px 10px;border-radius:5px;margin-bottom:8px}}
.ev{{font-size:13px;background:#f6f9fc;border-left:3px solid #cfe0f2;padding:8px 12px;margin:6px 0;border-radius:4px}}
.ev.none{{color:#8a2f2f;border-left-color:#e6b7b7}}.evh{{font-weight:700;color:#1f3b63}}
.gap{{font-size:13px;color:#8a2f2f;margin:6px 0}}.gap.ok{{color:#2f6b3d}}
.rev{{font-size:13px;background:#eef4fb;border:1px solid #cfe0f2;border-radius:6px;padding:9px 12px;margin-top:8px;color:#1f3b63}}
.pill{{background:#e4f3e8;color:#2f6b3d;border-radius:12px;padding:1px 8px;font-size:11px;font-weight:700}}
.note{{font-size:12px;color:#5b6b7f;border-top:1px solid #e7ecf2;margin-top:26px;padding-top:12px}}</style></head>
<body><h1>COMPLY-Colorado — Measurement Report</h1>
<p class="sub">{esc(district)} · measured against SB 26-189 · {report['provisions']} policy provisions examined</p>
<div class="summary"><div class="v">{verdict}</div>
<div>Must-pass requirements addressed: <b>{s['must_pass_addressed']}/{s['must_pass_total']}</b></div>
<div style="margin-top:6px">{tiers}</div></div>
{rows}
<div class="note">Measurement uses a transparent cue-based judge for this offline demo; production serves the same interface with an LLM judge and attorney-in-the-loop confirmation. Provisional and Contested items are shown as built to the expected standard, subject to the Attorney General's final rules — not as guaranteed approval. Not legal advice.</div>
</body></html>"""

if __name__=="__main__":
    path=sys.argv[1] if len(sys.argv)>1 else "sample_district_policy.txt"
    rep=run(path)
    json.dump(rep,open("/home/claude/measurement_report.json","w"),indent=2)
    open("/home/claude/measurement_report.html","w",encoding="utf-8").write(render_html(rep))
    sc=rep["score"]
    print(f"provisions examined: {rep['provisions']}")
    print(f"within probable AG test: {sc['within_probable_ag_test']}")
    print(f"must-pass addressed: {sc['must_pass_addressed']}/{sc['must_pass_total']}")
    print("by tier:", sc["by_tier"])
    # F1 spotlight
    f1=next(r for r in rep["results"] if r["id"]=="F1")
    print("\nF1 measured:", f1["measured"]["status"], "| re-measured:", f1.get("remeasured"))
    if f1["measured"]["evidence"]: print("F1 evidence:", f1["measured"]["evidence"]["text"][:90])
    print("F1 gap:", f1["measured"]["gap"])
