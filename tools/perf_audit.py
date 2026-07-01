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
    # globalExecutorParallelism: bumped default(~14)->20 on 2026-06-29 (c2me-ocl author rec for GPU-worldgen
    # throughput). REVERTED to 14 (default) 2026-07-01: OCL is .disabled (throughput rationale moot) AND the
    # governor FPS-test JFR confirmed c2me workers saturate the cores + starve the render thread during heavy
    # gen (22752 c2me vs 2752 render samples) = exactly the "frame stutter during heavy gen" revert condition.
    # 14 favors frames; a boot A/B could test even lower. (memory: dh-governor-role-and-c2me-gen-bottleneck)
    ("c2me globalExecutorParallelism",  ["globalExecutorParallelism"], 14),
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
    # MUST stay false. Enabled it 2026-06-20 (the boot crash it was once blamed for was actually the
    # sparsestructures.json5 missing-comma construct abort, NOT this) -- but with dynamic_resources ON,
    # WORLD-JOIN broke: it defers resource/registry load past world-join, so EntityJoinLevelEvent hit
    # "Cannot get config value before config is loaded" + the update_recipes packet failed to encode
    # (enchantment id not yet in the synced map) -> player kicked to menu on EVERY world load. Reverted.
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
    # dynamic_resources: UNSET is fine -- modernfix's DEFAULT is already false, and the author
    # intentionally left it unset (no explicit line) 2026-07-01 rather than re-add one. The only real
    # drift is an explicit 'true' (that broke world-join, see comment above). false or unset = OK.
    if key == "mixin.perf.dynamic_resources":
        ok = (val != "true")
    else:
        ok = (val == expected)
    drift += (not ok)
    note = "" if ok else (f"   (must NOT be 'true' -- remove it from modernfix-mixins.properties)"
                          if key == "mixin.perf.dynamic_resources"
                          else f"   (want {expected!r} -- re-add to modernfix-mixins.properties)")
    print(f"   [{'OK  ' if ok else 'DRIFT'}] {key:36s} = {val!r}" + note)

print(f"\n=== {'ALL TUNED VALUES INTACT' if drift == 0 else str(drift) + ' VALUE(S) DRIFTED -- re-apply'} ===")
sys.exit(1 if drift else 0)
