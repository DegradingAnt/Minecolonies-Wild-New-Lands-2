"""Revised tagged mod list (multiplayer-optimised pack) -> .uvrun/mod-list.txt
Tags: [BLOAT:cat] (MP-aware: singleplayer-pointless DROPPED), [EXTERNAL], [CUSTOM], [FIXn].
Prints the tagged subset to console."""
import json, os, re

INST = r"C:\Users\linde\curseforge\minecraft\Instances\Ultimate vibes distant horizons version"
meta = json.load(open(os.path.join(INST, ".uvrun", "modmeta.json"), encoding="utf-8"))
present = {e["file"] for e in meta}
try:
    suspects = {s["file"]: s for s in json.load(open(os.path.join(INST, ".uvrun", "bloat-suspects.json"), encoding="utf-8"))["suspects"]}
except Exception:
    suspects = {}

# MULTIPLAYER PACK: these categories are NOT bloat here. Drop them.
DROP_CATEGORIES = {"singleplayer-pointless"}

cf_files = set()
try:
    mi = json.load(open(os.path.join(INST, "minecraftinstance.json"), encoding="utf-8", errors="replace"))
    for a in mi.get("installedAddons", []):
        f = (a.get("installedFile") or {}).get("fileNameOnDisk")
        if f: cf_files.add(f.lower())
except Exception as e:
    print("WARN minecraftinstance.json:", e)

FIXES = {
    "quark": "FIX1+14", "spawn": "FIX2", "create": "FIX4",
    "supplemental_patches": "FIX5/7/8/9", "veil": "FIX6", "moonlight": "FIX10",
    "supplementaries": "FIX10", "expanded_combat": "FIX11", "tombstone": "FIX12",
    "journeymap": "FIX15",
}
CUSTOM_PAT = re.compile(r"-local|packfixes|sable-compat", re.I)

lines = []          # full list
bloat, ext, cust, patch = [], [], [], []
for e in sorted(meta, key=lambda x: x["file"].lower()):
    f = e["file"]
    ids = [m.get("modId") or "?" for m in e["mods"]] or ["?"]
    name = "; ".join(str(m.get("name")) for m in e["mods"]) if e["mods"] else e.get("note", "?")
    tags = []
    s = suspects.get(f)
    if s and s.get("category") not in DROP_CATEGORIES:
        verdict = s.get("verdict", "unverified")
        mark = "BLOAT!" if verdict == "confirmed" else ("BLOAT?" if verdict in ("unverified", "uncertain") else "")
        if verdict == "cleared": mark = ""
        if mark:
            tags.append("[%s %s]" % (mark, s.get("category")))
            bloat.append((mark, f, s.get("category"), (s.get("reason") or "")[:160]))
    if f.lower() not in cf_files:
        tags.append("[EXTERNAL]"); ext.append(f)
    if CUSTOM_PAT.search(f):
        tags.append("[CUSTOM]"); cust.append(f)
    fix = ""
    for mid in ids:
        if mid in FIXES: fix = FIXES[mid]
    if "mrpgc" in f.lower(): fix = "FIX3"
    if fix:
        tags.append("[%s]" % fix); patch.append((f, fix))
    lines.append(("%-58s %-46s %s" % (f, name[:45], " ".join(tags))).rstrip())

# vanilla patch note
patch.append(("(vanilla ItemStack)", "FIX13"))

out = os.path.join(INST, ".uvrun", "mod-list.txt")
with open(out, "w", encoding="utf-8") as fh:
    fh.write("ULTIMATE VIBES - mod list (multiplayer-optimised), %d jars / %d mod ids\n" % (len(meta), sum(len(e['mods']) for e in meta)))
    fh.write("Tags: [BLOAT! cat]=verified suspect  [BLOAT? cat]=needs-your-call  [EXTERNAL]=not from CurseForge  [CUSTOM]=local/hand-built  [FIXn]=patched by PackFixes\n")
    fh.write("(multiplayer pack: mods are NOT flagged for being multiplayer-focused)\n\n")
    fh.write("\n".join(lines))
print("wrote", out)

def show(title, items):
    print("\n=== %s (%d) ===" % (title, len(items)))
    for it in items: print(" ", it)

print("\nBLOAT SUSPECTS (MP-aware):")
for mark, f, cat, reason in sorted(bloat, key=lambda x: (x[0] != "BLOAT!", x[2])):
    print("  %-7s %-22s %s\n           %s" % (mark, cat, f, reason))
show("EXTERNAL (non-CurseForge)", ext)
show("CUSTOM builds", cust)
print("\n=== PATCHED by PackFixes (%d) ===" % len(patch))
for f, fix in patch: print("  %-10s %s" % (fix, f))
