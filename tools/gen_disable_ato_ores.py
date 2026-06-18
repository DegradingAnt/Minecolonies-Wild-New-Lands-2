#!/usr/bin/env python3
"""Disable worldgen for ATO materials that nothing outside ATO consumes (audit_ato_v2.py).
Overrides each dead material's NeoForge biome_modifier (overworld/nether/end) with
{"type":"neoforge:none"} in UltimateVibes-Compat -> higher datapack priority shadows ATO's
add_features modifier -> ore stops generating. Items stay registered (just unobtainable via
worldgen); ride in the same datapack the server already copies.
"""
import os, json

DEAD = ["cinnabar", "fluorite", "iridium", "osmium", "peridot", "platinum", "ruby", "sapphire", "uranium"]
DIMS = ["overworld", "nether", "end"]

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..",
        "config", "paxi", "datapacks", "UltimateVibes-Compat",
        "data", "alltheores", "neoforge", "biome_modifier"))
os.makedirs(OUT, exist_ok=True)

n = 0
for mat in DEAD:
    for dim in DIMS:
        with open(os.path.join(OUT, f"{mat}_{dim}.json"), "w", encoding="utf-8") as f:
            json.dump({"type": "neoforge:none"}, f, indent=2)
            f.write("\n")
        n += 1

print(f"Wrote {n} biome_modifier overrides (neoforge:none) -> {OUT}")
print(f"Disabled worldgen for: {', '.join(DEAD)} (x {len(DIMS)} dims each)")
