#!/usr/bin/env python3
"""Harvest a boot log into the data files the loot/recipe fixers consume.
Run after a boot so the fix scripts are driven by CURRENT errors (survives pack updates).

Reads logs/latest.log (or argv[1]) and writes, under .uvrun/compat-port/:
  - failing_loot.json   {"tables": {table_id: [[root_type, absent_key], ...]}}
        from:  Couldn't parse element ResourceKey[.. / .. loot_table]:<TABLE> -
               Unknown registry key in ResourceKey[.. / .. <type>]: <KEY>
  - recipe_errors.json  [{"recipe": id, "reason": text}]  (for the malformed-recipe pass)
And prints a triage summary (loot tables, recipe errors, missing-loot-table refs,
unknown-tag warnings) so a human/skill can see what still needs a hand-written fix.

No jar edits, no game state touched -- pure read of the log.

By default MERGES into the existing failing_loot.json (a CompatPort-active boot only
surfaces NEW breakage, since already-fixed tables no longer error -- merging keeps the
list comprehensive so a clean rebuild never loses coverage). Pass --fresh to overwrite.
For a guaranteed-complete harvest, boot with the CompatPort datapack disabled so ALL
loot errors surface, then run with --fresh."""
import json, os, re, sys, collections

ROOT = r"C:/Users/linde/curseforge/minecraft/Instances/Ultimate vibes distant horizons version"
ARGS = [a for a in sys.argv[1:] if not a.startswith("-")]
FRESH = "--fresh" in sys.argv
LOG  = ARGS[0] if ARGS else os.path.join(ROOT, "logs/latest.log")
OUTD = os.path.join(ROOT, ".uvrun/compat-port")

RE_LOOT = re.compile(
    r"Couldn't parse element ResourceKey\[minecraft:root / minecraft:loot_table\]:(\S+)"
    r" - Unknown registry key in ResourceKey\[minecraft:root / minecraft:(\w+)\]: (\S+)")
RE_RECIPE   = re.compile(r"RecipeManager/?\].*Parsing error loading recipe (\S+?): (.*)$")
RE_LTREF    = re.compile(r"Unknown loot table called (\S+)")
RE_TAG      = re.compile(r"Unknown tag '?([\w:/]+)'?|tag ([\w:/]+) .*does not exist", re.I)

tables = {}                       # table_id -> list[[root_type, key]]
recipes = []                      # {recipe, reason}
ltrefs = collections.Counter()    # missing loot-table references
ns_loot = collections.Counter()   # absent-loot count per namespace

with open(LOG, encoding="utf-8", errors="replace") as f:
    for line in f:
        m = RE_LOOT.search(line)
        if m:
            tid, root_type, key = m.group(1), m.group(2), m.group(3)
            tid = tid.rstrip(".")
            tables.setdefault(tid, [])
            if [root_type, key] not in tables[tid]:
                tables[tid].append([root_type, key])
            ns_loot[tid.split(":", 1)[0]] += 1
            continue
        m = RE_RECIPE.search(line)
        if m:
            recipes.append({"recipe": m.group(1), "reason": m.group(2).strip()[:200]})
            continue
        m = RE_LTREF.search(line)
        if m:
            ltrefs[m.group(1).rstrip(".")] += 1

os.makedirs(OUTD, exist_ok=True)
flp = os.path.join(OUTD, "failing_loot.json")
merged = 0
if not FRESH and os.path.exists(flp):
    try:
        prev = json.load(open(flp)).get("tables", {})
    except Exception:
        prev = {}
    for tid, refs in prev.items():
        cur = tables.setdefault(tid, [])
        for r in refs:
            if r not in cur:
                cur.append(r); merged += 1
json.dump({"tables": tables}, open(flp, "w"))
json.dump(recipes, open(os.path.join(OUTD, "recipe_errors.json"), "w"), indent=2)

print(f"log: {LOG}")
print(f"mode: {'FRESH (overwrite)' if FRESH else f'MERGE (+{merged} kept from prior failing_loot.json)'}")
print(f"\n=== LOOT (absent-item) tables: {len(tables)} tables, "
      f"{sum(len(v) for v in tables.values())} absent refs ===")
for ns, c in ns_loot.most_common():
    print(f"   {ns:34s} {c:5d} absent refs   -> build_loot.py auto-resolves owning jar")
print(f"\n=== RECIPE parse errors: {len(recipes)} (need hand-written neoforge:false override) ===")
by_reason = collections.Counter(r["reason"].split(":")[0][:48] for r in recipes)
for reason, c in by_reason.most_common():
    print(f"   x{c:<3d} {reason}")
print(f"\n=== MISSING loot-table references: {len(ltrefs)} ===")
for ref, c in ltrefs.most_common(15):
    print(f"   x{c:<3d} {ref}")
print("\nwrote: .uvrun/compat-port/failing_loot.json  +  recipe_errors.json")
print("next:  python .uvrun/compat-port/build_loot.py   (regenerates CompatPort loot overrides)")
