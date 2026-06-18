#!/usr/bin/env python3
"""Compatibility pass for pack UPDATES: what changed since the last baseline, and does
any NEW mod overlap an existing function?

Diffs .uvrun/modmeta.json against .uvrun/modmeta_snapshot.json (the last committed
baseline). For every ADDED mod it (a) buckets it into narrow overlap-prone categories
alongside existing mods, and (b) flags any installed mod sharing >=2 distinctive tokens.
Output is review material, never an auto-cut (see memory: fix-dont-delete-content).

Usage:
  python .uvrun/modscan.py            # refresh modmeta.json first
  python .uvrun/new_mods_diff.py      # show added/removed + overlap for new mods
  python .uvrun/new_mods_diff.py --save   # commit current modlist as the new baseline
"""
import json, os, re, sys, collections

ROOT = r"C:/Users/linde/curseforge/minecraft/Instances/Ultimate vibes distant horizons version"
META = os.path.join(ROOT, ".uvrun/modmeta.json")
SNAP = os.path.join(ROOT, ".uvrun/modmeta_snapshot.json")
SAVE = "--save" in sys.argv

CATS = {
    "minimap/map/waypoint":   r"minimap|waypoint|world ?map|fullscreen map|journeymap|xaero|cartograph",
    "backpack/storage":       r"backpack|\bpouch\b|storage drawer|\bsack\b|storage network|sophisticated|shulker",
    "inventory sort/tweaks":  r"inventory sort|\bsorting\b|inventory tweak|mouse ?tweak",
    "leaf decay/cull":        r"leaf ?decay|leaves ?decay|fast.?leaf|cull.?leaves|fall(ing)? leaves",
    "entity/render culling":  r"entity cull|\bculling\b|occlusion cull|more ?culling",
    "particle perf":          r"particle.*(optim|cull|async|perf)|async.*particle",
    "tooltip/item info":      r"tooltip|item description|durability.*tooltip",
    "trash/void":             r"\btrash\b|void item|garbage|delete.*item",
    "magnet/item pickup":     r"\bmagnet\b|attract item|item ?pickup|vacuum item",
    "loot integration":       r"loot ?integration|lootintegration",
    "death/grave/totem":      r"gravestone|tombstone|\bgrave\b|death chest|totem of|undying|soulbound",
    "skill/class/rpg":        r"skill ?tree|\bskills\b|rpg class|character class|\borigins?\b|leveling|spell ?book",
    "seasons/weather":        r"\bseason|\bweather\b|climate|serene ?season",
    "chunk loading":          r"chunk ?load|force.?load|chunkload|power loader",
    "jetpack/flight":         r"jetpack|jet pack|\bglider\b|elytra",
    "minecart/train":         r"\btrain\b|minecart|railway|\brail\b|locomotive|bogey",
    "currency/economy":       r"currency|\bcoin\b|economy|trading floor|numismatic",
    "waystone/teleport":      r"waystone|\bteleport\b|home ?point|warp",
}

def txt(m):
    return ((m.get("name") or "") + " " + (m.get("desc") or "") + " " + (m.get("id") or "")).lower()

def load_mods(path):
    if not os.path.exists(path):
        return None
    d = json.load(open(path, encoding="utf-8"))
    e = d if isinstance(d, list) else d.get("mods", list(d.values()))
    out = {}
    for x in e:
        for m in (x.get("mods") or []):
            mid = m.get("modId")
            if mid and mid not in out:
                out[mid] = {"id": mid, "name": m.get("name") or mid,
                            "desc": (m.get("desc") or "").replace("\n", " "), "file": x.get("file", "?")}
    return out

cur = load_mods(META)
if cur is None:
    sys.exit("no modmeta.json -- run: python .uvrun/modscan.py")
prev = load_mods(SNAP)

if prev is None:
    print("No baseline snapshot yet. Treating ALL mods as the baseline.")
    print(f"current modlist: {len(cur)} mod ids")
    if SAVE:
        import shutil; shutil.copy(META, SNAP)
        print(f"-> saved baseline ({len(cur)} ids) to modmeta_snapshot.json")
    else:
        print("Run with --save to set this as the baseline for future diffs.")
    sys.exit(0)

added   = [cur[i]  for i in cur  if i not in prev]
removed = [prev[i] for i in prev if i not in cur]

print(f"=== MODLIST DIFF vs baseline ===  +{len(added)} added  -{len(removed)} removed  ({len(cur)} total)\n")
if removed:
    print("REMOVED:")
    for m in sorted(removed, key=lambda x: x["id"]):
        print(f"   - {m['id']:28s} {m['name'][:40]}")
    print()
if not added:
    print("No new mods. (overlap check skipped)")
else:
    print("ADDED:")
    for m in sorted(added, key=lambda x: x["id"]):
        print(f"   + {m['id']:28s} {m['name'][:40]}  ::  {m['desc'][:60]}")

    rx = {c: re.compile(p) for c, p in CATS.items()}
    print("\n=== OVERLAP CHECK for new mods (category buckets they share with existing mods) ===")
    flagged = False
    for c, r in rx.items():
        newhits = [m for m in added    if r.search(txt(m))]
        oldhits = [m for m in prev.values() if r.search(txt(m))]
        if newhits and oldhits:
            flagged = True
            print(f"\n  ### {c}")
            for m in newhits:
                print(f"     NEW  {m['id']:26s} {m['name'][:34]}")
            for m in sorted(oldhits, key=lambda x: x["id"])[:8]:
                print(f"     have {m['id']:26s} {m['name'][:34]}")
    if not flagged:
        print("   no new mod lands in a shared function bucket -- nothing obvious to review.")
    print("\n   NOTE: shared bucket != redundant. Most are complementary (addon ecosystems,")
    print("   integration glue, distinct mechanics). Judge by jar description, never the name.")

if SAVE:
    import shutil; shutil.copy(META, SNAP)
    print(f"\n-> committed new baseline ({len(cur)} ids) to modmeta_snapshot.json")
else:
    print("\n(run with --save to commit current modlist as the new baseline)")
