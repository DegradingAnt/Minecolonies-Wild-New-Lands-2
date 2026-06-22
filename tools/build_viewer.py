"""Bundle the deco geometry + REAL block textures (vanilla from block_tex/, modded extracted from the
mod jars) into render3d/viewer/data.js for the interactive WebGL viewer. Textures are embedded as base64
data-URIs (so they ride in a .js file, dodging the repo's *.png gitignore, and load on file:// with no
CORS). Private dev only — bundling modded textures here is fine. Run:  python build_viewer.py"""
import json, os, glob, base64, io, zipfile
from PIL import Image

DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DIR)
TEXDIR = os.path.join(DIR, "block_tex")
OUT = os.path.join(DIR, "render3d", "viewer")
os.makedirs(OUT, exist_ok=True)

G = json.load(open(os.path.join(DIR, "piece_geometry.json"), encoding="utf-8"))
_ap = os.path.join(DIR, "authored_pieces.json")          # hand-rebuilt pieces override the iso geometry
if os.path.exists(_ap):
    G.update(json.load(open(_ap, encoding="utf-8")))

# ---- collect every block id used ----
ids = set()
for v in G.values():
    for b in v["boxes"]:
        ids.add(b.get("block", "minecraft:stone"))
        for f in b.get("family", []):
            ids.add(f)
ids |= {"minecraft:grass_block", "minecraft:water", "minecraft:dirt"}   # viewer ground + water
# the viewer also lets you swap PALETTE + dial WEATHERING, so we need textures for every block any
# theme palette / condition family / copper-oxidation stage could swap in (not just what's placed now).
_cond = json.load(open(os.path.join(DIR, "condition.json"), encoding="utf-8"))
for famlist in _cond.get("families", {}).values():
    if isinstance(famlist, list):
        for pair in famlist:
            ids.add(pair[0])
_pal = json.load(open(os.path.join(DIR, "modded_palette.json"), encoding="utf-8"))
for theme in _pal.values():
    if isinstance(theme, dict):
        for blocks in theme.get("roles", {}).values():
            for b in blocks:
                ids.add(b)
_themes = json.load(open(os.path.join(DIR, "piece_themes.json"), encoding="utf-8")).get("pieces", {})
for bid in list(ids):                                  # copper oxidation stages -> textures for the dial
    ns, nm = bid.split(":") if ":" in bid else ("minecraft", bid)
    if ns == "minecraft" and "copper" in nm and "ore" not in nm and not nm.startswith("raw_"):
        core = nm
        for p in ("waxed_", "exposed_", "weathered_", "oxidized_"):
            if core.startswith(p):
                core = core[len(p):]
        plain = core in ("copper", "copper_block")
        for st in ("", "exposed_", "weathered_", "oxidized_"):
            ids.add("minecraft:" + (("copper_block" if st == "" else st + "copper") if plain
                                    else (core if st == "" else st + core)))
vanilla = sorted(i for i in ids if i.startswith("minecraft:"))
modded = sorted(i for i in ids if not i.startswith("minecraft:"))
need_ns = sorted(set(m.split(":")[0] for m in modded))

# ---- index namespace -> mod jar (one pass, name-matches first so it resolves fast) ----
jars = glob.glob(os.path.join(ROOT, "mods", "*.jar"))
def name_score(j):
    b = os.path.basename(j).lower()
    return -sum(1 for ns in need_ns if ns.split("_")[0] in b)   # likely matches first
jars.sort(key=name_score)
ns_jar = {}
prefixes = {ns: "assets/%s/textures/block/" % ns for ns in need_ns}
for jp in jars:
    if len(ns_jar) == len(need_ns):
        break
    try:
        z = zipfile.ZipFile(jp)
        names = z.namelist()
    except Exception:
        continue
    for ns in need_ns:
        if ns in ns_jar:
            continue
        pre = prefixes[ns]
        if any(n.startswith(pre) for n in names):
            ns_jar[ns] = jp
print("namespace -> jar:")
for ns in need_ns:
    print("   %-22s %s" % (ns, os.path.basename(ns_jar.get(ns, "<<NOT FOUND>>"))))

_jar_cache = {}
def jar(jp):
    if jp not in _jar_cache:
        _jar_cache[jp] = zipfile.ZipFile(jp)
    return _jar_cache[jp]

MAT = [  # flat-colour fallback when a texture can't be resolved (rare)
    (("lantern", "torch", "glow", "candle"), (255, 208, 120)),
    (("lightning_rod",), (150, 165, 158)), (("copper",), (190, 140, 95)),
    (("deepslate",), (74, 74, 82)), (("blackstone",), (44, 40, 48)),
    (("mossy",), (96, 112, 84)), (("cobble",), (112, 112, 114)),
    (("calcite", "quartz", "diorite"), (224, 224, 220)), (("tuff",), (110, 110, 104)),
    (("mud",), (120, 96, 80)), (("sand",), (214, 200, 150)),
    (("spruce",), (116, 88, 60)), (("log", "wood", "plank", "oak", "barrel"), (165, 132, 90)),
    (("brick",), (150, 110, 95)), (("dirt", "podzol"), (110, 86, 62)),
    (("stone", "andesite"), (140, 140, 142)), (("glass",), (198, 224, 234)),
]
def flat_png(bid):
    b = bid.split(":")[-1]
    col = next((c for keys, c in MAT if any(k in b for k in keys)), (150, 148, 145))
    im = Image.new("RGBA", (16, 16), col + (255,))
    return im

def load_block_tex_png(fname):
    p = os.path.join(TEXDIR, fname + ".png")
    if os.path.exists(p):
        try:
            return Image.open(p).convert("RGBA")
        except Exception:
            return None
    return None

def load_jar_tex_png(ns, cand):
    jp = ns_jar.get(ns)
    if not jp:
        return None
    path = "assets/%s/textures/block/%s.png" % (ns, cand)
    try:
        with jar(jp).open(path) as f:
            return Image.open(io.BytesIO(f.read())).convert("RGBA")
    except Exception:
        return None

SHAPE_SUF = ("_slab", "_stairs", "_wall", "_fence_gate", "_fence", "_button", "_pressure_plate", "_door", "_trapdoor")
WOODS = ("oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "mangrove", "cherry", "bamboo",
         "crimson", "warped", "pale_oak")
def base_name(name):
    for s in SHAPE_SUF:
        if name.endswith(s):
            return name[:-len(s)]
    return name

def load_jar_rel(ns, rel):
    jp = ns_jar.get(ns)
    if not jp:
        return None
    try:
        with jar(jp).open("assets/%s/textures/block/%s.png" % (ns, rel)) as f:
            return Image.open(io.BytesIO(f.read())).convert("RGBA")
    except Exception:
        return None

_jar_idx = {}
def jar_block_index(ns):   # [(basename_stem, full_subpath)] for every png under textures/block/ (incl. subdirs)
    if ns in _jar_idx:
        return _jar_idx[ns]
    jp = ns_jar.get(ns); out = []
    if jp:
        pre = "assets/%s/textures/block/" % ns
        for n in jar(jp).namelist():
            if n.startswith(pre) and n.endswith(".png"):
                rel = n[len(pre):-4]
                out.append((rel.split("/")[-1], rel))
    _jar_idx[ns] = out
    return out

def vanilla_candidates(name, face):
    base = base_name(name)
    cands = ([name + "_top", name, base + "_top", base] if face == "top"
             else [name, name + "_side", base, base + "_side"])
    for w in WOODS:                                   # wood slab/stairs/fence -> planks texture
        if name.startswith(w + "_") and any(name.endswith(s) for s in SHAPE_SUF + ("_planks",)):
            cands.append(w + "_planks")
    if base.endswith("_brick"):                       # stone_brick_slab -> stone_bricks (plural)
        cands.append(base + "s")
    if name.endswith("_brick"):
        cands.append(name + "s")
    if name.startswith("waxed_"):                     # waxed copper shares the un-waxed texture
        cands.append(name[6:])
    if name.startswith("smooth_") or base.startswith("smooth_"):   # smooth_X -> X_top / X_block_bottom
        c = base_name(name).replace("smooth_", "", 1)
        cands += [c + "_top", c + "_bottom", c, c + "_block_bottom", c + "_block_top"]
    cands += {"campfire": ["campfire_log"], "soul_campfire": ["soul_campfire_log"],
              "water": ["water_still"], "lava": ["lava_still"]}.get(name, [])
    return cands

OVERRIDE = {   # blocks whose own texture isn't cleanly named/nested -> nearest vanilla material
    "born_in_chaos_v1:webbed_cobblestone": "cobblestone",
    "dawnoftimebuilder:stone_bricks_edge": "stone_bricks",
    "tombstone:white_marble": "calcite",
    # minecolonies gates render via a custom renderer (no static PNG) -> vanilla wood/iron stand-in for the viewer
    "minecolonies:gate_wood": "spruce_planks",
    "minecolonies:gate_iron": "iron_block",
}

def resolve(bid, face):
    ns, name = bid.split(":") if ":" in bid else ("minecraft", bid)
    if bid in OVERRIDE:
        im = (load_block_tex_png(OVERRIDE[bid] + "_top") if face == "top" else None) \
            or load_block_tex_png(OVERRIDE[bid])
        if im is not None:
            return im
    if ns == "minecraft":
        for c in vanilla_candidates(name, face):
            im = load_block_tex_png(c)
            if im is not None:
                return im
    else:
        base = base_name(name)
        for c in ([name + "_top", name, base + "_top", base] if face == "top" else [name, name + "_side", base]):
            im = load_jar_tex_png(ns, c)
            if im is not None:
                return im
        if ns == "domum_ornamentum":                  # DO blocks retexture to a vanilla material
            mat = name
            for suf in ("_extra", "_double_slab", "_slab", "_stairs", "_wall", "_fence", "_compat"):
                if mat.endswith(suf):
                    mat = mat[:-len(suf)]
            im = load_block_tex_png(mat) or load_block_tex_png(mat + "s")
            if im is not None:
                return im
        idx = jar_block_index(ns)                      # fuzzy: substring or token-swap match in the jar
        toks = set(name.split("_"))
        best = None
        for stem, rel in idx:
            if stem == name or stem in name or name in stem or set(stem.split("_")) == toks:
                if best is None or len(stem) < len(best):
                    best = stem; bestrel = rel
        if best:
            im = load_jar_rel(ns, bestrel)
            if im is not None:
                return im
    other = load_block_tex_png(name) if ns == "minecraft" else load_jar_tex_png(ns, name)
    return other if other is not None else flat_png(bid)

def datauri(im):
    im = im.convert("RGBA")
    if im.size != (16, 16):
        im = im.resize((16, 16), Image.NEAREST)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

TEX = {}
missing = []
for bid in sorted(ids):
    side = resolve(bid, "side")
    top = resolve(bid, "top")
    TEX[bid] = {"side": datauri(side), "top": datauri(top)}

# VOXELIZE to the Minecraft integer grid (the iso boxes have fractional positions = illegal in MC;
# snap to int + enumerate unit cells + dedup [later box wins] so placement is legal AND overlaps/
# z-fighting are resolved). Each cell carries its ROLE so the viewer can re-palette + weather it.
ROLES = ["facing", "floor", "ground", "timber", "pillar", "trim", "accent", "default"]
_ri = {r: i for i, r in enumerate(ROLES)}

def voxelize(boxes):
    grid = {}                                          # (x,y,z) -> (block, role)
    for b in boxes:
        x0 = int(round(b["x"])); y0 = int(round(b["y"])); z0 = int(round(b["z"]))
        dx = max(1, int(round(b["dx"]))); dy = max(1, int(round(b["dy"]))); dz = max(1, int(round(b["dz"])))
        blk = b.get("block", "minecraft:stone"); role = b.get("role", "facing")
        for ix in range(dx):
            for iy in range(dy):
                for iz in range(dz):
                    grid[(x0 + ix, y0 + iy, z0 + iz)] = (blk, role)
    return grid

_LIGHT_KW = ("lantern", "glow", "sea_lantern", "torch", "shroomlight", "froglight", "candle", "_lamp")
def thin_lights(grid):
    """The iso pipeline turned every 'glow' shading area into literal lantern blocks (banner_stand had 255).
    Lights aren't structural — keep them SPARSE (≥3 apart) and drop the rest to air, so a build reads as a
    few light points, not a lantern wall. (Same intent as the in-game accent thinning.)"""
    lights = [c for c, (b, r) in grid.items() if any(k in b.split(":")[-1] for k in _LIGHT_KW)]
    lights.sort()                                      # deterministic
    kept = []
    for c in lights:
        if any(max(abs(c[0] - k[0]), abs(c[1] - k[1]), abs(c[2] - k[2])) <= 2 for k in kept):
            del grid[c]                                # excess glow-fill -> air
        else:
            kept.append(c)
    return grid

geo = {}
for name, v in G.items():
    grid = thin_lights(voxelize(v["boxes"]))
    if not grid:
        geo[name] = {"w": 0, "d": 0, "h": 0, "n": 0, "pal": [], "cells": []}
        continue
    blocks = sorted(set(b for b, _ in grid.values()))
    _bi = {b: i for i, b in enumerate(blocks)}
    xs = [c[0] for c in grid]; ys = [c[1] for c in grid]; zs = [c[2] for c in grid]
    mnx, mny, mnz = min(xs), min(ys), min(zs)
    cells = [[c[0] - mnx, c[1] - mny, c[2] - mnz, _bi[br[0]], _ri.get(br[1], 7)] for c, br in grid.items()]
    geo[name] = {"w": max(xs) - mnx + 1, "d": max(zs) - mnz + 1, "h": max(ys) - mny + 1,
                 "n": len(cells), "pal": blocks, "cells": cells}

with open(os.path.join(OUT, "data.js"), "w", encoding="utf-8") as f:
    f.write("window.ROLES=" + json.dumps(ROLES) + ";\n")
    f.write("window.GEO=" + json.dumps(geo, separators=(",", ":")) + ";\n")
    f.write("window.TEX=" + json.dumps(TEX, separators=(",", ":")) + ";\n")
    f.write("window.COND=" + json.dumps(_cond, separators=(",", ":")) + ";\n")     # families + aging dial
    f.write("window.PAL=" + json.dumps(_pal, separators=(",", ":")) + ";\n")       # theme -> role -> blocks
    f.write("window.THEMES=" + json.dumps(_themes, separators=(",", ":")) + ";\n") # piece -> theme
sz = os.path.getsize(os.path.join(OUT, "data.js"))
import hashlib                                            # stamp a version so the live viewer auto-reloads on rebuild
ver = hashlib.md5(open(os.path.join(OUT, "data.js"), "rb").read()).hexdigest()[:12]
open(os.path.join(OUT, "version.txt"), "w").write(ver)
print("wrote viewer/data.js  | %d pieces, %d block textures, %d cells, %.0f KB | ver %s"
      % (len(geo), len(TEX), sum(p["n"] for p in geo.values()), sz / 1024, ver))
