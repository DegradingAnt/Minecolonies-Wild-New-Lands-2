#!/usr/bin/env python3
"""Redundancy / bloat clusterer for Ultimate Vibes. Judges by DESCRIPTION (not filename).
Buckets mods into narrow overlap-prone functional categories; flags clusters with 2+ mods.
Also flags low-content 'pure extra' candidates. Output = my review material (NOT auto-cut)."""
import json, ast, re

d = json.load(open(r".uvrun/modmeta.json"))
entries = d if isinstance(d, list) else d.get("mods", list(d.values()))

mods = []  # (modId, name, desc, file, classes, recipes, sizeMB)
for e in entries:
    mv = e.get("mods", [])
    if isinstance(mv, str):
        try: mlist = ast.literal_eval(mv)
        except Exception: mlist = []
    else:
        mlist = mv or []
    for m in mlist:
        mods.append({
            "id": (m.get("modId") or "?"), "name": (m.get("name") or "?"),
            "desc": (m.get("desc") or "").replace("\n", " "),
            "file": e.get("file", "?"),
            "classes": int(e.get("classes", 0) or 0),
            "recipes": int(e.get("recipes", 0) or 0),
            "size": float(e.get("sizeMB", 0) or 0),
        })

def txt(m):
    return (m["name"] + " " + m["desc"] + " " + m["id"]).lower()

# narrow overlap-prone categories (regex on name+desc+id)
CATS = {
    "minimap/map/waypoint":      r"minimap|waypoint|world ?map|fullscreen map|journeymap|xaero|cartograph",
    "backpack/storage":          r"backpack|\bpouch\b|storage drawer|\bsack\b|item storage|storage network|sophisticated|shulker",
    "inventory sorting/tweaks":  r"inventory sort|\bsorting\b|inventory tweak|inventory management|sort.*invent",
    "leaf decay/leaf cull":      r"leaf ?decay|leaves ?decay|fast.?leaf|cull.?leaves|leaf.?cull|fall(ing)? leaves",
    "entity/render culling":     r"entity cull|\bculling\b|occlusion cull|more ?culling|too ?fast",
    "tooltip/item info":         r"tooltip|item description|enchant.*description|durability.*tooltip|legendary tooltip|item.?descriptions",
    "trash/void":                r"\btrash\b|void item|garbage|delete.*item|trash ?slot|trash ?can",
    "magnet/item pickup":        r"\bmagnet\b|attract item|item ?pickup|pick.?up notif|vacuum item",
    "loot integration":          r"loot ?integration|lootintegration",
    "death/grave/totem":         r"gravestone|tombstone|\bgrave\b|death chest|keep ?invent|totem of|undying|soulbound",
    "skill/class/origins/rpg":   r"skill ?tree|\bskills\b|rpg class|character class|\borigins?\b|\bpowers?\b|leveling|level ?up|spell ?book|mana",
    "seasons/weather/climate":   r"\bseason|\bweather\b|climate|serene ?season",
    "compat/integration glue":   r"compat|integration|\bbridge\b|let'?s do compat|cross.?mod",
    "magnets/pickup":            r"",  # placeholder
    "minimap radar":             r"",  # placeholder
    "anvil/enchant utility":     r"\banvil\b|enchant.*(infus|appar|easy)|easy ?magic|enchant.*table",
    "totem/extra-life":          r"more ?totem|extra ?life|second chance|hardcore revival|revival",
    "horse/mount/boat util":     r"\bhorse\b|\bmount\b|boat.*fix|reach ?around",
}
CATS = {k: v for k, v in CATS.items() if v}

print("================ REDUNDANCY CLUSTERS (2+ mods, narrow function) ================")
for cat, pat in CATS.items():
    rx = re.compile(pat)
    hits = [m for m in mods if rx.search(txt(m))]
    # de-dup by id
    seen = set(); uniq = []
    for m in hits:
        if m["id"] not in seen:
            seen.add(m["id"]); uniq.append(m)
    if len(uniq) >= 2:
        print(f"\n### {cat}  ({len(uniq)} mods)")
        for m in sorted(uniq, key=lambda x: -x["classes"]):
            print(f"   - {m['name'][:32]:32s} [{m['id'][:22]:22s}] cls={m['classes']:<4} rec={m['recipes']:<4} {m['size']}MB :: {m['desc'][:90]}")

# low-content 'pure extra' candidates: tiny class count, no recipes, small (excluding libs/APIs which are deps)
print("\n\n================ LOW-CONTENT CANDIDATES (classes<=8, recipes=0, <0.3MB) — review for pure-extra ================")
low = [m for m in mods if m["classes"] <= 8 and m["recipes"] == 0 and m["size"] < 0.3]
seen = set()
for m in sorted(low, key=lambda x: x["classes"]):
    if m["id"] in seen: continue
    seen.add(m["id"])
    print(f"   - {m['name'][:34]:34s} [{m['id'][:22]:22s}] cls={m['classes']:<3} {m['size']}MB :: {m['desc'][:85]}")
print(f"\n  ({len(seen)} low-content candidates)")
print(f"\nTOTAL mod ids analyzed: {len(mods)}")
