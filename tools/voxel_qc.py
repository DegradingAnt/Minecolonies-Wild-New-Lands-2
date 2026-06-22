"""TRUE-3D QC renderer for the deco geometry (the missing piece — the design board is 2.5D HAND-DRAWN
iso, so it hid every 3D flaw; this renders the ACTUAL piece_geometry.json boxes as real 3D cuboids the
way Minecraft places them, so floats / bad scale / broken massing are finally VISIBLE). Output: a labelled
contact sheet (front iso of every piece, grouped by family) + optional per-piece multi-angle.
Run from .uvrun:  python voxel_qc.py [contact|<piece>]"""
import json, math, sys, os
from PIL import Image, ImageDraw, ImageFont

DIR = os.path.dirname(os.path.abspath(__file__))
G = json.load(open(os.path.join(DIR, "piece_geometry.json"), encoding="utf-8"))
_ap = os.path.join(DIR, "authored_pieces.json")
if os.path.exists(_ap):
    G.update(json.load(open(_ap, encoding="utf-8")))

def mat_color(bid):
    b = bid.split(":")[-1]
    table = [
        (("lantern", "torch", "glow", "fire", "candle"), (255, 208, 120)),
        (("lightning_rod",), (150, 165, 158)),
        (("oxidized", "weathered"), (110, 175, 150)),
        (("exposed_copper", "copper"), (190, 140, 95)),
        (("deepslate_tile", "deepslate_brick", "polished_deepslate"), (78, 78, 86)),
        (("cobbled_deepslate", "deepslate"), (68, 68, 74)),
        (("blackstone",), (44, 40, 48)),
        (("mossy_cobble", "mossy"), (96, 112, 84)),
        (("cobble",), (112, 112, 114)),
        (("chiseled_stone", "stone_brick", "stonebrick"), (138, 138, 140)),
        (("mud_brick", "packed_mud", "mud"), (120, 96, 80)),
        (("sandstone", "sand"), (214, 200, 150)),
        (("stripped_spruce", "spruce"), (116, 88, 60)),
        (("stripped_oak", "oak_log", "log", "wood"), (150, 116, 74)),
        (("plank", "oak", "barrel"), (172, 142, 98)),
        (("andesite",), (142, 142, 144)),
        (("polished_blackstone",), (60, 56, 64)),
        (("gravel",), (126, 121, 119)),
        (("rooted_dirt", "coarse_dirt", "podzol", "dirt"), (110, 86, 62)),
        (("quartz", "calcite", "diorite"), (224, 224, 220)),
        (("end_rod",), (236, 232, 224)),
        (("glass",), (198, 224, 234)),
        (("moss",), (92, 120, 70)),
        (("grass", "fern"), (104, 148, 80)),
        (("stone",), (140, 140, 142)),
    ]
    for keys, col in table:
        if any(k in b for k in keys):
            return col
    return (155, 150, 148)

def shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)

def render_piece(boxes, U=9, flip=False):
    """Front iso of the real voxel boxes. flip=True views the BACK (180° about Y) to catch hidden floats."""
    if flip:
        xs = [b["x"] for b in boxes] + [b["x"] + b["dx"] for b in boxes]
        zs = [b["z"] for b in boxes] + [b["z"] + b["dz"] for b in boxes]
        mx, mz = (max(xs) if xs else 0), (max(zs) if zs else 0)
        boxes = [dict(b, x=mx - b["x"] - b["dx"], z=mz - b["z"] - b["dz"]) for b in boxes]

    def proj(x, y, z):
        return (x - z) * U, (x + z) * (U * 0.5) - y * U

    pts = []
    for b in boxes:
        for cx in (b["x"], b["x"] + b["dx"]):
            for cy in (b["y"], b["y"] + b["dy"]):
                for cz in (b["z"], b["z"] + b["dz"]):
                    pts.append(proj(cx, cy, cz))
    if not pts:
        return Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    minx = min(p[0] for p in pts); maxx = max(p[0] for p in pts)
    miny = min(p[1] for p in pts); maxy = max(p[1] for p in pts)
    pad = 6
    W = int(maxx - minx) + pad * 2
    H = int(maxy - miny) + pad * 2
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img, "RGBA")

    def sp(x, y, z):
        px, py = proj(x, y, z)
        return (px - minx + pad, py - miny + pad)

    # painter's order: far (small x+z, then low y) first
    for b in sorted(boxes, key=lambda b: (b["x"] + b["z"], b["y"])):
        x, y, z, dx, dy, dz = b["x"], b["y"], b["z"], b["dx"], b["dy"], b["dz"]
        col = mat_color(b.get("block", "stone"))
        x2, y2, z2 = x + dx, y + dy, z + dz
        top = [sp(x, y2, z), sp(x2, y2, z), sp(x2, y2, z2), sp(x, y2, z2)]
        rgt = [sp(x2, y, z), sp(x2, y2, z), sp(x2, y2, z2), sp(x2, y, z2)]    # +x face
        frt = [sp(x, y, z2), sp(x2, y, z2), sp(x2, y2, z2), sp(x, y2, z2)]    # +z face
        d.polygon(frt, fill=shade(col, 0.58), outline=(0, 0, 0, 60))
        d.polygon(rgt, fill=shade(col, 0.76), outline=(0, 0, 0, 60))
        d.polygon(top, fill=shade(col, 1.0), outline=(0, 0, 0, 70))
    return img

def fit(img, cw, ch):
    if img.width == 0 or img.height == 0:
        return img
    s = min(cw / img.width, ch / img.height, 1.0)
    return img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.LANCZOS)

TIER_SUF = ("_great_road", "_highway", "_great", "_harbour", "_small", "_road", "_path", "_trail", "_long")
def fam(p):
    for s in TIER_SUF:
        if p.endswith(s):
            return p[:-len(s)]
    return p

OUT3D = os.path.join(DIR, "render3d")   # self-contained: board html/md + per-piece pngs, relative paths

def contact(outp=None):
    names = sorted(G.keys(), key=lambda p: (fam(p), G[p]["w"] * G[p]["d"]))
    cols = 6
    cw, ch = 250, 250
    rows = (len(names) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * cw, rows * ch), (28, 30, 34, 255))
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 13)
    except Exception:
        font = ImageFont.load_default()
    for i, name in enumerate(names):
        cx, cy = (i % cols) * cw, (i // cols) * ch
        v = G[name]
        im = fit(render_piece(v["boxes"]), cw - 16, ch - 40)
        sheet.paste(im, (cx + (cw - im.width) // 2, cy + 24 + (ch - 40 - im.height) // 2), im)
        d.text((cx + 6, cy + 4), f"{name}  {v['w']}x{v['d']}x{v['h']}", fill=(235, 235, 235), font=font)
        d.rectangle([cx, cy, cx + cw - 1, cy + ch - 1], outline=(70, 72, 78))
    outf = outp or os.path.join(DIR, "voxel_qc_contact.png")
    os.makedirs(os.path.dirname(outf), exist_ok=True)
    sheet.save(outf)
    print("wrote", outf, sheet.size)

def render_pair(name, U=13):
    """front | back of one piece on a card."""
    a = render_piece(G[name]["boxes"], U=U)
    b = render_piece(G[name]["boxes"], U=U, flip=True)
    W = a.width + b.width + 30
    H = max(a.height, b.height) + 20
    img = Image.new("RGBA", (W, H), (30, 32, 36, 255))
    img.paste(a, (10, 10 + (H - 20 - a.height) // 2), a)
    img.paste(b, (a.width + 20, 10 + (H - 20 - b.height) // 2), b)
    return img

def render_all():
    """Render EVERY piece (front|back) into render3d/, plus the contact sheet. Then build the board."""
    os.makedirs(OUT3D, exist_ok=True)
    for name in G:
        render_pair(name).save(os.path.join(OUT3D, name + ".png"))
    contact(os.path.join(OUT3D, "_contact.png"))
    print("rendered", len(G), "pieces -> render3d/")
    board()

def board():
    names = sorted(G.keys(), key=lambda p: (fam(p), G[p]["w"] * G[p]["d"]))
    fams = {}
    for n in names:
        fams.setdefault(fam(n), []).append(n)
    # --- GitHub markdown ---
    md = ["# WNL Deco — TRUE 3D build view", "",
          "_Auto-rendered from `piece_geometry.json` by `voxel_qc.py`. This is what **Minecraft actually builds** "
          "block-for-block (the main design board is hand-drawn 2.5-D and hides 3-D flaws). Each piece is shown "
          "**front | back**. Regenerate: `python .uvrun/voxel_qc.py all`._", "",
          "![all pieces](./_contact.png)", ""]
    for f, ns in fams.items():
        md.append("## %s\n" % f)
        for n in ns:
            v = G[n]
            md.append("**%s** — %d×%d×%d, %d boxes  " % (n, v["w"], v["d"], v["h"], v["n"]))
            md.append("![%s](./%s.png)\n" % (n, n))
    open(os.path.join(OUT3D, "DESIGN-BOARD-3D.md"), "w", encoding="utf-8").write("\n".join(md))
    # --- 2nd-monitor HTML ---
    cards = []
    for f, ns in fams.items():
        cards.append('<h2>%s</h2><div class="row">' % f)
        for n in ns:
            v = G[n]
            cards.append('<div class="c"><div class="t">%s &middot; %d&times;%d&times;%d</div>'
                         '<img src="./%s.png"></div>' % (n, v["w"], v["d"], v["h"], n))
        cards.append('</div>')
    html = ("<!doctype html><meta charset=utf-8><title>WNL deco — 3D</title>"
            "<style>body{background:#1e2024;color:#ddd;font-family:system-ui;margin:16px}"
            "img{background:#222;border:1px solid #444;max-width:480px;height:auto}"
            ".row{display:flex;flex-wrap:wrap;gap:14px}.c{background:#26282c;padding:8px;border-radius:6px}"
            ".t{font-size:13px;margin-bottom:4px;color:#bbb}h2{border-bottom:1px solid #444;margin-top:30px}</style>"
            "<h1>WNL Deco — true 3D build view</h1>"
            "<p>What Minecraft actually builds (front | back). The hand-drawn board is 2.5-D and hid these; "
            "this is the honest 3D. <b>Ctrl+R</b> to refresh after a re-render.</p>"
            '<p><img src="./_contact.png" style="max-width:900px"></p>' + "".join(cards))
    open(os.path.join(OUT3D, "DESIGN-BOARD-3D.html"), "w", encoding="utf-8").write(html)
    print("wrote render3d/DESIGN-BOARD-3D.md + .html")

def one(name):
    if name not in G:
        print("no piece", name); return
    a = render_piece(G[name]["boxes"], U=14)
    b = render_piece(G[name]["boxes"], U=14, flip=True)
    W = a.width + b.width + 30
    H = max(a.height, b.height) + 20
    img = Image.new("RGBA", (W, H), (28, 30, 34, 255))
    img.paste(a, (10, 10), a)
    img.paste(b, (a.width + 20, 10), b)
    out = os.path.join(DIR, f"voxel_qc_{name}.png")
    img.save(out)
    print("wrote", out, img.size, "(front | back)")

if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "contact"
    if arg == "contact":
        contact()
    elif arg == "all":
        render_all()
    elif arg == "board":
        board()
    else:
        one(arg)
