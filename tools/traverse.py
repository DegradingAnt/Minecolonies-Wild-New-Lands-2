"""TRAVERSABILITY check (user spec): an entity must be able to (1) PASS THROUGH a gatehouse front-to-back
(it sits on the road it spawns at), and (2) REACH EVERY FLOOR (via stairs/ladders, not just open shafts).
Voxelizes the piece, finds where an entity can stand (solid below + 2 air), and floods a realistic walk
graph from the ground entrances: horizontal steps, ±1 step-ups (stairs/slabs), and vertical moves only
through ladder/stair columns. Reports pass-through YES/NO + floors reached / total. Run: python traverse.py [piece]"""
import json, os, sys
from collections import deque

DIR = os.path.dirname(os.path.abspath(__file__))
G = json.load(open(os.path.join(DIR, "piece_geometry.json"), encoding="utf-8"))
_ap = os.path.join(DIR, "authored_pieces.json")
if os.path.exists(_ap):
    G.update(json.load(open(_ap, encoding="utf-8")))


def voxmap(boxes):
    m = {}
    for b in boxes:
        x0 = int(round(b["x"])); y0 = int(round(b["y"])); z0 = int(round(b["z"]))
        for ix in range(max(1, int(round(b["dx"])))):
            for iy in range(max(1, int(round(b["dy"])))):
                for iz in range(max(1, int(round(b["dz"])))):
                    m[(x0 + ix, y0 + iy, z0 + iz)] = b["block"].split(":")[-1]
    return m


def check(name):
    solid = voxmap(G[name]["boxes"])
    S = set(solid)
    xs = [c[0] for c in S]; ys = [c[1] for c in S]; zs = [c[2] for c in S]
    x0, x1 = min(xs) - 1, max(xs) + 1; y0, y1 = min(ys), max(ys) + 2; z0, z1 = min(zs) - 1, max(zs) + 1

    def air(c): return c not in S and x0 <= c[0] <= x1 and y0 <= c[1] <= y1 and z0 <= c[2] <= z1
    def passable(c): return air(c) and air((c[0], c[1] + 1, c[2]))            # entity-tall gap
    def standable(c): return passable(c) and (c[0], c[1] - 1, c[2]) in S
    def climb(c): return ("ladder" in solid.get(c, "") or "stairs" in solid.get(c, "")
                          or "ladder" in solid.get((c[0], c[1] - 1, c[2]), "")
                          or "stairs" in solid.get((c[0], c[1] - 1, c[2]), ""))

    floor_cells = [c for c in ((x, y, z) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)
                               for z in range(z0, z1 + 1)) if standable(c)]
    floors = sorted(set(c[1] for c in floor_cells))
    # outside air = air reachable from the padded bbox border; an ENTRANCE = standable cell touching it
    NB6 = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
    outside = set(); dq = deque()
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            for z in range(z0, z1 + 1):
                if (x in (x0, x1) or y in (y0, y1) or z in (z0, z1)) and air((x, y, z)):
                    outside.add((x, y, z)); dq.append((x, y, z))
    while dq:
        c = dq.popleft()
        for d in NB6:
            n = (c[0] + d[0], c[1] + d[1], c[2] + d[2])
            if air(n) and n not in outside: outside.add(n); dq.append(n)
    seeds = [c for c in floor_cells if any((c[0] + d[0], c[1] + d[1], c[2] + d[2]) in outside for d in NB6)]

    reach = set(seeds); dq = deque(seeds)
    STEP = [(1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1)]                     # walk
    while dq:
        c = dq.popleft()
        for d in STEP:                                                        # flat + ±1 step (stairs/slabs)
            for dy in (0, 1, -1):
                n = (c[0] + d[0], c[1] + dy, c[2] + d[2])
                if passable(n) and n not in reach: reach.add(n); dq.append(n)
        for dy in (1, -1):                                                    # vertical only via a ladder/stair column
            n = (c[0], c[1] + dy, c[2])
            if passable(n) and n not in reach and (climb(c) or climb(n)): reach.add(n); dq.append(n)

    reached_floors = sorted(set(c[1] for c in floor_cells if c in reach))
    sealed = [c for c in floor_cells if c not in reach]
    fr = any(c[2] <= z0 + 1 for c in reach); bk = any(c[2] >= z1 - 1 for c in reach)
    ok = (fr and bk) and len(reached_floors) == len(floors)
    print("%-14s %s  pass-through:%-3s  floors:%d/%d reached  unreachable-floor-cells:%d  ys=%s"
          % (name, "OK " if ok else "FIX", "YES" if (fr and bk) else "NO",
             len(reached_floors), len(floors), len(sealed), floors))
    return ok


if __name__ == "__main__":
    for n in ([sys.argv[1]] if len(sys.argv) > 1 else ["gatehouse"]):
        if n in G:
            check(n)
