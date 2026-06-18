import zipfile, json, os, re
BK = ".uvrun/jar-backups"
DP = "config/paxi/datapacks/UltimateVibes-DataFixes"
SJ = zipfile.ZipFile(f"{BK}/sablephysicscompat-1.3.0.jar")
def wjson(path, obj):
    full = os.path.join(DP, path); os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="\n") as f: json.dump(obj, f, indent=2)

# 1) bouncy.json tag: strip trailing comma, write clean (override, keep replace:false)
raw = SJ.read("data/sable/tags/block/bouncy.json").decode("utf-8")
cleaned = re.sub(r',(\s*[}\]])', r'\1', raw)   # remove trailing commas before } or ]
d = json.loads(cleaned)                          # validate
wjson("data/sable/tags/block/bouncy.json", d)
print(f"sable bouncy.json: trailing comma stripped, {len(d['values'])} values, parses OK")

# 2) float.json array -> single-object files (Sable 2.0 format)
arr = json.loads(SJ.read("data/sable/physics_block_properties/float.json"))
assert isinstance(arr, list)
# override float.json itself with the first entry (now a single object)
wjson("data/sable/physics_block_properties/float.json", arr[0])
# remaining entries -> new single-object files
for i, obj in enumerate(arr[1:], start=1):
    wjson(f"data/sable/physics_block_properties/float_aero_{i:02d}.json", obj)
print(f"sable float.json: split {len(arr)} entries -> float.json + {len(arr)-1} float_aero_NN files")
