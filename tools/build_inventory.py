#!/usr/bin/env python3
"""Build a categorized mod-inventory.md from existing modmeta.json + mod-spreadsheet.tsv.
No fan-out: classifies each mod by keyword heuristics over name+desc, groups by function."""
import json, csv, re, io, sys

ROOT = r"C:\Users\linde\curseforge\minecraft\Instances\Ultimate vibes distant horizons version"
meta = json.load(open(ROOT + r"\.uvrun\modmeta.json", encoding="utf-8"))

# index spreadsheet by jar file
ss = {}
with open(ROOT + r"\.uvrun\mod-spreadsheet.tsv", encoding="utf-8") as f:
    r = csv.DictReader(f, delimiter="\t")
    for row in r:
        ss[row["Jar file"]] = row

# Category definitions: (label, [keywords]) — first match wins, order = priority.
CATS = [
    ("Libraries / API / Core", [
        "library", "loader independent", "api for", "core library", "lib mod",
        "framework", "dependency for", "required by", "common code", "registry helper",
        "codec", "data attachment", "config library", "menu library", "geckolib",
        "architectury", "kotlin", "fabric api", "forge config", "resourceful",
        "midnightlib", "balm", "cloth config", "yacl", "supermartijn", "moonlight",
        "collective", "puzzles lib", "framework for", "modding", "it utils",
        "shared code", "config file format", "configuration file format", "documentation for",
        "data-driven documentation", "baked model loader", "lib", "utils", "epherolib",
        "octolib", "coroutil", "almanac", "patchouli", "prickle", "gaboulibs", "bagus"]),
    ("Performance / Optimization", [
        "performance", "optimi", "fps", "lag", "memory", "framerate", "faster",
        "speed up", "reduce", "boost", "modernfix", "ferrite", "sodium", "embeddium",
        "rubidium", "lithium", "canary", "saturn", "krypton", "entity culling",
        "dynamic resources", "concurrent", "tick", "throttle", "cache", "async",
        "connection and packet size", "lightweight mod which solves", "better world loading"]),
    ("Rendering / Shaders / Visual FX", [
        "shader", "iris", "oculus", "distant horizon", "lod", "render", "lighting",
        "shadow", "bloom", "post-process", "vfx", "visual effect", "screen effect",
        "camera", "first person", "third person", "fog", "sky", "cloud", "weather render",
        "particle", "animation", "emissive", "connected textures", "ctm", "continuity",
        "ambient", "fancy", "pretty", "beautif", "blue flame", "dyed flame", "colorful",
        "flames", "imprint", "wakes", "trims", "elytra trim", "armor trim", "hats"]),
    ("World Generation / Biomes / Terrain", [
        "biome", "world gen", "worldgen", "terrain", "generation", "noise",
        "cave", "underground", "ore distribution", "geode", "geolog", "tectonic",
        "continents", "region", "climate", "dimension", "nether", "end ", "overworld",
        "biolith", "terrablender", "tara", "surface rule", "feature placement",
        "season", "erosion", "cliff", "geophilic", "terralith", "stone cliffs"]),
    ("Structures / Dungeons", [
        "structure", "dungeon", "ruin", "village", "town", "temple", "tower",
        "stronghold", "outpost", "castle", "city", "settlement", "shrine",
        "catacomb", "monument", "landmark", "building generation", "repurposed",
        "mineshaft", "witch hut", "yung"]),
    ("MineColonies & Colony", [
        "minecolonies", "colony", "colonies", "citizen", "stylepack", "stylecolonies",
        "warehouse workshop", "spice of minecolonies"]),
    ("Tech / Automation / Create", [
        "create", "automation", "machine", "factory", "logistic", "pipe", "energy",
        "power", "mechanical", "contraption", "gear", "tech mod", "industrial",
        "redstone", "circuit", "wireless", "storage drawer", "conveyor", "processing",
        "crafting automation", "ae2", "applied energistics", "pneumatic",
        "sawmill", "cable", "facade", "hopper", "item transfer", "uncraft"]),
    ("RPG / Magic / Combat / Skills", [
        "rpg", "magic", "spell", "mana", "combat", "weapon", "sword", "bow",
        "attack", "damage", "skill", "level up", "leveling", "experience", "class",
        "ability", "talent", "enchant", "curse", "artifact", "relic", "wand", "staff",
        "scroll", "ritual", "summon", "elemental", "druid", "necromanc", "paladin",
        "better combat", "parry", "dodge", "stamina", "souls", "boss", "raid",
        "apotheosis", "iron's spell", "irons spell", "mahou", "ars ", "tetra",
        "trident", "knight", "medieval", "antique", "swing", "clean swing"]),
    ("Mobs / Entities / Animals", [
        "mob", "monster", "creature", "animal", "entity", "spawn", "villager",
        "pet", "companion", "horse", "dragon", "fish", "bird", "insect", "beast",
        "wildlife", "fauna", "zombie", "skeleton", "golem", "familiar", "mount",
        "naturalist", "alex's", "alexs", "exotic birds", "critter", "wolf"]),
    ("Building / Decoration / Furniture", [
        "decoration", "decor", "furniture", "build", "block palette", "wood set",
        "stone set", "chair", "table", "lamp", "fence", "window", "door", "roof",
        "slab", "stair", "pillar", "column", "statue", "banner", "flower", "plant",
        "garden", "macaw", "chipped", "rechiseled", "diagonal", "framed", "deco",
        "dynamic trees", "trees that grow", "dense trees", "dense versions of vanilla trees",
        "blocks and items from different cultures", "roman style", "vanilla+ blocks",
        "block variations", "functional and useful vanilla"]),
    ("Food / Farming / Cooking / Drinks", [
        "food", "farm", "crop", "cook", "kitchen", "recipe for", "drink", "brew",
        "coffee", "tea ", "wine", "beer", "meal", "cuisine", "harvest", "agricultur",
        "botany", "croptopia", "pam", "delight", "sushi", "bakery", "fruit", "vegetable",
        "seed", "orchard", "vinery", "butcher", "let's do", "lets do", "spice of"]),
    ("Storage / Inventory / Items / QoL", [
        "storage", "inventory", "backpack", "chest", "barrel", "shulker", "sorting",
        "sort", "quality of life", "qol", "tweak", "convenience", "auto pickup",
        "trash", "bundle", "pouch", "tool belt", "quick", "hotbar", "crafting tweak",
        "right click", "shift click", "stack", "container", "ender chest",
        "carry", "pick up", "packing", "clump", "magnet", "totem", "undying",
        "accessor", "curio", "bauble", "canister", "heart canister", "polymorph",
        "recipe conflict", "smithing template", "darksmithing", "small ships", "boat"]),
    ("Map / HUD / Info / Tooltips", [
        "minimap", "map mod", "journeymap", "xaero", "waypoint", "hud", "overlay",
        "tooltip", "jade", "waila", "the one probe", "jei", "rei", "emi", "recipe viewer",
        "ingredient", "compass", "coordinate", "info", "status", "indicator", "armor bar",
        "health bar", "what am i looking at", "appleskin", "durability",
        "advancement", "beacon", "potion effect", "effect descriptions", "ping",
        "chat head", "notifier", "be notified", "leaderboard", "what are they up to"]),
    ("Adventure / Exploration / Quests", [
        "adventure", "exploration", "explore", "quest", "questing", "ftb quest",
        "loot", "treasure", "discovery", "journey", "expedition", "waystone", "teleport",
        "fast travel", "grappling", "climb", "parkour", "parcool", "backpack travel",
        "trial", "challenge", "bounty", "bountiful", "bounty board"]),
    ("Audio / Ambience / Music", [
        "sound", "audio", "music", "ambience", "ambient sound", "soundtrack",
        "voice", "noise effect", "dynamic music", "reverb", "footstep sound",
        "sound physics", "presence footsteps"]),
    ("Security / Fixes / Anti-cheat", [
        "telemetry", "anti-cheat", "anticheat", "crash", "exploit", "no chat report",
        "save my shit", "block common mods from connecting", "internet", "signatures from player",
        "tag parser", "fix a server", "tag fixes", "tags for items", "fixes for", "toast control",
        "blocking annoying popups", "void totem", "world loading"]),
    ("Compatibility / Integration", [
        "compat", "compatibility", "addon for", "integration", "support for many modded",
        "providing tags", "bridge between", "[let's do addon]", "born in configuration",
        "unofficial config", "config for"]),
    ("Utility / Tweaks / Vanilla+", [
        "tweak", "utility", "utilitarian", "various features", "vanilla friendly",
        "backport", "vanillabackport", "backporting", "improve game interaction",
        "control over the passage of time", "customize the length", "betterdays",
        "small things, improving", "armor stand", "trigger", "feature", "enhanc"]),
]

def classify(name, desc):
    hay = (name + " || " + desc).lower()
    for label, kws in CATS:
        for kw in kws:
            if kw in hay:
                return label
    return "Other / Uncategorized"

# Build records
recs = []
for m in meta:
    file = m.get("file", "")
    mods = m.get("mods") or [{}]
    primary = mods[0]
    name = primary.get("name") or primary.get("modId") or file
    modid = primary.get("modId", "")
    ver = primary.get("version", "")
    desc = (primary.get("desc") or "").strip().replace("\n", " ")
    desc = re.sub(r"\s+", " ", desc)
    row = ss.get(file, {})
    bloat = (row.get("Bloat verdict") or "").strip()
    patches = (row.get("PackFixes patches") or "").strip()
    sizeMB = m.get("sizeMB", 0) or 0
    classes = m.get("classes", 0)
    cat = classify(name, desc)
    recs.append(dict(file=file, name=name, modid=modid, ver=ver, desc=desc,
                     bloat=bloat, patches=patches, sizeMB=sizeMB, classes=classes, cat=cat))

# Group
from collections import defaultdict
groups = defaultdict(list)
for r in recs:
    groups[r["cat"]].append(r)

order = [c[0] for c in CATS] + ["Other / Uncategorized"]

out = io.StringIO()
out.write("# Mod Inventory — Ultimate Vibes (Distant Horizons version)\n\n")
out.write(f"_Generated from `modmeta.json` + `mod-spreadsheet.tsv` on 2026-06-13. "
          f"{len(recs)} jars. Categories are keyword-heuristic over each mod's own description — "
          f"a mod is filed under its single best-matching function, so multi-purpose mods land in one bucket only._\n\n")

# Summary table
out.write("## Category counts\n\n| Category | Mods |\n|---|---|\n")
for cat in order:
    if groups[cat]:
        out.write(f"| {cat} | {len(groups[cat])} |\n")
out.write(f"| **Total** | **{len(recs)}** |\n\n")

# Legend
out.write("**Flags:** 🔧 = patched by PackFixes · ⚠️ = flagged bloat-suspect · 📦 = ≥2 MB\n\n")

for cat in order:
    rs = sorted(groups[cat], key=lambda x: x["name"].lower())
    if not rs:
        continue
    out.write(f"## {cat} ({len(rs)})\n\n")
    for r in rs:
        flags = []
        if r["patches"]:
            flags.append("🔧")
        if r["bloat"] and "suspect" in r["bloat"].lower() or "confirm" in (r["bloat"] or "").lower():
            flags.append("⚠️")
        if (r["sizeMB"] or 0) >= 2:
            flags.append("📦")
        fl = (" " + "".join(flags)) if flags else ""
        d = r["desc"] if r["desc"] else "_(no description in jar)_"
        if len(d) > 160:
            d = d[:157] + "…"
        out.write(f"- **{r['name']}** `{r['modid']}` v{r['ver']}{fl} — {d}\n")
    out.write("\n")

open(ROOT + r"\.uvrun\mod-inventory.md", "w", encoding="utf-8").write(out.getvalue())
print("WROTE mod-inventory.md")
print("counts:")
for cat in order:
    if groups[cat]:
        print(f"  {len(groups[cat]):3d}  {cat}")
print(f"  ---  {len(recs)} total")
