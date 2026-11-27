# -*- coding: utf-8 -*-
r"""In-app updater: check GitHub, download the full zip, replace the install tree.

Mirrors MAA's model: the running exe copies itself to a staging folder, the
copy waits for the parent to exit, swaps files, then relaunches. State lives
in %APPDATA%\HousamoAuthKeyManager\update_state.json so a killed update can be
explained (and retried) on the next start.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile

from . import config

UP_API = "https://api.github.com/repos/fenghuo6183/HousamoAuthKeyManager/releases?per_page=20"
ASSET_NAME = "AuthKeyManager-win64.zip"
MIRRORS = ("https://gh-proxy.com/", "https://ghfast.top/")
STATE_NAME = "update_state.json"
LOG_NAME = "update.log"
_UA = "HousamoAuthKeyManager-Updater"


# -- versions ----------------------------------------------------------
def parse_version(text):
    numbers = re.findall(r"\d+", (text or "").lstrip("vV"))
    return tuple(int(n) for n in numbers[:4]) or (0,)


def is_newer(remote_tag, local_version):
    return parse_version(remote_tag) > parse_version(local_version)


FORCE_MARKERS = ("force-update", "强制更新")


def is_forced(release):
    """True when the release says it must be installed (重要/安全修复).

    发版时在 release 说明（或标题）里写 force-update，客户端就不给跳过。
    """
    release = release or {}
    text = "%s\n%s" % (release.get("body") or "", release.get("name") or "")
    return any(marker in text for marker in FORCE_MARKERS)


def pick_asset(release):
    assets = (release or {}).get("assets") or []
    for asset in assets:
        if asset.get("name") == ASSET_NAME:
            return _asset(asset)
    for asset in assets:
        if (asset.get("name") or "").lower().endswith(".zip"):
            return _asset(asset)
    return None


def _asset(asset):
    return {"name": asset.get("name") or "",
            "url": asset.get("browser_download_url") or "",
            "digest": asset.get("digest") or ""}


def has_desktop_asset(release):
    for asset in (release or {}).get("assets") or []:
        if (asset.get("name") or "") == ASSET_NAME:
            return True
    return False


def select_release(releases):
    """Newest published release that actually ships the desktop zip.

    The repo also carries Android-only releases; those must never be offered to
    the desktop app (and a Windows-only release must never be the "latest" that
    the Android update check sees).
    """
    candidates = [r for r in (releases or []) if not (r or {}).get("draft")]
    for release in candidates:
        if has_desktop_asset(release):
            return release
    return {}


def fetch_latest(timeout=15):
    request = urllib.request.Request(UP_API, headers={"User-Agent": _UA,
                                                      "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if isinstance(payload, dict):
        payload = [payload]
    return select_release(payload)


# -- paths / state -----------------------------------------------------
def update_dir():
    folder = os.path.join(os.environ.get("TEMP") or os.environ.get("TMP") or ".",
                          "HousamoAuthKeyManager-update")
    os.makedirs(folder, exist_ok=True)
    return folder


def state_path():
    return os.path.join(config.app_dir(), STATE_NAME)


def log_path():
    return os.path.join(config.app_dir(), LOG_NAME)


def append_log(line):
    try:
        with open(log_path(), "a", encoding="utf-8") as fh:
            fh.write("%s  %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), line))
    except Exception:
        pass


def read_state():
    try:
        with open(state_path(), "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def write_state(**fields):
    data = read_state()
    data.update(fields)
    data["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        tmp = state_path() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, state_path())
    except Exception:
        pass
    return data


def install_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def dir_writable(path):
    probe = os.path.join(path, ".write-test-%d" % os.getpid())
    try:
        with open(probe, "wb") as fh:
            fh.write(b"x")
        os.remove(probe)
        return True
    except Exception:
        return False


# -- download ----------------------------------------------------------
def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _expected(digest):
    text = (digest or "").strip()
    if text.startswith("sha256:"):
        return text.split(":", 1)[1].lower()
    return text.lower() if len(text) == 64 else ""


def _fetch(url, dest, timeout=120):
    request = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(request, timeout=timeout) as response, \
            open(dest, "wb") as fh:
        shutil.copyfileobj(response, fh)


def download(zip_url, digest="", log=None):
    """Download to update_dir(); verify sha256 when known. Raises on failure."""
    def note(msg):
        if log:
            log(msg)

    target = os.path.join(update_dir(), ASSET_NAME)
    candidates = [zip_url] + [prefix + zip_url for prefix in MIRRORS]
    expected = _expected(digest)
    last_error = None
    for index, url in enumerate(candidates):
        for attempt in (1, 2):
            try:
                note("下载第 %d 个源（第 %d 次）：%s" % (index + 1, attempt, url))
                _fetch(url, target)
                if expected and sha256_file(target) != expected:
                    raise IOError("sha256 校验失败")
                note("下载完成：%s" % target)
                return target
            except Exception as exc:
                last_error = exc
                note("这个源失败：%s" % exc)
                try:
                    os.remove(target)
                except OSError:
                    pass
    raise IOError("下载更新失败：%s" % last_error)


# -- install -----------------------------------------------------------
def stage_copy(install, stage=None, log=None):
    stage = stage or os.path.join(update_dir(), "stage")
    if os.path.isdir(stage):
        shutil.rmtree(stage, ignore_errors=True)
    shutil.copytree(install, stage)
    if log:
        log("已复制程序到临时目录：%s" % stage)
    return stage


def _wait_pid(pid, timeout=90):
    if not pid:
        return
    try:
        import ctypes
        SYNCHRONIZE = 0x00100000
        handle = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, int(pid))
        if handle:
            ctypes.windll.kernel32.WaitForSingleObject(handle, int(timeout * 1000))
            ctypes.windll.kernel32.CloseHandle(handle)
    except Exception:
        time.sleep(2)


def _zip_members(zf):
    names = [n for n in zf.namelist() if not n.endswith("/")]
    if not names:
        return names, ""
    tops = {n.split("/", 1)[0] for n in names}
    if len(tops) == 1 and "/" in names[0]:
        top = tops.pop()
        if "." in top:
            return names, ""
        return names, top + "/"
    return names, ""


def apply_update(zip_path, install, parent_pid=0, log=print):
    """Wait for the old process, replace the install tree, relaunch. Returns bool."""
    try:
        write_state(stage="applying", zip=zip_path, install=install)
        log("等待旧进程退出…")
        _wait_pid(parent_pid)
        with zipfile.ZipFile(zip_path) as zf:
            names, prefix = _zip_members(zf)
            if not names:
                raise ValueError("更新包里没有文件")
            for member in names:
                rel = member[len(prefix):] if prefix and member.startswith(prefix) else member
                if not rel or rel.startswith("/") or ".." in rel.replace("\\", "/").split("/"):
                    raise ValueError("更新包含有非法路径：%s" % member)
                target = os.path.join(install, rel.replace("/", os.sep))
                os.makedirs(os.path.dirname(target), exist_ok=True)
                temp = target + ".new"
                with zf.open(member) as src, open(temp, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                os.replace(temp, target)
                log("已更新 %s" % rel)
        exe = os.path.join(install, "AuthKeyManager.exe")
        write_state(stage="done", finished_at=time.strftime("%Y-%m-%d %H:%M:%S"))
        log("更新完成，正在启动新版本…")
        if os.path.isfile(exe):
            try:
                subprocess.Popen([exe], cwd=install)
            except Exception as exc:
                # Files are already in place; a failed relaunch must not mark
                # the update as failed.
                log("更新已完成，但自动启动失败：%s" % exc)
        _cleanup()
        return True
    except Exception as exc:
        write_state(stage="failed", error=str(exc))
        log("更新失败：%s" % exc)
        return False


def _cleanup():
    for path in (os.path.join(update_dir(), ASSET_NAME),
                 os.path.join(update_dir(), "stage")):
        try:
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            elif os.path.isfile(path):
                os.remove(path)
        except Exception:
            pass
