#!/usr/bin/env python3
"""Print full Render-thread stacks within given time windows (the hitch boundaries).
Usage: jfr_around.py <file.jfr> <hh:mm:ss.mmm-hh:mm:ss.mmm> [more windows...]"""
import subprocess, sys, re

JFR = r"C:\Users\linde\Adoptium\jdk-25.0.3+9\bin\jfr.exe"
path = sys.argv[1]
windows = []
for w in sys.argv[2:]:
    a, b = w.split("-")
    windows.append((a, b))


def in_win(t):
    for a, b in windows:
        if a <= t <= b:
            return True
    return False


proc = subprocess.Popen([JFR, "print", "--events", "jdk.ExecutionSample", "--stack-depth", "20", path],
                        stdout=subprocess.PIPE, text=True, errors="replace", bufsize=1 << 20)
cur_t = None; cur_thread = None; frames = []; in_stack = False; keep = False
printed = 0
for line in proc.stdout:
    s = line.rstrip("\n")
    st = s.strip()
    if st.startswith("jdk.ExecutionSample"):
        if keep and frames and printed < 60:
            print(f"\n[{cur_t}] Render thread:")
            for f in frames[:16]:
                print(f"    {f}")
            printed += 1
        cur_t = None; cur_thread = None; frames = []; in_stack = False; keep = False
        continue
    m = re.search(r"startTime = (\d{2}:\d{2}:\d{2}\.\d+)", st)
    if m:
        cur_t = m.group(1)[:12]
    m = re.search(r'sampledThread = "([^"]+)"', st)
    if m:
        cur_thread = m.group(1)
        keep = (cur_thread == "Render thread" and cur_t and in_win(cur_t))
    if "stackTrace = [" in st:
        in_stack = True
        continue
    if in_stack:
        if st == "]":
            in_stack = False
        else:
            fr = st[3:] if st.startswith("at ") else st
            frames.append(fr.split("(")[0])
