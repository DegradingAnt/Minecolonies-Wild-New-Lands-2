#!/usr/bin/env python3
"""ACCURATE ATO material usage audit (v2).
A material is "dead outside ATO" if NO loaded non-ATO recipe uses its ingot/gem/parts
as an INGREDIENT. Excludes: ore-processing (ore/raw forms), result-side refs (production),
and recipes gated on an ABSENT mod (mod_loaded conditions that never fire).
"""
import os, re, glob, zipfile, json
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODS = os.path.join(ROOT, "mods")
DP   = os.path.join(ROOT, "config", "paxi", "datapacks")

# ---- present mod ids (from each jar's neoforge.mods.toml) ----
present = set(["minecraft", "neoforge", "c", "forge"])
MODID_RE = re.compile(r'modId\s*=\s*"([^"]+)"')
for jp in glob.glob(os.path.join(MODS, "*.jar")):
    try:
        z = zipfile.ZipFile(jp)
        for tn in ("META-INF/neoforge.mods.toml", "META-INF/mods.toml"):
            if tn in z.namelist():
                present |= set(MODID_RE.findall(z.read(tn).decode("utf-8", "ignore")))
                break
    except Exception:
        pass

# ---- ATO base materials (strip dimension/variant prefixes) ----
ato = [j for j in glob.glob(os.path.join(MODS, "*.jar")) if "alltheores" in os.path.basename(j).lower()]
materials = set()
if ato:
    z = zipfile.ZipFile(ato[0])
    for n in z.namelist():
        m = re.match(r"assets/alltheores/models/item/(?:deepslate_|other_|end_|nether_)*([a-z]+)_ore\.json$", n)
        if m:
            materials.add(m.group(1))
materials = sorted(materials)

CONSUME_FORMS = ["ingots","gems","dusts","nuggets","plates","gears","rods","wires","storage_blocks"]
ITEM_SUFFIX   = ["ingot","gem","dust","nugget","plate","gear","rod","wire","block"]

def consume_pats(mat):
    p = [f"c:{f}/{mat}" for f in CONSUME_FORMS]
    p += [f"alltheores:{mat}_{s}" for s in ITEM_SUFFIX]
    return p

def collect_ingredient_refs(obj):
    """all item/tag strings NOT under a result/output key."""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in ("result","results","output","outputs"):
                continue
            if k.lower() in ("item","tag") and isinstance(v, str):
                out.append(v)
            else:
                out += collect_ingredient_refs(v)
    elif isinstance(obj, list):
        for it in obj:
            out += collect_ingredient_refs(it)
    return out

def cond_modids(obj):
    out = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() == "modid" and isinstance(v, str):
                out.add(v)
            if k.lower() == "values" and isinstance(v, list):
                for x in v:
                    if isinstance(x, str) and ":" not in x and "." not in x:
                        out.add(x)
            out |= cond_modids(v)
    elif isinstance(obj, list):
        for it in obj:
            out |= cond_modids(it)
    return out

consumers = defaultdict(set)   # mat -> set(consumer namespaces)
hits      = defaultdict(int)

RECIPE_RE = re.compile(r"data/([^/]+)/recipes?/.+\.json$")

def handle(ns, txt):
    if ns == "alltheores":
        return
    try:
        data = json.loads(txt)
    except Exception:
        return
    # skip recipes gated on an ABSENT mod
    cond = data.get("neoforge:conditions") or data.get("fabric:load_conditions")
    if cond:
        req = cond_modids(cond)
        if req and any(m not in present for m in req):
            return
    refs = set(collect_ingredient_refs(data))
    for mat in materials:
        if any(p in refs for p in consume_pats(mat)):
            consumers[mat].add(ns)
            hits[mat] += 1

for jp in glob.glob(os.path.join(MODS, "*.jar")):
    try:
        z = zipfile.ZipFile(jp)
    except Exception:
        continue
    for n in z.namelist():
        rm = RECIPE_RE.match(n)
        if rm:
            handle(rm.group(1), z.read(n).decode("utf-8", "ignore"))
for f in glob.glob(os.path.join(DP, "**", "*.json"), recursive=True):
    rm = RECIPE_RE.search(f.replace(os.sep, "/"))
    if rm:
        try:
            handle(rm.group(1), open(f, encoding="utf-8", errors="ignore").read())
        except Exception:
            pass

print(f"present mods: {len(present)} | ATO materials: {len(materials)}\n")
print(f"{'material':12s} {'recipes':>7s}  real non-ATO CONSUMERS (ingredient use, loaded mods only)")
print("-" * 80)
dead, keep = [], []
for mat in sorted(materials, key=lambda m: (len(consumers[m]), hits[m])):
    cs = sorted(consumers[mat])
    (dead if not cs else keep).append(mat)
    tag = "  <== DEAD (disable)" if not cs else ""
    print(f"{mat:12s} {hits[mat]:7d}  {', '.join(cs) if cs else '— NONE —'}{tag}")
print(f"\nDEAD (disable): {', '.join(dead) if dead else '(none)'}")
print(f"KEEP: {', '.join(keep)}")
