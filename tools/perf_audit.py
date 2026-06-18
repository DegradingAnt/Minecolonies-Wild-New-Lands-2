#!/usr/bin/env python3
"""Perf-config drift audit for Ultimate Vibes.
Mod updates frequently REWRITE their own config file back to defaults, silently undoing
a perf pass. This checks the hand-tuned values against what's on disk and reports drift.
Exit code 0 = all good, 1 = at least one DRIFT (so a skill can branch on it).

Tuned values are the PROGRESS-27 perf pass (verified 2026-06-14). When you intentionally
retune a value, update EXPECTED here so the audit tracks the new intent."""
import json, os, sys

ROOT = r"C:/Users/linde/curseforge/minecraft/Instances/Ultimate vibes distant horizons version"
try:
    import tomllib
except ImportError:
    tomllib = None

def get(d, path):
    for k in path:
        if not isinstance(d, dict) or k not in d:
            return ("__MISSING__",)
        d = d[k]
    return d

def load_json(rel):
    try:
        return json.load(open(os.path.join(ROOT, rel), encoding="utf-8"))
    except Exception as ex:
        return {"__ERR__": str(ex)}

# (label, relpath, key-path, expected)  -- JSON configs
JSON_CHECKS = [
    ("asyncparticles particleLimit",      "config/asyncparticles/asyncparticles.json", ["particle", "particleLimit"],     8192),
    ("asyncparticles tick.failBehavior",  "config/asyncparticles/asyncparticles.json", ["tick", "failBehavior"],          "MARK_AS_SYNC"),
    ("asyncparticles render.failBehavior","config/asyncparticles/asyncparticles.json", ["rendering", "failBehavior"],     "MARK_AS_SYNC"),
    ("entityculling tracingDistance",     "config/entityculling.json",                 ["tracingDistance"],                96),
    ("particlerain maxParticleAmount",    "config/particlerain/config.json",           ["perf", "maxParticleAmount"],      750),
    ("sodium no_error_gl_context(off)",   "config/sodium-options.json",                ["performance", "use_no_error_g_l_context"], False),
    ("sodium leaves_quality",             "config/sodium-options.json",                ["quality", "leaves_quality"],      "FANCY"),
]
# (label, c2me.toml key-path, expected)  -- TOML, parsed via tomllib (true vs "default")
TOML_CHECKS = [
    ("c2me useDensityFunctionCompiler", ["vanillaWorldGenOptimizations", "useDensityFunctionCompiler"], True),
    # nativeAcceleration.enabled REVERTED to "default" (off) 2026-06-14 — speculative AVX2 native worldgen,
    # benefit never confirmed + JNI risk; user flagged it. No longer a tracked-on value.
]

drift = 0
print("=== PERF CONFIG AUDIT (tuned values vs on-disk) ===\n")
cache = {}
for label, rel, path, expected in JSON_CHECKS:
    if rel not in cache:
        cache[rel] = load_json(rel)
    val = get(cache[rel], path)
    ok = (val == expected)
    drift += (not ok)
    print(f"   [{'OK  ' if ok else 'DRIFT'}] {label:36s} = {val!r}" + ("" if ok else f"   (want {expected!r})"))

if tomllib:
    try:
        c2 = tomllib.load(open(os.path.join(ROOT, "config/c2me.toml"), "rb"))
    except Exception as ex:
        c2 = {"__ERR__": str(ex)}
    for label, path, expected in TOML_CHECKS:
        val = get(c2, path)
        ok = (val == expected)
        drift += (not ok)
        print(f"   [{'OK  ' if ok else 'DRIFT'}] {label:36s} = {val!r}" + ("" if ok else f"   (want {expected!r})"))
else:
    print("   [SKIP] c2me.toml checks (no tomllib; run on Python 3.11+)")

# --- modernfix .properties toggles (tracked: user wants these ON; updates can reset them) ---
# expected active override -> value
MODERNFIX_CHECKS = {
    # MUST stay false: dynamic_resources prunes unbaked-model/sprite data, which breaks
    # Domum Ornamentum's runtime-retextured blocks (wrong textures). DO is a hard
    # MineColonies dependency -> correctness wins. RAM benefit was negligible here
    # (63GB/24GB allocated; ferritecore still dedups). Disabled 2026-06-15. Do NOT re-enable.
    "mixin.perf.dynamic_resources":   "false",
    "mixin.perf.deduplicate_location": "true",  # RL string interning (RAM) -- safe, keep ON
}
mfp = os.path.join(ROOT, "config/modernfix-mixins.properties")
active = {}
if os.path.exists(mfp):
    for ln in open(mfp, encoding="utf-8", errors="replace"):
        s = ln.strip()
        if s and not s.startswith("#") and "=" in s:
            k, _, v = s.partition("=")
            active[k.strip()] = v.split("#")[0].strip()
for key, expected in MODERNFIX_CHECKS.items():
    val = active.get(key, "__UNSET__")
    ok = (val == expected)
    drift += (not ok)
    print(f"   [{'OK  ' if ok else 'DRIFT'}] {key:36s} = {val!r}" + ("" if ok else f"   (want {expected!r} -- re-add to modernfix-mixins.properties)"))

print(f"\n=== {'ALL TUNED VALUES INTACT' if drift == 0 else str(drift) + ' VALUE(S) DRIFTED -- re-apply'} ===")
sys.exit(1 if drift else 0)
