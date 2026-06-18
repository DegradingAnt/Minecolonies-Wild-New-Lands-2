#!/usr/bin/env python3
"""Per-mod inclusive sample attribution from a JFR dump.
Usage: jfr_mod_attribution.py <file.jfr> [start hh:mm:ss] [end hh:mm:ss]
Attributes each ExecutionSample to mods via (a) package roots, (b) mixin
handler frame names (handler$x$modid$y). Reports Render thread, Server
thread, and c2me-worker pool separately."""
import subprocess, sys, re
from collections import Counter

JFR = r"C:\Users\linde\Adoptium\jdk-25.0.3+9\bin\jfr.exe"
path, t0, t1 = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else None), (sys.argv[3] if len(sys.argv) > 3 else None)

SKIP = re.compile(r"^(java\.|jdk\.|sun\.|com\.sun\.|net\.minecraft\.|net\.neoforged\.|cpw\.mods\.|org\.lwjgl|com\.mojang\.|org\.spongepowered\.|it\.unimi\.|com\.google\.|org\.slf4j|io\.netty|com\.electronwill|org\.apache|kotlin|org\.joml|oshi\.|org\.objectweb|com\.llamalad7|org\.openjdk)")
MIXIN = re.compile(r"\$[a-z]{3}\d{3}\$([a-zA-Z_0-9]+?)\$")
ALIAS = {
    "caffeinemc": "sodium", "simibubi": "create", "createmod": "create(catnip/ponder)",
    "engine_room": "flywheel", "teamabnormals": "blueprint-family(CC/autumnity/...)",
    "creative": "creativecore/ambientsounds", "mehvahdjukaar": "moonlight/supplementaries",
    "aetherianartificer": "townstead", "theillusivec4": "curios", "maxhenkel": "voicechat",
    "seibel": "distanthorizons", "irisshaders": "iris", "ftb": "ftb-mods",
    "jedlimlx": "supplemental_patches", "tterrag": "registrate", "rbasamoyai": "createbigcannons",
    "piglinmine": "jeioptimizer", "coolerpromc": "uncrafteverything", "buuz135": "stv/functionalstorage",
    "minecolonies": "minecolonies", "ldtteam": "minecolonies/structurize",
}

def mod_of(frame):
    m = MIXIN.search(frame)
    if m:
        return "mixin:" + m.group(1)
    if SKIP.match(frame):
        return None
    m = re.match(r"([a-z][a-z_0-9]*)\.([a-zA-Z_0-9]+)\.", frame)
    if not m:
        return None
    seg1, seg2 = m.group(1), m.group(2)
    if seg1 in ("com", "net", "dev", "io", "me", "org", "top", "de", "ca", "at", "fr", "vazkii", "team", "einstein", "fuzs", "gg", "xyz", "cy", "uk", "se", "nl", "dan", "tv", "owmii", "snownee", "mod", "earth", "club", "moe", "eu", "binnie", "satisfy"):
        key = seg2.lower()
    else:
        key = seg1.lower()
    return ALIAS.get(key, key)

groups = {"Render thread": Counter(), "Server thread": Counter(), "c2me-workers": Counter()}
totals = Counter()
cur_time = None; cur_thread = None; frames = []; in_stack = False

def flush():
    if cur_thread is None: return
    if t0 and cur_time and not (t0 <= cur_time <= (t1 or "99")): return
    g = None
    if cur_thread == "Render thread": g = "Render thread"
    elif cur_thread == "Server thread": g = "Server thread"
    elif cur_thread.startswith("c2me-worker"): g = "c2me-workers"
    if g is None: return
    totals[g] += 1
    mods = set()
    for f in frames:
        mm = mod_of(f)
        if mm: mods.add(mm.replace("mixin:", ""))
    for mname in mods:
        groups[g][mname] += 1

for line in subprocess.Popen([JFR, "print", "--events", "jdk.ExecutionSample", path],
                             stdout=subprocess.PIPE, text=True, errors="replace", bufsize=1 << 20).stdout:
    line = line.rstrip("\n")
    if line.startswith("jdk.ExecutionSample"):
        flush(); cur_time = None; cur_thread = None; frames = []; in_stack = False; continue
    m = re.search(r"startTime = (\d{2}:\d{2}:\d{2})", line)
    if m: cur_time = m.group(1); continue
    m = re.search(r'sampledThread = "([^"]+)"', line)
    if m: cur_thread = m.group(1); continue
    if "stackTrace = [" in line: in_stack = True; continue
    if in_stack:
        if line.strip() == "]": in_stack = False
        else:
            fr = line.strip()
            frames.append(fr[3:] if fr.startswith("at ") else fr)
flush()

print(f"window: {t0 or 'ALL'}..{t1 or 'ALL'}")
for g in ("Render thread", "Server thread", "c2me-workers"):
    n = max(totals[g], 1)
    print(f"\n== {g}: {totals[g]} samples — inclusive % (sample contains mod code)")
    for mname, c in groups[g].most_common(28):
        print(f"  {100*c/n:5.1f}%  {mname}")
