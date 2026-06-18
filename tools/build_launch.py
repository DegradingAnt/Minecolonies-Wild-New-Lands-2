"""Builds a java @argfile replicating CurseForge's NeoForge 1.21.1 launch for this instance."""
import json, os

INSTALL = r"C:\Users\linde\curseforge\minecraft\Install"
INSTANCE = r"C:\Users\linde\curseforge\minecraft\Instances\Ultimate vibes distant horizons version"
VERSION = "neoforge-21.1.233"
LIBDIR = os.path.join(INSTALL, "libraries")
NATIVES = os.path.join(INSTALL, "natives", VERSION)

def load(name):
    return json.load(open(os.path.join(INSTALL, "versions", name, name + ".json"), encoding="utf-8"))

nf = load(VERSION)
van = load(nf["inheritsFrom"])  # 1.21.1

def rules_ok(rules):
    if not rules:
        return True
    allow = False
    for r in rules:
        applies = True
        osr = r.get("os", {})
        if osr.get("name") and osr["name"] != "windows":
            applies = False
        if osr.get("arch") and osr["arch"] != "x86_64":
            applies = False  # we are x64; 'x86' rules don't apply
        if r.get("features"):
            applies = False  # skip feature-gated (demo, resolution, quickplay)
        if applies:
            allow = r["action"] == "allow"
    return allow

# classpath: neoforge libs first, then vanilla, dedupe by path, client jar last
cp, seen = [], set()
for lib in nf["libraries"] + van["libraries"]:
    if not rules_ok(lib.get("rules")):
        continue
    art = lib.get("downloads", {}).get("artifact")
    if not art:
        continue
    p = os.path.join(LIBDIR, art["path"].replace("/", os.sep))
    if p in seen:
        continue
    seen.add(p)
    if not os.path.isfile(p):
        print("MISSING LIB:", p)
    cp.append(p)
# client jar must use the neoforge-<ver>.jar name: it is in FML's module ignoreList
# (the original 1.21.1.jar name becomes a bogus automatic module and breaks resolution)
cp.append(os.path.join(INSTALL, "versions", VERSION, VERSION + ".jar"))

subs = {
    "${natives_directory}": NATIVES,
    "${launcher_name}": "uvfixes-runner",
    "${launcher_version}": "1.0",
    "${classpath}": ";".join(cp),
    "${library_directory}": LIBDIR,
    "${classpath_separator}": ";",
    "${version_name}": VERSION,
    "${auth_player_name}": "DegridingAnt018",
    "${game_directory}": INSTANCE,
    "${assets_root}": os.path.join(INSTALL, "assets"),
    "${assets_index_name}": van["assetIndex"]["id"],
    "${auth_uuid}": "2ff5a1ce38c047adb2db6dbeb046c9fb",
    "${auth_access_token}": "uvfixes-offline",
    "${clientid}": "uvfixes",
    "${auth_xuid}": "0",
    "${user_type}": "msa",
    "${version_type}": "release",
}

def expand(tok):
    for k, v in subs.items():
        tok = tok.replace(k, v)
    return tok

def collect(args):
    out = []
    for a in args:
        if isinstance(a, str):
            out.append(expand(a))
        elif rules_ok(a.get("rules")):
            v = a["value"]
            out.extend(expand(x) for x in (v if isinstance(v, list) else [v]))
    return out

jvm = collect(van["arguments"]["jvm"]) + collect(nf["arguments"].get("jvm", []))
game = collect(van["arguments"]["game"]) + collect(nf["arguments"].get("game", []))

# exact memory/GC flags observed in the real sessions' crash reports
mem = ["-XX:HeapDumpPath=MojangTricksIntelDriversForPerformance_javaw.exe_minecraft.exe.heapdump",
       "-Xss1M", "-Xmx29728m", "-Xms256m", "-XX:+UseZGC", "-XX:+ZGenerational"]
# drop duplicates CurseForge would not pass twice
jvm = [a for a in jvm if not a.startswith(("-Xmx", "-Xms", "-Xss", "-XX:HeapDumpPath"))]

def q(tok):
    return '"' + tok.replace("\\", "\\\\").replace('"', '\\"') + '"'

lines = [q(t) for t in (mem + jvm + [nf["mainClass"]] + game)]
argfile = os.path.join(INSTANCE, ".uvrun", "launch.args")
open(argfile, "w", encoding="utf-8").write("\n".join(lines))
print("classpath entries:", len(cp))
print("mainClass:", nf["mainClass"])
print("argfile:", argfile)
print("sample game args:", " ".join(game[:8]))
