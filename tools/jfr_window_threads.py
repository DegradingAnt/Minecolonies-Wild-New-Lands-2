#!/usr/bin/env python3
"""Count execution samples per thread within a time window.
Usage: jfr_window_threads.py <file.jfr> <start hh:mm:ss.mmm> <end hh:mm:ss.mmm>"""
import subprocess, sys, re
from collections import Counter

JFR = r"C:\Users\linde\Adoptium\jdk-25.0.3+9\bin\jfr.exe"
path, start, end = sys.argv[1], sys.argv[2], sys.argv[3]
proc = subprocess.Popen([JFR, "print", "--events", "jdk.ExecutionSample", path],
                        stdout=subprocess.PIPE, text=True, errors="replace", bufsize=1 << 20)
c = Counter()
cur_t = None
for line in proc.stdout:
    s = line.strip()
    if s.startswith("jdk.ExecutionSample"):
        cur_t = None
        continue
    m = re.search(r"startTime = (\d{2}:\d{2}:\d{2}\.\d+)", s)
    if m:
        cur_t = m.group(1)[:12]
    m = re.search(r'sampledThread = "([^"]+)"', s)
    if m and cur_t and start <= cur_t <= end:
        c[m.group(1)] += 1
print(f"window {start}..{end}: {sum(c.values())} samples")
for th, n in c.most_common(25):
    print(f"  {n:3d}  {th}")
