"""SIMPLE physical-plausibility check (user: "does this LOOK physically plausible — floating blocks are
legal in MC but look bad"). Voxelizes each piece to the MC grid, flood-fills from the GROUND course, and
reports any block whose mass is NOT connected back to the ground = floating. Isolated blocks (0 neighbours)
are the worst. Arches/overhangs that connect back through the structure are NOT flagged (they're supported).
Run from .uvrun:  python plausibility.py"""
import json, os
from collections import deque

DIR = os.path.dirname(os.path.abspath(__file__))
G = json.load(open(os.path.join(DIR, "piece_geometry.json"), encoding="utf-8"))
_ap = os.path.join(DIR, "authored_pieces.json")
if os.path.exists(_ap):
    G.update(json.load(open(_ap, encoding="utf-8")))
NB = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]

def voxset(boxes):
    s = set()
    for b in boxes:
        x0 = int(round(b["x"])); y0 = int(round(b["y"])); z0 = int(round(b["z"]))
        for ix in range(max(1, int(round(b["dx"])))):
            for iy in range(max(1, int(round(b["dy"])))):
                for iz in range(max(1, int(round(b["dz"])))):
                    s.add((x0 + ix, y0 + iy, z0 + iz))
    return s

rep = []
for name, v in G.items():
    s = voxset(v["boxes"])
    if not s:
        continue
    miny = min(c[1] for c in s)
    seen = set(c for c in s if c[1] == miny)          # ground course = supported seed
    dq = deque(seen)
    while dq:
        c = dq.popleft()
        for d in NB:
            n = (c[0] + d[0], c[1] + d[1], c[2] + d[2])
            if n in s and n not in seen:
                seen.add(n); dq.append(n)
    floating = s - seen
    if floating:
        iso = sum(1 for c in floating if not any((c[0] + d[0], c[1] + d[1], c[2] + d[2]) in s for d in NB))
        # count disconnected components among floating cells
        fset = set(floating); comps = 0
        while fset:
            comps += 1; st = [next(iter(fset))]; fset.discard(st[0])
            while st:
                c = st.pop()
                for d in NB:
                    n = (c[0] + d[0], c[1] + d[1], c[2] + d[2])
                    if n in fset:
                        fset.discard(n); st.append(n)
        rep.append((name, len(floating), len(s), iso, comps))

rep.sort(key=lambda r: -r[1])
print("piece                     floating/total   isolated  clusters")
for name, fl, tot, iso, comps in rep:
    print("%-24s  %4d/%-5d       %4d      %d" % (name, fl, tot, iso, comps))
print("\n%d / %d pieces have floating blocks | %d total floating cells"
      % (len(rep), len(G), sum(r[1] for r in rep)))
