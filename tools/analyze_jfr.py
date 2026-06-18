#!/usr/bin/env python3
"""Aggregate jdk.ExecutionSample events from a JFR dump.
Usage: analyze_jfr.py <file.jfr> [start_hh:mm:ss] [end_hh:mm:ss]
Prints: samples per thread; top deepest-app frames on Render thread;
inclusive subsystem buckets on Render thread."""
import subprocess, sys, re
from collections import Counter

JFR = r"C:\Users\linde\Adoptium\jdk-25.0.3+9\bin\jfr.exe"
path = sys.argv[1]
t0 = sys.argv[2] if len(sys.argv) > 2 else None
t1 = sys.argv[3] if len(sys.argv) > 3 else None

proc = subprocess.Popen([JFR, "print", "--events", "jdk.ExecutionSample", path],
                        stdout=subprocess.PIPE, text=True, errors="replace", bufsize=1 << 20)

thread_counts = Counter()
render_top = Counter()
render_buckets = Counter()
render_total = 0

BUCKETS = {
    "jei": "JEI", "uncrafteverything": "uncrafteverything", "jeioptimizer": "jeioptimizer",
    "sodium": "sodium/embeddium", "iris": "iris", "distanthorizons": "DistantHorizons",
    "seasonhud": "seasonhud", "journeymap": "journeymap", "minecolonies": "minecolonies",
    "supplementaries": "supplementaries", "create": "create", "flywheel": "flywheel",
    "entityculling": "entityculling", "immediatelyfast": "immediatelyfast",
    "farmersdelight": "farmersdelight", "voicechat": "voicechat",
    "LevelRenderer": "vanilla LevelRenderer", "EntityRenderDispatcher": "vanilla entity rendering",
    "ParticleEngine": "vanilla particles", "GameRenderer": "vanilla GameRenderer",
    "BlockEntityRenderDispatcher": "vanilla blockentity rendering",
    "skinlayers": "skinlayers3d", "physicsmod": "physics", "waveycapes": "waveycapes",
    "presencefootsteps": "presencefootsteps", "ambientsounds": "ambientsounds",
    "epherolib": "epherolib", "veil": "veil", "enhancedvisuals": "enhancedvisuals",
    "particlerain": "particlerain", "subtle_effects": "subtle_effects", "wakes": "wakes",
}

cur_time = None
cur_thread = None
frames = []
in_stack = False

def flush():
    global render_total
    if cur_thread is None:
        return
    if t0 and cur_time and not (t0 <= cur_time <= (t1 or "99")):
        return
    thread_counts[cur_thread] += 1
    if cur_thread == "Render thread":
        render_total_inc()
        # deepest non-JDK frame
        for f in frames:
            if not re.match(r"(java\.|jdk\.|sun\.|com\.sun\.|org\.lwjgl)", f):
                render_top[f.split("(")[0]] += 1
                break
        hits = set()
        for f in frames:
            fl = f.lower()
            for key, label in BUCKETS.items():
                if key.lower() in fl:
                    hits.add(label)
        for h in hits:
            render_buckets[h] += 1

def render_total_inc():
    global render_total
    render_total += 1

for line in proc.stdout:
    line = line.rstrip("\n")
    m = re.match(r"jdk\.ExecutionSample", line)
    if m:
        flush()
        cur_time = None; cur_thread = None; frames = []; in_stack = False
        continue
    m = re.search(r"startTime = \d{2}:\d{2}:\d{2}", line)
    if m:
        cur_time = m.group(0)[-8:]
        continue
    m = re.search(r'sampledThread = "([^"]+)"', line)
    if m:
        cur_thread = m.group(1)
        continue
    if "stackTrace = [" in line:
        in_stack = True
        continue
    if in_stack:
        if line.strip() == "]":
            in_stack = False
        else:
            fr = line.strip()
            if fr.startswith("at "):
                fr = fr[3:]
            frames.append(fr)
flush()

print(f"window: {t0 or 'ALL'}..{t1 or 'ALL'}")
print("== samples per thread (top 10):")
for t, c in thread_counts.most_common(10):
    print(f"  {c:6d}  {t}")
print(f"== Render thread: {render_total} samples")
print("== Render thread deepest app frames (top 25):")
for f, c in render_top.most_common(25):
    print(f"  {c:6d} ({100*c/max(render_total,1):4.1f}%)  {f}")
print("== Render thread inclusive subsystem buckets:")
for b, c in render_buckets.most_common(20):
    print(f"  {c:6d} ({100*c/max(render_total,1):4.1f}%)  {b}")
