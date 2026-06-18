#!/usr/bin/env python3
"""Native-method-sample breakdown for the Render thread (GPU/driver stalls).
Usage: jfr_native.py <file.jfr>"""
import subprocess, sys
from collections import Counter

JFR = r"C:\Users\linde\Adoptium\jdk-25.0.3+9\bin\jfr.exe"
path = sys.argv[1]
proc = subprocess.Popen([JFR, "print", "--events", "jdk.NativeMethodSample", "--stack-depth", "14", path],
                        stdout=subprocess.PIPE, text=True, errors="replace", bufsize=1 << 20)
data = proc.stdout.read()
blocks = data.split("jdk.NativeMethodSample")
topnative = Counter()
subsystem = Counter()
tot = 0
KEYS = ["distanthorizons", "iris", "sodium", "glObject", "GLBuffer", "glMapBuffer",
        "glUseProgram", "glBindBuffer", "glBufferData", "glBufferSubData", "glBufferStorage",
        "glClientWaitSync", "SwapBuffers", "glFinish", "glFlush", "glDrawElements",
        "glReadPixels", "nglMapBufferRange", "glTexImage", "glTexSubImage", "shadow"]
for b in blocks:
    if 'sampledThread = "Render thread"' not in b:
        continue
    tot += 1
    grab = False
    frames = []
    for l in b.splitlines():
        if "stackTrace = [" in l:
            grab = True
            continue
        if grab:
            ls = l.strip()
            if ls == "]":
                break
            frames.append(ls.split("(")[0])
    if frames:
        topnative[frames[0]] += 1
    blob = " ".join(frames)
    for key in KEYS:
        if key.lower() in blob.lower():
            subsystem[key] += 1
print(f"Render-thread NATIVE samples: {tot}")
print("== top innermost native frame:")
for f, c in topnative.most_common(15):
    print(f"  {c:4d} ({100*c/max(tot,1):4.1f}%)  {f}")
print("== subsystem keyword hits (inclusive, a sample can hit several):")
for k, c in subsystem.most_common():
    print(f"  {c:4d} ({100*c/max(tot,1):4.1f}%)  {k}")
