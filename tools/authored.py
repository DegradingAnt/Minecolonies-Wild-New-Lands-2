"""Hand-AUTHORED deco pieces — the rebuild, now KIT-OF-PARTS: reusable parametric COMPONENTS (tower, curtain
stub, gate) composed into pieces. MC-legal (integer grid), symmetric (mirror_x), enterable + fully traversable
(pass-through + every floor via stairs/ladders), real functional blocks, ground-connected (no floats). Style:
researched REAL MEDIEVAL castle gatehouse. authored_pieces.json {name:{boxes,accents}} MERGED over
piece_geometry.json by the viewer/QC tools and by the in-game showroom (verbatim). python authored.py"""
import json, os, math
DIR = os.path.dirname(os.path.abspath(__file__))


class Build:
    def __init__(s): s.c = {}

    def set(s, x, y, z, b, r="facing"): s.c[(int(round(x)), int(round(y)), int(round(z)))] = (b, r)

    def fill(s, x0, y0, z0, x1, y1, z1, b, r="facing"):
        x0, y0, z0, x1, y1, z1 = (int(round(v)) for v in (x0, y0, z0, x1, y1, z1))
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                for z in range(min(z0, z1), max(z0, z1) + 1):
                    s.set(x, y, z, b, r)

    def clear(s, x0, y0, z0, x1, y1, z1):
        x0, y0, z0, x1, y1, z1 = (int(round(v)) for v in (x0, y0, z0, x1, y1, z1))
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                for z in range(min(z0, z1), max(z0, z1) + 1):
                    s.c.pop((x, y, z), None)

    def disc(s, cx, cz, r, y, b, role="floor", hollow=False, th=1.5):
        for x in range(int(cx - r - 1), int(cx + r + 2)):
            for z in range(int(cz - r - 1), int(cz + r + 2)):
                d = ((x - cx) ** 2 + (z - cz) ** 2) ** 0.5
                if (d <= r + 0.4) and (not hollow or d > r - th):
                    s.set(x, y, z, b, role)

    def drum(s, cx, cz, r, y0, y1, base, band, role="facing"):    # banded hollow round tower
        for y in range(y0, y1 + 1):
            s.disc(cx, cz, r, y, band if (y - y0) % 4 == 0 else base, role, hollow=True, th=1.6)

    def cone(s, cx, cz, r, y0, grad, role="trim"):                # conical roof, copper gradient bottom->top
        H = int(round(r)) + 2
        for h in range(H + 1):
            rr = r * (1 - h / float(H))
            col = grad[min(len(grad) - 1, h * len(grad) // (H + 1))]
            s.disc(cx, cz, rr, y0 + h, col, role)
        s.set(cx, y0 + H + 1, cz, grad[-1], role)

    def merlons(s, x0, z0, x1, z1, y, b, role="trim"):            # crenellations (every-other on the ring)
        for x in range(x0, x1 + 1):
            for z in (z0, z1):
                if (x + z) % 2 == 0: s.set(x, y, z, b, role)
        for z in range(z0, z1 + 1):
            for x in (x0, x1):
                if (x + z) % 2 == 0: s.set(x, y, z, b, role)

    def ring_merlons(s, cx, cz, r, y, b, role="trim"):            # crenellations around a drum (SUPPORT-AWARE: no floats)
        for k in range(0, 360, 20):
            a = math.radians(k)
            x = int(round(cx + r * math.cos(a))); z = int(round(cz + r * math.sin(a)))
            if k % 40 == 0 and (x, y - 1, z) in s.c: s.set(x, y, z, b, role)   # only on a solid cell below

    def spiral(s, cx, cz, r, y0, y1, b):                          # newel spiral stair (1 step per quarter turn)
        a = 0.0; y = y0
        while y <= y1:
            x = int(round(cx + (r - 0.6) * math.cos(a))); z = int(round(cz + (r - 0.6) * math.sin(a)))
            s.set(x, y, z, b, "floor"); a += math.pi / 2.2; y += 1

    def mirror_x(s, ax):
        for (x, y, z), v in list(s.c.items()):
            s.c.setdefault((2 * ax - x, y, z), v)

    def boxes(s):
        return [{"x": x, "y": y, "z": z, "dx": 1, "dy": 1, "dz": 1, "block": b, "role": r}
                for (x, y, z), (b, r) in s.c.items()]


# ---- COHESIVE MEDIEVAL PALETTE (coursed stone, timber, iron, copper-gradient roofs) ----
STONE = "minecraft:stone_bricks"; RUBBLE = "minecraft:cobblestone"; MOSSY = "minecraft:mossy_stone_bricks"
CRACK = "minecraft:cracked_stone_bricks"; QUOIN = "minecraft:chiseled_stone_bricks"
BATTER = "minecraft:cobbled_deepslate"; PLINTH = "minecraft:deepslate_bricks"
TRIM = "minecraft:polished_andesite"; FLOOR = "minecraft:stone_bricks"
TIMBER = "minecraft:spruce_log"; TIMBS = "minecraft:stripped_spruce_log"; PLANK = "minecraft:spruce_planks"
GATEW = "minecolonies:gate_wood"; STUD = "minecraft:iron_block"; PORT = "minecraft:iron_bars"
LADDER = "minecraft:ladder"; STAIR = "minecraft:stone_brick_stairs"
GLASS = "minecraft:light_blue_stained_glass"; LANT = "minecraft:lantern"
# copper-gradient cone roof: bright copper at the eaves -> oxidised verdigris at the peak
COP = ["minecraft:cut_copper", "minecraft:exposed_cut_copper", "minecraft:weathered_cut_copper", "minecraft:oxidized_cut_copper"]
FINIAL = "minecraft:lightning_rod"


def scatter_stone(b):
    """Varied/random texturing: scatter the main stone-brick into cracked/mossy/cobble + a little rubble,
    deterministically per cell, so the masonry reads aged + hand-laid (not a flat uniform wall). Class-locked
    (all stone-brick family). Run BEFORE mirror so the pattern stays symmetric."""
    fam = [("minecraft:stone_bricks", 0.60), ("minecraft:cracked_stone_bricks", 0.80),
           ("minecraft:mossy_stone_bricks", 0.93), ("minecraft:cobblestone", 1.0)]
    for (x, y, z), (blk, role) in list(b.c.items()):
        if blk == "minecraft:stone_bricks" and role in ("facing", "ground"):
            h = (x * 73856093) ^ (y * 19349663) ^ (z * 83492791)
            r = ((h * 1103515245 + 12345) & 0x7fffffff) / float(0x7fffffff)
            for bid, cum in fam:
                if r <= cum:
                    b.c[(x, y, z)] = (bid, role); break


# ================================ KIT-OF-PARTS COMPONENTS ================================
# Reusable parametric parts. Each mutates a Build; pieces below COMPOSE them. Scale/variation
# live in the parameters, so "make it bigger" or "swap the roof" is a knob, not a rebuild.

def tower(b, cx, cz, R, y0=1, drum_top=24, floors=(10, 17)):
    """Round drum-tower: battered foot, banded drum, proud plinth + belt courses, 8 buttress ribs, framed
    windows, interior mezzanine floors + spiral stair, and a WALKABLE machicolated parapet ring AROUND a
    central conical COPPER roof — so the top reads as a real roof yet you can walk the whole ring."""
    Ri = int(round(R))
    b.disc(cx, cz, R + 1.0, y0, BATTER, "ground", hollow=True, th=2.4)        # battered foot (hollow ->
    b.disc(cx, cz, R + 0.5, y0 + 1, BATTER, "ground", hollow=True, th=2.4)    #   ground room open from the road)
    b.drum(cx, cz, R, y0 + 2, drum_top, STONE, MOSSY, "facing")
    b.disc(cx, cz, R + 0.3, y0 + 2, TRIM, "trim", hollow=True, th=1.3)        # base plinth (proud)
    for y in range(y0 + 7, drum_top, 6):
        b.disc(cx, cz, R + 0.3, y, TRIM, "trim", hollow=True, th=1.3)         # proud belt courses (break the curve)
    for k in range(0, 360, 45):                                              # 8 vertical buttress ribs
        rx = int(round(cx + (R + 0.4) * math.cos(math.radians(k))))
        rz = int(round(cz + (R + 0.4) * math.sin(math.radians(k))))
        b.fill(rx, y0 + 2, rz, rx, drum_top - 1, rz, QUOIN, "pillar")
    for f in floors:                                                         # interior mezzanine floors (+ stair gap)
        b.disc(cx, cz, R - 1.5, f, PLANK, "floor"); b.clear(cx + 1, f, cz, cx + 1, f, cz)
    b.spiral(cx, cz, R, y0, drum_top + 1, STAIR)
    for y in range(y0, drum_top + 1): b.set(cx + Ri - 1, y, cz, LADDER, "floor")   # ladder: clear, certain vertical access
    for (ax, az) in [(cx, cz - Ri), (cx - Ri, cz), (cx, cz + Ri)]:           # tall framed windows, cardinal faces
        for f in floors:
            b.clear(ax, f + 1, az, ax, f + 2, az); b.set(ax, f + 3, az, GLASS, "accent")
    deck = drum_top + 1
    b.disc(cx, cz, R + 0.8, drum_top, TRIM, "trim")                         # cantilevered machicolation cornice
    b.disc(cx, cz, R, deck, FLOOR, "floor")                                 # the WALKABLE deck ring
    b.ring_merlons(cx, cz, R - 0.2, deck + 1, STONE, "trim")                # crenellated parapet (support-aware)
    tr = max(2.0, R - 3.0)                                                  # central roofed turret
    b.disc(cx, cz, tr, deck, STONE, "facing", hollow=True, th=1.5)
    b.disc(cx, cz, tr, deck + 1, STONE, "facing", hollow=True, th=1.5)
    b.cone(cx, cz, tr + 0.8, deck + 2, COP, "trim")                         # copper conical roof (reads as a roof)
    b.set(cx, deck + 2 + int(round(tr + 0.8)) + 3, cz, FINIAL, "accent")    # finial
    b.set(cx, drum_top - 5, cz - Ri, LANT, "accent")                        # exterior sconce


def curtain_stub(b, x0, x1, z0, z1, top=10):
    """A crenellated, WALKABLE curtain-wall stub that joins the city wall to the gate; quoined ends, arrow-loops
    on the outer face, a ladder up onto the wall-walk."""
    b.fill(x0, 1, z0, x1, top, z1, STONE, "facing")
    b.clear(x0 + 1, 1, z0 + 1, x1 - 1, top - 1, z1 - 1)                     # hollow interior
    b.fill(x0, top, z0, x1, top, z1, FLOOR, "floor")                        # wall-walk surface
    b.merlons(x0, z0, x1, z1, top + 1, STONE, "trim")
    for z in range(z0 + 1, z1, 2): b.clear(x0, 4, z, x0, 6, z)              # arrow-loops (outer face)
    b.fill(x0, 1, z0, x0, top, z0, QUOIN, "pillar"); b.fill(x0, 1, z1, x0, top, z1, QUOIN, "pillar")
    for y in range(1, top): b.set(x0 + 1, y, z0 + 1, LADDER, "floor")       # ladder up onto the wall-walk


# ---- IN-GAME PARTS: load a hand-built part (scanned via /wnp scanpart) and stamp it into the composer ----
PARTS_DIR = os.path.join(os.path.dirname(DIR), "config", "wnl_pathways", "parts")

def load_part(name, rng=None):
    """Load a RANDOM variant of <name> (name.json / name_2.json / …) -> {w,d,h,boxes,accents}. Pass a seeded
    random.Random as rng for deterministic per-placement variety in the worldgen composer."""
    import glob, re, random
    files = [f for f in glob.glob(os.path.join(PARTS_DIR, name + "*.json"))
             if re.fullmatch(re.escape(name) + r"(_\d+)?", os.path.splitext(os.path.basename(f))[0])]
    if not files:
        raise FileNotFoundError("no part '%s' in %s" % (name, PARTS_DIR))
    d = json.load(open((rng or random).choice(sorted(files)), encoding="utf-8"))
    return d[next(iter(d))]

def part(b, name, ox=0, oy=0, oz=0):
    """Stamp a hand-built part into Build b at (ox,oy,oz), verbatim. Returns (w,d,h) so the composer can snap
    parts edge-to-edge on a grid (this is how 'build small tiles in-game -> compose big' works)."""
    g = load_part(name)
    for bx in g["boxes"]:
        b.c[(ox + bx["x"], oy + bx["y"], oz + bx["z"])] = (bx["block"], bx.get("role", "part"))
    return g["w"], g["d"], g["h"]


# ================================ COMPOSED PIECES ================================

def gatehouse(R=6.0):
    """Grand medieval city gatehouse, COMPOSED from kit-of-parts. 9-WIDE carriageway (fits GREAT_ROAD=9)
    through twin BIG drum-towers (walkable machicolated decks AROUND central conical copper roofs); raised
    portcullis + MineColonies timber gates; murder-holes + windowed guard hall; crenellated curtain stubs;
    spiral stairs to every level; scattered aged masonry. Bigger scale (~45 wide). Left half, mirror at x=AX."""
    b = Build()
    AX = 22
    cx, cz = 12, 8                  # left tower centre (R=6 -> x6..18, abuts the carriageway at x18)
    GX = 18                         # carriageway / gate-mass left edge (carriageway x18..26, 9 wide)
    DEPTH = 14
    DRUM_TOP = 24
    PASS_H = 9                      # 9 wide x 9 tall carriageway (grand, matches the road)
    VAULT = PASS_H + 1              # 10: passage ceiling = guard-hall floor (= wall-walk level too)
    HALL_TOP = 15
    MASS_TOP = 16                   # gate-top wall-walk surface

    # ground + 9-wide cobbled carriageway
    b.fill(0, 0, 0, AX, 0, DEPTH + 4, STONE, "ground")
    b.fill(GX, 0, 0, AX, 0, DEPTH + 4, RUBBLE, "ground")

    curtain_stub(b, 0, 6, 5, 13, top=VAULT)                         # left curtain stub (walk at y10)
    tower(b, cx, cz, R, y0=1, drum_top=DRUM_TOP, floors=(VAULT, 17))

    # --- central gate mass over the carriageway ---
    b.fill(GX, 1, 0, AX, MASS_TOP, DEPTH, STONE, "facing")
    b.fill(GX - 1, 1, 0, GX - 1, MASS_TOP, DEPTH, STONE, "facing")  # straight JAMB down the passage side (mirror -> x27): closes the round-tower side holes
    b.fill(GX, 0, 0, AX, 0, DEPTH + 4, RUBBLE, "ground")
    b.clear(GX, 1, 0, AX, PASS_H, DEPTH + 4)                        # carriageway THROUGH (9 wide x 9 tall, no centre pillar)
    b.fill(GX, VAULT, 1, AX, VAULT, DEPTH, STONE, "floor")          # vault / guard-hall floor
    for z in range(3, DEPTH, 3): b.clear(GX + 2, VAULT, z, GX + 2, VAULT, z)   # 1-wide murder-holes
    for x in range(GX, AX + 1):                                     # raised portcullis up in its slot
        for y in range(PASS_H - 2, PASS_H + 1): b.set(x, y, 1, PORT, "accent")
    b.fill(GX, 1, 3, GX, PASS_H - 2, 3, TIMBS, "pillar")            # jamb post (at the wall, not the road)
    b.fill(GX, 1, 4, GX + 1, PASS_H - 2, 4, GATEW, "accent")        # MineColonies gate leaf (swung open vs the jamb)
    b.set(GX, PASS_H, 0, QUOIN, "accent")                          # arch keystone (front)
    # guard hall (windowed) over the gate, reached from the towers
    b.clear(GX, VAULT + 1, 2, AX, HALL_TOP, DEPTH - 1)
    b.fill(GX, VAULT + 1, 2, GX, HALL_TOP, DEPTH - 1, STONE, "facing")   # hall SIDE WALL (mirror -> x26): no side holes
    for z in range(3, DEPTH, 3): b.clear(GX + 2, VAULT, z, GX + 2, VAULT, z)
    b.fill(GX, VAULT + 2, 0, AX, VAULT + 3, 0, GLASS, "accent")     # front window band of the hall
    for x in (GX, AX): b.fill(x, VAULT + 2, 0, x, VAULT + 3, 0, TRIM, "trim")  # mullions
    for z in (5, 10):
        b.set(GX, VAULT + 1, z, GLASS, "accent"); b.set(GX, VAULT + 2, z, GLASS, "accent")  # side windows
    # projecting machicolation + WALKABLE gate-top battlement (connects the two towers)
    b.fill(GX, HALL_TOP, 0, AX, HALL_TOP, 0, TRIM, "trim")          # corbel course (proud)
    b.fill(GX - 1, MASS_TOP - 1, 0, AX, MASS_TOP - 1, 0, STONE, "facing")    # projecting parapet (cantilever)
    for x in range(GX + 1, AX, 2): b.clear(x, MASS_TOP - 1, 0, x, MASS_TOP - 1, 0)  # machicolation drop-gaps
    b.fill(GX, MASS_TOP, 1, AX, MASS_TOP, DEPTH, FLOOR, "floor")    # gate-top wall-walk
    b.merlons(GX, 0, AX, DEPTH, MASS_TOP + 1, STONE, "trim")
    b.fill(GX, 1, 0, GX, HALL_TOP, 0, QUOIN, "pillar")            # buttress pier framing the gate mouth
    for i in range(MASS_TOP - VAULT):                              # hall -> gate-top stair (with risers, no floats)
        b.set(AX - 1, VAULT + i, 2 + i, STAIR, "floor")
        if i: b.set(AX - 1, VAULT + i - 1, 2 + i, STONE, "facing")

    # --- stitch the parts: every doorway = a FLOOR underfoot + a 2-TALL opening above it (entity-walkable) ---
    b.clear(15, 1, 8, GX, 2, 10)                                    # carriageway -> tower (ground y0; 2 tall, 3 wide)
    b.fill(5, VAULT, 8, 8, VAULT, 9, PLANK, "floor")               # wall-walk <-> tower: floor bridge (y10) ...
    b.clear(5, VAULT + 1, 8, 8, VAULT + 2, 9)                       #   ... + 2-tall opening (y11,12)
    b.fill(15, VAULT, 7, 19, VAULT, 8, PLANK, "floor")             # hall <-> tower: floor bridge (y10) ...
    b.clear(15, VAULT + 1, 7, 19, VAULT + 2, 8)                     #   ... + 2-tall opening
    b.fill(15, MASS_TOP, 7, 19, MASS_TOP, 8, FLOOR, "floor")       # gate-top walk <-> tower: floor bridge (y16) ...
    b.clear(15, MASS_TOP + 1, 7, 19, MASS_TOP + 2, 8)              #   ... + 2-tall opening
    b.clear(AX - 1, MASS_TOP, 6, AX - 1, MASS_TOP + 2, 7)          # HATCH: hall stair climbs up through the gate-top walk

    scatter_stone(b)
    b.mirror_x(AX)
    return {"boxes": b.boxes(), "accents": []}


PIECES = {"gatehouse": gatehouse()}

if __name__ == "__main__":
    out = {n: pc for n, pc in PIECES.items()}
    json.dump(out, open(os.path.join(DIR, "authored_pieces.json"), "w"), separators=(",", ":"))
    print("authored_pieces.json: %d piece(s), %d blocks (%s)"
          % (len(out), sum(len(p["boxes"]) for p in out.values()), ", ".join(out)))
