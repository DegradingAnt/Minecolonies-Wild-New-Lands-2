"""STRUCTURAL-SOUNDNESS check (user spec): find HOLES in structural members (an air cell hemmed in by
solid on most sides = an unintended gap in a wall/floor/roof) and other "dumb" structural choices. Reports
pinholes (>=5 solid neighbours), surface gaps (==4), and per-Y floor-gap counts so non-solid floors show up.
Run: python structcheck.py [piece]"""
import json, os, sys
DIR = os.path.dirname(os.path.abspath(__file__))
G = json.load(open(os.path.join(DIR, "piece_geometry.json"), encoding="utf-8"))
_ap = os.path.join(DIR, "authored_pieces.json")
if os.path.exists(_ap):
    G.update(json.load(open(_ap, encoding="utf-8")))
NB6 = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]


def voxset(boxes):
    s = set()
    for b in boxes:
        x0 = int(round(b["x"])); y0 = int(round(b["y"])); z0 = int(round(b["z"]))
        for ix in range(max(1, int(round(b["dx"])))):
            for iy in range(max(1, int(round(b["dy"])))):
                for iz in range(max(1, int(round(b["dz"])))):
                    s.add((x0 + ix, y0 + iy, z0 + iz))
    return s


def check(name):
    S = voxset(G[name]["boxes"])
    xs = [c[0] for c in S]; ys = [c[1] for c in S]; zs = [c[2] for c in S]
    x0, x1, y0, y1, z0, z1 = min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)

    def nsolid(c): return sum(1 for d in NB6 if (c[0] + d[0], c[1] + d[1], c[2] + d[2]) in S)

    # candidate gap cells = empty cells strictly inside the bounding box
    pin, gap = [], []
    floorgap = {}
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            for z in range(z0, z1 + 1):
                c = (x, y, z)
                if c in S:
                    continue
                n = nsolid(c)
                if n >= 5:
                    pin.append(c)
                elif n == 4:
                    gap.append(c)
                # floor gap: empty cell with solid directly below + solid on >=2 sides (a hole in a floor)
                if (x, y - 1, z) in S and sum(1 for d in NB6[:2] + NB6[4:] if (x + d[0], y, z + d[2]) in S) >= 2:
                    floorgap[y] = floorgap.get(y, 0) + 1

    worst = sorted(floorgap.items(), key=lambda kv: -kv[1])[:4]
    print("%-14s pinholes(>=5):%-4d  surface-gaps(==4):%-4d  | floor-gaps by y(top): %s"
          % (name, len(pin), len(gap), ", ".join("y%d:%d" % (y, n) for y, n in worst) or "none"))
    if pin:
        print("   pinhole samples:", pin[:8])
    return len(pin), len(gap)


if __name__ == "__main__":
    for n in ([sys.argv[1]] if len(sys.argv) > 1 else ["gatehouse"]):
        if n in G:
            check(n)
