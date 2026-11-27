# -*- coding: utf-8 -*-
"""Housamo (东京放课后召唤师) AuthKey extraction and import."""
from __future__ import annotations

import hashlib
import os
import re
import tempfile
import time

PKG = "jp.co.lifewonders.housamo"
EXT_DIR = "/sdcard/Android/data/%s/files/Data" % PKG
AUTHKEY = EXT_DIR + "/AuthKey"
EXT_CANDIDATES = [
    AUTHKEY,
    EXT_DIR + "/authkey",
    "/storage/emulated/0/Android/data/%s/files/Data/AuthKey" % PKG,
    "/storage/emulated/0/Android/data/%s/files/Data/authkey" % PKG,
]
PREFS = "/data/data/%s/shared_prefs/%s.v2.playerprefs.xml" % (PKG, PKG)
MAGIC_HINTS = ("auth", "key", "token", "session")


class GameError(RuntimeError):
    pass


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def clean_key(data):
    """Normalise the raw file bytes into the token we store and write back."""
    if not data:
        return b""
    text = data
    if text.startswith(b"\xef\xbb\xbf"):
        text = text[3:]
    text = text.strip()
    return text


def looks_like_key(data):
    data = clean_key(data)
    if len(data) < 8 or len(data) > 8192:
        return False
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError:
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9+/=_.:\-]+", text))


def fingerprint(data):
    text = clean_key(data).decode("utf-8", "replace")
    if len(text) <= 8:
        return text
    return "%s…%s (%d)" % (text[:4], text[-4:], len(text))


def game_installed(adb, serial):
    try:
        out = adb.shell(serial, "pm list packages %s" % PKG, timeout=15)
        return PKG in out
    except Exception:
        return False


def _read_file(adb, serial, path, root=False):
    cmd = 'cat "%s" 2>/dev/null' % path
    if root:
        cmd = 'su -c %s' % _shquote(cmd)
    data = adb.shell_bytes(serial, cmd)
    return data


def _shquote(text):
    return "'" + text.replace("'", "'\\''") + "'"


def extract(adb, serial, log=None):
    """Return (key_bytes, method_description)."""
    def note(msg):
        if log:
            log(msg)

    for path in EXT_CANDIDATES:
        note("尝试读取 " + path)
        data = _read_file(adb, serial, path)
        if looks_like_key(data):
            note("已从外部存储读取到 AuthKey")
            return clean_key(data), path

    note("外部存储未找到，尝试 root 路径 shared_prefs")
    if adb.su_available(serial):
        data = _read_file(adb, serial, PREFS, root=True)
        if data:
            text = data.decode("utf-8", "replace")
            match = re.search(r'<string name="[^"]*(?:auth|key|token)[^"]*"\s*>([^<]+)</string>', text, re.I)
            if match and looks_like_key(match.group(1).encode()):
                note("已从 shared_prefs 读取到 AuthKey")
                return clean_key(match.group(1).encode()), PREFS
        listing = adb.shell(serial, "su -c %s" % _shquote('find /data/data/%s -iname "*auth*" -o -iname "*key*" 2>/dev/null' % PKG), timeout=25)
        for line in listing.splitlines():
            line = line.strip()
            if not line:
                continue
            data = _read_file(adb, serial, line, root=True)
            if looks_like_key(data):
                note("已在 " + line + " 找到 AuthKey")
                return clean_key(data), line

    note("扫描游戏目录中的 *AuthKey* 文件")
    listing = adb.shell(serial, 'find %s -iname "*authkey*" 2>/dev/null' % EXT_DIR, timeout=25)
    for line in listing.splitlines():
        line = line.strip()
        if not line:
            continue
        data = _read_file(adb, serial, line)
        if looks_like_key(data):
            note("已在 " + line + " 找到 AuthKey")
            return clean_key(data), line

    raise GameError("没有找到 AuthKey。请确认：游戏已登录过一次、设备已连接且已授权 USB 调试；新版本可能把 key 放在私有目录，需要 root。")


def _write_external(adb, serial, key, log):
    target = AUTHKEY
    tmp_local = os.path.join(tempfile.gettempdir(), "housamo_authkey.tmp")
    with open(tmp_local, "wb") as fh:
        fh.write(key)
    remote_tmp = "/data/local/tmp/housamo_authkey.tmp"
    adb.push(serial, tmp_local, remote_tmp)
    log("已把 key 上传到设备临时目录")
    try:
        adb.shell(serial, 'mkdir -p "%s"' % EXT_DIR)
        adb.shell(serial, 'cp "%s" "%s"' % (remote_tmp, target), timeout=25)
        if adb.shell_bytes(serial, 'cat "%s"' % target) == key:
            adb.shell(serial, 'chmod 644 "%s"' % target)
            log("已写入外部存储 AuthKey")
            return target
    except Exception as exc:
        log("外部存储写入失败：%s" % exc)

    if adb.su_available(serial):
        adb.shell(serial, 'su -c %s' % _shquote('mkdir -p %s' % EXT_DIR), timeout=20)
        adb.shell(serial, 'su -c %s' % _shquote('cp %s %s' % (remote_tmp, target)), timeout=25)
        uid = adb.shell(serial, 'su -c %s' % _shquote('stat -c %%u "%s"' % target), timeout=15).strip()
        if uid.isdigit():
            adb.shell(serial, 'su -c %s' % _shquote('chown %s:%s "%s"' % (uid, uid, target)), timeout=15)
            adb.shell(serial, 'su -c %s' % _shquote('chmod 660 "%s"' % target), timeout=15)
        if adb.shell_bytes(serial, 'cat "%s"' % target) == key:
            log("已通过 root 写入外部存储 AuthKey")
            return target
    raise GameError("写入 AuthKey 失败，请确认设备存储可写。")


def _write_shared_prefs(adb, serial, key, log):
    if not adb.su_available(serial):
        raise GameError("设备没有 root，无法写入私有目录。")
    raw = _read_file(adb, serial, PREFS, root=True)
    if not raw:
        raise GameError("未找到 shared_prefs 配置文件。")
    text = raw.decode("utf-8", "replace")
    value = key.decode("utf-8", "replace")
    new_text, count = re.subn(r'(<string name="[^"]*(?:auth|key|token)[^"]*"\s*>)([^<]*)(</string>)',
                              lambda m: m.group(1) + value + m.group(3), text, count=1, flags=re.I)
    if count == 0:
        raise GameError("配置文件里没有 auth_key 字段。")
    tmp_local = os.path.join(tempfile.gettempdir(), "housamo_prefs.tmp")
    with open(tmp_local, "wb") as fh:
        fh.write(new_text.encode("utf-8"))
    remote_tmp = "/data/local/tmp/housamo_prefs.tmp"
    adb.push(serial, tmp_local, remote_tmp)
    uid = adb.shell(serial, 'su -c %s' % _shquote('stat -c %%u "%s"' % PREFS), timeout=15).strip()
    adb.shell(serial, 'su -c %s' % _shquote('cp %s %s' % (remote_tmp, PREFS)), timeout=25)
    if uid.isdigit():
        adb.shell(serial, 'su -c %s' % _shquote('chown %s:%s "%s"' % (uid, uid, PREFS)), timeout=15)
    log("已通过 root 写入 shared_prefs")
    return PREFS


def import_key(adb, serial, key, log=None):
    """Stop the game, write the key, verify by reading it back."""
    def note(msg):
        if log:
            log(msg)

    if not looks_like_key(key):
        raise GameError("这个 AuthKey 内容看起来不合法，已取消写入。")
    note("停止游戏进程")
    adb.shell(serial, "am force-stop %s" % PKG, timeout=20)
    time.sleep(1)
    target = _write_external(adb, serial, clean_key(key), note)
    note("校验写入结果")
    back = adb.shell_bytes(serial, 'cat "%s"' % target)
    if clean_key(back) != clean_key(key):
        raise GameError("写入后读回内容不一致，已中止。")
    note("写入成功，重新打开游戏即可登录。")
    return target


def backup_current(adb, serial, vault, log=None):
    try:
        data, source = extract(adb, serial, log)
    except Exception:
        return None
    stamp = time.strftime("%Y%m%d-%H%M%S")
    name = "自动备份 %s %s" % (serial, stamp)
    return vault.add(name=name, key=data, note="导入前自动备份", source=source, device=serial)
