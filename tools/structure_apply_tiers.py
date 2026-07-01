import json, collections, sys, copy
ROOT = "C:/Users/linde/curseforge/minecraft/Instances/Ultimate vibes distant horizons version"
DRY = "--write" not in sys.argv

CATS = [
 ("Small Props & Micro-deco", ["log_pile","_pile","bench","cart","duck","swing","pump","dome","crate","barrel","scarecrow","snowman","snow_pile","flotsam","bee_","lamp","lantern","sign","pot_","pail","stool","picnic"]),
 ("Graves & Undead Sites", ["grave","graveyard","mausoleum","skull","fossil","bone","ossuary","sarcophagus"]),
 ("Bridges & Crossings", ["bridge","aqueduct","viaduct","crossing","overpass"]),
 ("Villages & Towns", ["village","town","hamlet","settlement","capital","_city","tavern","inn"]),
 ("Player-style Dwellings", ["house","home","cottage","farm","hut","cabin","homestead","manor","estate","villa","barn","windmill","shack","lodge","dwelling"]),
 ("Dungeons & Lairs", ["dungeon","crypt","tomb","catacomb","lair","den","vault","cellar","prison","jail","hideout","hideaway"]),
 ("Towers & Spires", ["tower","spire","turret","watchtower","obelisk","minaret"]),
 ("Temples, Pyramids & Religious", ["temple","shrine","altar","sanctuary","monastery","church","pagoda","chapel","cathedral","monk","priest","pyramid","ziggurat","monolith","archway","acropolis","mystical"]),
 ("Fortresses, Castles & Forts", ["castle","fortress","fort","keep","citadel","stronghold","bastion","barracks","garrison","factory"]),
 ("Ruins & Remnants", ["ruin","abandoned","remnant","rubble","collapsed","broken","derelict","wreck","decay","scraps","endscraps"]),
 ("Camps, Outposts & Markets", ["camp","outpost","encampment","tent","market","trading","caravan","waystation"]),
 ("Boss Arenas & Raids", ["boss","arena","colosseum","raid","pillager","illager","mansion","summon","ritual","illusioner","_nest"]),
 ("Nether structures", ["nether","crimson","warped","soul","fungus","blaze","piglin"]),
 ("End & Astral", ["end_","ender","_end","void","obsidian","chorus","shulker","dragon","astral","meteor","starlight","star_","spiral"]),
 ("Aquatic & Coastal", ["dock","harbor","harbour","port","pier","fishing","coastal","beach","underwater","ocean","ship","boat","lighthouse","shipwreck","reef","mermaid","pirate","oasis"]),
 ("Underground & Mines", ["cave","mine","mineshaft","underground","cavern","grotto","tunnel","quarry"]),
 ("Skeletons & Mob Spawns", ["skeleton","spawn","zombie","undead"]),
 ("Nature & Decoration", ["tree","bush","rock","boulder","well","statue","fountain","pillar","monument","garden","grove","_stone","crystal","mushroom","flower","_ice","geode","amethyst","_log","logs","floating_island"]),
]
# author's eyeballed weights (screenshot 2026-06-30). multiplier on spacing.  cut -> disable.
WEIGHT = {
 "Small Props & Micro-deco": 2, "Graves & Undead Sites": 8, "Bridges & Crossings": 2,
 "Villages & Towns": 4, "Player-style Dwellings": 2, "Dungeons & Lairs": 4,
 "Towers & Spires": 8, "Temples, Pyramids & Religious": 4, "Fortresses, Castles & Forts": 8,
 "Ruins & Remnants": 1, "Camps, Outposts & Markets": 2, "Boss Arenas & Raids": 8,
 "Nether structures": 4, "End & Astral": 4, "Aquatic & Coastal": 2,
 "Underground & Mines": 4, "Skeletons & Mob Spawns": 4, "Nature & Decoration": 2,
 "Misc / Uncategorized": 1,
}
# audit gives mem (member structures) for better categorization
audit = {e["set"]: e for e in (json.loads(l) for l in open(ROOT + "/.uvrun/structure_audit.jsonl") if l.strip())}

# surgical per-set overrides (user verbal 2026-06-30): floating very rare, junk cut
SURGICAL_CUT = {"structuresplus:random_blocks"}
SURGICAL_FLOAT8 = {"expanded_combat:gas_cloud_structure"}  # +any set whose mem hits floating_island

def cat(name):
    e = audit.get(name)
    mem = e.get("mem", []) if e else []
    blob = (name + " " + " ".join(mem)).lower()
    for label, kws in CATS:
        if any(kw in blob for kw in kws):
            return label
    return "Misc / Uncategorized"

cfg = json.load(open(ROOT + "/config/structurify.json"))
sets = cfg["structure_sets"]

per = collections.defaultdict(lambda: {"n":0, "old":0, "new":0, "cut":0})
cuts, floats = [], []
MAXSEP = 0
for s in sets:
    name = s["name"]
    c = cat(name)
    mult = WEIGHT[c]
    old_sp = s.get("spacing", 32)
    old_sep = s.get("separation", 8)
    # floating override: named floating-island sets + the audit's own float-flag (user: ALL floating super-rare)
    ae = audit.get(name)
    is_float = (name in SURGICAL_FLOAT8
                or (ae and any("floating_island" in m for m in ae.get("mem", [])))
                or (ae and ae.get("float")))
    if name in SURGICAL_CUT:
        s["is_disabled"] = True; per[c]["cut"] += 1; cuts.append(name); continue
    if is_float:
        mult = max(mult, 8); floats.append(name)
    new_sp = max(1, round(old_sp * mult))
    # scale separation with the ratio but keep it strictly < spacing
    new_sep = min(new_sp - 1, max(old_sep, round(old_sep * mult)))
    s["spacing"] = new_sp
    s["separation"] = new_sep
    s["override_global_spacing_and_separation_modifier"] = True
    MAXSEP = max(MAXSEP, new_sep)
    per[c]["n"] += 1; per[c]["old"] += old_sp; per[c]["new"] += new_sp

print("MODE:", "DRY-RUN (no write)" if DRY else "WRITE")
print("sets total: %d   max separation after: %d" % (len(sets), MAXSEP))
print("=" * 78)
print("%-32s  n    avg_sp: old -> new   (x weight)" % "CATEGORY")
for c, _ in CATS + [("Misc / Uncategorized", [])]:
    d = per[c]
    if not d["n"] and not d["cut"]: continue
    ao = d["old"]//max(1,d["n"]); an = d["new"]//max(1,d["n"])
    cutnote = ("  +%d CUT" % d["cut"]) if d["cut"] else ""
    print("%-32s %3d   %4d -> %4d         (x%d)%s" % (c, d["n"], ao, an, WEIGHT[c], cutnote))
print("=" * 78)
print("SURGICAL cut (%d): %s" % (len(cuts), ", ".join(cuts)))
print("SURGICAL float->x8 (%d): %s" % (len(floats), ", ".join(floats)))

if not DRY:
    import shutil
    shutil.copy(ROOT + "/config/structurify.json", ROOT + "/config/structurify.json.pretiers.bak")
    json.dump(cfg, open(ROOT + "/config/structurify.json", "w"), indent=2)
    print("\nWROTE config/structurify.json (backup: structurify.json.pretiers.bak)")
