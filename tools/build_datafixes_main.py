import zipfile, json, os
BK = ".uvrun/jar-backups"
DP = "config/paxi/datapacks/UltimateVibes-DataFixes"

def wbytes(path, data):
    full = os.path.join(DP, path); os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="\n") as f: f.write(data)
def wjson(path, obj):
    full = os.path.join(DP, path); os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="\n") as f: json.dump(obj, f, indent=2)

# ---------- TRACKS ----------
TJ = zipfile.ZipFile(f"{BK}/tracks-neoforge-1.21.1-1.0.1.jar")
# 3 loot tables: text-replace Tracks: -> tracks: (override by path)
loot = ["data/tracks/loot_table/blocks/suspension_track.json",
        "data/tracks/loot_table/blocks/track_drive_wheel.json",
        "data/tracks/loot_table/blocks/track_mount.json"]
for p in loot:
    txt = TJ.read(p).decode("utf-8")
    assert "Tracks:" in txt
    wbytes(p, txt.replace("Tracks:", "tracks:"))
# 3 tags: fix values, write as MERGE (no replace) so other mods' entries survive
tags = ["data/create/tags/block/safe_nbt.json",
        "data/minecraft/tags/block/mineable/axe.json",
        "data/minecraft/tags/block/mineable/pickaxe.json"]
for p in tags:
    d = json.loads(TJ.read(p))
    d.pop("replace", None)  # force merge
    d["values"] = [(v.replace("Tracks:", "tracks:") if isinstance(v, str) else v) for v in d["values"]]
    wjson(p, d)
print(f"tracks: {len(loot)} loot (override) + {len(tags)} tags (merge) done")

# ---------- DRUIDS + ELEMENTAL: spell_engine:scroll -> spell_engine:spell_scroll (loot override) ----------
for jarname in ["druids-neoforge-1.1+1.21.1.jar", "elemental_wizards_rpg-neoforge-2.6.7+1.21.1.jar"]:
    Z = zipfile.ZipFile(f"{BK}/{jarname}"); n = 0
    for info in Z.infolist():
        p = info.filename
        if p.endswith(".json") and "loot_table" in p:
            txt = Z.read(p).decode("utf-8")
            if '"spell_engine:scroll"' in txt:
                wbytes(p, txt.replace('"spell_engine:scroll"', '"spell_engine:spell_scroll"')); n += 1
    print(f"{jarname.split('-')[0]}: {n} spell-scroll loot files (override) done")

# ---------- CEI: add reliquary:xp_still (merge) ----------
CJ = zipfile.ZipFile(f"{BK}/create-enchantment-industry-2.4.2.jar")
ceipath = "data/create_enchantment_industry/data_maps/fluid/unit/experience.json"
cei = json.loads(CJ.read(ceipath))
val = cei["values"]["reliquary:xp_juice_still"]
wjson(ceipath, {"values": {"reliquary:xp_still": val}})  # merge: adds correct key; stale key skipped harmlessly
print("CEI: reliquary:xp_still added (merge)")

# ---------- BEAUTIFY: rename name->value on minecraft:loot_table entries (override) ----------
BJ = zipfile.ZipFile(f"{BK}/beautify-neoforge-1.21.1-2.0.2.jar")
def fix_entry(e, c):
    if isinstance(e, dict):
        if e.get("type") == "minecraft:loot_table" and "name" in e:
            e["value"] = e.pop("name"); c[0] += 1
        for ch in e.get("children", []): fix_entry(ch, c)
    return e
nfiles = nentries = 0
for info in BJ.infolist():
    p = info.filename
    if p.endswith(".json") and "loot_table" in p:
        try: d = json.loads(BJ.read(p))
        except Exception: continue
        c = [0]
        for pool in (d.get("pools") or []):
            for e in pool.get("entries", []): fix_entry(e, c)
        if c[0] > 0:
            wjson(p, d); nfiles += 1; nentries += c[0]
print(f"beautify: {nentries} loot_table entries fixed across {nfiles} files (override)")
