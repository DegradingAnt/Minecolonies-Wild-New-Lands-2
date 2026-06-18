"""Derive bloat-audit views from modmeta.json -> .uvrun/modreport.txt"""
import json, os, re
from collections import defaultdict

INST = r"C:\Users\linde\curseforge\minecraft\Instances\Ultimate vibes distant horizons version"
meta = json.load(open(os.path.join(INST, ".uvrun", "modmeta.json"), encoding="utf-8"))
OUT = os.path.join(INST, ".uvrun", "modreport.txt")

IGNORE_DEPS = {"neoforge", "minecraft", "forge"}

id2jar = defaultdict(list)          # modid -> [jar files]
jar2ids = {}                        # file -> [modids]
required_by = defaultdict(set)      # modid -> set(jar that requires it)
optional_by = defaultdict(set)
jij_provided = defaultdict(list)    # artifact name fragment -> [host jars]

for e in meta:
    ids = [m["modId"] for m in e["mods"] if m.get("modId")]
    jar2ids[e["file"]] = ids
    for i in ids:
        id2jar[i].append(e["file"])
    for d in e["deps"]:
        on = d.get("on")
        if not on or on in IGNORE_DEPS:
            continue
        if d["type"] in ("required",):
            required_by[on].add(e["file"])
        else:
            optional_by[on].add(e["file"])
    for j in e["jij"]:
        art = j.split(":")[-1].split(" ")[0].lower()
        jij_provided[art].append(e["file"])

lines = []
A = lines.append

A("== DUPLICATE / MULTI-VERSION MOD IDS (same modid in >1 jar) ==")
for mid, jars in sorted(id2jar.items()):
    if len(jars) > 1:
        A("  %s: %s" % (mid, ", ".join(jars)))

A("")
A("== ZERO-CONSUMER JARS (no installed jar requires OR optionally uses any of its modids) ==")
A("   (content mods are fine here; suspicious if it LOOKS like a library/api/core)")
for e in meta:
    ids = jar2ids[e["file"]]
    if not ids:
        continue
    req = sum(len(required_by[i]) for i in ids)
    opt = sum(len(optional_by[i]) for i in ids)
    if req == 0 and opt == 0:
        libish = any(re.search(r"lib|api|core|base|framework|util", i) for i in ids)
        names = "; ".join(str(m.get("name")) for m in e["mods"])
        A("  %s%s [%s] (%s) %.1fMB models=%d recipes=%d" % (
            "LIB? " if libish else "", e["file"], ",".join(ids), names,
            e["sizeMB"], e.get("models", 0), e.get("recipes", 0)))

A("")
A("== LIB-NAMED JARS WITH CONSUMERS (context: who needs them) ==")
for e in meta:
    ids = jar2ids[e["file"]]
    if not any(re.search(r"lib|api|core|base|framework", i) for i in ids):
        continue
    req = set()
    for i in ids:
        req |= required_by[i]
    if req:
        A("  %s <- required by %d jars" % (e["file"], len(req)))

A("")
A("== STANDALONE JAR ALSO JIJ'D ELSEWHERE (JarJar would supply it anyway) ==")
for e in meta:
    base = re.sub(r"[-_]?\d.*$", "", e["file"].lower().replace(".jar", ""))
    for art, hosts in jij_provided.items():
        if base and (base == art or base.replace("-", "") == art.replace("-", "")):
            A("  %s ~ JiJ'd as '%s' inside: %s" % (e["file"], art, ", ".join(hosts[:5])))

A("")
A("== 30 BIGGEST JARS (jar-scan/transform time proxy) ==")
for e in sorted(meta, key=lambda x: -x["sizeMB"])[:30]:
    A("  %7.1fMB %s" % (e["sizeMB"], e["file"]))

A("")
A("== 30 MOST MODELS (model-bake time proxy) ==")
for e in sorted(meta, key=lambda x: -x.get("models", 0))[:30]:
    A("  %6d models %s" % (e.get("models", 0), e["file"]))

A("")
A("== FULL MOD LIST (file | modids | name | version | reqBy/optBy counts) ==")
for e in meta:
    ids = jar2ids[e["file"]]
    req = sum(len(required_by[i]) for i in ids)
    opt = sum(len(optional_by[i]) for i in ids)
    names = "; ".join("%s %s" % (m.get("name"), m.get("version")) for m in e["mods"]) or e.get("note", "?")
    A("%s | %s | %s | req:%d opt:%d | %.1fMB" % (e["file"], ",".join(ids), names, req, opt, e["sizeMB"]))

open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print("report written:", OUT, len(lines), "lines")
