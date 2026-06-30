"""Build WNL-MegaPack.zip — merge ALL resourcepacks/ into ONE pack_format-34 pack for 1.21.1.

CURATION ENGINE (2026-06-26, Phase 1) — data-driven from _dev/megapack-curation-rules.md (95 rules).
Two base anchors: Stay True = block/texture base; FreshAnimations = mob base. Everything else overlays
by TIER (low->high = base->override). Plus: per-pack ASSET EXCLUDES, mine-only concept DROPS, a
persistent WNL-Custom authoring layer applied LAST (top precedence). Overlay resolution + sanitizer
from the foundation fix are preserved.

DEFERRED to Phase 2 (flagged [investigate] in the spec, too risky to do blind):
  - variant AGGREGATION (#59): variety packs currently last-wins by tier (one variant shows), same as
    before — NOT regressed; true ETF random-variant merge is Phase 2.
  - SPLITS (#5 Armored Illager armor-vs-model, #27 Ender Eyes anim-vs-texture): need path inspection.
  - custom authoring (#19/#35/#60/#61/#63/#69-port/#71/#92) -> live in WNL-Custom, authored separately.
PRIVATE/personal only (bundles third-party art, credited). Run: python .uvrun/build_megapack.py"""
import os, io, json, zipfile, re

DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DIR)
RP = os.path.join(ROOT, "resourcepacks")              # source zips + OUTPUT live here
SRC = os.environ.get("WNL_MEGAPACK_SRC", RP)
OUT = os.path.join(RP, "WNL-MegaPack.zip")
CUSTOM_DIR = os.path.join(ROOT, "resourcepacks-src", "WNL-Custom")  # hand-authored layer (#62), applied LAST

# #243: drop the harvested broken CITs — CITResewn "Cannot resolve path @L3" (model-based trim CITs whose
# target models are missing; they render NOTHING, so dropping is visually neutral and just kills ~4500 load
# errors). Re-harvestable from a boot log: grep CITResewn "Cannot resolve path" -> assets/<ns>/<citpath>.
# (the 1 "legacy nbt" CIT — musketmod revolver — is EXCLUDED on purpose: it works, just deprecated syntax.)
_BROKEN_CITS_FILE = os.path.join(ROOT, "_dev", "megapack-broken-cits.txt")
DROP_CITS = set()
if os.path.exists(_BROKEN_CITS_FILE):
    with open(_BROKEN_CITS_FILE, "r", encoding="utf-8") as _bf:
        DROP_CITS = {ln.strip() for ln in _bf if ln.strip() and not ln.lstrip().startswith("#")}

# === DROPS: never merged (own output, removed-mod packs, + MINE-ONLY concept packs) ===
# mine-only = "port the IDEA, do NOT use textures" (design policy) -> source stays in resourcepacks/
# for reference, but its art never ships in the megapack. (#69 Display/Fresh Armor, #71 FA Variated
# Villagers, #72 Blue's Better Monsters, batch-2 Better Zombies.)
DROP_SUBSTR = [
    "wnl-megapack",                # our own output
    "visual titles",               # removed mod
    "display armor",               # #69 Fresh/Display Armor -> author 3D armor originally in WNL-Custom
    "blues_better_monsters",       # #72 mine-only
    "better zombies",              # batch-2 mine-only (Blue's Better Zombies)
    "fresh variated villagers",    # #71 mine-only (port the idea -> our own random-variant villagers)
    "cataclysmic",                 # #98 SOUND pack (94MB cataclysm music .ogg) -> outside the megapack;
                                   #     keep the zip in resourcepacks/ + enable it separately for the music
    "musgo",                       # 2026-06-30: PULLED per user "until we make its textures into a mod". Musgo
                                   #     overrides vanilla fence/brick blockstates with moss variants -> caused the
                                   #     fence->moss + structure "mu bricks" bugs. Re-add as a proper mod with its own
                                   #     placeable block IDs (tasks #244/#249), not as a vanilla-block override.
]
# Also drop any stray sound bloat from OTHER packs so the megapack stays texture/model-focused (#98 policy).
DROP_SOUNDS = True   # skip assets/<ns>/sounds/**.ogg during merge
def dropped_pack(f):
    fl = f.lower()
    return any(d in fl for d in DROP_SUBSTR)

# === PER-PACK ASSET EXCLUDES: skip matching paths from a specific pack during merge ===
# (substr -> predicate(internal_path)->True to SKIP). Source packs stay pristine.
def _excl_fresh_textures(p):   # #28/#66 Fresh Textures = MISC only; it wrongly won mob textures
    return "/textures/entity/" in p
def _excl_freshtextures_fa(p): # #3 FreshTextures+FA = mob-support, NOT the player (Fresh Moves drives player)
    return "/textures/entity/player/" in p or "/player/" in p and p.endswith(".jem") or "/cem/player" in p
PACK_EXCLUDES = [
    ("fresh textures", _excl_fresh_textures),     # matches "Fresh Textures 1.4.4" (NOT "freshtextures+fa")
    ("freshtextures+fa", _excl_freshtextures_fa),
]
def exclude_pred(packname):
    fl = packname.lower()
    for sub, pred in PACK_EXCLUDES:
        if sub == "fresh textures":
            if "fresh textures" in fl and "+fa" not in fl:
                return pred
        elif sub in fl:
            return pred
    return None

# === TIER TABLE (low number = applied first = LOWER priority; high overwrites) ===
# ordered, first-match wins. substrings are the REAL lowercased source-zip filenames.
TIER_RULES = [
    # -- FLOOR: last-line-of-defence + demoted ruining source --
    ("rcp", 1),                       # #95 The RCP: wins only what nothing else covers
    ("musgo", 1),                     # #36 Musgo: ruining source, NOT a global override -> never wins base
    # -- base-plus / below Stay True (gap-fill) --
    ("vanilla experience", 11),       # #37 base + variety (specific drivers win shared)
    ("freshtextures+fa", 14),         # #3/#25 base-plus, mob-only (player excluded), below all FA addons
    ("fresh textures", 10),           # #28 MISC base (entity excluded); keep below Stay True
    # -- CTM backups (below Stay True; fill connected-texture gaps only) --
    ("connected-", 13),               # #31/#33/#34 Connected Paths/Rocks/Bricks
    ("connected_copper_grate", 13),   # #50
    ("fusion connected blocks", 13),  # #51
    ("snow side", 13),                # #54 snowy-side overlay (custom patches pending)
    ("geo - ", 13),                   # GEO Fusion CTM
    # -- Stay True = THE block/vanilla-texture base anchor (#28) --
    ("stay true 1.21", 15),
    # -- low bases that must lose shared features to specific drivers --
    ("armor trim compat", 25),        # #23 trim-compat base
    ("emissive lanterns", 30),        # #32 emissive-ONLY base (its _e textures are unique paths)
    ("better-leaves", 30),            # #45 leaves base
    # -- Stay-True-style modded support --
    ("staytrue26", 42), ("stay true compat", 42),  # #44
    # -- FreshAnimations ecosystem (explicit sub-tiers; #25 hierarchy) --
    ("fa+all_extensions", 56), ("fa+player", 56),   # 56: extensions = FA base layer (own vanilla mobs)
    ("freshanimations", 55),                        # 55: FA base
    ("th + fresh", 50),                             # 50: FA texture-compat looks (lose models to FA)
    # 52: FA specific-mob compat addons (modded mobs animate w/ FA; overlay ON the base)
    ("fa illager", 52), ("armored illager", 52), ("morepiglins", 52), ("rotten creatures", 52),
    ("variants and ventures", 52), ("abnormally fresh", 52), ("assorted allays", 52),
    ("wandering traders", 52), ("mca_resourcepack", 52), ("quarkfacompat", 52),
    ("eating animations", 52), ("freshly modded", 52), ("endereyes", 52),
    ("semos", 48),                                  # #6 lib: load but don't win finished mobs [investigate]
    # 51: variety packs (refreshed family + Drodi's + Al's series + turtles) -> STACK (#38-41/#59/#67)
    ("refreshed-fa", 51), ("refreshed-v", 51), ("refreshed-v2", 51), ("boss-refreshed", 51),
    ("drodi", 51), ("freshturtle", 51), ("fresh moves", 51), ("fresh patch", 52),
    # -- category drivers (win their category over Stay True; #1/#2/#16/#17/#21/#18/#29/#55/#56/#58...) --
    ("armory", 45),                   # #1 armor (split from models = Phase 2)
    ("modded omelet", 45),            # #2 spawn eggs
    ("medieval_style_lootr", 45),     # #16 lootr (format 10 but wins lootr)
    ("fancy crops", 45),              # #17 crops
    ("fluffy carpet", 45),            # #21 wool/carpet
    ("modded swords", 46),            # #18 first-person item assets (high)
    ("better enchanting", 45), ("enchanting table", 45),  # #29
    ("lily pads", 45),                # #30 variety
    ("3d", 45),                       # #47 Nico's 3D Ladders (filename has 3d + ladders)
    ("torches", 45),                  # Torches Reimagined
    ("fancy", 45),
    ("cubic-sun-moon", 45),           # #35 sun/moon (shader patch pending)
    ("simple grass", 45),             # #19 grass flowers (bake pending)
    ("shivaklans", 45), ("animated textures", 45),  # #49 animated+emissive variety
    ("fusion stacking items", 45),    # #52 inventory item models
    ("cataclysm reimagined", 45),     # #55
    ("xali's potion", 40),            # #56 potions base (others can override)
    ("waystones", 45),                # #58
    ("muskets_overhaul", 45),         # kept musket pack (#40 Flintl0cks pulled)
    # -- GUI / icons / lang (top-ish, minimal conflict) --
    ("enhanced boss bars", 60),       # #46
    ("rpg_series_icons", 60), ("attribute icons", 60),  # #15 RPG icons base
    ("journeymap icons", 60),         # #57
    ("biomesnames", 60), ("terralithbiomesnames", 60),  # #43 name fixes
    ("descriptions", 60),             # enchantment descriptions
    ("rename compat", 60),            # The Rename Compat Project (lang/rename)
    # -- our fix layer (very top, below WNL-Custom) --
    ("texturefixes", 70),
]
def tier(f):
    fl = f.lower()
    for sub, t in TIER_RULES:
        # guard: "fresh textures" must NOT swallow "freshtextures+fa"
        if sub == "fresh textures" and "+fa" in fl:
            continue
        if sub in fl:
            return t
    return 40   # default: mod-specific item/block packs, above base, below category drivers

# === collect + order ===
packs = [f for f in os.listdir(SRC) if f.endswith(".zip") and not dropped_pack(f)]
dropped = [f for f in os.listdir(SRC) if f.endswith(".zip") and dropped_pack(f)]
packs.sort(key=lambda f: (tier(f), f.lower()))

# === per-file SANITIZER (preserved from the foundation fix) ===
ABSENT_NS = ("regions_unexplored:", "biomesoplenty:")
SANITIZE_LOG = []
def sanitize(n, data):
    nl = n.lower()
    if n in DROP_CITS:                              # #243: harvested broken CIT (CITResewn "Cannot resolve path")
        SANITIZE_LOG.append("drop broken CIT #243 " + n.split("/")[-1]); return None
    if nl.endswith("/drowned3.jem"):
        SANITIZE_LOG.append("drop drowned3.jem (EMF player_rot_y)"); return None
    if nl.endswith("/cem/frog.properties"):
        SANITIZE_LOG.append("drop frog.properties (ETF no-rules)"); return None
    if "ghastling_explosion" in nl or ("accessibility" in nl and nl.endswith(".mcmeta")):
        SANITIZE_LOG.append("drop dead animatica anim " + n.split("/")[-1]); return None
    if "optifine/ctm/" in nl and nl.endswith(".properties"):
        try:
            kept = []
            for line in data.decode("utf-8", "replace").splitlines():
                s = line.strip()
                if s.startswith("tintIndex") and "=" in s and not s.split("=", 1)[1].strip().lstrip("-").isdigit():
                    SANITIZE_LOG.append("strip bad tintIndex " + n.split("/")[-1]); continue
                # (b) tintBlock referencing absent-mod block OR non-existent minecraft:mossy_block (real=moss_block)
                if s.startswith("tintBlock") and "=" in s and (any(a in s for a in ABSENT_NS) or "mossy_block" in s):
                    SANITIZE_LOG.append("strip bad tintBlock " + n.split("/")[-1]); continue
                kept.append(line)
            # (a) FIX (not drop): Stay True's _overlays CTMs are method=overlay (17 tiles); a few (e.g.
            #     mushroom_stem) ship with NO method line -> Continuity defaults to method=ctm (needs 47)
            #     -> rejects. All _overlays are method=overlay, so inject it where missing -> CTM works.
            if "/_overlays/" in nl and not any(k.strip().startswith("method") for k in kept):
                kept.insert(0, "method=overlay")
                SANITIZE_LOG.append("add method=overlay " + n.split("/")[-1])
            return ("\n".join(kept)).encode("utf-8")
        except Exception:
            return data
    # verify-boot 2026-06-26 (c): CITResewn rejects `weight=` in CIT props -> strip it (CIT still applies)
    if "optifine/cit/" in nl and nl.endswith(".properties"):
        try:
            lines = data.decode("utf-8", "replace").splitlines()
            kept = [l for l in lines if not l.strip().startswith("weight=")]
            if len(kept) != len(lines):
                SANITIZE_LOG.append("strip citresewn weight= " + n.split("/")[-1])
            return ("\n".join(kept)).encode("utf-8")
        except Exception:
            return data
    return data

# === overlay resolution (preserved) ===
TARGET_FMT = 34
SKIP = ("pack.mcmeta", "pack.png")
JUNK = ("desktop.ini", ".ds_store", "thumbs.db")
def applicable_overlays(z):
    out = []
    try:
        meta = json.loads(z.read("pack.mcmeta").decode("utf-8", "replace"))
    except Exception:
        return out
    for ov in (meta.get("overlays") or {}).get("entries", []) or []:
        if not isinstance(ov, dict):
            continue
        fmts = ov.get("formats")
        if isinstance(fmts, dict):
            mn, mx = fmts.get("min_inclusive", 0), fmts.get("max_inclusive", 9999)
        elif isinstance(fmts, list) and len(fmts) >= 2:
            mn, mx = fmts[0], fmts[1]
        elif isinstance(fmts, int):
            mn, mx = fmts, fmts
        else:
            mn, mx = ov.get("min_format", 0), ov.get("max_format", 9999)
        try:
            if int(mn) <= TARGET_FMT <= int(mx) and ov.get("directory"):
                out.append(ov["directory"].rstrip("/") + "/assets/")
        except Exception:
            continue
    return out

def extract(zpath, packname):
    """Return {internal_path: clean_bytes} for one pack: base assets/ + applicable overlays,
    sanitized, with per-pack excludes applied. Used by the merge AND (future) category overrides."""
    out, ov_used = {}, []
    try:
        z = zipfile.ZipFile(zpath)
    except Exception as e:
        print("  SKIP (bad zip):", packname, e); return out, ov_used
    skip_pred = exclude_pred(packname)
    # ARCHITECTURE GUARD: the mob/variety/FA band (tier >= 50) is the MOB base (#59); it must NOT win
    # vanilla BLOCK textures (Stay True owns those, #28). Mixed packs like Drodi's Assortments ship
    # stray block textures (planks/crafting table) that would clobber the block base — scope them out.
    mob_band = tier(packname) >= 50
    ovs = applicable_overlays(z)
    if ovs:
        ov_used = [o[:-8] for o in ovs]
    for prefix in ["assets/"] + ovs:
        for n in z.namelist():
            if n.endswith("/") or n in SKIP or not n.startswith(prefix):
                continue
            internal = "assets/" + n[len(prefix):]
            il = internal.lower()
            if il.endswith(JUNK):
                continue
            if skip_pred and skip_pred(il):
                continue
            if mob_band and "/textures/block/" in il:
                continue   # mob/variety pack — block textures stay with the block base
            if DROP_SOUNDS and il.endswith(".ogg"):
                continue   # #98: sounds belong in separate packs, not the texture megapack (keeps it lean)
            try:
                raw = z.read(n)
            except Exception:
                continue
            clean = sanitize(internal, raw)
            if clean is None:
                continue
            out[internal] = clean
    z.close()
    return out, ov_used

# === merge low->high ===
files = {}
provenance = {}
per_pack_added = {}
overlay_log = []
for f in packs:
    assets, ov_used = extract(os.path.join(SRC, f), f)
    if ov_used:
        overlay_log.append("%-46s + overlays %s" % (f[:46], ov_used))
    for internal, data in assets.items():
        files[internal] = data
        provenance[internal] = f
    per_pack_added[f] = len(assets)

# === WNL-Custom authoring layer (#62) — folder, applied LAST = TOP precedence ===
custom_added = 0
if os.path.isdir(CUSTOM_DIR):
    base = os.path.join(CUSTOM_DIR, "assets")
    if os.path.isdir(base):
        for dp, _, fns in os.walk(base):
            for fn in fns:
                full = os.path.join(dp, fn)
                rel = os.path.relpath(full, CUSTOM_DIR).replace(os.sep, "/")
                if rel.lower().endswith(JUNK):
                    continue
                try:
                    with open(full, "rb") as fh:
                        files[rel] = fh.read()
                    provenance[rel] = "WNL-Custom"
                    custom_added += 1
                except Exception:
                    continue

# === pack.mcmeta (format 34) + CREDITS ===
mcmeta = {"pack": {"pack_format": 34,
    "description": "§6WNL Mega-Pack§r — curated merge (Stay True + FreshAnimations anchors), ported to 1.21.1.\nPrivate/personal use. Credit to all original authors — see CREDITS.txt."}}
credits = ["WNL Mega-Pack — curated personal resource collection (PRIVATE / personal use only).",
           "All textures belong to their original authors. Local merge of packs the user owns,",
           "ported to MC 1.21.1 (format 34), curated per _dev/megapack-curation-rules.md. NOT for redistribution.",
           "", "Source packs (low->high precedence):"]
for f in packs:
    credits.append("  [tier %2d] %s  (+%d assets won)" % (tier(f), f, sum(1 for w in provenance.values() if w == f)))
if custom_added:
    credits.append(""); credits.append("WNL-Custom authoring layer: +%d assets (top precedence)" % custom_added)
if dropped:
    credits.append(""); credits.append("Dropped (mine-only concept packs + removed mods — art not shipped):")
    for f in dropped:
        credits.append("  %s" % f)

# === emit ===
if os.path.exists(OUT):
    os.remove(OUT)
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    z.writestr("pack.mcmeta", json.dumps(mcmeta, indent=2))
    z.writestr("CREDITS.txt", "\n".join(credits))
    for n, data in files.items():
        z.writestr(n, data)

sz = os.path.getsize(OUT) / (1024 * 1024)

# === emit CONDENSED, MANAGEABLE CURATED LIST (_dev/megapack-curated-list.md) for user audit ===
import collections as _c, re as _re
def _short(pk):
    if pk is None: return "—"
    s = _re.sub(r"\xa7.", "", pk)                       # strip §color codes
    s = _re.sub(r"\.zip$", "", s)
    s = _re.sub(r"[ _\-]v?\d[\d.\-+ ()a-z]*$", "", s).strip()  # trim trailing version
    return s[:32] if s else pk[:32]
def _cat(p):
    parts = p.split("/"); ns = parts[1] if len(parts) > 1 else "?"; rest = "/".join(parts[2:])
    if ns == "minecraft":
        if rest.startswith("textures/block/"):  return "BLOCK"
        if rest.startswith("textures/item/"):   return "ITEM"
        if rest.startswith("textures/entity/"): return "ENTITY(tex)"
        if rest.startswith("optifine/cem"):     return "ENTITY(model .jem)"
        if rest.startswith("optifine/random"):  return "ENTITY(variants)"
        if rest.startswith("optifine/ctm"):     return "CTM"
        if rest.startswith("models/"):          return "MODEL"
        if rest.startswith("textures/gui") or "/gui/" in rest: return "GUI"
        if rest.startswith("textures/painting"):return "PAINTING"
        if "font" in rest:                       return "FONT"
        return "MISC-minecraft"
    return "MODDED: " + ns
foot = _c.Counter()
catwin = _c.defaultdict(_c.Counter)   # category -> winner -> count
for p, w in provenance.items():
    foot[w] += 1; catwin[_cat(p)][w] += 1
# per-mob: model (.jem) winner vs primary-texture winner  (the true garble signal)
ent = set()
for p in provenance:
    if p.startswith("assets/minecraft/textures/entity/"):
        s = p.split("/")
        if len(s) > 5: ent.add(s[4])   # require a FILE beyond the mob folder (skip loose entity/*.png)
mobrows = []
for m in sorted(ent):
    jem = provenance.get("assets/minecraft/optifine/cem/%s.jem" % m)
    tex = provenance.get("assets/minecraft/textures/entity/%s/%s.png" % (m, m))
    if not tex:
        for pp, w in sorted(provenance.items()):
            if pp.startswith("assets/minecraft/textures/entity/%s/" % m) and pp.endswith(".png"):
                tex = w; break
    flag = "  ⚠MISMATCH" if (jem and tex and jem != tex) else ""
    mobrows.append((m, jem, tex, flag))
mism = sum(1 for r in mobrows if r[3])
def _w(*cands):
    for c in cands:
        if c in provenance: return provenance[c]
    return None
# RULE COMPLIANCE spot-check: did the spec's key drivers actually win?
RULE_CHECKS = [
    ("#28 Stay True drives vanilla blocks", _w("assets/minecraft/textures/block/stone.png"), "stay true"),
    ("#45 Better Leaves drives leaves",      _w("assets/minecraft/textures/block/oak_leaves.png"), "better-leaves"),
    ("#21 Fluffy drives wool",               _w("assets/minecraft/textures/block/white_wool.png"), "fluffy"),
    ("#1 Armory drives armor",               _w("assets/minecraft/textures/models/armor/diamond_layer_1.png"), "armory"),
    ("#2 Modded Omelet drives spawn eggs",   _w("assets/minecraft/textures/item/allay_spawn_egg.png",
                                                "assets/minecraft/textures/item/creeper_spawn_egg.png"), "omelet"),
    ("#55 FA owns core mob models",          _w("assets/minecraft/optifine/cem/creeper.jem"), ("fa+", "freshanim")),
    ("#36 Musgo must NOT win vanilla blocks", _w("assets/minecraft/textures/block/stone.png"), ("!musgo",)),
    ("#29 enchanting-table driver",          _w("assets/minecraft/textures/block/enchanting_table_top.png"), "enchant"),
]
rc = []
for label, winner, expect in RULE_CHECKS:
    exps = expect if isinstance(expect, tuple) else (expect,)
    if winner is None:
        rc.append("- ?  %s — (asset not present)" % label)
    elif exps[0].startswith("!"):   # negative check: winner must NOT contain the token
        bad = exps[0][1:]
        rc.append(("- ✗  %s — got **%s**" if bad in winner.lower() else "- ✓  %s — %s") % (label, _short(winner)))
    elif any(e in winner.lower() for e in exps):
        rc.append("- ✓  %s — %s" % (label, _short(winner)))
    else:
        rc.append("- ✗  %s — got **%s** (expected ~%s)" % (label, _short(winner), "/".join(exps)))

def _line(c):   # "BLOCK   →  Stay True (3700) · Better Leaves (450) · …"
    tops = catwin[c].most_common(6); extra = len(catwin[c]) - len(tops)
    body = " · ".join("%s (%d)" % (_short(w), n) for w, n in tops)
    if extra > 0: body += " · +%d more" % extra
    return "- **%s** → %s" % (c.ljust(16), body)

ml = ["# WNL Mega-Pack — curated overview  (auto-generated; %d assets / %d packs)" % (len(provenance), len(packs)),
      "", "Audit: find a wrong driver → fix `_dev/megapack-curation-rules.md` + the tier table → rebuild.",
      "", "## Rule compliance (did the spec's drivers win?)"] + rc
ml += ["", "## Mobs — model | texture  (%d mobs · %d ⚠mismatch)" % (len(mobrows), mism),
       "⚠ = model and texture from DIFFERENT packs (garble risk) — check these first.", "", "```"]
for m, jem, tex, flag in mobrows:
    cell = "%-16s %-26s" % (m, _short(jem))
    cell += "" if (jem and tex and jem == tex) else ("| %s" % _short(tex))
    ml.append(cell + ("   <-- MISMATCH" if flag else ""))
ml += ["```", "", "## Vanilla categories — driver (count) · runners-up"]
for c in ["BLOCK", "ITEM", "ENTITY(tex)", "ENTITY(model .jem)", "ENTITY(variants)", "CTM",
          "MODEL", "GUI", "PAINTING", "FONT", "MISC-minecraft"]:
    if c in catwin: ml.append(_line(c))
modded = sorted(k for k in catwin if k.startswith("MODDED") and len(catwin[k]) > 1)
single = sum(1 for k in catwin if k.startswith("MODDED") and len(catwin[k]) == 1)
ml += ["", "## Modded namespaces with >1 pack (%d; %d single-pack omitted)" % (len(modded), single)]
for c in modded:
    ml.append(_line(c).replace("MODDED: ", ""))
ml += ["", "## Pack footprint (assets won)"]
for pk, n in foot.most_common():
    ml.append("- %5d  %s" % (n, _short(pk)))
try:
    with open(os.path.join(ROOT, "_dev", "megapack-curated-list.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(ml))
except Exception as _e:
    print("  (curated list write failed:", _e, ")")

print("=== WNL-MegaPack.zip built (curation engine Phase 1) ===")
print("  %d packs merged, %d dropped, %d unique assets, +%d WNL-Custom, %.1f MB"
      % (len(packs), len(dropped), len(files), custom_added, sz))
print("  OVERLAYS resolved for format %d in %d packs" % (TARGET_FMT, len(overlay_log)))
print("  SANITIZER applied %d fix/drop ops" % len(SANITIZE_LOG))
for s in sorted(set(SANITIZE_LOG)):
    print("    - " + s)
print("\n=== precedence order (low->high = base->override) ===")
last = None
for f in packs:
    t = tier(f)
    if t != last:
        print("  --- tier %d ---" % t); last = t
    print("    %-48s (+%d)" % (f[:48], per_pack_added.get(f, 0)))
if dropped:
    print("\n  DROPPED (mine-only/removed):", ", ".join(dropped))
print("\n  vanilla textures resolved from:")
for ns_pref in ("assets/minecraft/textures/block/stone.png", "assets/minecraft/textures/block/grass_block_top.png",
                "assets/minecraft/textures/block/oak_planks.png"):
    print("    %-44s <- %s" % (ns_pref.split("block/")[1], provenance.get(ns_pref, "(vanilla default)")))
