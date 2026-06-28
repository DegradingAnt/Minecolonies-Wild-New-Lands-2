#!/usr/bin/env python3
"""lootr_audit.py — audit Lootr integration across ALL structures.

Lootr (+ lootr_liason) converts loot-bearing block entities to per-player instances. Its core
converters handle: chest/trapped_chest, barrel, shulker_box, brushable (suspicious sand/gravel),
decorated_pot, and any RandomizableContainerBlockEntity (generic 'Inventory'); chest_minecart
(convert_mineshafts) + item_frame (convert_item_frames) are entity-side. lootr_liason's
ContainerDetectionLayer scans structures at worldgen and finalizes with correct timing.

This scans every structure .nbt template in mods/, finds block entities carrying a LootTable, and
buckets the CONTAINER BLOCK TYPE as Lootr-convertible (vanilla/standard) vs CUSTOM (modded block
that may not extend the standard container -> a coverage gap for the Lootr addon, task #103).
Pure static analysis (no boot). nbtlib required."""
import glob, zipfile, re, io, gzip, collections, sys
import nbtlib

# Lootr-convertible container blocks (handled by core converters; modded blocks that are simply
# these vanilla blocks are fine). Anything with a LootTable that ISN'T one of these is a CUSTOM
# container -> flag for manual BE-hierarchy check (#103 coverage).
VANILLA_LOOT_BLOCKS = {
    "minecraft:chest", "minecraft:trapped_chest", "minecraft:barrel",
    "minecraft:suspicious_sand", "minecraft:suspicious_gravel", "minecraft:decorated_pot",
    "minecraft:shulker_box", "minecraft:hopper", "minecraft:dispenser", "minecraft:dropper",
    "minecraft:furnace", "minecraft:blast_furnace", "minecraft:smoker", "minecraft:brewing_stand",
    "minecraft:chiseled_bookshelf",
}
# shulker_box colored variants
VANILLA_LOOT_BLOCKS |= {f"minecraft:{c}_shulker_box" for c in
    ("white","orange","magenta","light_blue","yellow","lime","pink","gray","light_gray","cyan",
     "purple","blue","brown","green","red","black")}

def iter_nbt(jar):
    z = zipfile.ZipFile(jar)
    for n in z.namelist():
        if re.match(r"data/[^/]+/structure[s]?/.+\.nbt$", n):
            yield n, z.read(n)

def parse_loot_blocks(raw):
    """Return list of (block_name, loot_table) for every loot-bearing BE in a structure nbt."""
    try:
        data = gzip.decompress(raw)
    except Exception:
        data = raw
    if b"LootTable" not in data:
        return []
    try:
        root = nbtlib.File.parse(io.BytesIO(data))
    except Exception:
        return []
    # structure nbt: {palette:[{Name,Properties}], blocks:[{pos,state,nbt}]}
    out = []
    palettes = []
    if "palette" in root: palettes = [root["palette"]]
    elif "palettes" in root: palettes = list(root["palettes"])
    if not palettes or "blocks" not in root: return out
    pal = palettes[0]
    def name_of(state):
        try: return str(pal[int(state)]["Name"])
        except Exception: return "?"
    for b in root["blocks"]:
        nbtv = b.get("nbt")
        if nbtv is None: continue
        if "LootTable" not in nbtv: continue
        out.append((name_of(b.get("state", -1)), str(nbtv.get("LootTable",""))))
    return out

def main():
    by_block = collections.Counter()             # block_name -> # of loot BEs
    custom_block_examples = collections.defaultdict(set)   # custom block -> {structure files}
    scanned = looty = 0
    for jp in sorted(glob.glob("mods/*.jar")):
        jar = jp.split("/")[-1].split("\\")[-1]
        try: it = list(iter_nbt(jp))
        except Exception: continue
        for n, raw in it:
            scanned += 1
            blocks = parse_loot_blocks(raw)
            if blocks: looty += 1
            for bn, lt in blocks:
                by_block[bn] += 1
                if bn not in VANILLA_LOOT_BLOCKS:
                    custom_block_examples[bn].add(f"{jar}:{n.split('/')[-1]}")
        if scanned % 4000 < len(it):
            print(f"  ...scanned {scanned} templates", file=sys.stderr)
    print(f"\n=== Lootr structure audit: {scanned} templates, {looty} loot-bearing ===\n")
    print("=== loot-container BLOCK TYPES found (count) — VANILLA=convertible ===")
    for bn, c in by_block.most_common():
        tag = "OK(vanilla)" if bn in VANILLA_LOOT_BLOCKS else "**CUSTOM**"
        print(f"  {c:6}  {tag:13} {bn}")
    print(f"\n=== CUSTOM (non-vanilla) loot containers — Lootr COVERAGE GAP candidates ({len(custom_block_examples)}) ===")
    if not custom_block_examples:
        print("  NONE — every structure loot container is a vanilla/standard type Lootr converts. ✓")
    for bn in sorted(custom_block_examples, key=lambda b: -by_block[b]):
        ex = sorted(custom_block_examples[bn])[:3]
        print(f"  {by_block[bn]:5}  {bn}")
        for e in ex: print(f"           e.g. {e}")

if __name__ == "__main__":
    main()
