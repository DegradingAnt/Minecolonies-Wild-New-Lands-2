#!/usr/bin/env python3
"""build_difficulty_tags.py — #175: register enemy structures into dungeon_difficulty's structure tags.

dungeon_difficulty reads structure tags -> difficulty zones (config already wired):
  overworld: #level_1/2/3 -> dungeon difficulty 1/2/3   nether: #level_4   end: #level_5/6
  #bosses -> 'heroic'
User design: grade by size + intended difficulty; bosses own tier; Cataclysm = endgame.
  bosses(heroic) = name(boss/arena/lair/throne/colosseum/sanctum) OR miniboss spawner
                   (ravager/evoker/warden/elder_guardian) OR Cataclysm boss-arena.
  else by dimension(inferred from spawner mobs + name) + size(ruiner tier):
    overworld: MASSIVE/FLOAT or cataclysm -> level_3 ; BIG/TOWN -> level_2 ; else level_1
    nether -> level_4 ;  end: BIG/MASSIVE -> level_6 else level_5
Additive tags (keep the mod's vanilla defaults). Output -> WNL-Difficulty Paxi datapack.
Reads .uvrun/enemy_structures.json (needs struct_spawners) + config/wnl_pathways/structure_tiers.json."""
import json, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EN = os.path.join(ROOT, ".uvrun", "enemy_structures.json")
TIERS = os.path.join(ROOT, "config", "wnl_pathways", "structure_tiers.json")
DP = os.path.join(ROOT, "config", "paxi", "datapacks", "WNL-Difficulty")

MINIBOSS = {"minecraft:ravager","minecraft:evoker","minecraft:warden","minecraft:elder_guardian"}
NETHER_MOBS = {"minecraft:blaze","minecraft:wither_skeleton","minecraft:piglin_brute","minecraft:magma_cube",
               "minecraft:hoglin","minecraft:ghast","minecraft:piglin","minecraft:zoglin","minecraft:zombified_piglin"}
END_MOBS = {"minecraft:shulker","minecraft:endermite","minecraft:enderman"}
BOSS_NAME = ("boss","arena","colosseum","coliseum","lair","throne","sanctum","leviathan","monstrosity",
             "harbinger","maledictus","ignis","guardian_arena")
NETHER_NAME = ("nether","crimson","warped","piglin","blaze","fortress","bastion","fungus","soul","fiery")
END_NAME = ("end_","ender","shulker","chorus","outer_end","_end","void")

def size_tier(t):
    if t in ("MASSIVE","FLOAT"): return "big"
    if t in ("BIG","TOWN"): return "mid"
    return "small"

def main():
    en = json.load(open(EN, encoding="utf-8"))
    enemies = en["enemy_structures"]
    spawners = en.get("struct_spawners", {})
    tiers = json.load(open(TIERS, encoding="utf-8"))
    tagsets = collections.defaultdict(list)   # tag name -> [structure ids]
    report = collections.Counter()
    for sid in enemies:
        ns = sid.split(":")[0]; name = sid.split(":",1)[1].lower()
        tier = tiers.get(sid, "DEFAULT")
        mobs = set(spawners.get(sid, []))
        is_cata = (ns == "cataclysm")
        # --- BOSS (heroic) ---
        if (any(k in name for k in BOSS_NAME) or (mobs & MINIBOSS)
                or (is_cata and any(k in name for k in ("arena","boss","ignis","monstrosity","leviathan","harbinger","ancient_remnant","maledictus")))):
            tagsets["bosses"].append(sid); report["bosses"] += 1; continue
        # --- dimension ---
        if (mobs & END_MOBS) or any(k in name for k in END_NAME) or ns in ("eternal_starlight","echoes_of_the_end__structures_"):
            dim = "end"
        elif (mobs & NETHER_MOBS) or any(k in name for k in NETHER_NAME) or ns in ("eternalnether","formationsnether"):
            dim = "nether"
        else:
            dim = "overworld"
        sz = size_tier(tier)
        if dim == "nether":
            tag = "level_4"
        elif dim == "end":
            tag = "level_6" if sz in ("big","mid") else "level_5"
        else:  # overworld
            if sz == "big" or is_cata: tag = "level_3"
            elif sz == "mid": tag = "level_2"
            else: tag = "level_1"
        tagsets[tag].append(sid); report[tag] += 1

    # write additive structure tags to the WNL-Difficulty datapack
    os.makedirs(DP, exist_ok=True)
    json.dump({"pack": {"pack_format": 48, "description": "WNL difficulty tuning: registers modded enemy structures into dungeon_difficulty level/boss tags (#175). Graded by size + Cataclysm=endgame + miniboss=heroic. Additive."}},
              open(os.path.join(DP, "pack.mcmeta"), "w"), indent=2)
    tdir = os.path.join(DP, "data", "dungeon_difficulty", "tags", "worldgen", "structure")
    os.makedirs(tdir, exist_ok=True)
    for tag, ids in tagsets.items():
        json.dump({"replace": False, "values": sorted(set(ids))},
                  open(os.path.join(tdir, f"{tag}.json"), "w"), indent=1)
    print("=== #175 difficulty tag assignment (additive; mod vanilla defaults kept) ===")
    for tag in ("level_1","level_2","level_3","level_4","level_5","level_6","bosses"):
        print(f"  {tag:9} {report.get(tag,0)}")
    print(f"  TOTAL graded: {sum(report.values())} / {len(enemies)} enemy structures")
    print(f"  -> {os.path.relpath(DP, ROOT)}")
    # sample of bosses for review
    print("\n  BOSS-tier sample:", sorted(tagsets.get("bosses",[]))[:18])

if __name__ == "__main__":
    main()
