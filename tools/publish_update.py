# -*- coding: utf-8 -*-
"""Push a small update (v1.0.1) and attach the new APK to a fresh release."""
import base64
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOK = open(os.path.join(ROOT, ".tmp", "gh_token.txt")).read().strip()
OWNER = "fenghuo6183"
REPO = "HousamoAuthKeyManager"
VERSION = "v1.0.1"
FILES = ["android/AndroidManifest.xml", "android/src/com/housamo/authkey/MainActivity.java",
         "android/build_apk.py", "README.md"]


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
        cur = api("GET", "/repos/%s/%s/contents/%s" % (OWNER, REPO, rel))
        sha = cur["sha"]
        newsha = base64.b64encode(hashlib.sha1(b"blob %d\0" % len(data) + data).digest()).hex()
        if newsha == sha:
            print("  unchanged", rel)
            continue
        api("PUT", "/repos/%s/%s/contents/%s" % (OWNER, REPO, rel), {
            "message": "fix(android): 修正 Android 11+ 包可见性导致游戏检测失败",
            "content": base64.b64encode(data).decode(), "sha": sha, "branch": "main"})
        print("  updated", rel)


def upload(release_id, name, path):
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
    print("updating files...")
    update_files()
    body = "\n".join([
        "## v1.0.1",
        "",
        "修复：Android 端顶部一直显示「游戏：未检测到」。",
        "",
        "原因：targetSdk 34 会应用 Android 11+ 的包可见性限制，应用默认看不到别的应用的包名，"
        "getPackageInfo() 直接抛 NameNotFound，所以游戏明明装着也被判成没装。",
        "",
        "修复内容：",
        "- AndroidManifest 增加 queries 声明游戏包名 + QUERY_ALL_PACKAGES 权限",
        "- 包名检测增加兜底：/sdcard/Android/data/jp.co.lifewonders.housamo 存在即视为已安装",
        "- 启动日志打印所有含 housamo / lifewonders 的包名和数据目录状态，方便排查",
        "",
        "签名与 1.0.0 相同，可直接覆盖安装。",
    ])
    try:
        rel = api("POST", "/repos/%s/%s/releases" % (OWNER, REPO), {
            "tag_name": VERSION, "name": "v1.0.1 修复安卓端游戏检测", "body": body,
            "target_commitish": "main", "draft": False, "prerelease": False})
    except SystemExit as e:
        print("release create:", e)
        rel = api("GET", "/repos/%s/%s/releases/tags/%s" % (OWNER, REPO, VERSION))
    print("release:", rel["html_url"])
    apk = os.path.join(ROOT, "dist", "HousamoAuthKeyManager-1.0.1.apk")
    upload(rel["id"], os.path.basename(apk), apk)


if __name__ == "__main__":
    main()
