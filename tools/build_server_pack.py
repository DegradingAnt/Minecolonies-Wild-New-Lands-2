#!/usr/bin/env python3
"""Assemble a NeoForge server pack from the client instance.
Strips: (a) every mod that declares side=CLIENT (NeoForge skips these anyway), and
(b) a curated list of client-only-but-UNDECLARED mods (DH, shaders, minimap, render,
audio, cosmetic) that would crash or are useless on a dedicated server.
Copies the rest + config/ + writes start script, server.properties, eula, README.
NOTE: a headless test-boot is the finalizing step -- it catches any straggler client
mod that crashes; add it to CURATED and re-run."""
import os, re, zipfile, shutil, json

ROOT = r"C:/Users/linde/curseforge/minecraft/Instances/Ultimate vibes distant horizons version"
OUT  = r"C:/Users/linde/curseforge/UltimateVibes-ServerPack"
MODS = os.path.join(ROOT, "mods")

# curated client-only mods that do NOT declare side=CLIENT (match by filename substring, lowercase)
CURATED = [
    "distanthorizons", "journeymap", "jmi", "jade-", "jadeaddons", "jadecolonies",
    "waveycapes", "skinlayers3d", "betterf3", "euphoriapatcher", "supplemental_patches",
    "irisveil", "continuity", "ambientsounds", "sound_physics", "presencefootsteps",
    "immersive_melodies", "medievalmusic", "biomemusic", "whitenoise", "enhancedvisuals",
    "justzoom", "betterthirdperson", "highlighter", "advancementplaques", "legendarytooltips",
    "simplytooltips", "modnametooltip", "effectdescriptions", "sodium-shadowy-path",
    "entityculling", "moreculling", "wavey", "boatiview", "spyglass_improvements",
    "chat_heads", "pingwheel", "betteradvancements", "controlling", "reeses-sodium",
    "embeddium", "oculus", "rubidium", "nvidium", "iris-", "sodium-", "partic5", "particull",
    "particlerain", "asyncparticles", "lambdynamiclights", "lambdynlights", "subtle_effects",
    "fancymenu", "drippyloadingscreen", "puzzlesaccesspoint", "dynamic_resource_bars",
    "immersiveoverlays", "appleskin", "bobby", "betterclouds", "complementary",
]

def declares_client_only(jar):
    try:
        with zipfile.ZipFile(os.path.join(MODS, jar)) as z:
            t = ""
            for c in ("META-INF/neoforge.mods.toml", "META-INF/mods.toml"):
                if c in z.namelist():
                    t = z.read(c).decode("utf-8", "replace"); break
            sides = re.findall(r'side\s*=\s*"([^"]+)"', t)
            return bool(sides) and all(s.upper() == "CLIENT" for s in sides)
    except Exception:
        return False

def is_curated(jar):
    jl = jar.lower()
    return any(k in jl for k in CURATED)

jars = [j for j in os.listdir(MODS) if j.endswith(".jar")]
strip = [j for j in jars if declares_client_only(j) or is_curated(j)]
keep  = [j for j in jars if j not in strip]

if os.path.isdir(OUT):
    shutil.rmtree(OUT)
os.makedirs(os.path.join(OUT, "mods"))
for j in keep:
    shutil.copy2(os.path.join(MODS, j), os.path.join(OUT, "mods", j))
# configs (server reads many of the same)
shutil.copytree(os.path.join(ROOT, "config"), os.path.join(OUT, "config"))
# the consolidated datapack travels with config/paxi already (inside config/)

open(os.path.join(OUT, "eula.txt"), "w").write("eula=true\n")
open(os.path.join(OUT, "server.properties"), "w").write(
    "motd=Ultimate Vibes (Distant Horizons)\nlevel-name=world\nmax-players=8\n"
    "view-distance=12\nsimulation-distance=10\nallow-flight=true\nspawn-protection=0\n"
    "online-mode=true\nenforce-secure-profile=false\n")
open(os.path.join(OUT, "user_jvm_args.txt"), "w").write(
    "# Java 25 + ZGC, 16G for server. Adjust -Xmx to your host RAM.\n"
    "-Xms8G\n-Xmx16G\n-XX:+UseZGC\n--enable-native-access=ALL-UNNAMED\n")
open(os.path.join(OUT, "START-README.txt"), "w").write(
    "Ultimate Vibes - server pack\n"
    "============================\n"
    "1. Install the NeoForge 21.1.233 DEDICATED SERVER into this folder\n"
    "   (https://neoforged.net -> 21.1.233 -> Installer -> --installServer).\n"
    "   That creates run.bat / run.sh + libraries/.\n"
    "2. Java 25 required (Temurin 25). user_jvm_args.txt sets ZGC + 16G.\n"
    "3. eula.txt is pre-accepted. Edit server.properties as needed.\n"
    "4. Run run.bat (Windows) / run.sh (Linux).\n"
    f"\nClient-only mods stripped: {len(strip)}. Kept: {len(keep)}.\n"
    "If the server crashes on boot referencing a client class, that mod is client-only\n"
    "and undeclared -- add its filename to CURATED in .uvrun/build_server_pack.py and re-run.\n")

json.dump({"stripped": sorted(strip), "kept_count": len(keep)},
          open(os.path.join(OUT, "_strip_manifest.json"), "w"), indent=1)
print(f"=== server pack -> {OUT} ===")
print(f"   kept {len(keep)} mods, stripped {len(strip)} client-only")
print(f"   stripped sample: {sorted(strip)[:8]}")
print("   + config/, eula, server.properties, user_jvm_args, README")
print("   NEXT: install NeoForge 21.1.233 dedicated server into the folder, then headless-test.")
