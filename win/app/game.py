# -*- coding: utf-8 -*-
"""Game definitions and AuthKey extraction/import for the supported games."""
from __future__ import annotations

import hashlib
import os
import re
import tempfile
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class Game:
    id: str
    label: str
    pkg: str
    sub: str
    file: str

    @property
    def ext_dir(self):
        return "/sdcard/Android/data/%s/%s" % (self.pkg, self.sub)

    @property
    def ext_key(self):
        return self.ext_dir + "/" + self.file

    @property
    def prefs(self):
        return "/data/data/%s/shared_prefs/%s.v2.playerprefs.xml" % (self.pkg, self.pkg)

    @property
    def ext_candidates(self):
        base = "/storage/emulated/0/Android/data/%s/%s" % (self.pkg, self.sub)
        return [self.ext_key,
                self.ext_dir + "/" + self.file.lower(),
                base + "/" + self.file,
                base + "/" + self.file.lower()]

    @property
    def prefs_candidates(self):
        tail = "/shared_prefs/%s.v2.playerprefs.xml" % self.pkg
        return ["/data/data/%s%s" % (self.pkg, tail),
                "/data/user/0/%s%s" % (self.pkg, tail)]


GAME_HOUSAMO = Game("housamo", "东京放课后", "jp.co.lifewonders.housamo",
                    "files/Data", "AuthKey")
GAME_LIVEAHERO = Game("liveahero", "LiveAHero", "jp.co.lifewonders.liveahero",
                      "files/datas", "userKey")
GAMES = (GAME_HOUSAMO, GAME_LIVEAHERO)

# Backwards compatible aliases (old code and old tests referenced these).
PKG = GAME_HOUSAMO.pkg
EXT_DIR = GAME_HOUSAMO.ext_dir
AUTHKEY = GAME_HOUSAMO.ext_key
PREFS = GAME_HOUSAMO.prefs
EXT_CANDIDATES = GAME_HOUSAMO.ext_candidates
MAGIC_HINTS = ("auth", "key", "token", "session")


class GameError(RuntimeError):
    pass


def game_by_id(game_id):
    for g in GAMES:
        if g.id == game_id:
            return g
    return GAME_HOUSAMO


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def clean_key(data):
    """Normalise the raw file bytes into the token we store and write back."""
    if not data:
        return b""
    text = data
    if text.startswith(b"\xef\xbb\xbf"):
        text = text[3:]
    return text.strip()


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
    return "%s\u2026%s (%d)" % (text[:4], text[-4:], len(text))


def game_installed(adb, serial, game=GAME_HOUSAMO):
    try:
        out = adb.shell(serial, "pm list packages %s" % game.pkg, timeout=15)
        return game.pkg in out
    except Exception:
        return False


def _read_file(adb, serial, path, root=False):
    cmd = 'cat "%s" 2>/dev/null' % path
    if root:
        cmd = "su -c %s" % _shquote(cmd)
    return adb.shell_bytes(serial, cmd)


def _shquote(text):
    return "'" + text.replace("'", "'\\''") + "'"


def extract(adb, serial, game=GAME_HOUSAMO, log=None):
    """Return (key_bytes, method_description) for the given game."""
    def note(msg):
        if log:
            log(msg)

    for path in game.ext_candidates:
        note("尝试读取 " + path)
        data = _read_file(adb, serial, path)
        if looks_like_key(data):
            note("已从外部存储读取到 " + game.label + " 的 key")
            return clean_key(data), path

    note("外部存储未找到，尝试 root 路径 shared_prefs")
    if adb.su_available(serial):
        for prefs in game.prefs_candidates:
            data = _read_file(adb, serial, prefs, root=True)
            if not data:
                continue
            text = data.decode("utf-8", "replace")
            match = re.search(
                r'<string name="[^"]*(?:auth|key|token)[^"]*"\s*>([^<]+)</string>',
                text, re.I)
            if match and looks_like_key(match.group(1).encode()):
                note("已从 shared_prefs 读取到 key")
                return clean_key(match.group(1).encode()), prefs
        listing = adb.shell(
            serial,
            "su -c %s" % _shquote(
                'find /data/data/%s -iname "*auth*" -o -iname "*key*" 2>/dev/null'
                % game.pkg),
            timeout=25)
        for line in listing.splitlines():
            line = line.strip()
            if not line:
                continue
            data = _read_file(adb, serial, line, root=True)
            if looks_like_key(data):
                note("已在 " + line + " 找到 key")
                return clean_key(data), line

    note("扫描游戏目录中的 *" + game.file + "* 文件")
    listing = adb.shell(
        serial, 'find %s -iname "*%s*" 2>/dev/null' % (game.ext_dir, game.file.lower()),
        timeout=25)
    for line in listing.splitlines():
        line = line.strip()
        if not line:
            continue
        data = _read_file(adb, serial, line)
        if looks_like_key(data):
            note("已在 " + line + " 找到 key")
            return clean_key(data), line

    raise GameError("没有找到 %s 的 key。请确认：游戏已登录过一次、设备已连接且已授权 "
                    "USB 调试；新版本可能把 key 放在私有目录，需要 root。" % game.label)


def _write_external(adb, serial, key, game, log):
    target = game.ext_key
    tmp_local = os.path.join(tempfile.gettempdir(), "housamo_%s.tmp" % game.id)
    with open(tmp_local, "wb") as fh:
        fh.write(key)
    remote_tmp = "/data/local/tmp/housamo_%s.tmp" % game.id
    adb.push(serial, tmp_local, remote_tmp)
    log("已把 key 上传到设备临时目录")
    try:
        adb.shell(serial, 'mkdir -p "%s"' % game.ext_dir)
        # 原地覆盖：文件已存在时 cat > 保留原属主/权限
        stdin_cmd = ('if [ -f "%s" ]; then cat > "%s"; else cat > "%s" && chmod 660 "%s"; fi'
                     % (target, target, target, target))
        adb.shell_stdin(serial, stdin_cmd, key, timeout=30)
        if adb.shell_bytes(serial, 'cat "%s"' % target) == key:
            adb.shell(serial, 'chmod 644 "%s"' % target)
            log("已写入外部存储 " + game.file)
            return target
    except Exception as exc:
        log("外部存储写入失败：%s" % exc)

    if adb.su_available(serial):
        adb.shell(serial, "su -c %s" % _shquote("mkdir -p %s" % game.ext_dir), timeout=20)
        adb.shell(serial, "su -c %s" % _shquote("cp %s %s" % (remote_tmp, target)), timeout=25)
        uid = adb.shell(
            serial, "su -c %s" % _shquote('stat -c %%u "%s"' % target), timeout=15).strip()
        if uid.isdigit():
            adb.shell(serial, "su -c %s" % _shquote('chown %s:%s "%s"' % (uid, uid, target)),
                      timeout=15)
            adb.shell(serial, "su -c %s" % _shquote('chmod 660 "%s"' % target), timeout=15)
        if adb.shell_bytes(serial, 'cat "%s"' % target) == key:
            log("已通过 root 写入外部存储 " + game.file)
            return target
    raise GameError("写入 key 失败，请确认设备存储可写。")


def _write_shared_prefs(adb, serial, key, game=GAME_HOUSAMO, log=None):
    def note(msg):
        if log:
            log(msg)

    if not adb.su_available(serial):
        raise GameError("设备没有 root，无法写入私有目录。")
    prefs = game.prefs
    raw = _read_file(adb, serial, prefs, root=True)
    if not raw:
        raise GameError("未找到 shared_prefs 配置文件。")
    text = raw.decode("utf-8", "replace")
    value = key.decode("utf-8", "replace")
    new_text, count = re.subn(
        r'(<string name="[^"]*(?:auth|key|token)[^"]*"\s*>)([^<]*)(</string>)',
        lambda m: m.group(1) + value + m.group(3), text, count=1, flags=re.I)
    if count == 0:
        raise GameError("配置文件里没有 auth_key 字段。")
    name = "housamo_prefs_%s.tmp" % game.id
    tmp_local = os.path.join(tempfile.gettempdir(), name)
    with open(tmp_local, "wb") as fh:
        fh.write(new_text.encode("utf-8"))
    remote_tmp = "/data/local/tmp/" + name
    adb.push(serial, tmp_local, remote_tmp)
    uid = adb.shell(serial, "su -c %s" % _shquote('stat -c %%u "%s"' % prefs),
                    timeout=15).strip()
    adb.shell(serial, "su -c %s" % _shquote("cp %s %s" % (remote_tmp, prefs)), timeout=25)
    if uid.isdigit():
        adb.shell(serial, "su -c %s" % _shquote('chown %s:%s "%s"' % (uid, uid, prefs)),
                  timeout=15)
    note("已通过 root 写入 shared_prefs")
    return prefs


def import_key(adb, serial, key, game=GAME_HOUSAMO, log=None):
    """Stop the game, write the key, verify by reading it back."""
    def note(msg):
        if log:
            log(msg)

    if not looks_like_key(key):
        raise GameError("这个 key 内容看起来不合法，已取消写入。")
    note("停止 %s 进程" % game.label)
    adb.shell(serial, "am force-stop %s" % game.pkg, timeout=20)
    time.sleep(1)
    target = _write_external(adb, serial, clean_key(key), game, note)
    note("校验写入结果")
    back = adb.shell_bytes(serial, 'cat "%s"' % target)
    if clean_key(back) != clean_key(key):
        raise GameError("写入后读回内容不一致，已中止。")
    note("写入成功，重新打开游戏即可登录。")
    return target


def backup_current(adb, serial, vault, game=GAME_HOUSAMO, log=None):
    """Copy whatever key the device currently holds into the backup section."""
    try:
        data, source = extract(adb, serial, game, log)
    except Exception:
        return None
    stamp = time.strftime("%Y-%m-%d %H:%M")
    name = "导入前备份 %s" % stamp
    entry, _created = vault.add(name=name, key=data, note="导入前自动备份", source=source,
                                device=serial, kind="backup", game=game.id)
    return entry
