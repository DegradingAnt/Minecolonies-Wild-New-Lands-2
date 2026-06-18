#!/usr/bin/env python3
"""Scan all mod jars for convention food/crop/seed tags and report cross-mod duplicates.
Authoritative-enough source for building the AlmostUnified food unification config without a boot.
Reports, per tag, the set of providing mods (by item namespace), flagging tags shared by >=2 mods.
"""
import os, re, sys, json, zipfile, glob
from collections import defaultdict

MODS = os.path.join(os.path.dirname(__file__), "..", "mods")
MODS = os.path.abspath(MODS)

# tag path categories we care about (convention 'c' namespace, food-ish)
CATS = ["crops", "foods", "seeds", "fruits", "vegetables", "grains", "nuts",
        "berries", "vegetable", "fruit", "salad", "soup", "juice", "milk",
        "bread", "cheese", "meat", "fish", "cooked", "raw_fish", "raw_meat",
        "doughs", "dough", "pies", "drinks", "sandwiches", "spices", "herbs"]

# match data/<ns>/tags/item or items / <category...>/<name>.json
TAG_RE = re.compile(r"data/([^/]+)/tags/items?/(.+)\.json$")

# tag -> set(member item namespaces);  tag -> set(member full ids)
tag_mods = defaultdict(set)
tag_items = defaultdict(set)
# also record which jar defined the tag file (the "definer")
tag_definers = defaultdict(set)

def member_ns(s):
    s = s.strip()
    if s.startswith("#"):
        return None  # tag reference, skip namespace attribution
    if ":" in s:
        return s.split(":", 1)[0]
    return "minecraft"

jars = sorted(glob.glob(os.path.join(MODS, "*.jar")))
scanned = 0
for jp in jars:
    jar = os.path.basename(jp)
    try:
        z = zipfile.ZipFile(jp)
    except Exception:
        continue
    for name in z.namelist():
        m = TAG_RE.match(name)
        if not m:
            continue
        ns, path = m.group(1), m.group(2)
        # only convention namespace tags, and only food-ish categories
        if ns != "c":
            continue
        top = path.split("/")[0]
        if top not in CATS:
            continue
        tag = f"c:{path}"
        try:
            data = json.loads(z.read(name).decode("utf-8"))
        except Exception:
            continue
        vals = data.get("values", [])
        tag_definers[tag].add(jar)
        for v in vals:
            if isinstance(v, dict):
                v = v.get("id", "")
            if not isinstance(v, str):
                continue
            nsv = member_ns(v)
            if nsv:
                tag_mods[tag].add(nsv)
                tag_items[tag].add(v)
    scanned += 1

# group by category
by_cat = defaultdict(list)
for tag, mods in tag_mods.items():
    cat = tag.split("/", 1)[0]  # e.g. c:crops
    by_cat[cat].append((tag, mods))

print(f"Scanned {scanned} jars. Food-ish convention tags found: {len(tag_mods)}\n")

# DUPLICATES: tags with >=2 distinct member mod-namespaces
print("=" * 70)
print("CROSS-MOD DUPLICATE TAGS (>=2 providing mods) — unification candidates")
print("=" * 70)
for cat in sorted(by_cat):
    dups = sorted([(t, m) for (t, m) in by_cat[cat] if len(m) >= 2])
    if not dups:
        continue
    print(f"\n--- {cat} ({len(dups)} duplicate tags) ---")
    for tag, mods in dups:
        short = tag.split("/", 1)[1] if "/" in tag else tag
        crop = "croptopia" in mods
        mark = " *CROP*" if crop else ""
        print(f"  {short:28s} [{len(mods)}] {','.join(sorted(mods))}{mark}")

# SINGLE-mod tags (just counts per category, for scope)
print("\n" + "=" * 70)
print("SINGLE-PROVIDER tags per category (no unification needed)")
print("=" * 70)
for cat in sorted(by_cat):
    singles = [t for (t, m) in by_cat[cat] if len(m) == 1]
    print(f"  {cat:18s} {len(singles)} single-provider tags")

# CROPTOPIA coverage: which crops/foods does croptopia provide at all
print("\n" + "=" * 70)
print("CROPTOPIA coverage (tags where croptopia is a member)")
print("=" * 70)
for cat in sorted(by_cat):
    crop_tags = sorted([(t.split('/',1)[1] if "/" in t else t) for (t, m) in by_cat[cat] if "croptopia" in m])
    if crop_tags:
        print(f"\n--- {cat} ({len(crop_tags)}) ---")
        print("  " + ", ".join(crop_tags))
