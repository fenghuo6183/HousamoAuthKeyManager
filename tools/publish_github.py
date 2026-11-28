# -*- coding: utf-8 -*-
"""Publish this project to GitHub through the REST API (git transport is broken here)."""
import base64
import io
import json
import os
import sys
import urllib.error
import urllib.parse
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = os.path.join(ROOT, ".tmp", "gh_token.txt")
REPO = "HousamoAuthKeyManager"
DESC = "一键提取 / 导入《东京放课后召唤师》AuthKey 的 Windows + Android 工具（免 root 优先，支持模拟器多开）"
def app_version():
    env = os.environ.get("HAK_VERSION", "").strip()
    if env:
        return env.lstrip("vV")
    theme = os.path.join(ROOT, "win", "app", "theme.py")
    for line in io.open(theme, encoding="utf-8"):
        if line.startswith("APP_VERSION"):
            return line.split("=", 1)[1].strip().strip('"\'')
    raise SystemExit("no APP_VERSION in " + theme)


VERSION = "v" + app_version()

SKIP_DIRS = {".git", ".tools", ".tmp", "__pycache__", "build", "dist", "node_modules"}
SKIP_SUFFIX = {".pyc", ".spec", ".log"}
SKIP_PATHS = {"win/dist", "win/build", "android/build", "win/assets/platform-tools"}


def read_token():
    if not os.path.exists(TOKEN_FILE):
        raise SystemExit("no token at " + TOKEN_FILE)
    return open(TOKEN_FILE).read().strip()


TOK = read_token()


def api(method, path, body=None, tries=6):
    last = None
    for attempt in range(tries):
        try:
            return _api_once(method, path, body)
        except SystemExit as e:
            if "HTTP 5" not in str(e):
                raise
            last = e
        except Exception as e:
            last = e
        time.sleep(3 + attempt * 4)
    raise SystemExit("network failed on %s %s: %r" % (method, path, last))


def _api_once(method, path, body=None):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={
            "Authorization": "Bearer " + TOK,
            "Accept": "application/vnd.github+json",
            "User-Agent": "HousamoAuthKeyManager",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        })
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r) if r.status != 204 else {}
    except urllib.error.HTTPError as e:
        raise SystemExit("HTTP %d %s %s -> %s" % (e.code, method, path, e.read().decode("utf-8", "replace")[:300]))


def ensure_commit(owner):
    """Empty repos reject blob creation (409); bootstrap one file so refs/heads/main exists."""
    try:
        api("GET", "/repos/%s/%s/git/ref/heads/main" % (owner, REPO))
        return
    except SystemExit:
        pass
    try:
        api("GET", "/repos/%s/%s/commits" % (owner, REPO))
        return
    except SystemExit:
        pass
    print("bootstrap empty repo")
    api("PUT", "/repos/%s/%s/contents/.bootstrap" % (owner, REPO), {
        "message": "chore: bootstrap", "content": base64.b64encode(b"bootstrap\n").decode()})


def collect():
    files = []
    for dp, dns, fns in os.walk(ROOT):
        rel_dir = os.path.relpath(dp, ROOT).replace(os.sep, "/")
        if rel_dir == ".":
            rel_dir = ""
        dns[:] = [d for d in dns if d not in SKIP_DIRS and (rel_dir + "/" + d).strip("/") not in SKIP_PATHS]
        for f in fns:
            rel = (rel_dir + "/" + f).strip("/")
            if rel in SKIP_PATHS:
                continue
            if any(rel.endswith(s) for s in SKIP_SUFFIX):
                continue
            files.append(rel)
    return sorted(files)


def main():
    me = api("GET", "/user")
    owner = me["login"]
    print("user:", owner)
    try:
        repo = api("GET", "/repos/%s/%s" % (owner, REPO))
        print("repo exists:", repo["html_url"])
    except SystemExit:
        repo = api("POST", "/user/repos", {
            "name": REPO, "description": DESC, "private": False,
            "has_issues": True, "has_wiki": False, "auto_init": False})
        print("repo created:", repo["html_url"])

    ensure_commit(owner)

    files = collect()
    print("files:", len(files))
    tree = []
    for rel in files:
        full = os.path.join(ROOT, rel.replace("/", os.sep))
        data = open(full, "rb").read()
        blob = api("POST", "/repos/%s/%s/git/blobs" % (owner, REPO),
                   {"content": base64.b64encode(data).decode(), "encoding": "base64"})
        tree.append({"path": rel, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        print("  blob", rel, len(data))

    new_tree = api("POST", "/repos/%s/%s/git/trees" % (owner, REPO), {"tree": tree})
    parents = []
    for br in ("main", "master"):
        try:
            ref = api("GET", "/repos/%s/%s/git/ref/heads/%s" % (owner, REPO, br))
            parents = [ref["object"]["sha"]]
            break
        except SystemExit:
            continue

    commit = api("POST", "/repos/%s/%s/git/commits" % (owner, REPO), {
        "message": "release: %s 一键提取/导入 AuthKey（Windows + Android）" % VERSION,
        "tree": new_tree["sha"], "parents": parents})
    try:
        api("POST", "/repos/%s/%s/git/refs" % (owner, REPO),
            {"ref": "refs/heads/main", "sha": commit["sha"]})
    except SystemExit:
        api("PATCH", "/repos/%s/%s/git/refs/heads/main" % (owner, REPO),
            {"sha": commit["sha"], "force": True})
    api("PATCH", "/repos/%s/%s" % (owner, REPO), {"default_branch": "main"})
    print("commit:", commit["sha"])

    ver = VERSION.lstrip("vV")
    body_file = os.path.join(ROOT, ".tmp", "release_body.md")
    if os.path.exists(body_file):
        body = io.open(body_file, encoding="utf-8").read()
    else:
        body = "\n".join([
            "## 东放 AuthKey 管家 v%s" % ver,
            "",
            "_" + DESC + "_",
            "",
            "### 下载",
            "- AuthKeyManager-win64.zip — Windows 桌面版（解压即用，内置 adb）",
            "- HousamoAuthKeyManager-%s.apk — Android 版" % ver,
        ])
    title = os.environ.get("HAK_TITLE") or ("v%s" % ver)
    try:
        rel = api("POST", "/repos/%s/%s/releases" % (owner, REPO), {
            "tag_name": VERSION, "name": title, "body": body,
            "target_commitish": "main", "draft": False, "prerelease": False})
    except SystemExit:
        print("release exists, updating", VERSION)
        rel = api("GET", "/repos/%s/%s/releases/tags/%s" % (owner, REPO, VERSION))
        api("PATCH", "/repos/%s/%s/releases/%d" % (owner, REPO, rel["id"]),
            {"name": title, "body": body})
    print("release:", rel["html_url"])

    assets = ["dist/AuthKeyManager-win64.zip",
              "dist/HousamoAuthKeyManager-%s.apk" % ver]
    for asset in assets:
        p = os.path.join(ROOT, asset.replace("/", os.sep))
        if not os.path.exists(p):
            print("  skip missing", asset)
            continue
        name = os.path.basename(p)
        data = open(p, "rb").read()
        for existing in rel.get("assets", []):
            if existing.get("name") == name:
                api("DELETE", "/repos/%s/%s/releases/assets/%d" % (owner, REPO, existing["id"]))
        url = "https://uploads.github.com/repos/%s/%s/releases/%d/assets?name=%s" % (
            owner, REPO, rel["id"], urllib.parse.quote(name))
        info = None
        for attempt in range(6):
            try:
                req = urllib.request.Request(url, data=data, method="POST", headers={
                    "Authorization": "Bearer " + TOK,
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "HousamoAuthKeyManager",
                    "Content-Type": "application/octet-stream",
                    "Connection": "close"})
                with urllib.request.urlopen(req, timeout=600) as r:
                    info = json.load(r)
                break
            except urllib.error.HTTPError as e:
                msg = e.read().decode("utf-8", "replace")[:200]
                print("  upload retry", attempt, e.code, msg, flush=True)
                if e.code == 422:
                    break
            except Exception as e:
                print("  upload retry", attempt, type(e).__name__, flush=True)
            time.sleep(5 + attempt * 5)
        if info:
            print("  uploaded", name, info.get("size"), info.get("browser_download_url"))
        else:
            print("  FAILED asset", name)

    info = api("GET", "/repos/%s/%s" % (owner, REPO))
    print("")
    print("DONE", info["html_url"])
    print("RELEASE", rel["html_url"])


if __name__ == "__main__":
    main()
