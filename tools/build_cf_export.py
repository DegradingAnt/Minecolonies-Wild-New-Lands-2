#!/usr/bin/env python3
"""Build a publishable CurseForge export (manifest.json + overrides/) of the client pack.
- manifest = CF-distributable mods (projectID/fileID from minecraftinstance.json) for every
  mods/ jar that CF fingerprint-matched AND we did not author/modify.
- overrides/mods = our authored/modified jars (UltimateVibes-*, repackaged supplemental_patches,
  any sideloaded jar with no CF match) so the pack is self-contained + license-clean.
- overrides/ = config (incl. the consolidated UltimateVibes-Compat datapack) + resourcepacks +
  options.txt + defaultconfigs. Junk (.uvrun/.claude/logs/saves/DH cache) excluded.
LICENSING: we only redistribute our OWN jars in overrides/mods; CF mods download from CF."""
import json, os, zipfile, shutil

ROOT = r"C:/Users/linde/curseforge/minecraft/Instances/Ultimate vibes distant horizons version"
OUT_DIR = r"C:/Users/linde/curseforge"
STAGE = os.path.join(OUT_DIR, "_uvcf_stage")
MODS = os.path.join(ROOT, "mods")

inst = json.load(open(os.path.join(ROOT, "minecraftinstance.json"), encoding="utf-8"))
# fileName -> (projectID, fileID)
by_name = {}
for e in inst.get("installedAddons", []):
    f = e.get("installedFile") or {}
    fn = f.get("fileName") or e.get("fileNameOnDisk")
    if fn and e.get("addonID") and f.get("id"):
        by_name[fn] = (e["addonID"], f["id"])

# jars WE authored -> ship in overrides/mods (NOT manifest). Only our own code is bundled;
# everything CF-distributable (incl. supplemental_patches, which our resourcepack fixes on top
# of CF's pristine jar) downloads from CF. Sideloaded jars with no CF match also get bundled.
def is_ours(jar):
    return jar.lower().startswith("ultimatevibes")

jars = [j for j in os.listdir(MODS) if j.endswith(".jar")]
manifest_files = []
override_mods = []
unmatched = []
for j in jars:
    if is_ours(j):
        override_mods.append(j)
    elif j in by_name:
        pid, fid = by_name[j]
        manifest_files.append({"projectID": pid, "fileID": fid, "required": True})
    else:
        override_mods.append(j); unmatched.append(j)  # sideloaded / fingerprint miss

if os.path.isdir(STAGE):
    shutil.rmtree(STAGE)
os.makedirs(os.path.join(STAGE, "overrides", "mods"))

manifest = {
    "minecraft": {"version": "1.21.1", "modLoaders": [{"id": "neoforge-21.1.233", "primary": True}]},
    "manifestType": "minecraftModpack", "manifestVersion": 1,
    "name": "Ultimate Vibes (Distant Horizons)", "version": "1.0.0", "author": "",
    "files": manifest_files, "overrides": "overrides",
}
json.dump(manifest, open(os.path.join(STAGE, "manifest.json"), "w"), indent=2)
open(os.path.join(STAGE, "modlist.html"), "w").write(
    "<ul>" + "".join(f"<li>{f['projectID']}:{f['fileID']}</li>" for f in manifest_files) + "</ul>")

# overrides: our mods
for j in override_mods:
    shutil.copy2(os.path.join(MODS, j), os.path.join(STAGE, "overrides", "mods", j))
# overrides: config + resourcepacks + options.txt + defaultconfigs (skip junk)
for sub in ("config", "resourcepacks", "defaultconfigs"):
    src = os.path.join(ROOT, sub)
    if os.path.isdir(src):
        shutil.copytree(src, os.path.join(STAGE, "overrides", sub))
for fl in ("options.txt",):
    if os.path.isfile(os.path.join(ROOT, fl)):
        shutil.copy2(os.path.join(ROOT, fl), os.path.join(STAGE, "overrides", fl))

# zip it
zip_path = os.path.join(OUT_DIR, "UltimateVibes-CF.zip")
if os.path.exists(zip_path):
    os.remove(zip_path)
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for dp, _dn, fns in os.walk(STAGE):
        for fn in fns:
            full = os.path.join(dp, fn)
            z.write(full, os.path.relpath(full, STAGE))
shutil.rmtree(STAGE)
sz = os.path.getsize(zip_path) / 1e6
print(f"=== CF export -> {zip_path} ({sz:.1f} MB) ===")
print(f"   manifest CF mods: {len(manifest_files)}")
print(f"   overrides/mods (ours+local): {len(override_mods)} -> {sorted(override_mods)}")
print(f"   fingerprint-miss (sideloaded, also bundled): {len(unmatched)} -> {sorted(unmatched)[:6]}")
