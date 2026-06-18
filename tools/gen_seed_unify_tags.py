#!/usr/bin/env python3
"""Seeds Phase B, approach A: unify duplicate plantable seeds to the Croptopia seed.
Writes c:seeds/<crop> tag files (full variant set) into UltimateVibes-Compat so AU
unifies them (mod_priorities [minecraft, croptopia] -> croptopia seed canonical).
Light touch: JEI/recipe unification only; each mod's farm still grows its own crop
(no loot_unification). Tree-seeds (cherry/lemon/date) deliberately EXCLUDED (different
plant/growth). roasted_sunflower (a food) handled in the prepared-food pass.
"""
import os, json

DP = os.path.abspath(os.path.join(os.path.dirname(__file__), "..",
        "config", "paxi", "datapacks", "UltimateVibes-Compat", "data", "c", "tags", "item", "seeds"))
os.makedirs(DP, exist_ok=True)

SEEDS = {
    "asparagus":  ["croptopia:asparagus_seed", "expandeddelight:asparagus_seeds"],
    "eggplant":   ["croptopia:eggplant_seed", "culturaldelights:eggplant_seeds"],
    "tomato":     ["croptopia:tomato_seed", "farm_and_charm:tomato_seeds", "farmersdelight:tomato_seeds"],
    "barley":     ["croptopia:barley_seed", "farm_and_charm:barley_seeds"],
    "cucumber":   ["croptopia:cucumber_seed", "culturaldelights:cucumber_seeds"],
    "lettuce":    ["croptopia:lettuce_seed", "farm_and_charm:lettuce_seeds"],
    "oat":        ["croptopia:oat_seed", "farm_and_charm:oat_seeds"],
    "strawberry": ["croptopia:strawberry_seed", "farm_and_charm:strawberry_seeds"],
}

for crop, items in SEEDS.items():
    values = [{"id": i, "required": False} for i in items]
    with open(os.path.join(DP, f"{crop}.json"), "w", encoding="utf-8") as f:
        json.dump({"values": values}, f, indent=2)
        f.write("\n")

print(f"Wrote {len(SEEDS)} c:seeds/<crop> tag files -> {DP}")
for crop in sorted(SEEDS):
    print(f"  c:seeds/{crop}: {', '.join(SEEDS[crop])}")
