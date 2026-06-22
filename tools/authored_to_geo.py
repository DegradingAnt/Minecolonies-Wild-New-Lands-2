"""Merge hand-authored pieces (.uvrun/authored_pieces.json) into the IN-GAME config that DecoShowroom reads
(config/wnl_pathways/piece_geometry.json). Computes w/d/h from the boxes, flags each piece `verbatim:true`
so the mod places the EXACT authored blocks (no scatter / no copper re-oxidation) for in-world hand-polish.
Run: python authored_to_geo.py    (game can be open; the config is re-read on /wnp showroom)"""
import json, os

DIR = os.path.dirname(os.path.abspath(__file__))
INST = os.path.dirname(DIR)
ap = json.load(open(os.path.join(DIR, "authored_pieces.json"), encoding="utf-8"))
cfg_path = os.path.join(INST, "config", "wnl_pathways", "piece_geometry.json")
cfg = json.load(open(cfg_path, encoding="utf-8")) if os.path.exists(cfg_path) else {}

for name, g in ap.items():
    boxes = g["boxes"]; accents = g.get("accents", [])
    xs = []; ys = []; zs = []
    for b in boxes:
        xs += [b["x"], b["x"] + b["dx"] - 1]; ys += [b["y"], b["y"] + b["dy"] - 1]; zs += [b["z"], b["z"] + b["dz"] - 1]
    for a in accents:
        xs.append(a["x"]); ys.append(a["y"]); zs.append(a["z"])
    minx, maxx = min(xs), max(xs); miny, maxy = min(ys), max(ys); minz, maxz = min(zs), max(zs)
    cfg[name] = {"w": maxx - minx + 1, "d": maxz - minz + 1, "h": maxy - miny + 1,
                 "verbatim": True, "boxes": boxes, "accents": accents}
    print("%-16s %d boxes  %dx%d h%d" % (name, len(boxes), maxx - minx + 1, maxz - minz + 1, maxy - miny + 1))

json.dump(cfg, open(cfg_path, "w", encoding="utf-8"), separators=(",", ":"))
print("merged -> config/wnl_pathways/piece_geometry.json  (pieces now: %d)" % len(cfg))
