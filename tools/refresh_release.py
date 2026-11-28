# -*- coding: utf-8 -*-
"""Refresh one file + one release asset in place (same tag), used after a tiny rebuild."""
import base64, json, os, sys, time, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOK = open(os.path.join(ROOT, ".tmp", "gh_token.txt")).read().strip()
OWNER, REPO = "fenghuo6183", "HousamoAuthKeyManager"
API = "https://api.github.com"


def call(method, path, body=None, raw=None, ctype="application/json", tries=5):
    last = None
    for i in range(tries):
        try:
            data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
            req = urllib.request.Request(API + path, data=data, method=method, headers={
                "Authorization": "Bearer " + TOK,
                "Accept": "application/vnd.github+json",
                "Content-Type": ctype,
                "User-Agent": "housamo-refresh",
            })
            with urllib.request.urlopen(req, timeout=60) as r:
                txt = r.read().decode()
                return json.loads(txt) if txt.strip() else {}
        except urllib.error.HTTPError as e:
            body_txt = e.read().decode()[:300]
            if 400 <= e.code < 500 and e.code != 429:
                raise SystemExit("HTTP %s %s %s -> %s" % (e.code, method, path, body_txt))
            last = "HTTP %s %s" % (e.code, body_txt)
        except Exception as e:
            last = repr(e)
        time.sleep(2 + i * 3)
    raise SystemExit("failed %s %s: %s" % (method, path, last))


def put_file(rel_path):
    local = os.path.join(ROOT, rel_path)
    content = open(local, "rb").read()
    cur = call("GET", "/repos/%s/%s/contents/%s" % (OWNER, REPO, rel_path))
    res = call("PUT", "/repos/%s/%s/contents/%s" % (OWNER, REPO, rel_path), {
        "message": "sync " + rel_path,
        "content": base64.b64encode(content).decode(),
        "sha": cur["sha"],
    })
    print("  updated %s %s" % (rel_path, res["content"]["size"]))


def refresh_asset(tag, asset_path, name=None):
    name = name or os.path.basename(asset_path)
    rel = call("GET", "/repos/%s/%s/releases/tags/%s" % (OWNER, REPO, tag))
    for a in rel.get("assets", []):
        if a["name"] == name:
            call("DELETE", "/repos/%s/%s/releases/assets/%d" % (OWNER, REPO, a["id"]))
            print("  deleted old asset", name)
    url = "https://uploads.github.com/repos/%s/%s/releases/%d/assets?name=%s" % (OWNER, REPO, rel["id"], urllib.parse.quote(name))
    data = open(asset_path, "rb").read()
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "Authorization": "Bearer " + TOK,
        "Content-Type": "application/octet-stream",
        "User-Agent": "housamo-refresh",
    })
    with urllib.request.urlopen(req, timeout=300) as r:
        j = json.loads(r.read().decode())
    print("  uploaded %s %d %s" % (j["name"], j["size"], j["browser_download_url"]))


if __name__ == "__main__":
    tag = sys.argv[1]
    files = [a for a in sys.argv[2:] if not a.startswith("--asset=")]
    assets = [a[8:] for a in sys.argv[2:] if a.startswith("--asset=")]
    for f in files:
        put_file(f)
    for a in assets:
        refresh_asset(tag, a)
