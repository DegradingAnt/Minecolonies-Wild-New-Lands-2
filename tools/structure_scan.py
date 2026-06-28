#!/usr/bin/env python3
"""structure_scan.py — PARALLEL (multiprocessing) structure-NBT scan, two outputs in one pass:

  (A) LOOTR audit (#79/#103): every container block type carrying a LootTable, bucketed
      vanilla-convertible vs CUSTOM (a coverage gap).
  (B) ENEMY structures (#175): structures that spawn hostile mobs = "enemy territory". Detected from
      mob_spawner / trial_spawner block entities in the NBT (their entity ids) AND from the structure
      JSON's spawn_overrides (monster category). Mapped template->structure by the path prefix
      data/<ns>/structure/<struct>/...  + the real structure-JSON ids.

Parallelized across CPU cores (one worker per jar). nbtlib required."""
import glob, zipfile, re, io, gzip, json, collections, sys, os
import nbtlib
from multiprocessing import Pool

VANILLA_LOOT_BLOCKS = {
    "minecraft:chest","minecraft:trapped_chest","minecraft:barrel","minecraft:suspicious_sand",
    "minecraft:suspicious_gravel","minecraft:decorated_pot","minecraft:hopper","minecraft:dispenser",
    "minecraft:dropper","minecraft:furnace","minecraft:blast_furnace","minecraft:smoker",
    "minecraft:brewing_stand","minecraft:chiseled_bookshelf",
}
VANILLA_LOOT_BLOCKS |= {f"minecraft:{c}_shulker_box" for c in
    ("white","orange","magenta","light_blue","yellow","lime","pink","gray","light_gray","cyan",
     "purple","blue","brown","green","red","black")} | {"minecraft:shulker_box"}
SPAWNER_BLOCKS = {"minecraft:spawner","minecraft:mob_spawner","minecraft:trial_spawner"}

def find_entity_ids(o, out):
    """recursively collect entity ids from a spawner BE nbt (SpawnData/SpawnPotentials/configs)."""
    if isinstance(o, dict):
        e = o.get("entity")
        if isinstance(e, dict) and "id" in e:
            out.add(str(e["id"]))
        for v in o.values(): find_entity_ids(v, out)
    elif isinstance(o, (list, tuple)):
        for v in o: find_entity_ids(v, out)

def parse_nbt(raw):
    try: data = gzip.decompress(raw)
    except Exception: data = raw
    has_loot = b"LootTable" in data
    has_spawn = (b"spawner" in data) or (b"Spawn" in data)
    if not has_loot and not has_spawn: return None
    try: root = nbtlib.File.parse(io.BytesIO(data))
    except Exception: return None
    return root

def scan_jar(jp):
    jar = os.path.basename(jp)
    by_block = collections.Counter()
    custom = collections.defaultdict(set)
    prefix_spawn = collections.defaultdict(set)   # struct-prefix -> {mob ids}
    struct_monster = set()                         # structure ids w/ monster spawn_overrides
    struct_ids = set()
    try: z = zipfile.ZipFile(jp)
    except Exception: return (jar, by_block, dict(custom), dict(prefix_spawn), struct_monster, struct_ids)
    with z:
        for n in z.namelist():
            # structure JSONs: collect ids + monster spawn_overrides
            m = re.match(r"data/([^/]+)/worldgen/structure/(.+)\.json$", n)
            if m:
                sid = f"{m.group(1)}:{m.group(2)}"; struct_ids.add(sid)
                try: d = json.loads(z.read(n))
                except Exception: d = None
                if isinstance(d, dict):
                    so = d.get("spawn_overrides") or {}
                    if isinstance(so, dict) and "monster" in so: struct_monster.add(sid)
                continue
            # structure NBT templates
            mm = re.match(r"data/([^/]+)/structure[s]?/(.+)\.nbt$", n)
            if not mm: continue
            ns = mm.group(1); rest = mm.group(2)
            prefix = f"{ns}:{rest.split('/')[0]}"   # heuristic structure id from path
            root = parse_nbt(z.read(n))
            if root is None: continue
            pal = root["palette"] if "palette" in root else (root["palettes"][0] if "palettes" in root else None)
            if pal is None or "blocks" not in root: continue
            def name_of(state):
                try: return str(pal[int(state)]["Name"])
                except Exception: return "?"
            for b in root["blocks"]:
                nv = b.get("nbt")
                if nv is None: continue
                bn = name_of(b.get("state", -1))
                if "LootTable" in nv:
                    by_block[bn] += 1
                    if bn not in VANILLA_LOOT_BLOCKS: custom[bn].add(f"{jar}:{n.split('/')[-1]}")
                if bn in SPAWNER_BLOCKS or "Spawner" in bn or "spawner" in bn:
                    ids = set(); find_entity_ids(nv, ids)
                    if ids: prefix_spawn[prefix] |= ids
    return (jar, by_block, dict(custom), dict(prefix_spawn), struct_monster, struct_ids)

def main():
    jars = sorted(glob.glob("mods/*.jar"))
    workers = min(20, os.cpu_count() or 4)
    print(f"scanning {len(jars)} jars on {workers} workers...", file=sys.stderr)
    by_block = collections.Counter(); custom = collections.defaultdict(set)
    prefix_spawn = collections.defaultdict(set); struct_monster = set(); all_structs = set()
    with Pool(workers) as p:
        for jar, bb, cu, ps, sm, si in p.imap_unordered(scan_jar, jars):
            by_block.update(bb)
            for k,v in cu.items(): custom[k] |= set(v)
            for k,v in ps.items(): prefix_spawn[k] |= set(v)
            struct_monster |= sm; all_structs |= si
    # ---- (A) LOOTR ----
    print("="*70); print("(A) LOOTR loot-container audit")
    for bn,c in by_block.most_common():
        print(f"  {c:6}  {'OK' if bn in VANILLA_LOOT_BLOCKS else '**CUSTOM**':10} {bn}")
    print(f"\n  CUSTOM (Lootr coverage-gap) container types: {len(custom)}")
    for bn in sorted(custom, key=lambda b:-by_block[b]):
        print(f"    {by_block[bn]:5}  {bn}   e.g. {sorted(custom[bn])[0]}")
    # ---- (B) ENEMY structures (#175) ----
    # spawner-prefix -> real structure ids (prefix may == structure id, or be a path subdir)
    enemy = set(struct_monster)
    spawner_mobs = collections.Counter()
    struct_spawners = collections.defaultdict(set)   # structure id -> {spawner mob ids}
    for pfx, mobs in prefix_spawn.items():
        for mob in mobs: spawner_mobs[mob]+=1
        if pfx in all_structs:
            enemy.add(pfx); struct_spawners[pfx] |= set(mobs)
        else:
            for sid in all_structs:
                if sid.split(':')[0]==pfx.split(':')[0] and sid.split(':')[1].split('/')[0]==pfx.split(':')[1]:
                    enemy.add(sid); struct_spawners[sid] |= set(mobs)
    print("\n"+"="*70); print("(B) ENEMY structures (#175 — spawn hostile mobs)")
    print(f"  via monster spawn_overrides: {len(struct_monster)}")
    print(f"  via spawner blocks (mapped): {len(enemy)-len(struct_monster & enemy)} extra")
    print(f"  TOTAL enemy structures: {len(enemy)} / {len(all_structs)}")
    print(f"\n  spawner mob ids seen (top 25):")
    for mob,c in spawner_mobs.most_common(25): print(f"    {c:4} {mob}")
    # write enemy list for #175 config-gen
    out = {"enemy_structures": sorted(enemy), "via_spawn_overrides": sorted(struct_monster),
           "spawner_mobs": dict(spawner_mobs), "total_structures": len(all_structs),
           "struct_spawners": {k: sorted(v) for k, v in struct_spawners.items()}}
    json.dump(out, open(".uvrun/enemy_structures.json","w"), indent=1)
    json.dump({"custom_loot_containers": {k:sorted(v) for k,v in custom.items()},
               "block_counts": dict(by_block)}, open(".uvrun/lootr_gaps.json","w"), indent=1)
    print("\nwrote .uvrun/enemy_structures.json + .uvrun/lootr_gaps.json")

if __name__ == "__main__":
    main()
