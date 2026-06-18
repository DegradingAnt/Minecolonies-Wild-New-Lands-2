#!/usr/bin/env python3
"""Audit ATO (All The Ores) materials by downstream recipe usage.
For each ATO material, count how many recipe files (across ALL jars + the compat datapack)
reference it via c:<form>/<mat> tags or alltheores:<mat>* items, and WHICH mod namespaces
do so. Materials referenced ~only by alltheores itself (self ore->ingot->block chain) and
with few total recipes = low-content prune candidates.
"""
import os, re, glob, zipfile, json
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODS = os.path.join(ROOT, "mods")
DP   = os.path.join(ROOT, "config", "paxi", "datapacks")

# 1) derive ATO materials from its ore item models: assets/alltheores/models/item/<mat>_ore.json
ato = [j for j in glob.glob(os.path.join(MODS, "*.jar")) if "alltheores" in os.path.basename(j).lower()]
materials = set()
if ato:
    z = zipfile.ZipFile(ato[0])
    for n in z.namelist():
        m = re.match(r"assets/alltheores/models/item/(?:deepslate_|other_)?([a-z_]+)_ore\.json$", n)
        if m:
            materials.add(m.group(1))
materials = sorted(materials)

FORMS = ["ores","ingots","dusts","nuggets","raw_materials","plates","gears","rods",
         "storage_blocks","wires","gems"]

# build precise reference patterns per material
def patterns(mat):
    pats = [f'c:{f}/{mat}"' for f in FORMS]
    pats += [f'c:storage_blocks/raw_{mat}"']
    pats += [f'alltheores:{mat}_', f'alltheores:raw_{mat}', f'alltheores:deepslate_{mat}_ore',
             f'alltheores:other_{mat}_ore', f'"alltheores:{mat}"']
    return pats

# mat -> recipe-file count, and set of referencing namespaces
total = defaultdict(int)
ns_refs = defaultdict(set)
non_ato = defaultdict(int)

RECIPE_RE = re.compile(r"data/([^/]+)/recipes?/.+\.json$")

def scan_zip(path, label=None):
    try:
        z = zipfile.ZipFile(path)
    except Exception:
        return
    for n in z.namelist():
        rm = RECIPE_RE.match(n)
        if not rm:
            continue
        ns = rm.group(1)
        try:
            txt = z.read(n).decode("utf-8", "ignore")
        except Exception:
            continue
        for mat in materials:
            if any(p in txt for p in patterns(mat)):
                total[mat] += 1
                ns_refs[mat].add(ns)
                if ns != "alltheores":
                    non_ato[mat] += 1

for j in glob.glob(os.path.join(MODS, "*.jar")):
    scan_zip(j)
# also scan loose datapack recipe files
for f in glob.glob(os.path.join(DP, "**", "*.json"), recursive=True):
    rm = RECIPE_RE.search(f.replace(os.sep, "/"))
    if not rm:
        continue
    ns = rm.group(1)
    try:
        txt = open(f, encoding="utf-8", errors="ignore").read()
    except Exception:
        continue
    for mat in materials:
        if any(p in txt for p in patterns(mat)):
            total[mat] += 1; ns_refs[mat].add(ns)
            if ns != "alltheores": non_ato[mat] += 1

print(f"ATO materials found: {len(materials)}\n")
print(f"{'material':14s} {'total':>5s} {'non-ATO':>7s}  consuming mods (non-alltheores)")
print("-" * 78)
rows = sorted(materials, key=lambda m: (non_ato[m], total[m]))
for mat in rows:
    others = sorted(ns_refs[mat] - {"alltheores", "minecraft", "c"})
    flag = "  <== PRUNE?" if non_ato[mat] <= 3 else ""
    print(f"{mat:14s} {total[mat]:5d} {non_ato[mat]:7d}  {', '.join(others) if others else '(only ATO/vanilla)'}{flag}")
