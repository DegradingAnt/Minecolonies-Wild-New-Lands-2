#!/usr/bin/env python3
"""Consolidate the 5 UltimateVibes Paxi datapacks into ONE publishable datapack.
- Merges data/ trees from all source packs into UltimateVibes-Compat/.
- PRUNES files whose top namespace is a removed mod (absent), keeping my own
  namespaces (uvfixes) and hyphen/underscore modId variants (hybrid-aquatic).
- Detects path collisions (same data path in 2 packs w/ different content).
- Writes a clean, publishable pack.mcmeta + LICENSE note.
Re-runnable. Source packs are left intact until verified, then retired by hand.
LICENSING: contains ONLY my own authored fixes/overrides -- no third-party mod data copied."""
import json, os, shutil, hashlib, collections

ROOT = r"C:/Users/linde/curseforge/minecraft/Instances/Ultimate vibes distant horizons version"
DPDIR = os.path.join(ROOT, "config/paxi/datapacks")
SRC_DIR = os.path.join(ROOT, ".uvrun/datapack-backups/pre-consolidation")  # sources moved here on 1st run
OUT_NAME = "UltimateVibes-Compat"
OUT = os.path.join(DPDIR, OUT_NAME)
MODS = os.path.join(ROOT, "mods")
# load order = priority low->high; later overrides earlier. Merge keeps highest-priority on collision.
SOURCES = ["UltimateVibes-Structures", "UltimateVibes-CompatPort", "UltimateVibes-BetterCombatWeapons",
           "UltimateVibes-CroptopiaBotanyPots", "UltimateVibes-DataFixes"]  # last = wins collisions

VANILLA = {"minecraft", "c", "forge", "neoforge", "fabric", "common", "fml", "mod"}
MINE = {"uvfixes", "ultimatevibes", "ultimatevibes_packfixes"}

meta = json.load(open(os.path.join(ROOT, ".uvrun/modmeta.json")))
entries = meta if isinstance(meta, list) else meta.get("mods", list(meta.values()))
INSTALLED = set(VANILLA) | set(MINE)
for x in entries:
    for m in (x.get("mods") or []):
        mid = (m.get("modId") or "").lower()
        if mid:
            INSTALLED.add(mid); INSTALLED.add(mid.replace("_", "-")); INSTALLED.add(mid.replace("-", "_"))

def absent(ns):
    return ns not in INSTALLED

# namespaces that an INSTALLED jar still ships data/<ns>/ for -- e.g. MyNethersDelight ships
# data/brewinandchewin/recipe/ (cross-mod compat for a now-removed mod). An override for such a
# namespace is NOT dead: it suppresses the broken cross-mod recipe/loot. Only prune if NO jar
# ships that namespace's data (then the override targets nothing).
import zipfile
SHIPPED = set()
for jar in sorted(os.listdir(MODS)):
    if not jar.endswith(".jar"):
        continue
    try:
        with zipfile.ZipFile(os.path.join(MODS, jar)) as z:
            for n in z.namelist():
                p = n.split("/")
                if len(p) >= 3 and p[0] == "data":
                    SHIPPED.add(p[1])
    except Exception:
        pass

def prunable(ns):
    return absent(ns) and ns not in SHIPPED   # absent mod AND nothing ships its data

if os.path.isdir(OUT):
    shutil.rmtree(OUT)
os.makedirs(os.path.join(OUT, "data"), exist_ok=True)

written = {}                       # relpath -> (pack, sha)
pruned = collections.Counter()     # namespace -> count
collisions = []
counts = collections.Counter()

for pk in SOURCES:
    base = os.path.join(SRC_DIR, pk, "data")
    if not os.path.isdir(base):
        print(f"   [missing source] {pk}"); continue
    for dp, _dn, fns in os.walk(base):
        for fn in fns:
            if not fn.endswith(".json"):
                continue
            src = os.path.join(dp, fn)
            rel = os.path.relpath(src, base)
            ns = rel.split(os.sep)[0]
            if prunable(ns):
                pruned[ns] += 1
                continue
            data = open(src, "rb").read()
            sha = hashlib.sha256(data).hexdigest()
            if rel in written and written[rel][1] != sha:
                collisions.append((rel, written[rel][0], pk))  # later pack wins (overwrite)
            dst = os.path.join(OUT, "data", rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, "wb").write(data)
            written[rel] = (pk, sha)
            counts[pk] += 1

# publishable metadata
json.dump({"pack": {
    "pack_format": 48,
    "description": "Ultimate Vibes — compatibility & fix datapack. Loot/recipe/tag/structure fixes for the modpack, consolidated. Authored overrides only."
}}, open(os.path.join(OUT, "pack.mcmeta"), "w"), indent=2)
open(os.path.join(OUT, "LICENSE.txt"), "w").write(
    "Ultimate Vibes compatibility datapack.\n"
    "Contains only original override/fix data authored for this modpack\n"
    "(loot table strips, recipe corrections, tag fixes, structure tweaks).\n"
    "No third-party mod assets are redistributed. Free to use/modify.\n")

print(f"=== consolidated -> {OUT_NAME} ===")
for pk in SOURCES:
    print(f"   {pk:34s} {counts[pk]:5d} files merged")
print(f"\n   total files: {sum(counts.values())}   unique paths: {len(written)}")
print(f"   PRUNED (removed-mod overrides): {sum(pruned.values())} files -> {dict(pruned)}")
if collisions:
    print(f"\n   ! COLLISIONS ({len(collisions)}) — later-priority pack won:")
    for rel, a, b in collisions[:20]:
        print(f"      {rel}   ({a} -> {b})")
else:
    print("   no path collisions ")
