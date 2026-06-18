#!/usr/bin/env python3
"""Show WHAT consumes the low-usage ATO materials: for each, list the loaded non-ATO
recipes that use its ingot/parts as ingredient -> what they PRODUCE. Helps judge
'meaningful content'."""
import os, re, glob, zipfile, json
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODS = os.path.join(ROOT, "mods")
DP   = os.path.join(ROOT, "config", "paxi", "datapacks")
TARGETS = ["uranium", "salt", "sulfur", "nickel", "aluminum", "tin"]

present = set(["minecraft","neoforge","c","forge"])
for jp in glob.glob(os.path.join(MODS, "*.jar")):
    try:
        z = zipfile.ZipFile(jp)
        for tn in ("META-INF/neoforge.mods.toml","META-INF/mods.toml"):
            if tn in z.namelist():
                present |= set(re.findall(r'modId\s*=\s*"([^"]+)"', z.read(tn).decode("utf-8","ignore"))); break
    except Exception: pass

CONSUME = lambda m: [f"c:ingots/{m}", f"c:gems/{m}", f"c:dusts/{m}", f"c:plates/{m}",
    f"c:gears/{m}", f"c:rods/{m}", f"c:nuggets/{m}", f"c:wires/{m}"] + \
    [f"alltheores:{m}_{s}" for s in ("ingot","gem","dust","plate","gear","rod","nugget","wire")]

def ing_refs(o):
    r=[]
    if isinstance(o,dict):
        for k,v in o.items():
            if k.lower() in("result","results","output","outputs"): continue
            if k.lower() in("item","tag") and isinstance(v,str): r.append(v)
            else: r+=ing_refs(v)
    elif isinstance(o,list):
        for x in o: r+=ing_refs(x)
    return r

def result_of(o):
    if isinstance(o,dict):
        for k,v in o.items():
            if k.lower() in("result","results","output","outputs"):
                if isinstance(v,str): return v
                if isinstance(v,dict): return v.get("id") or v.get("item") or ""
                if isinstance(v,list) and v:
                    x=v[0]; return (x.get("id") or x.get("item") or "") if isinstance(x,dict) else str(x)
        for v in o.values():
            rr=result_of(v)
            if rr: return rr
    return ""

def cond_mods(o):
    s=set()
    if isinstance(o,dict):
        for k,v in o.items():
            if k.lower()=="modid" and isinstance(v,str): s.add(v)
            if k.lower()=="values" and isinstance(v,list):
                for x in v:
                    if isinstance(x,str) and ":" not in x and "." not in x: s.add(x)
            s|=cond_mods(v)
    elif isinstance(o,list):
        for x in o: s|=cond_mods(x)
    return s

uses=defaultdict(list)
RE=re.compile(r"data/([^/]+)/recipes?/(.+)\.json$")
def handle(ns,path,txt):
    if ns=="alltheores": return
    try: d=json.loads(txt)
    except Exception: return
    c=d.get("neoforge:conditions") or d.get("fabric:load_conditions")
    if c:
        req=cond_mods(c)
        if req and any(m not in present for m in req): return
    refs=set(ing_refs(d)); res=result_of(d)
    for m in TARGETS:
        if any(p in refs for p in CONSUME(m)):
            uses[m].append(f"{ns}:{path.split('/')[-1]} -> {res or '?'}")

for jp in glob.glob(os.path.join(MODS,"*.jar")):
    try: z=zipfile.ZipFile(jp)
    except Exception: continue
    for n in z.namelist():
        mm=RE.match(n)
        if mm: handle(mm.group(1),mm.group(2),z.read(n).decode("utf-8","ignore"))
for f in glob.glob(os.path.join(DP,"**","*.json"),recursive=True):
    mm=RE.search(f.replace(os.sep,"/"))
    if mm:
        try: handle(mm.group(1),mm.group(2),open(f,encoding="utf-8",errors="ignore").read())
        except Exception: pass

for m in TARGETS:
    print(f"\n### {m}  ({len(uses[m])} consuming recipes)")
    for line in sorted(set(uses[m]))[:25]:
        print("   "+line)
