#!/usr/bin/env python3
"""Find render-thread stall windows: biggest gaps between consecutive Render thread
execution samples, plus synchronous I/O events on the Render thread.
Usage: jfr_timeline.py <file.jfr>"""
import subprocess, sys, re
from collections import Counter, defaultdict

JFR = r"C:\Users\linde\Adoptium\jdk-25.0.3+9\bin\jfr.exe"
path = sys.argv[1]


def to_ms(hms, frac):
    h, m, s = hms.split(":")
    return ((int(h) * 60 + int(m)) * 60 + int(s)) * 1000 + int(frac.ljust(3, "0")[:3])


# --- 1. Render thread execution-sample timeline: find biggest gaps ---
proc = subprocess.Popen([JFR, "print", "--events", "jdk.ExecutionSample", path],
                        stdout=subprocess.PIPE, text=True, errors="replace", bufsize=1 << 20)
render_times = []
cur_t = None
cur_thread = None
for line in proc.stdout:
    s = line.strip()
    if s.startswith("jdk.ExecutionSample"):
        cur_t = None; cur_thread = None
        continue
    m = re.search(r"startTime = (\d{2}:\d{2}:\d{2})\.(\d+)", s)
    if m:
        cur_t = to_ms(m.group(1), m.group(2))
    m = re.search(r'sampledThread = "([^"]+)"', s)
    if m:
        cur_thread = m.group(1)
        if cur_thread == "Render thread" and cur_t is not None:
            render_times.append(cur_t)
render_times.sort()
print(f"Render thread samples: {len(render_times)}")
if render_times:
    span = (render_times[-1] - render_times[0]) / 1000
    print(f"sampling span: {span:.1f}s -> avg {len(render_times)/max(span,1):.1f} samples/s (lower = more stalled)")
gaps = []
for i in range(1, len(render_times)):
    g = render_times[i] - render_times[i - 1]
    if g > 120:  # >120ms gap = a visible hitch
        gaps.append((g, render_times[i - 1]))
gaps.sort(reverse=True)
print(f"\n== Render-thread sampling GAPS >120ms (visible hitches): {len(gaps)}")
for g, t in gaps[:20]:
    ts = t / 1000
    hh = int(ts // 3600); mm = int((ts % 3600) // 60); ss = ts % 60
    print(f"  {g:7.0f}ms gap  ending ~{hh:02d}:{mm:02d}:{ss:06.3f}")

# --- 2. Synchronous I/O on the Render thread ---
for ev in ["jdk.FileRead", "jdk.FileWrite", "jdk.SocketRead", "jdk.SocketWrite"]:
    p = subprocess.Popen([JFR, "print", "--events", ev, path],
                         stdout=subprocess.PIPE, text=True, errors="replace", bufsize=1 << 20)
    blocks = p.stdout.read().split(ev)
    render_io = []
    for b in blocks:
        if "Render thread" not in b:
            continue
        md = re.search(r"duration = ([\d,\.]+) (ms|s|us)", b)
        if not md:
            continue
        val = float(md.group(1).replace(",", "."))
        if md.group(2) == "us":
            val /= 1000
        elif md.group(2) == "s":
            val *= 1000
        path_m = re.search(r'path = "?([^"\n]+)"?', b)
        render_io.append((val, path_m.group(1) if path_m else "?"))
    if render_io:
        render_io.sort(reverse=True)
        tot = sum(x[0] for x in render_io)
        print(f"\n== {ev} on Render thread: {len(render_io)} events, total {tot:.1f}ms")
        for val, pth in render_io[:8]:
            print(f"  {val:7.2f}ms  {pth[:80]}")
