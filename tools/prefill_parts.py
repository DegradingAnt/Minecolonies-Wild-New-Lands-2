"""Pre-fill a few WORKED-EXAMPLE parts by slicing regions out of the authored gatehouse, so the user has
real parts to /wnp showpart + study + build from. Writes config/wnl_pathways/parts/<name>.json (same shape
the in-game scanner writes). Run: python prefill_parts.py"""
import json, os

DIR = os.path.dirname(os.path.abspath(__file__))
INST = os.path.dirname(DIR)
g = json.load(open(os.path.join(DIR, "authored_pieces.json"), encoding="utf-8"))["gatehouse"]
boxes = g["boxes"]
PARTS = os.path.join(INST, "config", "wnl_pathways", "parts")
os.makedirs(PARTS, exist_ok=True)

# region slices (gatehouse is already mirrored: x0..44). Each = a clean sub-piece.
slices = {
    "example_tower":    lambda b: 6 <= b["x"] <= 18 and 2 <= b["z"] <= 14,                 # the left drum tower
    "example_gatearch": lambda b: 16 <= b["x"] <= 28 and 0 <= b["z"] <= 6 and b["y"] <= 18, # the gate frontispiece
    "example_wallstub": lambda b: 0 <= b["x"] <= 6 and 5 <= b["z"] <= 13 and b["y"] <= 11,  # a curtain-wall segment
}
for name, pred in slices.items():
    sel = [b for b in boxes if pred(b)]
    if not sel:
        print(name, "EMPTY"); continue
    mnx = min(b["x"] for b in sel); mny = min(b["y"] for b in sel); mnz = min(b["z"] for b in sel)
    mxx = max(b["x"] for b in sel); mxy = max(b["y"] for b in sel); mxz = max(b["z"] for b in sel)
    nb = [{"x": b["x"] - mnx, "y": b["y"] - mny, "z": b["z"] - mnz, "dx": 1, "dy": 1, "dz": 1,
           "block": b["block"], "role": "part"} for b in sel]
    part = {name: {"w": mxx - mnx + 1, "d": mxz - mnz + 1, "h": mxy - mny + 1,
                   "verbatim": True, "boxes": nb, "accents": []}}
    json.dump(part, open(os.path.join(PARTS, name + ".json"), "w"), separators=(",", ":"))
    print("%-18s %d blocks  %dx%dx%d -> parts/%s.json" % (name, len(nb), mxx - mnx + 1, mxz - mnz + 1, mxy - mny + 1, name))
