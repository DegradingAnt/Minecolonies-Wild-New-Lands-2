"""DEV-ONLY native jar patch for colonypathingedition vs minecolonies 1.1.1336+ (today's AI/pathfinding
rewrite removed handleLadders etc.). Disables ONLY the rewrite-affected pathfinding.* mixin group (+ its
sole accessor) in colonypathingedition.mixins.json, keeping ALL the worker-AI mixins + recipes + research +
farming. Marks the jar unofficial in mods.toml (NOT for redistribution; the pack isn't released — re-add the
official build once the author updates for the new MC). Run: python .uvrun/patch_cpe.py"""
import json, os, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "mods", "colonypathingedition-1.21.1-1.0.5-BETA-9.1.jar")
OUT = os.path.join(ROOT, "mods", "colonypathingedition-1.21.1-1.0.5-BETA-9.1-wnldev.jar")
MIXJSON = "colonypathingedition.mixins.json"
TOML = "META-INF/neoforge.mods.toml"

REMOVE = {
    "minecolonies.pathfinding.AbstractPathJobMixin",
    "minecolonies.pathfinding.MNodeMixin",
    "minecolonies.pathfinding.PathfindingUtilsMixin",
    "minecolonies.pathfinding.PathingOptionsMixin",
    "minecolonies.pathfinding.PathJobFindTreeMixin",
    "minecolonies.pathfinding.heuristic.PathJobMoveCloseToXNearYMixin",
    "minecolonies.pathfinding.heuristic.PathJobMoveToLocationMixin",
    "minecolonies.pathfinding.heuristic.PathJobMoveTowardsMixin",
    "minecolonies.pathfinding.heuristic.PathJobPathwayMixin",
    "minecolonies.pathfinding.heuristic.PathJobRaiderPathingMixin",
    "minecolonies.pathfinding.navigator.MinecoloniesAdvancedPathNavigateMixin",  # the handleLadders crasher
    "minecolonies.pathfinding.navigator.MovementHandlerMixin",
    "minecolonies.pathfinding.navigator.UnstuckMixin",
    "minecolonies.accessor.MinecoloniesAdvancedPathNavigateAccessor",            # only UnstuckMixin used it
}

zin = zipfile.ZipFile(SRC, "r")
mj = json.loads(zin.read(MIXJSON))
kept, cut = [], []
for arr in ("mixins", "client", "server"):
    if arr in mj:
        new = []
        for m in mj[arr]:
            (cut if m in REMOVE else new).append(m)
        mj[arr] = new
        kept.append((arr, len(new)))
mj_bytes = json.dumps(mj, indent=2).encode("utf-8")

toml = zin.read(TOML).decode("utf-8")
mark = "(WNL-DEV unofficial: pathfinding.* mixins disabled for MC 1.1.1336+ rewrite - NOT for redistribution)"
if "WNL-DEV" not in toml:
    toml = toml.replace('displayName="Pathfinding Edition For Minecolonies"',
                        'displayName="Pathfinding Edition For Minecolonies ' + mark + '"')
toml_bytes = toml.encode("utf-8")

zout = zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED)
for item in zin.infolist():
    data = zin.read(item.filename)
    if item.filename == MIXJSON:
        data = mj_bytes
    elif item.filename == TOML:
        data = toml_bytes
    zout.writestr(item, data)
zout.close(); zin.close()

print("disabled %d mixins: %s" % (len(cut), ", ".join(sorted(c.split(".")[-1] for c in cut))))
print("kept arrays:", kept)
print("-> " + OUT)
