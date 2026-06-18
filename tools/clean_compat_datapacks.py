#!/usr/bin/env python3
"""Strip dead references to NOT-INSTALLED mods out of the global compat datapacks
(datapacks/*.zip). These third-party 'X Compat' packs ship tag entries + recipes for
mods this pack doesn't have -> NeoForge 'tags are a bit cooked' chat spam + recipe-load
warnings. Removing the dead entries is behaviour-identical (NeoForge already drops them
at runtime) minus the noise. Only the explicitly ABSENT namespaces are touched -- every
installed mod (incl. byg) is left completely alone. Backs up each edited zip to .bak."""
import os, sys, zipfile, json

ROOT = r"C:\Users\linde\curseforge\minecraft\Instances\Ultimate vibes distant horizons version"
ABSENT = {"alexsmobs", "aether", "deep_aether"}  # verified absent (0 jars in mods/)
DP_DIR = os.path.join(ROOT, "datapacks")


def ns(rid):
    return rid.split(":", 1)[0].lstrip("#").lower() if isinstance(rid, str) and ":" in rid else None


def referenced_namespaces(obj, acc):
    if isinstance(obj, str):
        n = ns(obj)
        if n:
            acc.add(n)
    elif isinstance(obj, list):
        for v in obj:
            referenced_namespaces(v, acc)
    elif isinstance(obj, dict):
        for v in obj.values():
            referenced_namespaces(v, acc)


def clean_tag_values(values):
    out, removed = [], 0
    for v in values:
        rid = v if isinstance(v, str) else (v.get("id") if isinstance(v, dict) else None)
        if ns(rid) in ABSENT:
            removed += 1
            continue
        out.append(v)
    return out, removed


def process_zip(path):
    drops, tag_trims = 0, 0
    out_entries = []  # (name, bytes)
    with zipfile.ZipFile(path, "r") as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            name = info.filename
            raw = z.read(name)
            # 1) whole-file drop if it lives in an absent-mod path segment
            segs = [s.lower() for s in name.replace("\\", "/").split("/")]
            if any(s in ABSENT for s in segs):
                drops += 1
                continue
            # 2) JSON content handling
            if name.lower().endswith(".json"):
                try:
                    data = json.loads(raw)
                except Exception:
                    out_entries.append((name, raw)); continue
                # tag file -> trim absent values
                if isinstance(data, dict) and isinstance(data.get("values"), list):
                    newvals, removed = clean_tag_values(data["values"])
                    if removed:
                        data["values"] = newvals
                        tag_trims += removed
                        out_entries.append((name, json.dumps(data, indent=2).encode("utf-8")))
                        continue
                # recipe/other -> drop whole file if it references an absent mod
                refs = set()
                referenced_namespaces(data, refs)
                if refs & ABSENT:
                    drops += 1
                    continue
            out_entries.append((name, raw))
    if drops == 0 and tag_trims == 0:
        return (0, 0)
    # rewrite (backup first)
    bak = path + ".bak"
    if not os.path.exists(bak):
        os.replace(path, bak)
        src = bak
    else:
        src = path  # already backed up on a prior run
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in out_entries:
            z.writestr(name, data)
    return (drops, tag_trims)


def main():
    total_d, total_t = 0, 0
    for f in sorted(os.listdir(DP_DIR)):
        if not f.lower().endswith(".zip"):
            continue
        d, t = process_zip(os.path.join(DP_DIR, f))
        if d or t:
            print(f"  {f}: dropped {d} dead file(s), trimmed {t} tag entr(y/ies)")
            total_d += d; total_t += t
    print(f"DONE: removed {total_d} dead files + {total_t} dead tag entries (absent: {sorted(ABSENT)})")


if __name__ == "__main__":
    main()
