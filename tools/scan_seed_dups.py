#!/usr/bin/env python3
"""Find duplicate SEED items across mods for the unified crops (seeds Phase B, approach A).
Seeds are mostly NOT in convention tags, so enumerate them from item model filenames
(assets/<ns>/models/item/*seed*.json -> item id <ns>:<name>). Group by normalized crop key.
Report crops whose seed is provided by >=2 mods = unification candidates.
"""
import os, re, glob, zipfile
from collections import defaultdict

MODS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mods"))

# our unified crop set (from food pass) — focus, but also report any other dup seeds
UNIFIED = {
    "almond","asparagus","bellpepper","blueberry","cabbage","cherry","corn","cranberry",
    "eggplant","fig","garlic","kiwi","lemon","mango","onion","orange","peach","peanut",
    "pear","pecan","persimmon","pineapple","rice","soybean","tomato","walnut",
}

MODEL_RE = re.compile(r"assets/([^/]+)/models/item/(.+)\.json$")

def crop_key(name):
    n = name.lower()
    # strip seed words
    n = re.sub(r"(^|_)seeds?($|_)", "_", n)
    n = n.strip("_")
    # compact form (drop underscores) to match bell_pepper<->bellpepper, chile_pepper, etc.
    return n.replace("_", "")

# crop_key -> { mod_ns : set(seed_item_ids) }
seeds = defaultdict(lambda: defaultdict(set))

for jp in sorted(glob.glob(os.path.join(MODS, "*.jar"))):
    try:
        z = zipfile.ZipFile(jp)
    except Exception:
        continue
    for name in z.namelist():
        m = MODEL_RE.match(name)
        if not m:
            continue
        ns, item = m.group(1), m.group(2)
        if "seed" not in item.lower():
            continue
        # skip obvious non-crop seed-ish (seed bag, pouch, packet, sack)
        if any(x in item.lower() for x in ("bag", "pouch", "packet", "sack", "satchel", "pack")):
            continue
        key = crop_key(item)
        if not key:
            continue
        seeds[key][ns].add(f"{ns}:{item}")

print("=" * 72)
print("DUPLICATE SEEDS (seed provided by >=2 mods) — UNIFIED crops first")
print("=" * 72)
def emit(keys, header):
    rows = []
    for k in sorted(keys):
        mods = seeds.get(k, {})
        if len(mods) >= 2:
            allids = sorted(i for s in mods.values() for i in s)
            rows.append((k, allids))
    if rows:
        print(f"\n--- {header} ({len(rows)}) ---")
        for k, ids in rows:
            print(f"  {k:14s} -> {', '.join(ids)}")
    return {k for k, _ in rows}

dup_unified = emit(UNIFIED & set(seeds), "in our unified-crop set")
other = set(seeds) - UNIFIED
emit(other, "OTHER crops with dup seeds (not in unified set)")

# unified crops that DON'T have a dup seed (single provider) — just note count
single = [k for k in (UNIFIED & set(seeds)) if len(seeds[k]) == 1]
print(f"\n[info] unified crops with only ONE seed provider (no seed unify needed): {len(single)}")
print("  " + ", ".join(sorted(single)))
missing = sorted(UNIFIED - set(seeds))
print(f"\n[info] unified crops with NO seed item found via models: {len(missing)}")
print("  " + ", ".join(missing))
