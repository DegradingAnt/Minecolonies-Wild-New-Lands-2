import json, collections
ROOT = "C:/Users/linde/curseforge/minecraft/Instances/Ultimate vibes distant horizons version"
audit = [json.loads(l) for l in open(ROOT + "/.uvrun/structure_audit.jsonl") if l.strip()]
try:
    enemy = set(json.load(open(ROOT + "/.uvrun/enemy_structures.json"))["enemy_structures"])
except Exception:
    enemy = set()

CATS = [
 ("Small Props & Micro-deco", "", ["log_pile","_pile","bench","cart","duck","swing","pump","dome","crate","barrel","scarecrow","snowman","snow_pile","flotsam","bee_","lamp","lantern","sign","pot_","pail","stool","picnic"]),
 ("Graves & Undead Sites", "", ["grave","graveyard","mausoleum","skull","fossil","bone","ossuary","sarcophagus"]),
 ("Bridges & Crossings", "", ["bridge","aqueduct","viaduct","crossing","overpass"]),
 ("Villages & Towns", "", ["village","town","hamlet","settlement","capital","_city","tavern","inn"]),
 ("Player-style Dwellings", "", ["house","home","cottage","farm","hut","cabin","homestead","manor","estate","villa","barn","windmill","shack","lodge","dwelling"]),
 ("Dungeons & Lairs", "", ["dungeon","crypt","tomb","catacomb","lair","den","vault","cellar","prison","jail","hideout","hideaway"]),
 ("Towers & Spires", "", ["tower","spire","turret","watchtower","obelisk","minaret"]),
 ("Temples, Pyramids & Religious", "", ["temple","shrine","altar","sanctuary","monastery","church","pagoda","chapel","cathedral","monk","priest","pyramid","ziggurat","monolith","archway","acropolis","mystical"]),
 ("Fortresses, Castles & Forts", "", ["castle","fortress","fort","keep","citadel","stronghold","bastion","barracks","garrison","factory"]),
 ("Ruins & Remnants", "", ["ruin","abandoned","remnant","rubble","collapsed","broken","derelict","wreck","decay","scraps","endscraps"]),
 ("Camps, Outposts & Markets", "", ["camp","outpost","encampment","tent","market","trading","caravan","waystation"]),
 ("Boss Arenas & Raids", "", ["boss","arena","colosseum","raid","pillager","illager","mansion","summon","ritual","illusioner","_nest"]),
 ("Nether structures", "", ["nether","crimson","warped","soul","fungus","blaze","piglin"]),
 ("End & Astral", "", ["end_","ender","_end","void","obsidian","chorus","shulker","dragon","astral","meteor","starlight","star_","spiral"]),
 ("Aquatic & Coastal", "", ["dock","harbor","harbour","port","pier","fishing","coastal","beach","underwater","ocean","ship","boat","lighthouse","shipwreck","reef","mermaid","pirate","oasis"]),
 ("Underground & Mines", "", ["cave","mine","mineshaft","underground","cavern","grotto","tunnel","quarry"]),
 ("Skeletons & Mob Spawns", "", ["skeleton","spawn","zombie","undead"]),
 ("Nature & Decoration", "", ["tree","bush","rock","boulder","well","statue","fountain","pillar","monument","garden","grove","_stone","crystal","mushroom","flower","_ice","geode","amethyst","_log","logs","floating_island"]),
]

def cat(e):
    blob = (e["set"] + " " + " ".join(e.get("mem", []))).lower()
    for label, _, kws in CATS:
        if any(kw in blob for kw in kws):
            return label
    return "Misc / Uncategorized"

misc = [e for e in audit if cat(e) == "Misc / Uncategorized"]
# group by namespace for readability
byns = collections.defaultdict(list)
for e in misc:
    byns[e["ns"]].append(e)

print("MISC / UNCATEGORIZED — %d structure sets across %d mods" % (len(misc), len(byns)))
print("=" * 90)
for ns in sorted(byns, key=lambda n: -len(byns[n])):
    es = byns[ns]
    print("\n### %s  (%d)" % (ns, len(es)))
    for e in sorted(es, key=lambda e: (e.get("sp") if isinstance(e.get("sp"), (int,float)) else 999)):
        setname = e["set"].split(":", 1)[1]
        sp = e.get("sp")
        mem = ", ".join(m.replace("_"," ") for m in e.get("mem", [])[:5])
        flags = []
        if e.get("loot"): flags.append("loot")
        if e.get("float"): flags.append("FLOAT")
        if e["set"] in enemy: flags.append("combat")
        fl = (" [" + ",".join(flags) + "]") if flags else ""
        print("  - %-34s sp=%-4s  %s%s" % (setname, sp, mem, fl))
