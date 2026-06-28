#!/usr/bin/env python3
"""expand_ruiner_tiers.py — expand the RUINER tier map from structure-SET granularity to
individual-STRUCTURE granularity, so RuinerEngine's per-structure-id lookup
(TIERS.getOrDefault(id.toString())) actually hits (was missing → 1233 UNTIERED).

Method (preserves the curated hand-tuned set tiers — NO from-scratch reclassify):
  1. {structure_id -> set_id} from every jar's worldgen/structure_set/*.json
  2. each member structure INHERITS its set's tier from the existing curated map
  3. orphans (set untiered, or structure setless) -> keyword classify() (same rules as
     categorize_structures.py), reported separately for review
Dry-run by default; --apply writes config/wnl_pathways/structure_tiers.json (backs up first).
The authoritative ground-truth structure list is the boot audit (Registries.STRUCTURE)."""
import sys, os, glob, zipfile, re, json, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODS = os.path.join(ROOT, "mods")
RUINER_TIERS = os.path.join(ROOT, "config", "wnl_pathways", "structure_tiers.json")
AUDIT = os.path.join(ROOT, "config", "wnl_pathways", "structure_audit_boot.txt")

# --- keyword classifiers (mirror categorize_structures.py; ruiner tiers: DECO/RUIN/LOOT/TOWN/BIG/DEFAULT) ---
RUIN_KW = ("ruin","ruined","abandoned","overgrown","derelict","decay","rubble","remains","fallen",
    "broken","wreck","collapsed","forgotten","lone","lonely","ambient","grave","tombstone","debris",
    "husk","crumbl","weathered","deserted")
LOOT_KW = ("dungeon","vault","treasure","crypt","tomb","catacomb","labyrinth","bunker","hoard",
    "reliquary","loot","mineshaft","lab","laboratory","sanctum","chamber","stash","cache","trove")
TOWN_KW = ("town","village","city","capital","castle","fortress","keep","mansion","stronghold",
    "citadel","palace","monastery","cathedral","metropolis","fort","port","harbor","harbour",
    "settlement","manor","estate","hall","tavern","outpost","house","cottage","hut","cabin")
BIG_KW  = ("mega","arena","colosseum","coliseum","colossal","giant","titan","behemoth","boss",
    "huge","massive","pyramid","temple","ziggurat","tower","spire","lighthouse")
DECO_KW = ("rock","boulder","pillar","stone_circle","tree","bush","oasis","camp","tent","shrine",
    "statue","obelisk","monolith","altar","well","fountain","ruins","wall","skull","fossil","pile")

def classify(sid):
    s = sid.split(":")[-1].lower()
    def has(kw): return any(k in s for k in kw)
    if has(LOOT_KW): return "LOOT"
    if has(BIG_KW):  return "BIG"
    if has(TOWN_KW): return "TOWN"
    if has(RUIN_KW): return "RUIN"
    if has(DECO_KW): return "DECO"
    return "DEFAULT"

def main():
    apply = "--apply" in sys.argv
    # 1) membership
    struct2set = {}
    for jp in sorted(glob.glob(os.path.join(MODS, "*.jar"))):
        try: z = zipfile.ZipFile(jp)
        except Exception: continue
        with z:
            for n in z.namelist():
                m = re.match(r"data/([^/]+)/worldgen/structure_set/(.+)\.json$", n)
                if not m: continue
                sid = f"{m.group(1)}:{m.group(2)}"
                try: d = json.loads(z.read(n))
                except Exception: continue
                for s in d.get("structures", []):
                    st = s.get("structure")
                    if st: struct2set.setdefault(st, sid)
    # 2) curated set tiers + the FULL structure list.
    # Source = UNION of (a) every structure defined in current jars (worldgen/structure/*.json) and
    # (b) the boot audit (Registries.STRUCTURE — the runtime registry, which also catches
    # code-registered structures + vanilla). The union means a jar-added structure mod is tiered on a
    # re-run even WITHOUT a fresh boot (the audit alone would miss it until the next boot).
    curated = json.load(open(RUINER_TIERS, encoding="utf-8"))
    structures = set()
    for jp in glob.glob(os.path.join(MODS, "*.jar")):
        try: z = zipfile.ZipFile(jp)
        except Exception: continue
        with z:
            for n in z.namelist():
                m = re.match(r"data/([^/]+)/worldgen/structure/(.+)\.json$", n)
                if m: structures.add(f"{m.group(1)}:{m.group(2)}")
    n_jar = len(structures)
    n_audit_only = 0
    if os.path.exists(AUDIT):
        for line in open(AUDIT, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#"): continue
            sid = line.split()[0]
            if sid not in structures: n_audit_only += 1
            structures.add(sid)
    structures = sorted(structures)
    print(f"[structure list] {n_jar} from jars + {n_audit_only} audit-only (code-registered/vanilla) = {len(structures)} total")

    out = dict(curated)            # keep curated set keys (harmless; single-structure sets rely on them)
    src = collections.Counter()    # provenance: inherited / curated-direct / orphan-classified
    orphans = []                   # (structure_id, assigned_tier, reason)
    for st in structures:
        if st in curated:
            src["direct"] += 1; continue                       # structure id already explicitly tiered
        setid = struct2set.get(st)
        if setid and setid in curated:
            out[st] = curated[setid]; src["inherited"] += 1     # inherit parent set's curated tier
        else:
            tier = classify(st)
            out[st] = tier; src["orphan"] += 1
            reason = "setless" if setid is None else f"set-untiered({setid.split(':')[-1]})"
            orphans.append((st, tier, reason))

    # ---- report ----
    print(f"=== ruiner tier expansion ===")
    print(f"structures (audit): {len(structures)}   curated set/struct keys: {len(curated)}")
    print(f"  direct (already keyed): {src['direct']}")
    print(f"  inherited from set tier: {src['inherited']}")
    print(f"  orphan (classified):     {src['orphan']}")
    print(f"  -> expanded map total keys: {len(out)}")
    final = collections.Counter()
    for st in structures: final[out.get(st, "UNTIERED")] += 1
    print("\n=== resulting per-STRUCTURE tier distribution ===")
    for t,c in final.most_common(): print(f"  {t:12} {c}")
    print(f"\n=== {len(orphans)} ORPHAN classifications (REVIEW THESE) ===")
    byt = collections.defaultdict(list)
    for st,t,r in orphans: byt[t].append((st,r))
    for t in ("TOWN","LOOT","BIG","RUIN","DECO","DEFAULT"):
        lst = byt.get(t,[])
        if not lst: continue
        print(f"\n  --- {t} ({len(lst)}) ---")
        for st,r in lst[:18]: print(f"    {st:55} [{r}]")
        if len(lst) > 18: print(f"    ... +{len(lst)-18} more")

    if apply:
        import shutil
        if os.path.exists(RUINER_TIERS): shutil.copy(RUINER_TIERS, RUINER_TIERS + ".presetexpand.bak")
        json.dump(out, open(RUINER_TIERS, "w", encoding="utf-8"), indent=1, sort_keys=True)
        print(f"\nAPPLIED -> {os.path.relpath(RUINER_TIERS, ROOT)} ({len(out)} keys; backup .presetexpand.bak)")
    else:
        print("\n(dry-run; re-run with --apply to write the expanded tier map)")

if __name__ == "__main__":
    main()
