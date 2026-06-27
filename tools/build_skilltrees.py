#!/usr/bin/env python3
"""
Build the WNL puffish_skills trees:
  - MARTIAL: one figure root ("Warrior's Path") -> 6 weapon item lanes x 3 tiers.
  - PARKOUR: one figure root ("Traceur's Path") -> 5 movement item lanes x 3 tiers.

Both share the same topology: a single texture-icon ROOT at top-center that fans out
to each lane's tier-1 node; each lane is a vertical column of 3 item-icon nodes.

Outputs:
  - datapack JSON under config/paxi/datapacks/WNL-SkillTrees/data/wnl_skills/puffish_skills/
  - Paxi resourcepack under config/paxi/resourcepacks/WNL-SkillTrees-Assets/ carrying the
    backgrounds + the two figure root textures (datapacks can't serve assets/, so the
    custom PNGs ride in a Paxi-loaded resourcepack).
Re-runnable; game must be CLOSED to apply (mods/packs are locked while running).
"""
import json, os, hashlib, shutil

ROOT = r"C:/Users/linde/curseforge/minecraft/Instances/Ultimate vibes distant horizons version"
NS   = "wnl_skills"
DP   = f"{ROOT}/config/paxi/datapacks/WNL-SkillTrees/data/{NS}/puffish_skills"
RP   = f"{ROOT}/config/paxi/resourcepacks/WNL-SkillTrees-Assets"
ART  = f"{ROOT}/_dev/art-assets"

# Shared connection colour scheme (gold unlocked / grey available / red excluded).
COLORS = {"connections": {
    "locked":   {"fill": "#23211d", "stroke": "#272521"},
    "available":{"fill": "#595856", "stroke": "#605e5c"},
    "unlocked": {"fill": "#b37d12", "stroke": "#bf8c26"},
    "excluded": {"fill": "#b31212", "stroke": "#bf2626"}}}

# kill-entity XP source, shared by both categories.
EXPERIENCE = {
    "experience_per_level": {"type": "expression",
        "data": {"expression": "min((level*10)^1.6+100,20000)"}},
    "sources": [{"type": "puffish_skills:kill_entity", "data": {
        "variables": {
            "dropped_xp": {"operations": [{"type": "get_dropped_experience"}]},
            "max_health": {"operations": [{"type": "get_killed_living_entity"},
                                          {"type": "get_max_health"}]}},
        "experience": "dropped_xp + max_health / 40",
        "anti_farming": {"limit_per_chunk": 15, "reset_after_seconds": 300}}}]}

TIERS = [("", "", 0.03), ("_adept", " Adept", 0.05), ("_master", " Master", 0.10)]

def nid(cat, key):
    """Deterministic 16-hex skill id so re-runs are stable."""
    return hashlib.md5(f"{cat}:{key}".encode()).hexdigest()[:16]

def item_icon(item):    return {"type": "item",    "data": {"item": item}}
def tex_icon(path):     return {"type": "texture", "data": {"texture": f"{NS}:textures/{path}.png"}}

def attr_reward(attr, value):
    return [{"type": "puffish_skills:attribute",
             "data": {"attribute": attr, "operation": "multiply_base", "value": value}}]

def build_category(cat, title, root_def, root_icon_path, bg_name, lanes):
    """
    lanes: list of dicts {key,label,icon(dict),attr}. Emits the 5 category files.
    Layout: root at (0,-130); lanes spread on x (80px apart, centred); tiers y=-60/0/60.
    """
    out = f"{DP}/categories/{cat}"
    os.makedirs(out, exist_ok=True)

    # --- definitions.json ---
    defs = {root_def: {
        "icon": tex_icon(root_icon_path),
        "rewards": attr_reward(lanes[0]["attr"], 0.02),
        "title": {"text": title.split("'")[0].strip() if "'" in title else title},
        "description": {"text": "Where the path begins."}}}
    for ln in lanes:
        for suf, lbl, val in TIERS:
            verb = {"": "Begin", "_adept": "Deepen", "_master": "Master"}[suf]
            tail = {"": f"Begin the {ln['label'].lower()} path.",
                    "_adept": f"Deepen your {ln['label'].lower()}.",
                    "_master": f"Master {ln['label'].lower()}."}[suf]
            defs[ln["key"] + suf] = {
                "icon": ln["icon"],
                "rewards": attr_reward(ln["attr"], val),
                "title": {"text": ln["label"] + lbl},
                "description": {"text": tail}}

    # --- skills.json (positions) + connections.json ---
    skills, links = {}, []
    n = len(lanes)
    xs = [(-(n - 1) / 2 + i) * 80 for i in range(n)]   # centred lane columns
    root_id = nid(cat, root_def)
    skills[root_id] = {"definition": root_def, "x": 0, "y": -130, "root": True}
    for i, ln in enumerate(lanes):
        prev = root_id
        for t, (suf, _lbl, _v) in enumerate(TIERS):
            sid = nid(cat, ln["key"] + suf)
            skills[sid] = {"definition": ln["key"] + suf,
                           "x": int(xs[i]), "y": -60 + t * 60}
            links.append([prev, sid])     # root->t1, t1->t2, t2->t3
            prev = sid

    category = {
        "title": {"text": title},
        "icon": tex_icon(root_icon_path),
        "unlocked_by_default": True,
        "exclusive_root": False,
        "background": {"texture": f"{NS}:textures/gui/{bg_name}.png",
                       "width": 768, "height": 463, "position": "fill"},
        "colors": COLORS}

    _w(f"{out}/category.json", category)
    _w(f"{out}/definitions.json", defs)
    _w(f"{out}/skills.json", skills)
    _w(f"{out}/connections.json", {"normal": {"bidirectional": links}})
    _w(f"{out}/experience.json", EXPERIENCE)
    print(f"  {cat}: root + {n} lanes x 3 tiers = {1 + n*3} nodes")

def _w(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)

# ---------------------------------------------------------------- categories
MARTIAL_LANES = [
    {"key": "sword",    "label": "Sword",    "icon": item_icon("minecraft:iron_sword"), "attr": "minecraft:attack_damage"},
    {"key": "axe",      "label": "Axe",      "icon": item_icon("minecraft:iron_axe"),   "attr": "minecraft:attack_damage"},
    {"key": "mace",     "label": "Mace",     "icon": item_icon("minecraft:mace"),       "attr": "minecraft:attack_damage"},
    {"key": "bow",      "label": "Bow",      "icon": item_icon("minecraft:bow"),        "attr": "minecraft:attack_speed"},
    {"key": "crossbow", "label": "Crossbow", "icon": item_icon("minecraft:crossbow"),   "attr": "minecraft:attack_speed"},
    {"key": "shield",   "label": "Shield",   "icon": item_icon("minecraft:shield"),     "attr": "minecraft:armor"},
]
PARKOUR_LANES = [
    {"key": "sprint", "label": "Sprint", "icon": item_icon("minecraft:feather"),         "attr": "minecraft:movement_speed"},
    {"key": "jump",   "label": "Jump",   "icon": item_icon("minecraft:rabbit_foot"),     "attr": "minecraft:jump_strength"},
    {"key": "leap",   "label": "Leap",   "icon": item_icon("minecraft:firework_rocket"), "attr": "minecraft:movement_speed"},
    {"key": "roll",   "label": "Roll",   "icon": item_icon("minecraft:slime_ball"),      "attr": "minecraft:safe_fall_distance"},
    {"key": "vault",  "label": "Vault",  "icon": item_icon("minecraft:ladder"),          "attr": "minecraft:step_height"},
]

print("Building categories:")
build_category("martial", "Martial Arts", "warrior_root", "skill/warrior_root", "martial_bg", MARTIAL_LANES)
build_category("parkour", "The Traceur's Path", "traceur_root", "skill/traceur_root", "parkour_bg", PARKOUR_LANES)

# config.json lists both categories
_w(f"{DP}/config.json", {"version": 3, "categories": ["martial", "parkour"]})

# ---------------------------------------------------------------- resourcepack
print("Building Paxi resourcepack WNL-SkillTrees-Assets:")
gui   = f"{RP}/assets/{NS}/textures/gui"
skill = f"{RP}/assets/{NS}/textures/skill"
os.makedirs(gui, exist_ok=True)
os.makedirs(skill, exist_ok=True)
copies = [
    (f"{ART}/skill-bg/martial_bg_768x463.png", f"{gui}/martial_bg.png"),
    (f"{ART}/skill-bg/parkour_bg_768x463.png", f"{gui}/parkour_bg.png"),
    (f"{ART}/skill-icons/martial/combat_stance.png", f"{skill}/warrior_root.png"),
    (f"{ART}/skill-icons/parkour/sprint.png",        f"{skill}/traceur_root.png"),
]
for src, dst in copies:
    shutil.copy2(src, dst)
    print(f"  {os.path.relpath(dst, RP)}")
_w(f"{RP}/pack.mcmeta", {"pack": {"pack_format": 34,
    "description": "WNL Skill Trees assets: tree backgrounds + figure root icons."}})

# ---------------------------------------------------------------- load orders
dp_lo = f"{ROOT}/config/paxi/datapack_load_order.json"
rp_lo = f"{ROOT}/config/paxi/resourcepack_load_order.json"
lo = json.load(open(dp_lo))
if "WNL-SkillTrees" not in lo["loadOrder"]:
    lo["loadOrder"].insert(lo["loadOrder"].index("WNL-MrpgcClasses") + 1, "WNL-SkillTrees")
    _w(dp_lo, lo)
rlo = json.load(open(rp_lo))
if "WNL-SkillTrees-Assets" not in rlo["loadOrder"]:
    rlo["loadOrder"].append("WNL-SkillTrees-Assets")
    _w(rp_lo, rlo)
print("Load orders updated. Done.")
