#!/usr/bin/env python3
"""UltimateVibes lean compat-port: loot tables.
Strips absent-mod / unregistered-item entries from loot tables that fail to parse,
reading the PRISTINE table from the owning mod jar (never an edited jar) and writing
a cleaned override into a Paxi datapack. No jar editing.

- Absent-mod tables (idas -> ars_nouveau/iceandfire, not installed): strip absent
  entries; if a table empties out, fall back to a thematically-appropriate vanilla
  treasure table so the structure's chests still reward.
- Self-referential block tables (cif/culturaldelights/minecolonies_compatibility:
  block drops its own item, but the item form isn't registered): strip -> empty
  block table (drops nothing, which is the current behaviour, minus the parse error).
"""
import json, os, re, zipfile, sys

ROOT = r"C:/Users/linde/curseforge/minecraft/Instances/Ultimate vibes distant horizons version"
OUT  = os.path.join(ROOT, "config/paxi/datapacks/UltimateVibes-Compat")

# table-namespace -> owning jar is AUTO-RESOLVED from mods/ (scan for the jar that owns
# data/<ns>/loot_table(s)/) so this survives pack updates without manual edits.
# Any namespace with no installed owner is treated as an absent mod and skipped.
MODS = os.path.join(ROOT, "mods")

def build_ns_jar_index(namespaces):
    """For each namespace, find the installed jar that ships its loot tables."""
    idx, need = {}, set(namespaces)
    for jar in sorted(os.listdir(MODS)):
        if not jar.endswith(".jar") or not need:
            continue
        try:
            with zipfile.ZipFile(os.path.join(MODS, jar)) as z:
                names = z.namelist()
                for ns in list(need):
                    if any(n.startswith(f"data/{ns}/loot_table/") or
                           n.startswith(f"data/{ns}/loot_tables/") for n in names):
                        idx[ns] = jar
                        need.discard(ns)
        except Exception:
            pass
    return idx

# extra namespace-level strip safety for idas's optional-integration items
ABSENT_NS = {"ars_nouveau", "iceandfire"}

# vanilla fallback by idas structure (keeps emptied dungeon chests rewarding)
def idas_fallback(path):
    if "archmages_tower" in path or "enchantingtower" in path:
        return "minecraft:chests/stronghold_library"
    return "minecraft:chests/simple_dungeon"  # dread_citadel, haunted_manor, labyrinth

fail = json.load(open(os.path.join(ROOT, ".uvrun/compat-port/failing_loot.json")))["tables"]
# auto-resolve table-namespace -> owning jar from the namespaces actually present
NS_JAR = build_ns_jar_index({tid.split(":", 1)[0] for tid in fail})
# absent key set = every unknown key MC reported across all failing tables
ABSENT_KEYS = set()
for tid, keys in fail.items():
    for _rt, k in keys:
        ABSENT_KEYS.add(k)

def is_absent_item(name):
    if not name:
        return False
    return name in ABSENT_KEYS or name.split(":")[0] in ABSENT_NS

def clean_entry(e):
    t = e.get("type", "").replace("minecraft:", "")
    if t == "item":
        return None if is_absent_item(e.get("name", "")) else e
    if t in ("alternatives", "group", "sequence"):
        kids = [k for k in (clean_entry(c) for c in e.get("children", [])) if k]
        if not kids:
            return None
        e["children"] = kids
        return e
    return e  # tag / dynamic / empty / loot_table / loot_table-ref -> keep

def clean_table(tbl):
    newpools = []
    for p in tbl.get("pools", []):
        ents = [x for x in (clean_entry(e) for e in p.get("entries", [])) if x]
        if ents:
            p["entries"] = ents
            newpools.append(p)
    tbl["pools"] = newpools
    return tbl, len(newpools)

def read_source(jarpath, ns, sub):
    with zipfile.ZipFile(jarpath) as z:
        names = set(z.namelist())
        for d in ("loot_table", "loot_tables"):
            p = f"data/{ns}/{d}/{sub}.json"
            if p in names:
                return json.loads(z.read(p))
    return None

def write_both(ns, sub, obj):
    js = json.dumps(obj, indent=2)
    for d in ("loot_table", "loot_tables"):
        fp = os.path.join(OUT, "data", ns, d, sub + ".json")
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        open(fp, "w").write(js)

os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, "pack.mcmeta"), "w").write(json.dumps({
    "pack": {
        "pack_format": 48,
        "description": "UltimateVibes lean compat-port (loot). Strips absent-mod / unregistered-item refs from failing loot tables (idas->ars_nouveau/iceandfire absent; cif/culturaldelights/minecolonies_compat self-ref). Reconstructed from pristine jars; no jar editing."
    }
}, indent=2))

stats = {"stripped_kept": 0, "fallback": 0, "drops_nothing": 0, "skipped_absent_mod": 0, "error": 0}
log = []
for tid, keys in sorted(fail.items()):
    ns, sub = tid.split(":", 1)
    jar = NS_JAR.get(ns)
    if not jar:
        stats["skipped_absent_mod"] += 1
        continue
    jarpath = os.path.join(ROOT, "mods", jar)
    try:
        src = read_source(jarpath, ns, sub)
        if src is None:
            log.append(f"  ! SOURCE NOT FOUND  {tid}")
            stats["error"] += 1
            continue
        cleaned, npools = clean_table(src)
        if npools > 0:
            write_both(ns, sub, cleaned)
            stats["stripped_kept"] += 1
            log.append(f"  ~ stripped, {npools} pool(s) kept   {tid}")
        elif ns == "idas":
            fb = idas_fallback(sub)
            obj = {"type": "minecraft:chest", "pools": [
                {"rolls": 1, "entries": [{"type": "minecraft:loot_table", "value": fb}]}]}
            write_both(ns, sub, obj)
            stats["fallback"] += 1
            log.append(f"  > emptied -> fallback {fb}   {tid}")
        else:
            obj = {"type": "minecraft:block", "pools": []}  # self-ref block: drops nothing, parses clean
            write_both(ns, sub, obj)
            stats["drops_nothing"] += 1
            log.append(f"  0 self-ref -> drops nothing   {tid}")
    except Exception as ex:
        stats["error"] += 1
        log.append(f"  ! ERROR {tid}: {ex}")

print("\n".join(log))
print("\n=== STATS ===")
for k, v in stats.items():
    print(f"  {k:20s} {v}")
print(f"\nABSENT_KEYS collected: {len(ABSENT_KEYS)}")
# validate every emitted json parses
bad = 0
for dp, _dn, fns in os.walk(OUT):
    for fn in fns:
        if fn.endswith(".json"):
            try:
                json.load(open(os.path.join(dp, fn)))
            except Exception as ex:
                bad += 1
                print("  INVALID JSON:", os.path.join(dp, fn), ex)
print(f"emitted-json validation: {'ALL VALID' if bad == 0 else str(bad)+' INVALID'}")
