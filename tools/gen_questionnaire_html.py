#!/usr/bin/env python3
"""Parse MEGA-QUESTIONNAIRE.md -> a clean interactive HTML form (app-style cards) for filling.
Open the .html in any browser, fill/accept-defaults, autosaves to localStorage, Export -> a filled
answers file to hand back. Re-run this after editing the .md to regenerate."""
import json, re, html
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "_dev" / "wnl-pathways-src"
SRC  = ROOT / "MEGA-QUESTIONNAIRE.md"
OUT  = ROOT / "MEGA-QUESTIONNAIRE.html"

# handles: "- ID — q" / "- **ID.** q" / "- **ID** — q" / "- ID. q"  (ID like PLACE-1, FACT-1.2, WAR-3)
QID = re.compile(r"^-\s+\**([A-Z]{3,}-\d+(?:\.\d+)?)\.?\**\s*[—–-]?\s*(.+)$")
DEF = re.compile(r"^\s*-?\s*\*\*\[DEFAULT:\s*(.*?)\]\*\*")

def parse(md):
    sections, cur, sub, q = [], None, None, None
    intro = []
    for raw in md.splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            cur = {"title": line[3:].strip(), "subs": []}
            sections.append(cur); sub = None; q = None
            continue
        if line.startswith("### ") and cur:
            sub = {"title": line[4:].strip(), "qs": []}
            cur["subs"].append(sub); q = None
            continue
        m = QID.match(line)
        if m and cur:
            if sub is None:
                sub = {"title": "", "qs": []}; cur["subs"].append(sub)
            q = {"id": m.group(1), "q": m.group(2).strip(), "default": ""}
            sub["qs"].append(q)
            continue
        d = DEF.match(line)
        if d and q is not None:
            q["default"] = d.group(1).strip()
            continue
    # drop the HOW-TO/CONTENTS pseudo-sections (no questions)
    sections = [s for s in sections if any(sub["qs"] for sub in s["subs"])]
    return sections

def main():
    md = SRC.read_text(encoding="utf-8")
    sections = parse(md)
    total = sum(len(sub["qs"]) for s in sections for sub in s["subs"])
    data = json.dumps(sections, ensure_ascii=False)
    page = TEMPLATE.replace("/*__DATA__*/", data).replace("__TOTAL__", str(total))
    OUT.write_text(page, encoding="utf-8")
    print(f"WROTE {OUT}\n  sections={len(sections)} questions={total}")

TEMPLATE = r"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>WNL Mega Design Questionnaire</title>
<style>
 :root{--bg:#15171c;--card:#1f232b;--card2:#252a34;--line:#2c313b;--txt:#e7e9ee;--mut:#9aa4b2;--acc:#6ea8fe;--ok:#4caf72;--badge:#3a4150}
 *{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--txt);font:15px/1.5 system-ui,Segoe UI,sans-serif}
 header{position:sticky;top:0;z-index:9;background:#191c22;border-bottom:1px solid var(--line);padding:10px 18px;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
 header h1{font-size:16px;margin:0} .grow{flex:1}
 button{background:var(--acc);color:#0b1020;border:0;border-radius:7px;padding:8px 13px;font-weight:600;cursor:pointer}
 button.ghost{background:#2b313c;color:var(--txt)} input[type=search]{background:#0f1116;border:1px solid var(--line);color:var(--txt);border-radius:7px;padding:7px 10px;min-width:180px}
 #prog{color:var(--mut);font-size:13px} #prog b{color:var(--ok)}
 .wrap{display:flex;max-width:1180px;margin:0 auto;gap:18px;padding:18px}
 nav{position:sticky;top:62px;align-self:flex-start;width:240px;font-size:13px;flex:none}
 nav a{display:block;color:var(--mut);text-decoration:none;padding:5px 8px;border-radius:6px} nav a:hover{background:var(--card);color:var(--txt)}
 main{flex:1;min-width:0} .sec{margin-bottom:30px} .sec h2{font-size:20px;border-bottom:2px solid var(--acc);padding-bottom:6px}
 .sub h3{font-size:15px;color:var(--acc);margin:18px 0 8px}
 .card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:13px 15px;margin:10px 0}
 .card.done{border-color:#34503f} .qhead{display:flex;gap:9px;align-items:baseline}
 .id{font:600 11px/1 ui-monospace,monospace;background:var(--badge);color:#c7d0de;padding:3px 6px;border-radius:5px;flex:none}
 .q{font-weight:600} .def{color:var(--mut);font-size:13px;margin:7px 0 9px;background:var(--card2);border-left:3px solid #3f6ea5;padding:7px 10px;border-radius:0 6px 6px 0}
 .def b{color:#bcd0ec;font-weight:600} textarea{width:100%;background:#0f1116;border:1px solid var(--line);color:var(--txt);border-radius:7px;padding:8px 10px;font:14px/1.45 inherit;resize:vertical;min-height:38px}
 textarea:focus{outline:0;border-color:var(--acc)} .hint{color:#69707d;font-size:12px;margin-top:4px}
 footer{max-width:1180px;margin:0 auto;padding:0 18px 60px;color:var(--mut)}
 .toast{position:fixed;bottom:16px;left:50%;transform:translateX(-50%);background:#2b313c;border:1px solid var(--line);padding:9px 16px;border-radius:8px;opacity:0;transition:.3s}
</style></head><body>
<header>
 <h1>WNL Mega Design Questionnaire</h1>
 <span id=prog></span><span class=grow></span>
 <input type=search id=q placeholder="filter questions...">
 <label style="font-size:13px;color:var(--mut)"><input type=checkbox id=onlyopen> only unanswered</label>
 <button class=ghost id=save>Save</button>
 <button id=export>Export answers ▾</button>
</header>
<div class=wrap>
 <nav id=nav></nav>
 <main id=main></main>
</div>
<footer>Answers autosave in this browser. <b>Export answers</b> downloads a filled file to send back. Blank = accept the [DEFAULT]. You have full design veto.</footer>
<div class=toast id=toast></div>
<script>
const SECTIONS=/*__DATA__*/, TOTAL=__TOTAL__, KEY="wnl_mega_answers_v1";
let ANS=JSON.parse(localStorage.getItem(KEY)||"{}");
const $=s=>document.querySelector(s), main=$("#main"), nav=$("#nav");
const slug=s=>s.toLowerCase().replace(/[^a-z0-9]+/g,"-");
function render(){
 main.innerHTML=""; nav.innerHTML="";
 SECTIONS.forEach((sec,si)=>{
  const id="s"+si; const a=document.createElement("a"); a.href="#"+id; a.textContent=sec.title; nav.appendChild(a);
  const el=document.createElement("section"); el.className="sec"; el.id=id;
  el.innerHTML=`<h2>${esc(sec.title)}</h2>`;
  sec.subs.forEach(sub=>{
   const sd=document.createElement("div"); sd.className="sub";
   if(sub.title) sd.innerHTML=`<h3>${esc(sub.title)}</h3>`;
   sub.qs.forEach(q=>{
    const v=ANS[q.id]||""; const done=v.trim()!=="";
    const c=document.createElement("div"); c.className="card"+(done?" done":""); c.dataset.id=q.id; c.dataset.t=(q.id+" "+q.q+" "+q.default).toLowerCase();
    c.innerHTML=`<div class=qhead><span class=id>${q.id}</span><span class=q>${esc(q.q)}</span></div>`+
      (q.default?`<div class=def><b>Default:</b> ${esc(q.default)}</div>`:``)+
      `<textarea data-id="${q.id}" placeholder="Leave blank to accept the default — or type your answer / tweak">${esc(v)}</textarea>`+
      `<div class=hint>blank = use default</div>`;
    sd.appendChild(c);
   });
   el.appendChild(sd);
  });
  main.appendChild(el);
 });
 main.querySelectorAll("textarea").forEach(t=>t.addEventListener("input",e=>{
   ANS[e.target.dataset.id]=e.target.value; const card=e.target.closest(".card");
   card.classList.toggle("done", e.target.value.trim()!==""); prog(); persist(true);
 }));
 prog(); filter();
}
function esc(s){return (s||"").replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));}
function prog(){const n=Object.values(ANS).filter(x=>x.trim()!=="").length;$("#prog").innerHTML=`<b>${n}</b> / ${TOTAL} answered`;}
let saveT; function persist(quiet){clearTimeout(saveT);saveT=setTimeout(()=>{localStorage.setItem(KEY,JSON.stringify(ANS));if(!quiet)toast("saved");},400);}
function toast(m){const t=$("#toast");t.textContent=m;t.style.opacity=1;setTimeout(()=>t.style.opacity=0,1200);}
function filter(){const term=$("#q").value.toLowerCase(),only=$("#onlyopen").checked;
 document.querySelectorAll(".card").forEach(c=>{const v=(ANS[c.dataset.id]||"").trim()!=="";
  c.style.display=((!term||c.dataset.t.includes(term))&&(!only||!v))?"":"none";});}
$("#q").oninput=filter; $("#onlyopen").onchange=filter;
$("#save").onclick=()=>{localStorage.setItem(KEY,JSON.stringify(ANS));toast("saved");};
$("#export").onclick=()=>{
 let md="# WNL Mega Questionnaire — ANSWERS\n\n";
 SECTIONS.forEach(sec=>{md+=`\n## ${sec.title}\n`;sec.subs.forEach(sub=>{if(sub.title)md+=`\n### ${sub.title}\n`;
   sub.qs.forEach(q=>{const a=(ANS[q.id]||"").trim();md+=`\n- ${q.id} — ${q.q}\n  - ANSWER: ${a||"[default] "+ (q.default||"")}\n`;});});});
 const blob=new Blob([md],{type:"text/markdown"});const u=URL.createObjectURL(blob);
 const a=document.createElement("a");a.href=u;a.download="MEGA-QUESTIONNAIRE-ANSWERS.md";a.click();URL.revokeObjectURL(u);
 toast("exported — send me the file");
};
render();
</script></body></html>"""

if __name__ == "__main__":
    main()
