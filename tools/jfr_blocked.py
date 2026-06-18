#!/usr/bin/env python3
"""Parse jdk.JavaMonitorEnter / jdk.ThreadPark events from a JFR dump.
Usage: jfr_blocked.py <file.jfr> <EventName>
Prints per-thread blocked totals + the longest individual stalls with stacks."""
import subprocess, sys, re
from collections import defaultdict

JFR = r"C:\Users\linde\Adoptium\jdk-25.0.3+9\bin\jfr.exe"
path = sys.argv[1]
event = sys.argv[2] if len(sys.argv) > 2 else "jdk.JavaMonitorEnter"

proc = subprocess.Popen([JFR, "print", "--events", event, path],
                        stdout=subprocess.PIPE, text=True, errors="replace", bufsize=1 << 20)

events = []
cur = None
for line in proc.stdout:
    s = line.strip()
    if s.startswith(event):
        if cur:
            events.append(cur)
        cur = {"frames": []}
        continue
    if cur is None:
        continue
    m = re.search(r"duration = ([\d,\.]+) (ms|s|us)", s)
    if m:
        cur["dur"] = m.group(1).replace(",", ".") + m.group(2)
    m = re.search(r"monitorClass = (\S+)", s)
    if m:
        cur["mon"] = m.group(1)
    m = re.search(r'(?:eventThread|sampledThread) = "([^"]+)"', s)
    if m:
        cur["thread"] = m.group(1)
    m = re.search(r'parkedClass = (\S+)', s)
    if m:
        cur["mon"] = m.group(1)
    if s.startswith("at ") and len(cur["frames"]) < 5:
        cur["frames"].append(s[3:].split("(")[0])
if cur:
    events.append(cur)


def ms(d):
    if not d:
        return 0.0
    if d.endswith("us"):
        return float(d[:-2]) / 1000
    if d.endswith("ms"):
        return float(d[:-2])
    if d.endswith("s"):
        return float(d[:-1]) * 1000
    return 0.0


byth = defaultdict(lambda: [0, 0.0])
for e in events:
    d = ms(e.get("dur", ""))
    byth[e.get("thread", "?")][0] += 1
    byth[e.get("thread", "?")][1] += d

print(f"== {event}: {len(events)} events")
print("== per-thread total blocked time (top 12):")
print("    total_ms     count  thread")
for th, (c, t) in sorted(byth.items(), key=lambda x: -x[1][1])[:12]:
    print(f"  {t:9.1f}ms  x{c:5d}  {th}")
print()
print("== LONGEST individual stalls (top 18):")
for e in sorted(events, key=lambda e: -ms(e.get("dur", "")))[:18]:
    print(f"  {ms(e.get('dur','')):8.1f}ms  [{e.get('thread','?')}]  on={e.get('mon','?')}")
    for f in e["frames"][:4]:
        print(f"               {f}")
