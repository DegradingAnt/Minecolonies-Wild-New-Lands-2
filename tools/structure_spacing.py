#!/usr/bin/env python3
"""Structure spawn + spacing pass. Re-scans jars for structures (biomes -> can-it-spawn)
and structure_sets (spacing/separation/salt -> crowding + overlap risk).
NOTE: SparseStructures spreadFactor=4 multiplies all spacing/separation at runtime (effective = raw x4),
and idBasedSalt=true re-hashes each set's salt from its id (mitigates raw salt collisions)."""
import json, os, zipfile, collections

ROOT = r"C:/Users/linde/curseforge/minecraft/Instances/Ultimate vibes distant horizons version"
MODS = os.path.join(ROOT, "mods")
SPREAD = 4  # sparsestructures spreadFactor

sets = []      # (id, type, spacing, sep, salt, nstructs, jar)
structs = {}   # id -> (biomes_repr, has_biomes, jar)

def biome_state(b):
    if b is None: return ("<none>", False)
    if isinstance(b, str): return (b[:40], True)            # "#tag" or "biome"
    if isinstance(b, list): return (f"list[{len(b)}]", len(b) > 0)
    if isinstance(b, dict): return (str(b)[:40], True)
    return (str(b)[:30], True)

for jar in sorted(os.listdir(MODS)):
    if not jar.endswith(".jar"): continue
    try:
        with zipfile.ZipFile(os.path.join(MODS, jar)) as z:
            for n in z.namelist():
                p = n.split("/")
                if len(p) >= 5 and p[0] == "data" and p[2] == "worldgen" and n.endswith(".json"):
                    sid = f"{p[1]}:{'/'.join(p[4:])[:-5]}"
                    if p[3] == "structure":
                        try:
                            d = json.loads(z.read(n)); br, ok = biome_state(d.get("biomes"))
                            structs[sid] = (br, ok, jar)
                        except Exception: pass
                    elif p[3] == "structure_set":
                        try:
                            d = json.loads(z.read(n)); pl = d.get("placement", {})
                            sets.append((sid, pl.get("type", "?"), pl.get("spacing"), pl.get("separation"),
                                         pl.get("salt"), len(d.get("structures", [])), jar))
                        except Exception: pass
    except Exception: pass

print("================ 1. STRUCTURES THAT CANNOT SPAWN (biomes empty/missing) ================")
dead = [(sid, br, jar) for sid, (br, ok, jar) in structs.items() if not ok]
for sid, br, jar in sorted(dead):
    note = "  (intentionally emptied by UltimateVibes)" if any(k in sid for k in ("gas_cloud", "aether")) else ""
    print(f"   {sid:48s} biomes={br}{note}  <{jar[:30]}>")
print(f"   -> {len(dead)} of {len(structs)} structures have no spawn biome")

print("\n================ 2. SALT COLLISIONS (sets sharing a salt -> overlap risk; mitigated by idBasedSalt) ================")
bysalt = collections.defaultdict(list)
for s in sets:
    if s[4] is not None and s[1].endswith("random_spread") or (s[4] is not None):
        bysalt[s[4]].append(s[0])
coll = {k: v for k, v in bysalt.items() if len(v) > 1}
for salt, ids in sorted(coll.items(), key=lambda x: -len(x[1])):
    print(f"   salt {salt}: {len(ids)} sets -> {', '.join(ids)[:140]}")
print(f"   -> {len(coll)} colliding salt-groups (SparseStructures idBasedSalt=true re-hashes these at runtime -> usually OK)")

print("\n================ 3. CROWDING: densest structure_sets (smallest EFFECTIVE spacing = raw x4) ================")
sp = [s for s in sets if isinstance(s[2], (int, float))]
for sid, typ, spc, sep, salt, ns, jar in sorted(sp, key=lambda x: x[2])[:25]:
    eff_sp = spc * SPREAD; eff_sep = (sep or 0) * SPREAD
    print(f"   eff_spacing={eff_sp:<5} eff_sep={eff_sep:<5} (raw {spc}/{sep})  {ns} struct(s)  {sid[:42]}  <{jar[:24]}>")
print(f"\n   total structure_sets={len(sets)}  (with numeric spacing={len(sp)})  structures={len(structs)}")
print(f"   median raw spacing={sorted(s[2] for s in sp)[len(sp)//2]} -> effective ~{sorted(s[2] for s in sp)[len(sp)//2]*SPREAD}")
