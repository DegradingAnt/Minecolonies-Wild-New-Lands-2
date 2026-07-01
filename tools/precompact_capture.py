#!/usr/bin/env python
"""PreCompact hook — mechanical savestate safety net.

Fires automatically when Claude Code is about to compact (manual or auto). Appends a timestamped
snapshot of the pack's mechanical state to _dev/SAVESTATE-auto.md so context is NEVER fully lost,
even if the rich `wnl-savestate` skill wasn't run. Also runs a "verification gate" (per the
context-amnesia 4-step protocol): if the rich SAVESTATE.md is older than recent file changes, it
warns that the narrative savestate is stale. Must NEVER throw — a failing hook must not block compaction.
"""
import sys, os, json, glob, subprocess

ROOT = r"C:\Users\linde\curseforge\minecraft\Instances\Ultimate vibes distant horizons version"
AUTO = os.path.join(ROOT, "_dev", "SAVESTATE-auto.md")
RICH = os.path.join(ROOT, "_dev", "wnl-pathways-src", "SAVESTATE.md")
TRAIL = os.path.join(ROOT, "_dev", ".change-trail.log")
CL = os.path.join(ROOT, "_dev", "CHANGELOG.md")
DEV = r"C:\Users\linde\curseforge\WNL-Dev"                 # the PRIVATE bank repo (curated copy)
SENTINEL = os.path.join(ROOT, ".uvrun", ".autopilot")     # present == autopilot engaged
CTR = os.path.join(ROOT, ".uvrun", ".autopilot_turns")

def safe(fn, default=""):
    try: return fn()
    except Exception as e: return f"{default}(err:{e})"

def git1(args):
    """Run a git command in the bank repo, return one trimmed line. Never throws (safe-wrapped by caller)."""
    out = subprocess.run(["git", "-C", DEV] + args, capture_output=True, text=True, timeout=8)
    return (out.stdout or "").strip()

def main():
    import datetime
    trigger = "?"
    try: trigger = (json.load(sys.stdin) or {}).get("trigger", "?")
    except Exception: pass
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    L = ["", f"## auto-capture {ts} (PreCompact, trigger={trigger})"]

    wnl = safe(lambda: sorted(os.path.basename(j) for j in
               glob.glob(os.path.join(ROOT, "mods", "WNL-*.jar")) +
               glob.glob(os.path.join(ROOT, "mods", "wnl_*.jar"))), [])
    L.append("- WNL jars: " + (", ".join(wnl) if isinstance(wnl, list) else str(wnl)))

    crashes = safe(lambda: sorted(glob.glob(os.path.join(ROOT, "crash-reports", "*.txt")),
                   key=os.path.getmtime, reverse=True), [])
    L.append("- latest crash: " + (os.path.basename(crashes[0]) if crashes else "none"))

    if os.path.exists(TRAIL):
        tail = safe(lambda: open(TRAIL, encoding="utf-8", errors="replace").read().splitlines()[-8:], [])
        if isinstance(tail, list):
            L.append("- recent file touches:")
            L += ["  " + t for t in tail]

    if os.path.exists(CL):
        top = safe(lambda: [l for l in open(CL, encoding="utf-8", errors="replace").read().splitlines()
                            if l.startswith("## ")][:3], [])
        if isinstance(top, list):
            L.append("- CHANGELOG top: " + " | ".join(top))

    # LAST BANKED INCREMENT: snapshot the bank-repo HEAD (hash + commit-DATE + subject) directly into the
    # capture, so a cold auto-compaction resume is self-contained even if git is slow/unavailable then. The
    # commit DATE lets the resume compare against the change-trail touch times above to spot IN-FLIGHT work
    # (any touch newer than this commit = edited-but-not-yet-banked at the moment compaction fired).
    last = safe(lambda: git1(["log", "-1", "--format=%h  %ci  %s"]), "")
    if isinstance(last, str) and last:
        L.append("- last banked (WNL-Dev HEAD): " + last)

    # AUTOPILOT STATE: record whether the autonomous grind was engaged (+ the continue counter) so the resume
    # knows it was mid-grind and should keep going (the SessionStart hook injects the auto-resume; this is the
    # human-readable breadcrumb in the snapshot).
    eng = os.path.exists(SENTINEL)
    turns = safe(lambda: int(open(CTR).read().strip() or "0"), "?")
    L.append("- autopilot: " + ("ENGAGED (grinding)" if eng else "off") + " | continue-turns: " + str(turns))

    # RESUME ANCHOR: the newest _dev/RESTART-*.md is the READ-FIRST doc (wnl-context skill). Point resume at it.
    restart = safe(lambda: max(glob.glob(os.path.join(ROOT, "_dev", "RESTART-*.md")), key=os.path.getmtime), "")
    has_restart = bool(restart) and isinstance(restart, str) and os.path.exists(restart)
    if has_restart:
        L.append("- ★ RESUME: read `_dev/" + os.path.basename(restart) +
                 "` FIRST (read-first anchor), then `git -C C:/Users/linde/curseforge/WNL-Dev log -1` for the last banked increment.")
    warn = ""
    anchor = restart if has_restart else RICH   # check the CURRENT rich savestate (RESTART doc), not the legacy SAVESTATE.md
    if os.path.exists(anchor) and os.path.exists(TRAIL):
        try:
            if os.path.getmtime(TRAIL) > os.path.getmtime(anchor) + 600:  # 10min: lenient for active grinding
                warn = "the RESTART savestate is OLDER than recent changes — refresh it (wnl-savestate) before the next compaction."
                L.append("- WARNING: " + warn)
        except Exception:
            pass

    try:
        with open(AUTO, "a", encoding="utf-8") as f:
            f.write("\n".join(L) + "\n")
    except Exception:
        pass

    msg = "[precompact] mechanical state captured to _dev/SAVESTATE-auto.md."
    if warn: msg += " WARNING: " + warn
    try: print(json.dumps({"systemMessage": msg}))
    except Exception: pass

try:
    main()
except Exception:
    pass  # never block compaction
sys.exit(0)
