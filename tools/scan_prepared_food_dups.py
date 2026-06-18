#!/usr/bin/env python3
"""Find cross-mod duplicate PREPARED foods (cooked dishes the same across >=2 mods).
Enumerate item registry names from item-model filenames in the food/cooking mods,
normalize, group across mods. Exclude raw ingredients already unified (the 31 crops +
their seed/raw forms). Flag 'prepared' (pie/soup/cake/...) vs name-match-only.
"""
import os, re, glob, zipfile
from collections import defaultdict

MODS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mods"))

# food/cooking content mods (item namespaces worth grouping)
FOOD_MODS = set("""croptopia farmersdelight abnormals_delight chefsdelight cuisinedelight
culturaldelights endersdelight expandeddelight fruitsdelight lendersdelight oceansdelight
mynethersdelight autochefsdelight aquaculturedelight farmersknives bakery brewery vinery
brewinandchewin farm_and_charm create_central_kitchen cookingforblockheads minersdelight
ecologics buzzier_bees autumnity upgrade_aquatic caverns_and_chasms hybrid_aquatic
wetland_whimsy naturalist galosphere meed candlelight t_and_t aquaculture
delightful nethersdelight""".split())

# raw ingredients already unified (exclude these + obvious non-prepared forms)
RAW = set("""almond asparagus barley bellpepper bellpeppers blueberry cabbage cherry corn
cranberry cucumber eggplant fig garlic kiwi lemon lettuce mango oat onion orange peach
peanut pear pecan persimmon pineapple rice soybean strawberry tomato walnut grape
artichoke avocado banana basil blackbean blackberry broccoli cantaloupe cashew cauliflower
celery chilepepper cinnamon coconut coffee currant date dragonfruit elderberry ginger
greenbean greenonion honeydew hops kale kumquat leek lime mustard nectarine nutmeg olive
pepper plum radish raspberry rhubarb rutabaga saguaro spinach squash starfruit sweetpotato
tea turmeric turnip vanilla yam zucchini wheat beetroot carrot potato apple melon""".split())

PREPARED_HINT = re.compile(r"(pie|soup|stew|cake|sandwich|juice|jam|jelly|bread|cookie|"
    r"salad|roll|pizza|burger|cream|smoothie|shake|tart|muffin|pancake|waffle|donut|"
    r"pudding|custard|porridge|curry|noodle|pasta|dumpling|roll|sushi|kebab|skewer|"
    r"fritter|chips|fries|popsicle|icecream|ice_cream|milkshake|coffee|tea|wine|beer|"
    r"cider|cocktail|toast|bagel|biscuit|brownie|gummy|candy|chocolate|honey|butter|"
    r"cheese|stir_fry|soda|lemonade|sauce|dip|spread|bowl|plate|cooked|baked|grilled|"
    r"fried|roasted|stuffed|glazed)")

MODEL_RE = re.compile(r"assets/([^/]+)/models/item/(.+)\.json$")

def norm(s):
    s = s.lower()
    s = re.sub(r"(^|_)(raw|cooked|cut|sliced|chopped|diced)(_|$)", "_", s)
    return s.strip("_")

name_mods = defaultdict(set)      # normalized -> set(ns)
name_ids  = defaultdict(set)      # normalized -> set(full id)

for jp in sorted(glob.glob(os.path.join(MODS, "*.jar"))):
    try: z = zipfile.ZipFile(jp)
    except Exception: continue
    for n in z.namelist():
        m = MODEL_RE.match(n)
        if not m: continue
        ns, item = m.group(1), m.group(2)
        if ns not in FOOD_MODS: continue
        if "/" in item: continue  # skip nested (e.g. block subfolders)
        key = norm(item)
        if not key or key in RAW: continue
        if any(x in key for x in ("seed", "sapling", "crop", "bush", "block", "_ore", "bag")): continue
        name_mods[key].add(ns)
        name_ids[key].add(f"{ns}:{item}")

dups = [(k, v) for k, v in name_mods.items() if len(v) >= 2]
dups.sort(key=lambda kv: (-len(kv[1]), kv[0]))

print(f"Cross-mod duplicate food-item names (>=2 food mods, raw ingredients excluded): {len(dups)}\n")
prepared, other = [], []
for k, mods in dups:
    (prepared if PREPARED_HINT.search(k) else other).append((k, mods))

print("=== LIKELY PREPARED DISHES (unify candidates) ===")
for k, mods in prepared:
    ids = sorted(name_ids[k])
    print(f"  {k:22s} [{len(mods)}] {', '.join(ids)}")
print(f"\n=== NAME-MATCH ONLY (verify — may be distinct items) ({len(other)}) ===")
for k, mods in other[:40]:
    print(f"  {k:22s} [{len(mods)}] {', '.join(sorted(mods))}")
