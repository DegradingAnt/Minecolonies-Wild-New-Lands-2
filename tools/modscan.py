"""Extract mod metadata from every jar in mods/ -> .uvrun/modmeta.json
Per jar: modids, names, versions, declared deps, JiJ'd libs, size, asset counts.
Used to build the bloat-suspect list (reverse-dep map, orphan libs, duplicates)."""
import zipfile, json, os, re, sys

INST = r"C:\Users\linde\curseforge\minecraft\Instances\Ultimate vibes distant horizons version"
MODS = os.path.join(INST, "mods")
OUT = os.path.join(INST, ".uvrun", "modmeta.json")

try:
    import tomllib
    def parse_toml(b):
        return tomllib.loads(b.decode("utf-8", "replace"))
except ImportError:
    parse_toml = None

def regex_fallback(text):
    """Crude extraction when toml parsing fails."""
    mods = [{"modId": m} for m in re.findall(r'^\s*modId\s*=\s*"([^"]+)"', text, re.M)]
    return {"mods": mods, "dependencies": {}, "_fallback": True}

def manifest_version(z):
    try:
        mf = z.read("META-INF/MANIFEST.MF").decode("utf-8", "replace")
        m = re.search(r"^Implementation-Version:\s*(\S+)", mf, re.M)
        return m.group(1) if m else None
    except KeyError:
        return None

out = []
for fn in sorted(os.listdir(MODS)):
    if not fn.lower().endswith(".jar"):
        continue
    path = os.path.join(MODS, fn)
    e = {"file": fn, "sizeMB": round(os.path.getsize(path) / 1048576, 2),
         "mods": [], "deps": [], "jij": []}
    try:
        z = zipfile.ZipFile(path)
        names = z.namelist()
        e["models"] = sum(1 for n in names if "/models/" in n and n.endswith(".json"))
        e["recipes"] = sum(1 for n in names if "/recipe" in n and n.endswith(".json"))
        e["classes"] = sum(1 for n in names if n.endswith(".class"))
        # JarJar embedded libs
        if "META-INF/jarjar/metadata.json" in names:
            try:
                jj = json.loads(z.read("META-INF/jarjar/metadata.json"))
                for j in jj.get("jars", []):
                    ident = j.get("identifier", {})
                    e["jij"].append("%s:%s %s" % (ident.get("group", "?"), ident.get("artifact", "?"),
                                                  j.get("version", {}).get("artifactVersion", "?")))
            except Exception as ex:
                e["jij"].append("parse-error: %s" % ex)
        toml_name = next((n for n in ("META-INF/neoforge.mods.toml", "META-INF/mods.toml") if n in names), None)
        if toml_name:
            raw = z.read(toml_name)
            data = None
            if parse_toml:
                try:
                    data = parse_toml(raw)
                except Exception:
                    pass
            if data is None:
                data = regex_fallback(raw.decode("utf-8", "replace"))
                e["tomlFallback"] = True
            mfv = manifest_version(z)
            for m in data.get("mods", []):
                ver = m.get("version", "?")
                if "${" in str(ver):
                    ver = mfv or ver
                desc = (m.get("description") or "").strip()
                desc = re.sub(r"\s+", " ", desc)[:400]
                e["mods"].append({"modId": m.get("modId"), "name": m.get("displayName"), "version": ver, "desc": desc})
            deps = data.get("dependencies", {}) or {}
            for mid, dl in deps.items():
                if not isinstance(dl, list):
                    continue
                for d in dl:
                    if not isinstance(d, dict):
                        continue
                    typ = d.get("type")
                    if typ is None:
                        typ = "required" if d.get("mandatory", True) else "optional"
                    e["deps"].append({"from": mid, "on": d.get("modId"), "type": str(typ).lower()})
        elif "fabric.mod.json" in names:
            e["note"] = "fabric-only jar"
            try:
                fj = json.loads(z.read("fabric.mod.json"))
                e["mods"].append({"modId": fj.get("id"), "name": fj.get("name"), "version": fj.get("version")})
            except Exception:
                pass
        else:
            e["note"] = "no mod metadata (library/datapack?)"
    except Exception as ex:
        e["error"] = str(ex)
    out.append(e)

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=0)
print("jars:", len(out))
print("mod ids:", sum(len(e["mods"]) for e in out))
print("no-metadata jars:", sum(1 for e in out if "note" in e))
print("toml fallbacks:", sum(1 for e in out if e.get("tomlFallback")))
print("errors:", sum(1 for e in out if "error" in e))
