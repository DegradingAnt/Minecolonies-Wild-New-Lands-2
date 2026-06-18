import zipfile, json, os, shutil

SRC_JAR = "mods/croptopia-neoforge-1.21.1-4.2.4.jar"
DP = "config/paxi/datapacks/UltimateVibes-CroptopiaBotanyPots"
PREFIX = "data/croptopia/recipe/botanypots/"

# fresh datapack dir
if os.path.isdir(DP): shutil.rmtree(DP)
os.makedirs(DP)

# pack.mcmeta (1.21.1 datapack pack_format = 48)
with open(os.path.join(DP, "pack.mcmeta"), "w") as f:
    json.dump({"pack": {
        "pack_format": 48,
        "description": "UltimateVibes patch: croptopia botany-pot crops migrated to botanypots 21.1.43 BasicCrop schema. Overrides 27 broken recipes. No jar editing."
    }}, f, indent=2)

def convert(old):
    seed = old["seed"]["item"]
    grow = old["growthTicks"]
    cats = old["categories"]
    assert len(cats) == 1, f"unexpected multi-category {cats}"
    soil = {"tag": f"botanypots:soil/{cats[0]}"}
    display = [{"type": "botanypots:simple",
                "block_state": {"Name": old["display"]["block"]}}]
    items = []
    for dr in old["drops"]:
        item = dr["output"]["item"]
        chance = dr.get("chance", 1.0)
        minr = dr.get("minRolls", 1)
        maxr = dr.get("maxRolls", 1)
        # base: guaranteed minRolls at the original chance
        items.append({"result": {"id": item, "count": minr}, "chance": chance})
        # extra rolls: each +1 at 0.5 to reproduce uniform [minRolls, maxRolls]
        for _ in range(maxr - minr):
            items.append({"result": {"id": item, "count": 1}, "chance": 0.5})
    new = {}
    if "bookshelf:load_conditions" in old:
        new["bookshelf:load_conditions"] = old["bookshelf:load_conditions"]
    new["type"] = "botanypots:crop"
    new["input"] = {"item": seed}
    new["soil"] = soil
    new["grow_time"] = grow
    new["display"] = display
    new["drops"] = [{"type": "botanypots:items", "items": items}]
    if "fabric:load_conditions" in old:
        new["fabric:load_conditions"] = old["fabric:load_conditions"]
    if "neoforge:conditions" in old:
        new["neoforge:conditions"] = old["neoforge:conditions"]
    return new

z = zipfile.ZipFile(SRC_JAR)
names = sorted(n for n in z.namelist() if n.startswith(PREFIX) and n.endswith(".json"))
outdir = os.path.join(DP, PREFIX)
os.makedirs(outdir)
count = 0
for n in names:
    old = json.loads(z.read(n))
    new = convert(old)
    with open(os.path.join(DP, n), "w") as f:
        json.dump(new, f, indent=2)
    count += 1
print(f"wrote {count} converted recipes to {DP}/{PREFIX}")
