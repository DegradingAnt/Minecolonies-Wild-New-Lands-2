#!/usr/bin/env python3
"""Absent-mod reference scanner for the lean compat-port + datapack consolidation.
Two reports:
  (A) PRUNE  -- files in MY Paxi datapacks whose target namespace is an ABSENT mod
               (override for a removed mod = dead weight -> drop on consolidation).
  (B) DISCOVER -- data files INSIDE installed jars (recipe/loot/tags/data_maps) that
               reference an absent-mod namespace, split by whether the file guards it
               (mod_loaded condition / required:false) -> UNGUARDED = real fix candidate.
Deterministic parse, no jar edits. Output is scoping material."""
import json, os, re, zipfile, collections

ROOT = r"C:/Users/linde/curseforge/minecraft/Instances/Ultimate vibes distant horizons version"
MODS = os.path.join(ROOT, "mods")
DPDIR = os.path.join(ROOT, "config/paxi/datapacks")
MY_PACKS = ["UltimateVibes-CompatPort", "UltimateVibes-DataFixes", "UltimateVibes-Structures",
            "UltimateVibes-CroptopiaBotanyPots", "UltimateVibes-BetterCombatWeapons"]

VANILLA = {"minecraft", "c", "forge", "neoforge", "fabric", "common", "fml", "mod"}
RL = re.compile(r"^[a-z0-9_.-]+:[a-z0-9_./-]+$")

# installed namespaces = every modId in the pack
meta = json.load(open(os.path.join(ROOT, ".uvrun/modmeta.json")))
entries = meta if isinstance(meta, list) else meta.get("mods", list(meta.values()))
INSTALLED = set(VANILLA)
for x in entries:
    for m in (x.get("mods") or []):
        if m.get("modId"):
            INSTALLED.add(m["modId"].lower())

def absent(ns):
    return ns not in INSTALLED

def walk_strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for v in o.values():
            yield from walk_strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk_strings(v)

def absent_refs(obj):
    out = set()
    for s in walk_strings(obj):
        s2 = s[1:] if s.startswith("#") else s     # tag ref
        if RL.match(s2):
            ns = s2.split(":", 1)[0]
            if absent(ns):
                out.add(ns)
    return out

def guarded_for(text, ns):
    # file declares mod_loaded for that ns, OR is full of required:false (optional entries)
    if re.search(r'"modid"\s*:\s*"' + re.escape(ns) + r'"', text):
        return True
    if '"required": false' in text or '"required":false' in text:
        return True
    return False

# ---------- (A) PRUNE: my datapack files targeting absent mods ----------
print("================ (A) PRUNE: my-datapack overrides targeting ABSENT mods ================")
prune = collections.defaultdict(list)
total_my = 0
for pk in MY_PACKS:
    base = os.path.join(DPDIR, pk, "data")
    if not os.path.isdir(base):
        print(f"   [missing] {pk}"); continue
    for dp, _dn, fns in os.walk(base):
        for fn in fns:
            if not fn.endswith(".json"):
                continue
            total_my += 1
            rel = os.path.relpath(os.path.join(dp, fn), base)
            ns = rel.split(os.sep)[0]
            if absent(ns):
                prune[pk].append((ns, rel))
for pk in MY_PACKS:
    if prune[pk]:
        byns = collections.Counter(ns for ns, _ in prune[pk])
        print(f"   {pk}: {len(prune[pk])} stale files -> {dict(byns)}")
tot_prune = sum(len(v) for v in prune.values())
print(f"   -> {tot_prune} of {total_my} my-datapack files target an absent mod (drop on consolidation)")

# ---------- (B) DISCOVER: absent-mod refs inside installed jars ----------
print("\n================ (B) DISCOVER: absent-mod refs in installed-jar data ================")
DATA_KINDS = ("recipe", "recipes", "loot_table", "loot_tables", "tags", "data_maps")
unguarded = collections.Counter()   # absent_ns -> count of unguarded files
guarded   = collections.Counter()
examples  = collections.defaultdict(list)
for jar in sorted(os.listdir(MODS)):
    if not jar.endswith(".jar"):
        continue
    try:
        with zipfile.ZipFile(os.path.join(MODS, jar)) as z:
            for n in z.namelist():
                p = n.split("/")
                if len(p) < 4 or p[0] != "data" or not n.endswith(".json"):
                    continue
                if p[2] not in DATA_KINDS:
                    continue
                owner = p[1]
                if absent(owner):       # the whole file belongs to an absent mod's data dir (rare) -> skip, not ours
                    continue
                try:
                    raw = z.read(n).decode("utf-8", "replace")
                    obj = json.loads(raw)
                except Exception:
                    continue
                for ns in absent_refs(obj):
                    if guarded_for(raw, ns):
                        guarded[ns] += 1
                    else:
                        unguarded[ns] += 1
                        if len(examples[ns]) < 2:
                            examples[ns].append(f"{jar[:26]}::{'/'.join(p[1:])[:48]}")
    except Exception:
        pass

print("   UNGUARDED absent-mod refs (no mod_loaded guard, not required:false) = real candidates:")
for ns, c in unguarded.most_common(30):
    ex = "  e.g. " + examples[ns][0] if examples[ns] else ""
    print(f"     {ns:24s} {c:4d} files{ex}")
print(f"\n   guarded (correctly skipped, NO action): {sum(guarded.values())} refs across {len(guarded)} absent namespaces")
print(f"   unguarded TOTAL: {sum(unguarded.values())} files across {len(unguarded)} absent namespaces")
print(f"\n   installed namespaces: {len(INSTALLED)}")
