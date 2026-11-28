# -*- coding: utf-8 -*-
"""Publish the Windows desktop build as a desktop-only release."""
import base64
import glob
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
VERSION = "v1.0.21-win"
ZIP = os.path.join(ROOT, "dist", "AuthKeyManager-win64.zip")

BODY = "\n".join([
    "## v1.0.21（Windows 桌面端）",
    "",
    "把手机端这段时间补的功能搬到桌面端，界面和设置页也跟着扩了。",
    "",
    "**局域网传输**",
    "- 账号库工具栏新增「局域网传输」：点开得到带配对码的地址，手机连同一个 Wi-Fi 用浏览器打开，逐条查看、逐条下载 key",
    "- 复制地址 / 在浏览器打开 / 停止三个按钮；关掉窗口立即停服",
    "",
    "**深色模式**",
    "- 设置页「主题」一键切浅色 / 深色，整窗即时重建，当前页、账号列表、操作日志都保留，不用重启",
    "- 深色下二维码仍是白底，不会被反色",
    "",
    "**应用锁**",
    "- 设置页「数据与存储」里设 4-6 位数字密码，下次打开程序先弹解锁窗",
    "- 只存 PBKDF2-SHA256 摘要和随机盐，设置文件里没有明文；连错 5 次窗口自动关闭",
    "",
    "**防止截屏**",
    "- 打开后系统截图和录屏里这个窗口是黑的（WDA_EXCLUDEFROMCAPTURE，Windows 10 2004+）",
    "",
    "**排版**",
    "- 设置页三张卡放不下时先隐藏日志卡，仍放不下就整页滚动；150% 缩放下解锁窗按内容自适应高度，不会被裁",
    "",
    "下载 `AuthKeyManager-win64.zip`，解压到任意目录，双击 AuthKeyManager.exe 即可，免安装。",
    "",
    "> 桌面端走自己的版本号（1.0.21-win），标记为 pre-release，安卓端读 releases/latest 不受影响。",
])


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
        if e.code == 404:
            return None
        raise SystemExit("HTTP %d %s %s -> %s" % (e.code, method, path,
                                                  e.read().decode("utf-8", "replace")[:300]))


def source_files():
    files = ["README.md", "win/main.py", "win/build.bat",
             "tools/make_win_zip.py", "tools/fetch_pyinstaller.py"]
    files += sorted(glob.glob("win/app/*.py"))
    files += sorted(glob.glob("win/tests/test_*.py"))
    files += sorted(glob.glob("docs/screens/win-*.png"))
    return [f.replace(os.sep, "/") for f in files]


def put_file(rel, message):
    full = os.path.join(ROOT, rel.replace("/", os.sep))
    if not os.path.exists(full):
        print("  missing", rel)
        return
    data = open(full, "rb").read()
    cur = api("GET", "/repos/%s/%s/contents/%s" % (OWNER, REPO, rel))
    payload = {"message": message,
               "content": base64.b64encode(data).decode(),
               "branch": "main"}
    if cur:
        newsha = base64.b64encode(hashlib.sha1(b"blob %d\0" % len(data) + data).digest()).hex()
        if newsha == cur["sha"]:
            print("  unchanged", rel)
            return
        payload["sha"] = cur["sha"]
    api("PUT", "/repos/%s/%s/contents/%s" % (OWNER, REPO, rel), payload)
    print("  wrote", rel, len(data))


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
            with urllib.request.urlopen(req, timeout=900) as r:
                info = json.load(r)
            print("  uploaded", name, info.get("size"), info.get("browser_download_url"))
            return
        except urllib.error.HTTPError as e:
            print("  retry", i, e.code, e.read().decode("utf-8", "replace")[:150], flush=True)
        except Exception as e:
            print("  retry", i, type(e).__name__, flush=True)
        time.sleep(5 + i * 5)
    raise SystemExit("upload failed: " + name)


def main():
    print("pushing sources...")
    for rel in source_files():
        put_file(rel, "feat(win): LAN share / dark mode / app lock / capture guard")

    print("creating release...")
    try:
        rel = api("POST", "/repos/%s/%s/releases" % (OWNER, REPO), {
            "tag_name": VERSION, "name": "v1.0.21 Windows 桌面端", "body": BODY,
            "target_commitish": "main", "draft": False, "prerelease": True})
    except SystemExit as e:
        print("release create:", e)
        rel = api("GET", "/repos/%s/%s/releases/tags/%s" % (OWNER, REPO, VERSION))
    print("release:", rel["html_url"])
    existing = {a["name"]: a["id"] for a in rel.get("assets", [])}
    name = os.path.basename(ZIP)
    if name in existing:
        print("  replacing existing asset:", name)
        api("DELETE", "/repos/%s/%s/releases/assets/%d" % (OWNER, REPO, existing[name]))
    upload(rel["id"], name, ZIP)
    print("done")


if __name__ == "__main__":
    main()
