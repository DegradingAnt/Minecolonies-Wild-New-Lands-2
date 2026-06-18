#!/usr/bin/env python3
"""Unify cross-mod duplicate PREPARED dishes (FarmersDelight-first canon).
Scans food mods, curates prepared dishes (>=2 mods, raw ingredients excluded),
writes c:foods/<dish> datapack tags, a separate prepared_food.json AU config
(FD-first priorities so it doesn't disturb the croptopia-first raw-crop config),
and adds the 'dish' placeholder. Isolated from materials.json/food.json.
"""
import os, re, json, glob, zipfile
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODS = os.path.join(ROOT, "mods")
DP_FOODS = os.path.join(ROOT, "config", "paxi", "datapacks", "UltimateVibes-Compat", "data", "c", "tags", "item", "foods")
AU = os.path.join(ROOT, "config", "almostunified")

FOOD_MODS = set("""croptopia farmersdelight abnormals_delight chefsdelight cuisinedelight
culturaldelights endersdelight expandeddelight fruitsdelight lendersdelight oceansdelight
mynethersdelight autochefsdelight aquaculturedelight farmersknives bakery brewery vinery
brewinandchewin farm_and_charm create_central_kitchen cookingforblockheads minersdelight
ecologics buzzier_bees autumnity upgrade_aquatic caverns_and_chasms hybrid_aquatic
wetland_whimsy naturalist galosphere meed candlelight t_and_t aquaculture""".split())

RAW = set("""almond asparagus barley bellpepper blueberry cabbage cherry corn cranberry
cucumber eggplant fig garlic kiwi lemon lettuce mango oat onion orange peach peanut pear
pecan persimmon pineapple rice soybean strawberry tomato walnut grape artichoke avocado
banana basil blackbean blackberry broccoli cantaloupe cashew cauliflower celery chilepepper
cinnamon coconut coffee currant date dragonfruit elderberry ginger greenbean greenonion
honeydew hops kale kumquat leek lime mustard nectarine nutmeg olive pepper plum radish
raspberry rhubarb rutabaga saguaro spinach squash starfruit sweetpotato tea turmeric turnip
vanilla yam zucchini wheat beetroot carrot potato apple melon""".split())

PREPARED_HINT = re.compile(r"(pie|soup|stew|cake|sandwich|juice|jam|jelly|bread|cookie|"
    r"salad|roll|pizza|burger|cream|smoothie|shake|tart|muffin|pancake|waffle|donut|pudding|"
    r"custard|porridge|curry|noodle|pasta|dumpling|sushi|kebab|skewer|fritter|chips|fries|"
    r"popsicle|icecream|milkshake|wine|beer|cider|cocktail|toast|bagel|biscuit|brownie|gummy|"
    r"candy|chocolate|honey|butter|cheese|stir_fry|soda|lemonade|sauce|dip|spread|cooked|"
    r"baked|grilled|fried|roasted|stuffed|glazed)")

# clear non-foods the prepared regex catches by accident
BLOCK = {"azalea_pressure_plate", "jellyfish_bucket", "plate"}

MODEL_RE = re.compile(r"assets/([^/]+)/models/item/(.+)\.json$")
def norm(s):
    s = s.lower(); s = re.sub(r"(^|_)(raw|cooked|cut|sliced|chopped|diced)(_|$)", "_", s)
    return s.strip("_")

name_ids = defaultdict(set)
for jp in sorted(glob.glob(os.path.join(MODS, "*.jar"))):
    try: z = zipfile.ZipFile(jp)
    except Exception: continue
    for n in z.namelist():
        m = MODEL_RE.match(n)
        if not m: continue
        ns, item = m.group(1), m.group(2)
        if ns not in FOOD_MODS or "/" in item: continue
        key = norm(item)
        if not key or key in RAW or key in BLOCK: continue
        if any(x in key for x in ("seed","sapling","crop","bush","block","_ore","bag")): continue
        name_ids[key].add(f"{ns}:{item}")

# curated prepared dishes: prepared-hint, >=2 distinct mod namespaces
dishes = {}
for key, ids in name_ids.items():
    if not PREPARED_HINT.search(key): continue
    mods = {i.split(":")[0] for i in ids}
    if len(mods) >= 2:
        dishes[key] = sorted(ids)

os.makedirs(DP_FOODS, exist_ok=True)
for dish, ids in dishes.items():
    with open(os.path.join(DP_FOODS, f"{dish}.json"), "w", encoding="utf-8") as f:
        json.dump({"values": [{"id": i, "required": False} for i in ids]}, f, indent=2); f.write("\n")

# add 'dish' placeholder
ph_path = os.path.join(AU, "placeholders.json")
ph = json.load(open(ph_path, encoding="utf-8"))
ph["dish"] = sorted(dishes.keys())
json.dump(ph, open(ph_path, "w", encoding="utf-8"), indent=2)

# write prepared_food.json (FD-first)
pf = {
    "mod_priorities": ["minecraft","farmersdelight","croptopia","bakery","culturaldelights",
        "cuisinedelight","farm_and_charm","vinery","abnormals_delight","autumnity","brewery",
        "fruitsdelight","candlelight","expandeddelight","aquaculturedelight","mynethersdelight","ecologics"],
    "priority_overrides": {}, "stone_variants": [],
    "tags": ["c:foods/{dish}"], "ignored_tags": [], "ignored_items": [],
    "ignored_recipe_types": ["cucumber:shaped_tag"], "ignored_recipe_ids": [],
    "recipe_viewer_hiding": True, "loot_unification": False, "ignored_loot_tables": []
}
json.dump(pf, open(os.path.join(AU, "unification", "prepared_food.json"), "w", encoding="utf-8"), indent=2)

print(f"Wrote {len(dishes)} c:foods/<dish> tags + prepared_food.json (FD-first) + 'dish' placeholder")
for d in sorted(dishes): print(f"  {d}: {', '.join(dishes[d])}")
