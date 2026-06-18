#!/usr/bin/env python3
"""Comprehensive 'export ALL changed stuff' for the Ultimate Vibes pack.
Regenerates a Desktop bundle from CURRENT instance state (idempotent -> safe to
run on a schedule/hook). Mirrors the established 2026-06-17 export layout.
Usage: export_pack.py [output_dir]   (default: Desktop\\UltimateVibes-Pack-Export)
"""
import os, sys, shutil, glob, datetime

ROOT = r"C:\Users\linde\curseforge\minecraft\Instances\Ultimate vibes distant horizons version"
OUT = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\linde\Desktop\UltimateVibes-Pack-Export"

# config files/dirs that are intentionally tuned for this pack (the "changed configs")
CHANGED_CONFIGS = [
    "DistantHorizons.toml", "dynamic_difficulty-common.toml", "entity_model_features.json",
    "logbegone.json", "modernfix-mixins.properties", "uvdhsmooth.properties",
    "calmtheleaks-common.toml", "almostunified", "spark",
]
# configs that ALSO belong on the dedicated server (worldgen / server-side mods)
SERVER_CONFIGS = ["calmtheleaks-common.toml", "logbegone.json", "DistantHorizons.toml",
                  "dynamic_difficulty-common.toml", "spark"]
# server-relevant custom mods (worldgen/server-side) -- DHSmooth is client-only and excluded
SERVER_MODS = ["UltimateVibes-PackFixes-", "UltimateVibes-MineColoniesCache-",
               "UltimateVibes-ArchersAttrFix-", "UltimateVibes-FTBChunksOffload-"]


def cp(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.isdir(src):
        shutil.copytree(src, dst, dirs_exist_ok=True)
    elif os.path.isfile(src):
        shutil.copy2(src, dst)


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    n = {"mods": 0, "config": 0, "datapacks": 0, "rp": 0, "server": 0}

    # ---- instance-overlay (client drop-in) ----
    ov = os.path.join(OUT, "instance-overlay")
    for j in glob.glob(os.path.join(ROOT, "mods", "UltimateVibes-*.jar")):
        cp(j, os.path.join(ov, "mods", os.path.basename(j))); n["mods"] += 1
    for c in CHANGED_CONFIGS:
        s = os.path.join(ROOT, "config", c)
        if os.path.exists(s):
            cp(s, os.path.join(ov, "config", c)); n["config"] += 1
    # Paxi compat datapack + load order
    if os.path.isdir(os.path.join(ROOT, "config", "paxi")):
        cp(os.path.join(ROOT, "config", "paxi"), os.path.join(ov, "config", "paxi"))
    for z in glob.glob(os.path.join(ROOT, "datapacks", "*.zip")):
        cp(z, os.path.join(ov, "datapacks", os.path.basename(z))); n["datapacks"] += 1
    for z in glob.glob(os.path.join(ROOT, "resourcepacks", "UltimateVibes-*.zip")):
        cp(z, os.path.join(ov, "resourcepacks", os.path.basename(z))); n["rp"] += 1

    # ---- server-upload (DatHost) ----
    su = os.path.join(OUT, "server-upload")
    for j in glob.glob(os.path.join(ROOT, "mods", "UltimateVibes-*.jar")):
        if any(os.path.basename(j).startswith(p) for p in SERVER_MODS):
            cp(j, os.path.join(su, os.path.basename(j))); n["server"] += 1
    # patched DH server jar from prior server-delivery if present
    for dh in glob.glob(os.path.join(ROOT, ".uvrun", "server-delivery", "DistantHorizons-*.jar")):
        cp(dh, os.path.join(su, os.path.basename(dh)))
    if os.path.isdir(os.path.join(ROOT, "config", "paxi", "datapacks", "UltimateVibes-Compat")):
        cp(os.path.join(ROOT, "config", "paxi", "datapacks", "UltimateVibes-Compat"),
           os.path.join(su, "UltimateVibes-Compat"))
    for c in SERVER_CONFIGS:
        s = os.path.join(ROOT, "config", c)
        if os.path.exists(s):
            cp(s, os.path.join(su, "config", c))

    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(os.path.join(OUT, "README.txt"), "w", encoding="utf-8") as f:
        f.write(
            "UltimateVibes — full pack export (auto-generated)\n"
            "=================================================\n"
            f"Generated: {stamp} from current instance state.\n\n"
            "instance-overlay/  -> drop into your client instance (merge mods/, config/,\n"
            f"   datapacks/, resourcepacks/). Custom mods: {n['mods']}, changed configs: {n['config']},\n"
            f"   global datapacks: {n['datapacks']}, resourcepacks: {n['rp']}.\n"
            "server-upload/     -> upload to the DatHost server's mods/ (worldgen + server fixes)\n"
            f"   + the UltimateVibes-Compat datapack. Server custom mods: {n['server']}.\n"
            "   (DHSmooth is client-only and intentionally NOT here.)\n\n"
            "This bundle is regenerated automatically at the end of each session.\n"
        )
    print(f"EXPORT OK -> {OUT}")
    print("  " + ", ".join(f"{k}={v}" for k, v in n.items()))


if __name__ == "__main__":
    main()
