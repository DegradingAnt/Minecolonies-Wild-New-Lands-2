import zipfile, json, os, shutil

DP = "config/paxi/datapacks/UltimateVibes-DataFixes"
BK = ".uvrun/jar-backups/[1.21.1-Neoforge] Hybrid Aquatic 1.5.5.jar"

# fresh datapack
if os.path.isdir(DP): shutil.rmtree(DP)
os.makedirs(DP)
with open(os.path.join(DP, "pack.mcmeta"), "w") as f:
    json.dump({"pack": {
        "pack_format": 48,
        "description": "UltimateVibes external data patches (reconstructed from pristine jars). Fixes worldgen/loot/tags/datamaps broken by the 2026-06-13 update. No jar editing."
    }}, f, indent=2)

def write(path, obj):
    full = os.path.join(DP, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as f:
        json.dump(obj, f, indent=2)

# ---- hybrid-aquatic: extract inline wrapper_function -> registered density_function + reference ----
z = zipfile.ZipFile(BK)
for name in ["deeper_deep_oceans", "trenches"]:
    mod_path = f"data/hybrid-aquatic/lithostitched/worldgen_modifier/{name}.json"
    orig = json.loads(z.read(mod_path))
    assert orig.get("type") == "lithostitched:wrap_density_function", orig.get("type")
    inline = orig["wrapper_function"]
    assert isinstance(inline, dict), "expected inline object in true original"
    # registered density function = the inline object
    write(f"data/hybrid-aquatic/worldgen/density_function/{name}.json", inline)
    # modifier now references it by id
    write(mod_path, {
        "type": "lithostitched:wrap_density_function",
        "target_function": orig["target_function"],
        "wrapper_function": f"hybrid-aquatic:{name}"
    })
    print(f"hybrid-aquatic: {name} -> registered df + reference modifier")
print("DataFixes datapack created with hybrid-aquatic fix")
