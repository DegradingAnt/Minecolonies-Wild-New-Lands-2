"""Build the full mod inventory spreadsheet -> .uvrun/mod-spreadsheet.tsv (+xlsx if openpyxl).
Columns: Jar, ModId, Name, Version, SizeMB, Bloat verdict/category/reason,
Source (curseforge/external), Custom build, PackFixes patches."""
import json, os, re

INST = r"C:\Users\linde\curseforge\minecraft\Instances\Ultimate vibes distant horizons version"
meta = json.load(open(os.path.join(INST, ".uvrun", "modmeta.json"), encoding="utf-8"))
try:
    suspects = {s["file"]: s for s in json.load(open(os.path.join(INST, ".uvrun", "bloat-suspects.json"), encoding="utf-8"))["suspects"]}
except Exception:
    suspects = {}

# CurseForge-tracked files
cf_files = set()
try:
    mi = json.load(open(os.path.join(INST, "minecraftinstance.json"), encoding="utf-8", errors="replace"))
    for a in mi.get("installedAddons", []):
        f = (a.get("installedFile") or {}).get("fileNameOnDisk")
        if f: cf_files.add(f.lower())
except Exception as e:
    print("WARN minecraftinstance.json:", e)

# PackFixes fix -> modid mapping (Fix 13 targets vanilla, gets its own row)
FIXES = {
    "quark": "Fix1 tiny-potato null-guard; Fix14 biolith (JiJ) registry re-seed",
    "spawn": "Fix2 fieldguide reflection guard",
    "create": "Fix4 Ponder StitchedSprite thread-safety (JiJ catnip)",
    "supplemental_patches": "Fix5 RENDERTARGETS regex; Fix7 uniform dedupe; Fix8 catch-all; Fix9 stitch guard",
    "veil": "Fix6 PerformanceRenderTargetMixin disabled",
    "moonlight": "Fix10 host: SimpleMixinPlugin head-guard",
    "supplementaries": "Fix10 CompatSodiumFluidRendererMixin disabled",
    "expanded_combat": "Fix11 vanilla-tab guard",
    "tombstone": "Fix12 getAmplifier config guard",
    "journeymap": "Fix15 join-event guard",
}
# mrpgc: resolve by file name pattern
CUSTOM_PAT = re.compile(r"-local|packfixes|sable-compat", re.I)

rows = []
for e in meta:
    f = e["file"]
    ids = [m.get("modId") or "?" for m in e["mods"]] or ["?"]
    names = "; ".join(str(m.get("name")) for m in e["mods"]) if e["mods"] else e.get("note", "?")
    vers = "; ".join(str(m.get("version")) for m in e["mods"]) if e["mods"] else ""
    s = suspects.get(f, {})
    bloat_verdict = s.get("verdict", "")
    if bloat_verdict == "unverified": bloat_verdict = "suspect (unverified)"
    elif bloat_verdict == "confirmed": bloat_verdict = "SUSPECT (verified)"
    elif bloat_verdict == "cleared": bloat_verdict = "cleared (keep)"
    bloat_info = " | ".join(x for x in (s.get("category"), s.get("reason")) if x)
    evidence = s.get("evidence") or ""
    source = "curseforge" if f.lower() in cf_files else "EXTERNAL"
    custom = "CUSTOM" if CUSTOM_PAT.search(f) else ""
    patched = ""
    for mid in ids:
        if mid in FIXES: patched = FIXES[mid]
    if "mrpgc" in f.lower() or "MRPGC" in names:
        patched = "Fix3 skill_tree class remap"
    rows.append([f, ",".join(ids), names, vers, e["sizeMB"], bloat_verdict, source, custom, patched, bloat_info, evidence])

rows.append(["(vanilla minecraft 1.21.1)", "minecraft", "Minecraft (NeoForge runtime)", "1.21.1/21.1.233", "",
             "", "mojang/neoforge", "", "Fix13 ItemStack.getHoverName guard (systemic)", "", ""])

HEAD = ["Jar file", "Mod ID", "Name", "Version", "Size MB", "Bloat verdict", "Source", "Custom build",
        "PackFixes patches", "Bloat category | reason", "Verify evidence"]
tsv = os.path.join(INST, ".uvrun", "mod-spreadsheet.tsv")
with open(tsv, "w", encoding="utf-8") as out:
    out.write("\t".join(HEAD) + "\n")
    for r in rows:
        out.write("\t".join(str(c).replace("\t", " ").replace("\n", " ") for c in r) + "\n")
print("tsv rows:", len(rows))
try:
    import openpyxl
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Mods"
    ws.append(HEAD)
    for r in rows: ws.append(r)
    wb.save(os.path.join(INST, ".uvrun", "mod-spreadsheet.xlsx"))
    print("xlsx written")
except ImportError:
    print("no openpyxl - tsv only")
print("external count:", sum(1 for r in rows if r[6] == "EXTERNAL"))
print("custom count:", sum(1 for r in rows if r[7] == "CUSTOM"))
print("patched jars:", sum(1 for r in rows if r[8]))
print("bloat: verified=%d unverified=%d cleared=%d" % (
    sum(1 for r in rows if r[5] == "SUSPECT (verified)"),
    sum(1 for r in rows if r[5] == "suspect (unverified)"),
    sum(1 for r in rows if r[5] == "cleared (keep)")))
