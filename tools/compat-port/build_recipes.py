#!/usr/bin/env python3
"""UltimateVibes compat-port: malformed-recipe fixes (Paxi datapack overrides, no jar edits).
Each entry is a recipe the mod shipped in a format the 1.21.1 RecipeManager rejects. We override
it at higher (datapack) priority with a CORRECTED, content-preserving version where the intent is
clear, or a parse-valid no-op deletion (neoforge:false) only where the source is unfixable.

Writes to config/paxi/datapacks/UltimateVibes-CompatPort/ at BOTH recipe/ (1.21.1) and recipes/.
Re-run after a pack update if harvest_log.py reports new RecipeManager parse errors; add the new
recipe + its corrected form here (read the pristine recipe from the jar first to preserve intent)."""
import json, os

ROOT = r"C:/Users/linde/curseforge/minecraft/Instances/Ultimate vibes distant horizons version"
OUT  = os.path.join(ROOT, "config/paxi/datapacks/UltimateVibes-Compat")

# --- helpers for the two recurring shapes ---
def fd_cut(ingredients, results, tool_tag="c:tools/knives", conditions=None):
    """farmersdelight:cutting -- 1.21.1 wants result entries as {"item":{"id":..,"count":..}}."""
    r = {"type": "farmersdelight:cutting",
         "ingredients": ingredients,
         "tool": [{"tag": tool_tag}],
         "result": [{"item": {"id": i, "count": c}} for i, c in results]}
    if conditions:
        r["neoforge:conditions"] = conditions
    return r

def jeb_breed(modid, entity, tamed=False):
    """justenoughbreeding:breeding -- inputs must be real ingredients, not {"meat":"true"}.
    Wolves (vanilla + modded variants) breed with the minecraft:wolf_food item tag."""
    r = {"neoforge:conditions": [{"type": "neoforge:mod_loaded", "modid": modid}],
         "type": "justenoughbreeding:breeding", "mod": modid,
         "input_entity": entity, "inputs": [{"tag": "minecraft:wolf_food"}]}
    if tamed:
        r["tamed"] = True
    return r

DELETE = {"neoforge:conditions": [{"type": "neoforge:false"}],
          "type": "minecraft:crafting_shapeless", "category": "misc",
          "ingredients": [{"item": "minecraft:stone"}],
          "result": {"id": "minecraft:stone", "count": 1}}

CL = [{"type": "neoforge:mod_loaded", "modid": "culturaldelights"}]

# recipe-id -> corrected recipe object
RECIPES = {
    # --- farmersdelight:cutting: old flat result -> nested {"item":{...}} (5 culturaldelights + endersdelight)
    "culturaldelights:cutting/cut_eggplant":  fd_cut([{"tag": "c:eggplants"}],  [("culturaldelights:cut_eggplant", 2)], conditions=CL),
    "culturaldelights:cutting/cut_pickle":    fd_cut([{"tag": "c:pickles"}],    [("culturaldelights:cut_pickle", 2)], conditions=CL),
    "culturaldelights:cutting/cut_avocado":   fd_cut([{"tag": "c:avocados"}],   [("culturaldelights:cut_avocado", 2), ("culturaldelights:avocado_pit", 1)], conditions=CL),
    "culturaldelights:cutting/tortilla_chips":fd_cut([{"tag": "c:tortillas"}],  [("culturaldelights:tortilla_chips", 3)], conditions=CL),
    "culturaldelights:cutting/cut_cucumber":  fd_cut([{"tag": "c:cucumbers"}],  [("culturaldelights:cut_cucumber", 2)], conditions=CL),
    "endersdelight:chorus_pie_slice":         fd_cut([{"item": "endersdelight:chorus_pie"}], [("endersdelight:chorus_pie_slice", 4)]),  # was result:[{"id":..}] + forge:tools/knives

    # --- justenoughbreeding: {"meat":"true"} -> {"tag":"minecraft:wolf_food"} (3 modded wolves)
    "justenoughbreeding:breeding/quark/shiba":                jeb_breed("quark", "quark:shiba", tamed=True),
    "justenoughbreeding:breeding/pet_cemetery/skeleton_wolf": jeb_breed("pet_cemetery", "pet_cemetery:skeleton_wolf"),
    "justenoughbreeding:breeding/pet_cemetery/zombie_wolf":   jeb_breed("pet_cemetery", "pet_cemetery:zombie_wolf"),

    # --- createaddition JEED integration: effect must be a string, not {"id":..}
    "createaddition:compat/jeed/shocking": {
        "type": "jeed:effect_provider", "effect": "createaddition:shocking",
        "providers": [{"item": "createaddition:tesla_coil"}],
        "neoforge:conditions": [{"type": "neoforge:mod_loaded", "modid": "jeed"}]},

    # --- supplementaries: pattern referenced 1/2 but key defines C/N -> fix pattern to C/N
    "supplementaries:candle_holders/candle_holder_cupric": {
        "neoforge:conditions": [
            {"type": "supplementaries:flag", "flag": "candle_holder"},
            {"type": "neoforge:mod_loaded", "modid": "buzzier_bees"},
            {"type": "neoforge:mod_loaded", "modid": "caverns_and_chasms"}],
        "type": "minecraft:crafting_shaped", "pattern": ["C", "N"],
        "key": {"C": {"item": "buzzier_bees:cupric_candle"}, "N": {"tag": "c:ingots/iron"}},
        "result": {"id": "supplementaries:candle_holder_cupric", "count": 1}},

    # --- hole_filler: typo "iteme" -> "item"
    "hole_filler_mod:throwable_hole_filler_water": {
        "type": "minecraft:crafting_shapeless",
        "ingredients": [{"item": "hole_filler_mod:filler_core"},
                        {"item": "minecraft:water_bucket"}, {"item": "minecraft:water_bucket"}],
        "result": {"id": "hole_filler_mod:throwable_hole_filler_water", "count": 1}},

    # --- dramaticdoors: pale_oak tall/short are RUNTIME-GENERATED & malformed (DD x VanillaBackport
    #     compat bug). No jar template exists to author a correct one -> delete the 2 broken variants.
    #     Normal pale-oak doors still craft (VanillaBackport). Only the tall/short variant is dropped.
    "dramaticdoors:short_pale_oak_door": DELETE,
    "dramaticdoors:tall_pale_oak_door":  DELETE,
}

def write_both(rid, obj):
    ns, sub = rid.split(":", 1)
    js = json.dumps(obj, indent=2)
    for d in ("recipe", "recipes"):
        fp = os.path.join(OUT, "data", ns, d, sub + ".json")
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        open(fp, "w").write(js)

fixes = dels = 0
for rid, obj in RECIPES.items():
    write_both(rid, obj)
    if obj is DELETE:
        dels += 1; print(f"  0 DELETE   {rid}")
    else:
        fixes += 1; print(f"  ~ FIX      {rid}")

# validate
bad = 0
for rid, obj in RECIPES.items():
    try:
        json.loads(json.dumps(obj))
    except Exception as ex:
        bad += 1; print("  INVALID:", rid, ex)
print(f"\n=== {fixes} fixes + {dels} deletions, written to recipe/ and recipes/  ({'ALL VALID' if not bad else str(bad)+' BAD'}) ===")
