#!/usr/bin/env python3
"""Auto-sync the WNL server bundle to the DatHost dedicated server via the DatHost API.

Refreshes the export, works out which server files ACTUALLY changed since the last sync,
then stop -> upload only the deltas (+ delete removed) -> start, so the update is applied.
Designed to run from the SessionEnd hook ("automatic on pack changes"): the change-detection
guard means the live server is only stopped/restarted when something server-relevant really
changed (client-only mods like DHSmooth aren't in the server bundle, so client tweaks don't
restart the server). First run uploads everything; later runs upload only the handful that changed.

CREDENTIALS (never committed; you create this file):  .uvrun/.server-secrets.env
    DATHOST_USER=you@example.com       # your DatHost account email
    DATHOST_PASS=your_api_password     # DatHost panel -> Account -> "API password"
    DATHOST_SERVER_ID=xxxxxxxxxxxxxxxx # the game-server id (it's in the server's panel URL)
If the file is missing/incomplete the script NO-OPS cleanly (exit 0) so the hook never fails.

USAGE
    python .uvrun/sync_server.py --check      # validate creds: just query server status, touch nothing
    python .uvrun/sync_server.py --dry-run    # show exactly what WOULD upload; server untouched
    python .uvrun/sync_server.py --no-restart # upload deltas but leave the running server alone
    python .uvrun/sync_server.py --pull-parts # ONLY download the server's universal part library to local
    python .uvrun/sync_server.py              # full auto: pull parts -> export -> diff -> stop -> upload -> start

Uses curl (ships with Windows 10/11 + Git Bash) for every API call -> no python dependencies.
NOTE: built to DatHost API 0.1 (https://dathost.net/api/0.1). Run --check then --dry-run before
trusting the first real sync; if an endpoint shape differs on your account, it's isolated here.
"""
import os, sys, json, hashlib, subprocess, time

ROOT     = r"C:/Users/linde/curseforge/minecraft/Instances/Ultimate vibes distant horizons version"
SU       = r"C:/Users/linde/Desktop/WNL-Pack-Export/server-upload"
SECRETS  = os.path.join(ROOT, ".uvrun", ".server-secrets.env")
MANIFEST = os.path.join(ROOT, ".uvrun", ".server-sync-manifest.json")
API      = "https://dathost.net/api/0.1"
DRY        = "--dry-run" in sys.argv
NO_RESTART = "--no-restart" in sys.argv
CHECK      = "--check" in sys.argv
PULL       = "--pull-parts" in sys.argv


def load_secrets():
    if not os.path.exists(SECRETS):
        return None
    d = {}
    for line in open(SECRETS, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip()
    return d if all(d.get(k) for k in ("DATHOST_USER", "DATHOST_PASS", "DATHOST_SERVER_ID")) else None


def sha1(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(base):
    m = {}
    for root, _, files in os.walk(base):
        for f in files:
            full = os.path.join(root, f)
            m[os.path.relpath(full, base).replace("\\", "/")] = sha1(full)
    return m


def curl(s, args):
    """Return (http_code, body). Trailing %{http_code} is split off the output."""
    base = ["curl", "-sS", "-m", "120", "-w", "\n%{http_code}",
            "-u", f'{s["DATHOST_USER"]}:{s["DATHOST_PASS"]}']
    r = subprocess.run(base + args, capture_output=True, text=True)
    body, _, code = r.stdout.rpartition("\n")
    return code.strip(), (body or r.stderr)


def sid(s):      return s["DATHOST_SERVER_ID"]
def gstate(s):
    code, body = curl(s, ["-X", "GET", f"{API}/game-servers/{sid(s)}"])
    if code == "200":
        try: return json.loads(body).get("on")
        except Exception: return None
    return None
def gstop(s):    return curl(s, ["-X", "POST", f"{API}/game-servers/{sid(s)}/stop"])
def gstart(s):   return curl(s, ["-X", "POST", f"{API}/game-servers/{sid(s)}/start"])
def gupload(s, rel, full):
    return curl(s, ["-X", "POST", "-F", f"file=@{full}", f"{API}/game-servers/{sid(s)}/files/{rel}"])
def gdelete(s, rel):
    return curl(s, ["-X", "DELETE", f"{API}/game-servers/{sid(s)}/files/{rel}"])


def glist(s, path):
    code, body = curl(s, ["-X", "GET", f"{API}/game-servers/{sid(s)}/files?path={path}"])
    if code != "200":
        print(f"[sync_server] file-list HTTP {code} (endpoint shape may differ on your account): {body[:160]}")
        return []
    try: return json.loads(body)
    except Exception: return []


def gdownload(s, rel, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    r = subprocess.run(["curl", "-sS", "-m", "120", "-u", f'{s["DATHOST_USER"]}:{s["DATHOST_PASS"]}',
                        "-o", dest, "-w", "%{http_code}", "-X", "GET",
                        f"{API}/game-servers/{sid(s)}/files/{rel}"], capture_output=True, text=True)
    return r.stdout.strip()


def pull_parts(s):
    """Download the server's UNIVERSAL part library (config/wnl_pathways/parts/*.json) to local, so parts
    captured by you OR your designer on the server reach your local composer + git. Merge: server files
    overwrite same-named local; local-only files (e.g. the worked examples) are kept."""
    prefix = "config/wnl_pathways/parts"
    local = os.path.join(ROOT, "config", "wnl_pathways", "parts")
    paths = []
    for e in glist(s, prefix):
        p = e.get("path") if isinstance(e, dict) else e
        if not p:
            continue
        if not p.startswith("config/"):                 # some accounts return paths relative to ?path=
            p = prefix + "/" + p.lstrip("/")
        if p.startswith(prefix) and p.endswith(".json"):
            paths.append(p)
    if not paths:
        print(f"[sync_server] no parts on the server under {prefix}/ — nothing to pull.")
        return 0
    got = 0
    for p in paths:
        if gdownload(s, p, os.path.join(local, os.path.basename(p))).startswith("2"):
            got += 1
        else:
            print(f"   ! download failed: {p}")
    print(f"[sync_server] pulled {got}/{len(paths)} part file(s) -> {local}")
    return 0


def main():
    s = load_secrets()
    if not s:
        print("[sync_server] not configured (.uvrun/.server-secrets.env missing/incomplete) — skipping.")
        return 0

    if CHECK:
        code, body = curl(s, ["-X", "GET", f"{API}/game-servers/{sid(s)}"])
        print(f"[sync_server] --check: HTTP {code}")
        print("  " + body[:300])
        print("  -> creds OK, server reachable." if code == "200"
              else "  -> check DATHOST_USER / DATHOST_PASS / DATHOST_SERVER_ID.")
        return 0

    if PULL:                                       # --pull-parts: ONLY download the server's part library
        return pull_parts(s)
    if not DRY:                                    # every normal sync first grabs the latest server captures
        pull_parts(s)

    # 1) refresh the export so server-upload/ is current
    subprocess.run([sys.executable, os.path.join(ROOT, ".uvrun", "export_pack.py")], check=False)
    if not os.path.isdir(SU):
        print("[sync_server] no server-upload/ to sync."); return 0

    # 2) diff vs last successful sync
    cur = build_manifest(SU)
    prev = {}
    if os.path.exists(MANIFEST):
        try: prev = json.load(open(MANIFEST))
        except Exception: prev = {}
    changed = sorted(r for r, h in cur.items() if prev.get(r) != h)
    removed = sorted(r for r in prev if r not in cur)
    if not changed and not removed:
        print("[sync_server] server bundle unchanged — no upload, no restart."); return 0
    print(f"[sync_server] {len(changed)} changed/new, {len(removed)} removed file(s).")

    if DRY:
        for r in changed[:60]: print("   + " + r)
        if len(changed) > 60: print(f"   ... +{len(changed) - 60} more")
        for r in removed[:60]: print("   - " + r)
        print("[sync_server] DRY RUN — nothing uploaded, server untouched."); return 0

    # 3) stop -> upload deltas -> start
    restart = not NO_RESTART
    if restart and gstate(s):
        print("[sync_server] stopping server…"); gstop(s)
        for _ in range(30):
            if gstate(s) is False: break
            time.sleep(2)
    ok = fail = 0
    for rel in changed:
        code, body = gupload(s, rel, os.path.join(SU, rel))
        if code.startswith("2"): ok += 1
        else: fail += 1; print(f"   ! upload {code} {rel}: {body[:140]}")
    for rel in removed:
        gdelete(s, rel)
    print(f"[sync_server] uploaded {ok} ok / {fail} failed; deleted {len(removed)}.")
    if restart:
        print("[sync_server] starting server…"); gstart(s)

    # 4) only advance the manifest if every upload succeeded (else retry the deltas next run)
    if fail == 0:
        json.dump(cur, open(MANIFEST, "w"), indent=0)
        print("[sync_server] sync complete; manifest updated.")
    else:
        print("[sync_server] some uploads failed — manifest NOT advanced (will retry next run).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
