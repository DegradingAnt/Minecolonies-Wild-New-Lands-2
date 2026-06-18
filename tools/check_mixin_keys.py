"""Check every supplemental_patches shader-mixin key against the base pack files.
Outputs all mixins whose key text is MISSING (=> mixin silently skipped)."""
import json, os, glob

MIX = r"C:\Windows\Temp\uvfixes\sp2\resourcepacks\builtin_shaders\assets\supplemental_patches\euphoria\mixins"
BASE = r"C:\Users\linde\curseforge\minecraft\Instances\Ultimate vibes distant horizons version\shaderpacks\ComplementaryReimagined_r5.8.1 + EuphoriaPatches_1.9.3"

missing, ok, nofile = [], 0, []
for jf in glob.glob(MIX + r"\**\*.json", recursive=True):
    try:
        spec = json.load(open(jf, encoding="utf-8"))
    except Exception as e:
        print("PARSE FAIL:", jf, e); continue
    specs = spec if isinstance(spec, list) else [spec]
    for s in specs:
        f = s.get("file"); key = s.get("key")
        if not f or not key: continue
        target = BASE + f.replace("/", os.sep)
        if not os.path.isfile(target):
            nofile.append((os.path.relpath(jf, MIX), f)); continue
        content = open(target, encoding="utf-8", errors="replace").read()
        if key in content:
            ok += 1
        else:
            missing.append((os.path.relpath(jf, MIX), f, key, s.get("type")))

print("keys OK:", ok)
print("target file missing:", len(nofile))
for j, f in nofile: print("  NOFILE", j, "->", f)
print("\nKEY MISMATCHES (%d):" % len(missing))
for j, f, key, typ in missing:
    print("  %-55s %-8s %s" % (j, typ, f))
    print("      key: %s" % key[:120])
