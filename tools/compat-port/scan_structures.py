#!/usr/bin/env python3
"""Inventory worldgen structures + structure_sets across all mod jars.
- structure_set: placement spacing/separation/salt (controls RARITY/spacing) -> for 'create rare'
- structure: start height / terrain_adaptation -> spot FLYING (sky) structures
"""
import json, os, zipfile, collections

ROOT = r"C:/Users/linde/curseforge/minecraft/Instances/Ultimate vibes distant horizons version"
MODS = os.path.join(ROOT, "mods")

sets = []      # (ns, name, jar, placement_type, spacing, separation, salt)
structs = []   # (ns, name, jar, start_height_repr, terrain_adaptation, step)
ns_set = collections.Counter()

def hrepr(sh):
    if sh is None: return "-"
    if isinstance(sh, (int, float)): return str(sh)
    if isinstance(sh, dict):
        t = sh.get("type", "?")
        if "value" in sh: return f"{t}:{sh['value']}"
        return t
    return str(sh)[:40]

for jar in sorted(os.listdir(MODS)):
    if not jar.endswith(".jar"): continue
    try:
        with zipfile.ZipFile(os.path.join(MODS, jar)) as z:
            for n in z.namelist():
                parts = n.split("/")
                # data/<ns>/worldgen/structure_set/<name>.json
                if len(parts) >= 5 and parts[0] == "data" and parts[2] == "worldgen" and n.endswith(".json"):
                    kind = parts[3]
                    ns = parts[1]
                    name = "/".join(parts[4:])[:-5]
                    if kind == "structure_set":
                        try:
                            d = json.loads(z.read(n))
                            pl = d.get("placement", {})
                            sets.append((ns, name, jar, pl.get("type", "?"),
                                         pl.get("spacing"), pl.get("separation"), pl.get("salt")))
                            ns_set[ns] += 1
                        except Exception: pass
                    elif kind == "structure":
                        try:
                            d = json.loads(z.read(n))
                            structs.append((ns, name, jar, hrepr(d.get("start_height")),
                                            d.get("terrain_adaptation", "-"), d.get("step", "-")))
                        except Exception: pass
    except Exception: pass

print("===== structure_set NAMESPACES (count) =====")
for ns, c in ns_set.most_common():
    print(f"  {c:3d}  {ns}")

print("\n===== CREATE-family structure_sets (rarity targets) =====")
for s in sorted(sets):
    if "create" in s[0] or "create" in s[1].lower():
        print(f"  {s[0]}:{s[1]}  [{s[3]} spacing={s[4]} sep={s[5]} salt={s[6]}]  <{s[2]}>")

print("\n===== candidate FLYING/SKY structures (absolute or high start_height, terrain_adaptation none) =====")
for ns, name, jar, sh, ta, step in sorted(structs):
    flying = False
    if "absolute" in sh.lower(): flying = True
    if ta in ("none",) and ("absolute" in sh.lower()): flying = True
    # numeric high y
    try:
        if sh.replace("-", "").isdigit() and int(sh) >= 120: flying = True
    except Exception: pass
    if "sky" in name.lower() or "float" in name.lower() or "fly" in name.lower() or "aerial" in name.lower() or "cloud" in name.lower() or "airship" in name.lower() or "balloon" in name.lower():
        flying = True
    if flying:
        print(f"  {ns}:{name}  start_height={sh} terrain_adaptation={ta} step={step}  <{jar}>")

print(f"\nTOTAL structure_sets={len(sets)}  structures={len(structs)}")
json.dump({"sets": sets, "structs": structs}, open(os.path.join(ROOT, ".uvrun/compat-port/structures.json"), "w"))
