#!/usr/bin/env python3
"""Generate convention-tag normalization for split food ingredients into the
UltimateVibes-Compat Paxi datapack, so AlmostUnified unifies each split ingredient
to the Croptopia canon consistently AND tag-based recipes still accept the canon.

For each SPLIT ingredient, every listed category tag gets the FULL real-variant set
(union), so croptopia is a member everywhere -> canonical everywhere -> tag recipes
resolve. Items use {"id","required":false} so a missing mod just skips (publishable-safe).

Keep-distinct items (ghasmati, cut_eggplant, cabbage_leaf) are NOT added here and are
handled by AU ignored_items in food.json. The lettuce mistag is likewise excluded.
white_eggplant is intentionally NOT kept distinct -> it stays in c:crops/eggplant and
unifies to croptopia automatically (already co-tagged).
"""
import os, json

DP = os.path.join(os.path.dirname(__file__), "..",
                  "config", "paxi", "datapacks", "UltimateVibes-Compat",
                  "data", "c", "tags", "item")
DP = os.path.abspath(DP)

# ingredient -> (category tags to fill, full real-variant item set [excl keep-distinct/mistags])
INGREDIENTS = {
    # crops <-> vegetables splits
    "cabbage":   (["crops", "vegetables", "foods"], ["croptopia:cabbage", "farmersdelight:cabbage", "minecolonies:cabbage"]),
    "asparagus": (["crops", "vegetables", "foods"], ["croptopia:asparagus", "expandeddelight:asparagus"]),
    "soybean":   (["crops", "vegetables", "foods"], ["croptopia:soybean", "minecolonies:soybean"]),
    # crops <-> fruits splits (croptopia in crops, fruitsdelight in fruits)
    "cranberry": (["crops", "fruits"], ["croptopia:cranberry", "fruitsdelight:cranberry"]),
    "kiwi":      (["crops", "fruits"], ["croptopia:kiwi", "fruitsdelight:kiwi"]),
    "peach":     (["crops", "fruits"], ["croptopia:peach", "fruitsdelight:peach"]),
    "pear":      (["crops", "fruits"], ["croptopia:pear", "fruitsdelight:pear"]),
    "pineapple": (["crops", "fruits"], ["croptopia:pineapple", "fruitsdelight:pineapple"]),
    # fruits/foods split + naming difference (bell_pepper vs bellpepper)
    "bellpepper": (["fruits", "vegetables", "foods"], ["croptopia:bellpepper", "minecolonies:bell_pepper"]),
    # secondary c:foods/* splits for otherwise-unified crops
    "rice":   (["crops", "foods"], ["croptopia:rice", "farmersdelight:rice", "minecolonies:rice"]),
    "tomato": (["crops", "foods"], ["croptopia:tomato", "farm_and_charm:tomato", "farmersdelight:tomato", "minecolonies:tomato"]),
    # 5-crop extension: dup crop items exist but were untagged -> tag them so AU unifies to croptopia
    "barley":     (["crops"],              ["croptopia:barley", "farm_and_charm:barley"]),
    "cucumber":   (["crops", "vegetables"], ["croptopia:cucumber", "culturaldelights:cucumber"]),
    "lettuce":    (["crops", "vegetables"], ["croptopia:lettuce", "farm_and_charm:lettuce"]),
    "oat":        (["crops"],              ["croptopia:oat", "farm_and_charm:oat"]),
    "strawberry": (["crops", "fruits"],    ["croptopia:strawberry", "farm_and_charm:strawberry"]),
}

written = []
for ingr, (cats, items) in INGREDIENTS.items():
    values = [{"id": i, "required": False} for i in items]
    for cat in cats:
        d = os.path.join(DP, cat)
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, f"{ingr}.json")
        # no "replace" -> APPEND to mod-provided members
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"values": values}, f, indent=2)
            f.write("\n")
        written.append(os.path.relpath(path, DP))

print(f"Wrote {len(written)} tag files under {DP}\n")
for w in sorted(written):
    print("  c/tags/item/" + w.replace(os.sep, "/"))
