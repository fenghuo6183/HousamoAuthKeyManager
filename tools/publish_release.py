# -*- coding: utf-8 -*-
"""Publish a release: update a file list through the contents API, then create a release and upload assets."""
import base64
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOK = open(os.path.join(ROOT, ".tmp", "gh_token.txt")).read().strip()
OWNER = "fenghuo6183"
REPO = "HousamoAuthKeyManager"
VERSION = sys.argv[1]
TITLE = sys.argv[2]
MESSAGE = sys.argv[3]
FILES = [f for f in sys.argv[4:] if not f.startswith("--")]
ASSETS = [f[8:] for f in sys.argv[4:] if f.startswith("--asset=")]
FORCED = "--forced" in sys.argv[4:]
BODY_FILE = next((f[7:] for f in sys.argv[4:] if f.startswith("--body=")), None)


def api(method, path, body=None, tries=6):
    last = None
    for i in range(tries):
        try:
            return _once(method, path, body)
        except SystemExit as e:
            if "HTTP 4" in str(e):
                raise
            last = e
        except Exception as e:
            last = e
        time.sleep(3 + i * 4)
    raise SystemExit("network failed %s %s: %r" % (method, path, last))


def _once(method, path, body=None):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={"Authorization": "Bearer " + TOK,
                 "Accept": "application/vnd.github+json",
                 "User-Agent": "HousamoAuthKeyManager",
                 "X-GitHub-Api-Version": "2022-11-28",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.load(r) if r.status != 204 else {}
    except urllib.error.HTTPError as e:
        raise SystemExit("HTTP %d %s %s -> %s" % (e.code, method, path,
                                                  e.read().decode("utf-8", "replace")[:300]))


def update_files():
    for rel in FILES:
        full = os.path.join(ROOT, rel.replace("/", os.sep))
        data = open(full, "rb").read()
        sha = None
        try:
            sha = api("GET", "/repos/%s/%s/contents/%s" % (OWNER, REPO, rel))["sha"]
        except SystemExit:
            pass
        if sha:
            newsha = base64.b64encode(hashlib.sha1(b"blob %d\0" % len(data) + data).digest()).hex()
            if newsha == sha:
                print("  unchanged", rel)
                continue
        body = {"message": MESSAGE, "content": base64.b64encode(data).decode(), "branch": "main"}
        if sha:
            body["sha"] = sha
        api("PUT", "/repos/%s/%s/contents/%s" % (OWNER, REPO, rel), body)
        print("  updated", rel, len(data))


def upload(release_id, path):
    name = os.path.basename(path)
    data = open(path, "rb").read()
    url = "https://uploads.github.com/repos/%s/%s/releases/%d/assets?name=%s" % (
        OWNER, REPO, release_id, urllib.parse.quote(name))
    for i in range(6):
        try:
            req = urllib.request.Request(url, data=data, method="POST", headers={
                "Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json",
                "User-Agent": "HousamoAuthKeyManager",
                "Content-Type": "application/octet-stream", "Connection": "close"})
            with urllib.request.urlopen(req, timeout=600) as r:
                info = json.load(r)
            print("  uploaded", name, info.get("size"), info.get("browser_download_url"))
            return
        except urllib.error.HTTPError as e:
            print("  retry", i, e.code, e.read().decode("utf-8", "replace")[:150], flush=True)
        except Exception as e:
            print("  retry", i, type(e).__name__, flush=True)
        time.sleep(5 + i * 5)
    print("  FAILED", name)


def main():
    body = TITLE
    if BODY_FILE:
        body = open(os.path.join(ROOT, BODY_FILE.replace("/", os.sep)), encoding="utf-8").read()
    if FORCED:
        body += "\n\nforce-update: 1\n这一版必须装，旧版不会自己停用。"
    print("updating files for", VERSION, "forced" if FORCED else "")
    update_files()
    try:
        rel = api("POST", "/repos/%s/%s/releases" % (OWNER, REPO), {
            "tag_name": VERSION, "name": TITLE, "body": body,
            "target_commitish": "main", "draft": False, "prerelease": False})
    except SystemExit as e:
        print("release create:", e)
        rel = api("GET", "/repos/%s/%s/releases/tags/%s" % (OWNER, REPO, VERSION))
    print("release:", rel["html_url"])
    for a in ASSETS:
        upload(rel["id"], os.path.join(ROOT, a.replace("/", os.sep)))


if __name__ == "__main__":
    main()
