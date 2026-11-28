# Windows 端功能对齐安卓端（1.2.0）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox ([ ]) syntax for tracking.

**Goal:** 让 Windows 客户端补齐安卓端的四项能力——双游戏、导入前备份独立分区、启动核对、应用内自动更新——并保持现有外观与四档缩放下零裁切。

**Architecture:** 先把单一游戏的常量化逻辑抽成 `Game` 数据模型，账号库按游戏拆成独立加密文件（`vault.<game.id>.dat`）；界面在现有 `App` 上增加两个切换器（游戏 / 账号·备份）与一个核对提示条；更新放在独立 `updater.py`，用「副本进程 + `--apply-update`」替换安装目录，状态写 `update_state.json`。

**Tech Stack:** Python 3.11+ / tkinter / Pillow（已装）、stdlib `urllib.request` + `zipfile`（不引入新依赖）、DPAPI 加密（现有 `app/dpapi.py`）。

**Spec:** docs/superpowers/specs/2026-11-27-win-parity-design.md

## Global Constraints

- 只改 `win/` 与 `README.md`；不碰 `android/`。
- 不新增第三方依赖：网络只允许 `urllib.request`，解压只允许 `zipfile`。
- 这个仓库**不是 git 仓库**：不要执行任何 `git` 命令。每个任务末尾用「`py_compile` + 测试 + `--selftest`」当检查点。
- 所有新尺寸必须走 `theme.px()`；`PillButton` / `MiniSlider` 自己会缩放，调用方传 96dpi 设计值，不要再包 `px()`。
- 用户可见文案用中文；日志统一 `self.log(tag, msg)`，tag 用「提取 / 导入 / 备份 / 设备 / 账号 / 错误 / 完成 / 设置 / 更新」。
- 测试文件放 `win/tests/`，每个文件可单独运行：`python win/tests/test_xxx.py`，末行 `if __name__ == "__main__": unittest.main()`。文件头固定两行：
  ```python
  import os, sys
  sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
  ```
- 测试不许读写真实 `%APPDATA%\HousamoAuthKeyManager`：一律 `os.environ["APPDATA"] = tempfile.mkdtemp()`（Task 3 后再加 `HOUSAMO_DATA_DIR` 支持）。
- 版本号 `1.2.0` 只在 Task 10 改；之前保持 `1.1.1`。

---

## 文件结构

| 文件 | 责任 |
| --- | --- |
| `win/app/game.py`（改） | `Game` 模型 + 双游戏的路径/提取/写入/备份 |
| `win/app/vault.py`（改） | 按游戏分文件、`kind` 分段、`.hak` v2 |
| `win/app/config.py`（改） | 新设置键、`HOUSAMO_DATA_DIR`、忽略表读写 |
| `win/app/widgets.py`（改） | 新增 `Segmented` 切换器 |
| `win/app/reconcile.py`（新） | 启动核对的纯逻辑（指纹判定） |
| `win/app/updater.py`（新） | 版本比较、检查、下载校验、副本进程替换、状态机 |
| `win/app/ui.py`（改） | 游戏切换、账号/备份分段、核对提示条、更新卡 |
| `win/main.py`（改） | 单实例、`--apply-update`、selftest 隔离数据目录 |
| `win/tests/*.py`（新） | 各任务的可运行测试 |
| `README.md`（改） | 功能列表、更新日志、构建说明 |

---

### Task 1: 多游戏数据层（game.py）

**Files:**
- Modify: `win/app/game.py`（整体重写，保留现有函数名）
- Modify: `win/app/ui.py`:546-561（`_init_backend` 支持 `HOUSAMO_NO_ADB`）、:948、:985、:988、:1003
- Test: `win/tests/test_game.py`

**Interfaces:**
- Consumes: 现有 `adb.Adb`（`shell / shell_bytes / shell_stdin / push / su_available`）
- Produces:
  - `Game(id, label, pkg, sub, file)`，属性 `ext_dir / ext_key / prefs / ext_candidates`
  - `GAME_HOUSAMO`、`GAME_LIVEAHERO`、`GAMES`、`game_by_id(game_id) -> Game`
  - `extract(adb, serial, game=GAME_HOUSAMO, log=None) -> (key_bytes, source_path)`
  - `import_key(adb, serial, key, game=GAME_HOUSAMO, log=None) -> remote_path`
  - `backup_current(adb, serial, vault, game=GAME_HOUSAMO, log=None) -> (entry, created) | None`
  - `game_installed(adb, serial, game=GAME_HOUSAMO) -> bool`

- [ ] **Step 1: 写失败测试** `win/tests/test_game.py`

```python
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import game


class GameModelTest(unittest.TestCase):
    def test_two_games(self):
        self.assertEqual([g.id for g in game.GAMES], ["housamo", "liveahero"])

    def test_housamo_paths(self):
        g = game.game_by_id("housamo")
        self.assertEqual(g.ext_dir,
                         "/sdcard/Android/data/jp.co.lifewonders.housamo/files/Data")
        self.assertEqual(g.ext_key, g.ext_dir + "/AuthKey")
        self.assertTrue(g.prefs.endswith("jp.co.lifewonders.housamo.v2.playerprefs.xml"))

    def test_liveahero_paths(self):
        g = game.game_by_id("liveahero")
        self.assertEqual(
            g.ext_key,
            "/sdcard/Android/data/jp.co.lifewonders.liveahero/files/datas/userKey")

    def test_unknown_game_falls_back(self):
        self.assertEqual(game.game_by_id("nope").id, "housamo")

    def test_candidates_have_lowercase_variant(self):
        g = game.game_by_id("liveahero")
        self.assertIn(g.ext_dir + "/userkey", g.ext_candidates)

    def test_clean_and_validate(self):
        self.assertEqual(game.clean_key(b"\xef\xbb\xbf abc \n"), b"abc")
        self.assertTrue(game.looks_like_key(b"A" * 32))
        self.assertFalse(game.looks_like_key(b"\x00\x01"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python win/tests/test_game.py`
Expected: `AttributeError: module 'app.game' has no attribute 'GAMES'`（当前只有模块级常量）

- [ ] **Step 3: 重写 `win/app/game.py`**

```python
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
    return "%s…%s (%d)" % (text[:4], text[-4:], len(text))


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
    name = "导入前备份 %s %s" % (serial, stamp)
    return vault.add(name=name, key=data, note="导入前自动备份", source=source,
                     device=serial, kind="backup", game=game.id)
```

- [ ] **Step 4: 改 ui.py 的 4 处调用点**

```python
# win/app/ui.py  do_extract.worker()
g = self.active_game
key, source = game.extract(self.adb, dev.serial, g, lambda m: self.log("提取", m))

# do_import.worker()
g = self.active_game
backup = game.backup_current(self.adb, dev.serial, self.vault, g, lambda m: self.log("备份", m))
target = game.import_key(self.adb, dev.serial, key, g, lambda m: self.log("导入", m))

# launch_game()
self.adb.shell(dev.serial, "monkey -p %s -c android.intent.category.LAUNCHER 1"
              % self.active_game.pkg, timeout=25)
```
Task 5 才会定义 `self.active_game`，本步先在 `__init__` 里加一行占位，Task 5 再完善：
```python
# win/app/ui.py  __init__  第 40 行附近
self.active_game = game.game_by_id(self.settings.get("active_game") or "housamo")
```
`_init_backend` 开头加无 adb 模式（测试用）：
```python
def _init_backend(self):
    if os.environ.get("HOUSAMO_NO_ADB") == "1":
        self.adb = None
        self._set_adb_chip("测试模式", "muted")
    else:
        try:
            self.adb = adb_mod.Adb()
            ...
```

- [ ] **Step 5: 跑测试与自检**

Run: `python win/tests/test_game.py`
Expected: `OK`
Run: `python -m py_compile win/app/game.py win/app/ui.py` → 无输出
Run: `python win/main.py --selftest` → `SELFTEST OK`

---

### Task 2: 账号库分文件 + 备份分段 + .hak v2

**Files:**
- Modify: `win/app/vault.py`
- Test: `win/tests/test_vault.py`

**Interfaces:**
- Consumes: `app.config.app_dir()`、`app.dpapi.protect/unprotect`、`app.game.game_by_id`
- Produces:
  - `default_vault_path(game_id="housamo")`、`vault_path_for(game_id)`
  - `migrate_legacy_vault() -> bool`
  - `Vault(path=None, game_id="housamo")`，属性 `game_id`
  - `Vault.add(name, key, note="", source="", device="", kind="account", game=None)`
  - `Vault.by_kind(kind) -> list`
  - `Vault.export_hak(entry_id, path, include_key=True)`（写 `version: 2` + `game`）
  - `Vault.import_hak(path) -> (entry, created)`

- [ ] **Step 1: 写失败测试** `win/tests/test_vault.py`

```python
import base64
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["APPDATA"] = tempfile.mkdtemp(prefix="hak-test-")

from app import dpapi
from app import vault

KEY = b"housamo-test-key-0123456789-abcdef"


class VaultFilesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="vault-")
        self.path = os.path.join(self.tmp, "vault.housamo.dat")

    def test_path_per_game(self):
        self.assertTrue(vault.default_vault_path("housamo").endswith("vault.housamo.dat"))
        self.assertTrue(vault.default_vault_path("liveahero").endswith("vault.liveahero.dat"))

    def test_kind_defaults_to_account(self):
        v = vault.Vault(self.path, game_id="housamo")
        entry, created = v.add(name="a", key=KEY)
        self.assertTrue(created)
        self.assertEqual(entry["kind"], "account")
        self.assertEqual(entry["game"], "housamo")
        self.assertEqual(v.by_kind("backup"), [])
        self.assertEqual(len(v.by_kind("account")), 1)

    def test_backup_section(self):
        v = vault.Vault(self.path, game_id="housamo")
        v.add(name="b1", key=KEY, kind="backup")
        self.assertEqual(len(v.by_kind("backup")), 1)
        self.assertEqual(len(v.by_kind("account")), 0)

    def test_same_key_allowed_in_other_game_file(self):
        a = vault.Vault(os.path.join(self.tmp, "vault.housamo.dat"), game_id="housamo")
        b = vault.Vault(os.path.join(self.tmp, "vault.liveahero.dat"), game_id="liveahero")
        a.add(name="a", key=KEY)
        _, created = b.add(name="b", key=KEY)
        self.assertTrue(created)

    def test_legacy_entries_get_kind(self):
        entry = {"id": "x", "name": "old", "note": "",
                 "key_b64": base64.b64encode(KEY).decode(),
                 "fingerprint": "f", "sha256": "0"}
        payload = {"version": 1, "entries": [entry]}
        with open(self.path, "wb") as fh:
            fh.write(dpapi.protect(json.dumps(payload).encode("utf-8")))
        v = vault.Vault(self.path, game_id="housamo")
        self.assertEqual(v.entries[0]["kind"], "account")
        self.assertEqual(v.entries[0]["game"], "housamo")

    def test_hak_v2_roundtrip(self):
        src = vault.Vault(self.path, game_id="housamo")
        entry, _ = src.add(name="travel", key=KEY)
        hak = os.path.join(self.tmp, "travel.hak")
        src.export_hak(entry["id"], hak)
        with open(hak, encoding="utf-8") as fh:
            payload = json.load(fh)
        self.assertEqual(payload["version"], 2)
        self.assertEqual(payload["game"], "housamo")

        dst = vault.Vault(os.path.join(self.tmp, "v2.dat"), game_id="housamo")
        _, created = dst.import_hak(hak)
        self.assertTrue(created)

    def test_hak_wrong_game_refused(self):
        src = vault.Vault(self.path, game_id="housamo")
        entry, _ = src.add(name="travel", key=KEY)
        hak = os.path.join(self.tmp, "travel.hak")
        src.export_hak(entry["id"], hak)
        other = vault.Vault(os.path.join(self.tmp, "la.dat"), game_id="liveahero")
        with self.assertRaises(ValueError):
            other.import_hak(hak)

    def test_legacy_hak_without_game_imports(self):
        hak = os.path.join(self.tmp, "old.hak")
        with open(hak, "w", encoding="utf-8") as fh:
            json.dump({"format": "housamo-authkey-backup", "version": 1,
                       "name": "old", "key_b64": base64.b64encode(KEY).decode()}, fh)
        v = vault.Vault(os.path.join(self.tmp, "la.dat"), game_id="liveahero")
        _, created = v.import_hak(hak)
        self.assertTrue(created)


class MigrateTest(unittest.TestCase):
    def test_migrates_legacy_vault(self):
        from app import config
        folder = config.app_dir()
        legacy = os.path.join(folder, "vault.dat")
        target = os.path.join(folder, "vault.housamo.dat")
        for path in (legacy, target):
            if os.path.exists(path):
                os.remove(path)
        with open(legacy, "wb") as fh:
            fh.write(b"old-bytes")
        self.assertTrue(vault.migrate_legacy_vault())
        self.assertFalse(os.path.exists(legacy))
        self.assertTrue(os.path.exists(target))
        self.assertFalse(vault.migrate_legacy_vault())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python win/tests/test_vault.py`
Expected: `TypeError: __init__() got an unexpected keyword argument 'game_id'`

- [ ] **Step 3: 改 `win/app/vault.py`**

文件头常量改为：
```python
VAULT_VERSION = 1
HAK_FORMAT = "housamo-authkey-backup"
HAK_VERSION = 2
LEGACY_NAME = "vault.dat"


def vault_path_for(game_id):
    from .config import app_dir
    folder = app_dir()
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "vault.%s.dat" % game_id)


def default_vault_path(game_id="housamo"):
    return vault_path_for(game_id)


def migrate_legacy_vault():
    """Rename the pre-1.2 single vault into the Housamo vault exactly once."""
    from .config import app_dir
    folder = app_dir()
    legacy = os.path.join(folder, LEGACY_NAME)
    target = os.path.join(folder, "vault.housamo.dat")
    if os.path.exists(legacy) and not os.path.exists(target):
        try:
            os.replace(legacy, target)
            return True
        except OSError:
            return False
    return False
```

```python
class Vault:
    def __init__(self, path=None, game_id="housamo"):
        self.game_id = game_id
        self.path = path or default_vault_path(game_id)
        self.entries = []
        self.load()

    def load(self):
        self.entries = []
        if not os.path.exists(self.path):
            return
        with open(self.path, "rb") as fh:
            raw = fh.read()
        if not raw:
            return
        try:
            payload = json.loads(dpapi.unprotect(raw).decode("utf-8"))
            self.entries = payload.get("entries", [])
        except Exception as exc:
            raise RuntimeError("账号库无法解密（文件可能被复制到了别的电脑）：%s" % exc)
        for entry in self.entries:
            entry.setdefault("kind", "account")
            entry.setdefault("game", self.game_id)

    def by_kind(self, kind):
        return [e for e in self.entries if e.get("kind", "account") == kind]

    def add(self, name, key, note="", source="", device="", kind="account", game=None):
        key = bytes(key)
        text = key.decode("utf-8", "replace")
        digest = hashlib.sha256(key).hexdigest()
        for entry in self.entries:
            if entry.get("sha256") == digest:
                return entry, False
        entry = {
            "id": uuid.uuid4().hex[:12],
            "name": name or "未命名账号",
            "note": note,
            "key_b64": base64.b64encode(key).decode("ascii"),
            "fingerprint": _fp(text),
            "sha256": digest,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "source": source,
            "device": device,
            "kind": kind if kind in ("account", "backup") else "account",
            "game": game or self.game_id,
        }
        self.entries.insert(0, entry)
        self.save()
        return entry, True
```

`export_hak` 的 payload 加两行：`"version": HAK_VERSION,` 与 `"game": entry.get("game") or self.game_id,`、`"kind": entry.get("kind", "account"),`。
`import_hak` 改为：
```python
    def import_hak(self, path):
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        if payload.get("format") != HAK_FORMAT:
            raise ValueError("不是有效的 .hak 备份文件")
        if not payload.get("key_b64"):
            raise ValueError("这个 .hak 文件里没有 key（可能是只读导出）")
        owner = payload.get("game") or ""
        if owner and owner != self.game_id:
            from .game import game_by_id
            raise ValueError("这个备份属于「%s」，请先切换到该游戏再导入。"
                             % game_by_id(owner).label)
        key = base64.b64decode(payload["key_b64"])
        entry, created = self.add(
            name=payload.get("name") or "导入的账号",
            key=key,
            note=payload.get("note", ""),
            source=payload.get("source", "hak"),
            kind=payload.get("kind", "account"),
            game=owner or self.game_id,
        )
        return entry, created
```

- [ ] **Step 4: 跑测试**

Run: `python win/tests/test_vault.py`
Expected: `OK`（8 个用例）
Run: `python -m py_compile win/app/vault.py`

---

### Task 3: 设置键 + 数据目录隔离 + 忽略表

**Files:**
- Modify: `win/app/config.py`
- Test: `win/tests/test_config.py`

**Interfaces:**
- Consumes: `app.game.GAMES`（校验 `active_game`）
- Produces:
  - `DEFAULTS` 新键：`active_game="housamo"`、`update_source="auto"`、`reconcile_ignored={}`、`last_update_check=0`
  - `app_dir()` 支持环境变量 `HOUSAMO_DATA_DIR`（测试隔离）
  - `ignore_reconcile(settings, game_id, digest)`、`is_reconcile_ignored(settings, game_id, digest) -> bool`

- [ ] **Step 1: 写失败测试** `win/tests/test_config.py`

```python
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["HOUSAMO_DATA_DIR"] = tempfile.mkdtemp(prefix="hak-cfg-")

from app import config


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "settings.json")

    def test_new_defaults(self):
        s = config.Settings(self.path)
        self.assertEqual(s.get("active_game"), "housamo")
        self.assertEqual(s.get("update_source"), "auto")
        self.assertEqual(s.get("reconcile_ignored"), {})
        self.assertEqual(s.get("last_update_check"), 0)

    def test_bad_active_game_normalised(self):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write('{"active_game": "wildcard"}')
        self.assertEqual(config.Settings(self.path).get("active_game"), "housamo")

    def test_bad_update_source_normalised(self):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write('{"update_source": "ftp"}')
        self.assertEqual(config.Settings(self.path).get("update_source"), "auto")

    def test_ignore_table(self):
        s = config.Settings(self.path)
        self.assertFalse(config.is_reconcile_ignored(s, "housamo", "abc"))
        config.ignore_reconcile(s, "housamo", "abc")
        config.ignore_reconcile(s, "housamo", "abc")
        self.assertTrue(config.is_reconcile_ignored(s, "housamo", "abc"))
        self.assertEqual(s.get("reconcile_ignored")["housamo"], ["abc"])

    def test_data_dir_override(self):
        self.assertEqual(config.app_dir(), os.environ["HOUSAMO_DATA_DIR"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python win/tests/test_config.py`
Expected: `KeyError/AssertionError`（`active_game` 为 None、`app_dir` 不等于覆盖目录）

- [ ] **Step 3: 实现**

```python
DEFAULTS = {
    "save_dir": "",
    "bg_image": "",
    "bg_blur": 12,
    "bg_alpha": 100,
    "active_game": "housamo",
    "update_source": "auto",
    "reconcile_ignored": {},
    "last_update_check": 0,
}


def app_dir():
    override = os.environ.get("HOUSAMO_DATA_DIR")
    if override:
        os.makedirs(override, exist_ok=True)
        return override
    base = _base_dir()
    folder = os.path.join(base, APP_FOLDER)
    os.makedirs(folder, exist_ok=True)
    return folder
```
`Settings.load` 的循环里，`isinstance(default, int)` 分支要保持 `bool` 排除；在 `elif isinstance(default, str)` 后加：
```python
            elif isinstance(default, dict):
                value = value if isinstance(value, dict) else dict(default)
```
循环之后加规范化：
```python
        from .game import GAMES
        if self.data.get("active_game") not in [g.id for g in GAMES]:
            self.data["active_game"] = DEFAULTS["active_game"]
        if self.data.get("update_source") not in ("auto", "github", "mirror"):
            self.data["update_source"] = DEFAULTS["update_source"]
```
文件末尾加：
```python
def is_reconcile_ignored(settings, game_id, digest):
    table = settings.get("reconcile_ignored") or {}
    return digest in (table.get(game_id) or [])


def ignore_reconcile(settings, game_id, digest):
    table = dict(settings.get("reconcile_ignored") or {})
    items = list(table.get(game_id) or [])
    if digest not in items:
        items.append(digest)
    table[game_id] = items
    settings.set("reconcile_ignored", table)
    return table
```
`win/main.py` 的 `--selftest` 分支开头加数据目录隔离：
```python
    if "--selftest" in sys.argv:
        import tempfile
        os.environ.setdefault("HOUSAMO_DATA_DIR", tempfile.mkdtemp(prefix="hak-selftest-"))
        os.environ.setdefault("HOUSAMO_NO_ADB", "1")
```

- [ ] **Step 4: 跑测试**

Run: `python win/tests/test_config.py` → `OK`
Run: `python win/main.py --selftest` → `SELFTEST OK`

---

### Task 4: `Segmented` 切换器

**Files:**
- Modify: `win/app/widgets.py`（文件末尾 `SectionTitle` 之前插入）
- Test: `win/tests/test_widgets.py`

**Interfaces:**
- Produces: `Segmented(app, master, options, active=None, command=None, pad_x=12)`
  - `options: list[tuple[str, str]]`（id, 文案）
  - `.active` 属性；`.select(key)`；`.set_active(key)`（不触发回调）；`.set_text(key, text)`

- [ ] **Step 1: 写失败测试** `win/tests/test_widgets.py`

```python
import os
import sys
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk

from app import theme
from app.widgets import Segmented


class SegmentedTest(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        theme.set_ui_scale(1.0)
        self.app = types.SimpleNamespace(pal=theme.PALETTE)
        self.hits = []

    def tearDown(self):
        self.root.destroy()

    def test_switch_and_callback(self):
        seg = Segmented(self.app, self.root, [("a", "A"), ("b", "B")],
                        active="a", command=self.hits.append)
        self.assertEqual(seg.active, "a")
        seg.select("b")
        self.assertEqual(seg.active, "b")
        self.assertEqual(self.hits, ["b"])
        seg.select("b")
        self.assertEqual(self.hits, ["b"])  # 重复点击不回调

    def test_set_active_silent(self):
        seg = Segmented(self.app, self.root, [("a", "A"), ("b", "B")], active="a")
        seg.set_active("b")
        self.assertEqual(seg.active, "b")

    def test_set_text(self):
        seg = Segmented(self.app, self.root, [("a", "A")])
        seg.set_text("a", "hello")
        self.assertEqual(seg.labels["a"].cget("text"), "hello")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python win/tests/test_widgets.py`
Expected: `ImportError: cannot import name 'Segmented'`

- [ ] **Step 3: 实现 `Segmented`**

```python
class Segmented(tk.Frame):
    """Pill switcher: 东京放课后 / LiveAHero，或 账号 / 备份。"""

    def __init__(self, app, master, options, active=None, command=None, pad_x=12):
        tk.Frame.__init__(self, master, bg=app.pal["card_soft"], bd=0, highlightthickness=0)
        self.app = app
        self.pal = app.pal
        self.options = list(options)
        self.active = active or (self.options[0][0] if self.options else None)
        self.command = command
        self.labels = {}
        for key, text in self.options:
            lab = tk.Label(self, text=text, font=theme_mod.font(9), bd=0,
                           highlightthickness=0, cursor="hand2",
                           padx=theme_mod.px(pad_x), pady=theme_mod.px(4))
            lab.pack(side="left", padx=theme_mod.px(2), pady=theme_mod.px(2))
            lab.bind("<Button-1>", lambda _e, k=key: self.select(k))
            self.labels[key] = lab
        self._paint()

    def _paint(self):
        for key, lab in self.labels.items():
            active = key == self.active
            lab.configure(bg=self.pal["accent"] if active else self.pal["card_soft"],
                          fg=self.pal["on_accent"] if active else self.pal["text_muted"])

    def set_active(self, key):
        self.active = key
        self._paint()

    def set_text(self, key, text):
        if key in self.labels:
            self.labels[key].configure(text=text)

    def select(self, key):
        if key == self.active:
            return
        self.active = key
        self._paint()
        if self.command:
            self.command(key)
```

- [ ] **Step 4: 跑测试**

Run: `python win/tests/test_widgets.py` → `OK`
Run: `python -m py_compile win/app/widgets.py`

---

### Task 5: 任务页游戏切换

**Files:**
- Modify: `win/app/ui.py`:21-22（import）、:48-49、:199-232、:546-561、:941-1006
- Test: `win/tests/test_ui_games.py`

**Interfaces:**
- Consumes: `game.GAMES / game_by_id`、`Segmented`、`vault.Vault(game_id=...)`
- Produces:
  - `App.active_game: Game`
  - `App.vaults: dict[str, Vault]`、`App.vault: Vault`（当前游戏）
  - `App.switch_game(game_id)`
  - `App._update_device_hint()`

- [ ] **Step 1: 写失败测试** `win/tests/test_ui_games.py`

```python
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["HOUSAMO_DATA_DIR"] = tempfile.mkdtemp(prefix="hak-ui-")
os.environ["HOUSAMO_NO_ADB"] = "1"

import tkinter as tk

from app import theme
from app.ui import App


class SwitchGameTest(unittest.TestCase):
    def setUp(self):
        theme.set_ui_scale(1.0)
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = App(self.root)
        self.root.update()

    def tearDown(self):
        self.root.destroy()

    def test_default_is_housamo(self):
        self.assertEqual(self.app.active_game.id, "housamo")
        self.assertTrue(self.app.vault.path.endswith("vault.housamo.dat"))

    def test_switch_to_liveahero(self):
        self.app.switch_game("liveahero")
        self.assertEqual(self.app.active_game.id, "liveahero")
        self.assertTrue(self.app.vault.path.endswith("vault.liveahero.dat"))
        self.assertEqual(self.app.settings.get("active_game"), "liveahero")
        self.assertIn("LiveAHero", self.app.btn_extract.text)

    def test_switch_back_keeps_same_instance(self):
        first = self.app.vault
        self.app.switch_game("liveahero")
        self.app.switch_game("housamo")
        self.assertIs(self.app.vault, first)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python win/tests/test_ui_games.py`
Expected: `AttributeError: 'App' object has no attribute 'switch_game'`

- [ ] **Step 3: 实现**

1) import 行改成：
```python
from .widgets import (MiniSlider, NavButton, PillButton, RoundCard, SectionTitle,
                      Segmented, chip, entry, label)
```
2) `__init__`（`self.vault = None` 附近）：
```python
        self.active_game = game.game_by_id(self.settings.get("active_game") or "housamo")
        self.vault = None
        self.vaults = {}
```
3) `_init_backend` 的账号库加载改成（替换原 `self.vault = vault_mod.Vault()` 三行）：
```python
        vault_mod.migrate_legacy_vault()
        for g in game.GAMES:
            try:
                self.vaults[g.id] = vault_mod.Vault(game_id=g.id)
            except Exception as exc:
                self.log("错误", "账号库加载失败（%s）：%s" % (g.label, exc))
        self.vault = self.vaults.get(self.active_game.id)
        self.refresh_vault()
```
4) `_build_task_page`：`right = tk.Frame(head, bg=pal["card"])` 之后、`adb_chip` 之前插入
```python
        self.game_seg = Segmented(self, right, [(g.id, g.label) for g in game.GAMES],
                                  active=self.active_game.id, command=self.switch_game)
        self.game_seg.pack(side="left", padx=(theme.px(0), theme.px(10)))
```
并把 `tree_box` 存起来：`self.tree_box = tree_box`；设备提示文案改为通过方法设置。
5) 新方法（放在 `refresh_devices` 之前）：
```python
    def switch_game(self, game_id):
        g = game.game_by_id(game_id)
        if g.id == self.active_game.id and self.vault is not None:
            return
        self.active_game = g
        self.settings.set("active_game", g.id)
        vault = self.vaults.get(g.id)
        if vault is None:
            try:
                vault = vault_mod.Vault(game_id=g.id)
                self.vaults[g.id] = vault
            except Exception as exc:
                self.log("错误", "账号库加载失败（%s）：%s" % (g.label, exc))
                return
        self.vault = vault
        if getattr(self, "game_seg", None):
            self.game_seg.set_active(g.id)
        self.btn_extract.set_text("提取 %s 的 key" % g.label)
        self.btn_import.set_text("导入到 %s" % g.label)
        self._update_device_hint()
        self.refresh_vault()
        self._refresh_data_card()
        self.log("设备", "已切换到 %s" % g.label)

    def _update_device_hint(self):
        try:
            online = [d for d in self.devices if d.online]
            if not self.devices:
                self.device_hint.configure(text="没有发现设备")
            else:
                self.device_hint.configure(
                    text="已发现 %d 台设备，选中一台后点下面「提取 %s 的 key」"
                         % (len(self.devices), self.active_game.label))
        except Exception:
            pass
```
6) 初始按钮文案：`_build_task_page` 里把两处文案改成 `"提取 %s 的 key" % self.active_game.label` 与 `"导入到 %s" % self.active_game.label`。
7) `_devices_done` 里把两处 `device_hint.configure(...)` 换成 `self._update_device_hint()`；`device_empty` 的大标题与副文案保持原文（游戏名已经出现在下方 hint 与切换器里，不再重复）。
8) `do_extract` 里提取成功后把章节提示带上游戏：
```python
        self.log("完成", "已保存 %s 账号，指纹 %s" % (self.active_game.label, entry.get("fingerprint")))
```
9) 没装这个游戏时禁用提取按钮（异步检查，放 `_update_device_hint` 之后）：
```python
    def _check_game_installed(self):
        online = [d for d in self.devices if d.online]
        if not self.adb or not online:
            return
        g = self.active_game
        serial = online[0].serial

        def runner():
            ok = game.game_installed(self.adb, serial, g)
            self.root.after(0, self._installed_done, g.id, ok)

        threading.Thread(target=runner, daemon=True).start()

    def _installed_done(self, game_id, ok):
        if game_id != self.active_game.id:
            return
        self.btn_extract.set_enabled(bool(ok))
        if not ok:
            self.log("设备", "这台设备上没有安装 %s" % self.active_game.label)
```
在 `_devices_done` 末尾与 `switch_game` 的 `refresh_vault()` 之后各加一行 `self._check_game_installed()`。

- [ ] **Step 4: 跑测试与自检**

Run: `python win/tests/test_ui_games.py` → `OK`
Run: `python -m py_compile win/app/ui.py`
Run: `python win/main.py --selftest` → `SELFTEST OK`

---

### Task 6: 账号库分段（账号 / 备份）+ 导出路径按游戏分层

**Files:**
- Modify: `win/app/ui.py`:273-323（`_build_vault_page`）、:326-399（设置页数据行）、:601-614（`export_to_dir`）、:710-719（`_refresh_data_card`）、:896-929（`refresh_vault`）、:971-996（`do_import`）、:1009-1026（重命名/备注）
- Test: `win/tests/test_ui_vault.py`

**Interfaces:**
- Consumes: `Vault.by_kind`、`Vault.add(kind="backup")`
- Produces:
  - `App.vault_kind: str`（"account" | "backup"）
  - `App._update_vault_actions()`
  - `App.export_to_dir(name, key)` 写到 `<save_dir>/<游戏 label>/<名字>/AuthKey.txt`

- [ ] **Step 1: 写失败测试** `win/tests/test_ui_vault.py`

```python
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["HOUSAMO_DATA_DIR"] = tempfile.mkdtemp(prefix="hak-uiv-")
os.environ["HOUSAMO_NO_ADB"] = "1"

import tkinter as tk

from app import theme
from app.ui import App

KEY_A = b"backup-key-0123456789-aaaa"
KEY_B = b"account-key-0123456789-bbbb"


class VaultSectionsTest(unittest.TestCase):
    def setUp(self):
        theme.set_ui_scale(1.0)
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = App(self.root)
        self.root.update()

    def tearDown(self):
        self.root.destroy()

    def _add(self, key, kind):
        return self.app.vault.add(name="n", key=key, kind=kind)[0]

    def test_account_rows_only(self):
        self._add(KEY_B, "account")
        self._add(KEY_A, "backup")
        self.app.vault_kind = "account"
        self.app.refresh_vault()
        rows = self.app.vault_tree.get_children()
        self.assertEqual(len(rows), 1)

    def test_backup_rows(self):
        self._add(KEY_B, "account")
        self._add(KEY_A, "backup")
        self.app.vault_kind = "backup"
        self.app.refresh_vault()
        self.assertEqual(len(self.app.vault_tree.get_children()), 1)
        self.assertIn("备份", self.app.count_chip.cget("text"))

    def test_data_card_shows_current_game(self):
        self.app._refresh_data_card()
        self.assertIn("vault.housamo.dat", self.app.data_rows["vault"].cget("text"))
        self.app.switch_game("liveahero")
        self.assertIn("vault.liveahero.dat", self.app.data_rows["vault"].cget("text"))

    def test_export_goes_under_game_folder(self):
        self.app.save_dir = tempfile.mkdtemp()
        out = self.app.export_to_dir("acc", KEY_B)
        self.assertIsNotNone(out)
        rel = os.path.relpath(out, self.app.save_dir).replace("\\", "/")
        self.assertEqual(rel, "东京放课后/acc/AuthKey.txt")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python win/tests/test_ui_vault.py`
Expected: `AttributeError: 'App' object has no attribute 'vault_kind'`（第一个用例）

- [ ] **Step 3: 实现**

1) `__init__` 加 `self.vault_kind = "account"`。
2) `_build_vault_page` 的 `right` 里，`count_chip` 之前插：
```python
        self.kind_seg = Segmented(self, right, [("account", "账号"), ("backup", "备份")],
                                   active="account", command=self.switch_vault_kind)
        self.kind_seg.pack(side="left", padx=(theme.px(0), theme.px(10)))
```
3) toolbar 的按钮保存引用，便于禁用：
```python
        self.btn_rename = PillButton(...)
        self.btn_rename.pack(...)
        self.btn_note = PillButton(...)
        self.btn_note.pack(...)
```
（另外五个按钮照旧实例化，不保存引用。）
4) 新增方法：
```python
    def switch_vault_kind(self, kind):
        self.vault_kind = kind
        self.kind_seg.set_active(kind)
        self.refresh_vault()

    def _update_vault_actions(self):
        entry = self.selected_entry()
        backup = bool(entry and entry.get("kind") == "backup")
        try:
            self.btn_rename.set_enabled(not backup)
            self.btn_note.set_enabled(not backup)
        except Exception:
            pass
```
5) `refresh_vault` 取数改成：
```python
        entries = self.vault.by_kind(self.vault_kind)
        if keyword:
            entries = [e for e in entries if ...]  # 保留原过滤体
        ...
        label_text = "账号" if self.vault_kind == "account" else "备份"
        total = len(self.vault.by_kind(self.vault_kind))
        all_total = len(self.vault.entries)
        if keyword:
            self.count_chip.configure(text="%d / %d 个%s" % (len(entries), total, label_text), ...)
        else:
            self.count_chip.configure(text="%d 个%s" % (total, label_text), ...)
        self._update_vault_actions()
```
并在 `_build_vault_page` 末尾加 `self.vault_tree.bind("<<TreeviewSelect>>", lambda e: self._update_vault_actions())`，同时让 count_chip 的提示能看出两段总量：`"%d 个%s · 共 %d" % (total, label_text, all_total)` 用于无关键字时。
6) `export_to_dir`：
```python
    def export_to_dir(self, name, key):
        """Write <保存文件夹>/<游戏>/<名字>/AuthKey.txt; returns path or None."""
        if not self.save_dir:
            return None
        folder = os.path.join(self.save_dir, self._safe_name(self.active_game.label),
                              self._safe_name(name))
        ...
```
7) `do_import` 里 `_require()` 之后拒绝备份→账号？不需要：备份也可以导入。只把备份条目的名称提示写清楚：
```python
        if entry.get("kind") == "backup":
            self.log("导入", "正在还原备份：%s" % entry.get("name"))
```
8) `rename_entry` / `edit_note` 开头加：
```python
        if entry.get("kind") == "backup":
            messagebox.showinfo(APP_TITLE, "备份条目不能改名，需要的话导入回游戏后再保存为账号。")
            return
```
9) 设置页数据行补「当前游戏库 / 保存位置」：
```python
# _build_settings_page  第 380 行的循环元组换成
        for key, title in (("data_dir", "应用数据目录"), ("vault", "当前游戏库"),
                           ("save_dir", "保存位置"), ("adb", "adb 组件")):
# _refresh_data_card  替换 vault 那一行
        g = self.active_game
        accounts = len(self.vault.by_kind("account")) if self.vault else 0
        backups = len(self.vault.by_kind("backup")) if self.vault else 0
        rows["vault"].configure(text="vault.%s.dat · %d 个账号 · %d 个备份"
                                     % (g.id, accounts, backups))
        rows["save_dir"].configure(
            text=os.path.join(self.save_dir, g.label) if self.save_dir else "未选择")
```
`switch_game` 已经会调用 `self._refresh_data_card()`（Task 5），`_show_page("settings")` 也已有调用，不用再加。

- [ ] **Step 4: 跑测试与自检**

Run: `python win/tests/test_ui_vault.py` → `OK`
Run: `python -m py_compile win/app/ui.py` → 无输出

---

### Task 7: 启动核对提示条

**Files:**
- Create: `win/app/reconcile.py`
- Modify: `win/app/ui.py`:199-270（提示条 UI）、:833-853（`_devices_done` 末尾）、:971-996
- Test: `win/tests/test_reconcile.py`

**Interfaces:**
- Consumes: `game.clean_key / game.fingerprint`、`config.is_reconcile_ignored / ignore_reconcile`
- Produces:
  - `digest_of(key_bytes) -> str`
  - `is_known(vault, digest) -> bool`
  - `should_prompt(vault, key_bytes, ignored) -> (bool, digest)`
  - `App.refresh_reconcile()`、`App.save_reconcile_entry()`、`App.dismiss_reconcile()`

- [ ] **Step 1: 写失败测试** `win/tests/test_reconcile.py`

```python
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import reconcile


class FakeVault:
    def __init__(self, digests):
        self.entries = [{"sha256": d} for d in digests]


class ReconcileTest(unittest.TestCase):
    def test_digest_normalises_whitespace(self):
        self.assertEqual(reconcile.digest_of(b"abc\n"), reconcile.digest_of(b"  abc  "))
        self.assertEqual(len(reconcile.digest_of(b"abc")), 64)

    def test_unknown_key_prompts(self):
        flag, digest = reconcile.should_prompt(FakeVault(["00"]), b"abc", [])
        self.assertTrue(flag)

    def test_known_key_silent(self):
        digest = reconcile.digest_of(b"abc")
        flag, _ = reconcile.should_prompt(FakeVault([digest]), b"abc", [])
        self.assertFalse(flag)

    def test_ignored_key_silent(self):
        digest = reconcile.digest_of(b"abc")
        flag, _ = reconcile.should_prompt(FakeVault([]), b"abc", [digest])
        self.assertFalse(flag)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python win/tests/test_reconcile.py`
Expected: `ModuleNotFoundError: No module named 'app.reconcile'`

- [ ] **Step 3: 实现 `win/app/reconcile.py`**

```python
# -*- coding: utf-8 -*-
"""Startup reconcile: is the key the device is running already in our vault?"""
from __future__ import annotations

import hashlib

from . import game as game_mod


def digest_of(key_bytes):
    return hashlib.sha256(game_mod.clean_key(key_bytes)).hexdigest()


def is_known(vault, digest):
    if vault is None:
        return True
    return any(e.get("sha256") == digest for e in vault.entries)


def should_prompt(vault, key_bytes, ignored):
    digest = digest_of(key_bytes)
    if digest in set(ignored or []):
        return False, digest
    return (not is_known(vault, digest)), digest
```

- [ ] **Step 4: 加提示条 UI 与方法**

`_build_task_page` 里 `tree_box` 创建之前插入：
```python
        self.reconcile_bar = tk.Frame(body, bg=pal["warn_soft"])
        inner = tk.Frame(self.reconcile_bar, bg=pal["warn_soft"])
        inner.pack(fill="x", padx=theme.px(14), pady=theme.px(10))
        self.reconcile_text = label(inner, self, "", size=9, color="warn", bg="warn_soft")
        self.reconcile_text.pack(side="left")
        PillButton(self, inner, "不用管", command=self.dismiss_reconcile, kind="ghost",
                   width=72, height=28, bg="warn_soft").pack(side="right")
        PillButton(self, inner, "存到账号库", command=self.save_reconcile_entry, kind="primary",
                   width=104, height=28).pack(side="right", padx=(theme.px(0), theme.px(8)))
```
新增方法（放 `do_extract` 之前）：
```python
    def refresh_reconcile(self):
        try:
            self.reconcile_bar.pack_forget()
        except Exception:
            pass
        self._reconcile_key = None
        if not self.adb:
            return
        online = [d for d in self.devices if d.online]
        if len(online) != 1:
            return
        g = self.active_game
        serial = online[0].serial
        token = getattr(self, "_reconcile_token", 0) + 1
        self._reconcile_token = token

        def worker():
            try:
                key, _source = game.extract(self.adb, serial, g)
            except Exception:
                return None
            return key

        def done(key):
            if key is None or token != self._reconcile_token:
                return
            ignored = (self.settings.get("reconcile_ignored") or {}).get(g.id, [])
            flag, digest = reconcile.should_prompt(self.vault, key, ignored)
            if not flag:
                return
            self._reconcile_key = key
            self._reconcile_digest = digest
            self._reconcile_serial = serial
            self.reconcile_text.configure(
                text="%s 里正在用的 key（%s）不在账号库里，要不要存一份？"
                     % (g.label, game.fingerprint(key)))
            self.reconcile_bar.pack(fill="x", pady=(theme.px(12), theme.px(0)),
                                    before=self.tree_box)
            self.log("设备", "发现账号库里没有的 key：%s" % game.fingerprint(key))

        def runner():
            result = worker()
            self.root.after(0, done, result)

        threading.Thread(target=runner, daemon=True).start()

    def save_reconcile_entry(self):
        key = getattr(self, "_reconcile_key", None)
        if not key:
            self.reconcile_bar.pack_forget()
            return
        name = "游戏内快照 %s" % time.strftime("%Y-%m-%d %H:%M")
        entry, created = self.vault.add(
            name=name, key=key, note="启动核对时发现", source=self._reconcile_serial,
            device=self._reconcile_serial, kind="account")
        self.vault_kind = "account"
        if getattr(self, "kind_seg", None):
            self.kind_seg.set_active("account")
        self.refresh_vault()
        self.reconcile_bar.pack_forget()
        self._reconcile_key = None
        self.log("完成", ("已存为 %s" if created else "账号库里已经有 %s") % entry.get("name"))

    def dismiss_reconcile(self):
        digest = getattr(self, "_reconcile_digest", "")
        if digest:
            config.ignore_reconcile(self.settings, self.active_game.id, digest)
        self.reconcile_bar.pack_forget()
        self._reconcile_key = None
        self.log("设备", "已忽略这次核对（以后不再提示这个 key）")
```
`_devices_done` 末尾加 `self.refresh_reconcile()`；`switch_game` 里 `refresh_vault()` 后也调用 `self.refresh_reconcile()`。
`__init__` 需要引用 `reconcile` 模块：`from . import reconcile`。

- [ ] **Step 5: 跑测试与自检**

Run: `python win/tests/test_reconcile.py` → `OK`
Run: `python win/main.py --selftest` → `SELFTEST OK`

---

### Task 8: `updater.py`（检查 / 下载 / 校验 / 副本替换 / 状态机）

**Files:**
- Create: `win/app/updater.py`
- Test: `win/tests/test_updater.py`

**Interfaces:**
- Consumes: `app.config.app_dir()`、stdlib `urllib.request / zipfile / hashlib / json / subprocess / ctypes`
- Produces:
  - `UP_API`、`ASSET_NAME = "AuthKeyManager-win64.zip"`、`MIRRORS`
  - `parse_version(tag) -> tuple[int, ...]`、`is_newer(remote_tag, local_version) -> bool`
  - `pick_asset(release) -> dict | None`（键：`name / url / digest`）
  - `fetch_latest(timeout=15) -> dict`（GitHub release JSON）
  - `update_dir()`、`download(zip_url, digest, log=None) -> str`
  - `state_path()`、`read_state()`、`write_state(**fields)`
  - `install_dir()`、`dir_writable(path) -> bool`
  - `stage_copy(install, stage, log=None) -> None`
  - `apply_update(zip_path, install, parent_pid=0, log=print) -> bool`
  - `append_log(line)`

- [ ] **Step 1: 写失败测试** `win/tests/test_updater.py`

```python
import hashlib
import os
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["HOUSAMO_DATA_DIR"] = tempfile.mkdtemp(prefix="hak-upd-")

from app import updater


class VersionTest(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(updater.parse_version("v1.2.10"), (1, 2, 10))
        self.assertEqual(updater.parse_version("1.2.0-beta"), (1, 2, 0))

    def test_newer(self):
        self.assertTrue(updater.is_newer("v1.2.0", "1.1.1"))
        self.assertFalse(updater.is_newer("v1.1.1", "1.1.1"))
        self.assertFalse(updater.is_newer("v1.0.9", "1.1.1"))

    def test_pick_asset_prefers_named_zip(self):
        release = {"assets": [
            {"name": "src.tar.gz", "browser_download_url": "https://x/src"},
            {"name": updater.ASSET_NAME, "browser_download_url": "https://x/z",
             "digest": "sha256:abc"}]}
        asset = updater.pick_asset(release)
        self.assertEqual(asset["url"], "https://x/z")

    def test_pick_asset_falls_back_to_any_zip(self):
        release = {"assets": [{"name": "foo.zip", "browser_download_url": "https://x/f"}]}
        self.assertEqual(updater.pick_asset(release)["name"], "foo.zip")

    def test_pick_asset_none(self):
        self.assertIsNone(updater.pick_asset({"assets": []}))


class ApplyTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="upd-")
        self.install = os.path.join(self.root, "install")
        os.makedirs(self.install)
        with open(os.path.join(self.install, "AuthKeyManager.exe"), "wb") as fh:
            fh.write(b"old")
        with open(os.path.join(self.install, "keep.txt"), "wb") as fh:
            fh.write(b"keep")

    def _zip(self, entries):
        path = os.path.join(self.root, "update.zip")
        with zipfile.ZipFile(path, "w") as zf:
            for name, data in entries.items():
                zf.writestr(name, data)
        return path

    def test_replace_and_clean(self):
        path = self._zip({"AuthKeyManager.exe": b"new", "sub/a.txt": "中文"})
        ok = updater.apply_update(path, self.install, 0, log=lambda *_: None)
        self.assertTrue(ok)
        with open(os.path.join(self.install, "AuthKeyManager.exe"), "rb") as fh:
            self.assertEqual(fh.read(), b"new")
        self.assertTrue(os.path.exists(os.path.join(self.install, "sub", "a.txt")))
        self.assertTrue(os.path.exists(os.path.join(self.install, "keep.txt")))
        self.assertEqual(updater.read_state()["stage"], "done")

    def test_strip_single_top_folder(self):
        path = self._zip({"AuthKeyManager/AuthKeyManager.exe": b"new"})
        self.assertTrue(updater.apply_update(path, self.install, 0, log=lambda *_: None))
        with open(os.path.join(self.install, "AuthKeyManager.exe"), "rb") as fh:
            self.assertEqual(fh.read(), b"new")

    def test_corrupt_zip_fails_and_records(self):
        bad = os.path.join(self.root, "bad.zip")
        with open(bad, "wb") as fh:
            fh.write(b"not a zip")
        self.assertFalse(updater.apply_update(bad, self.install, 0, log=lambda *_: None))
        self.assertEqual(updater.read_state()["stage"], "failed")

    def test_traversal_refused(self):
        path = self._zip({"../evil.txt": b"x"})
        self.assertFalse(updater.apply_update(path, self.install, 0, log=lambda *_: None))
        self.assertFalse(os.path.exists(os.path.join(self.root, "evil.txt")))

    def test_dir_writable(self):
        self.assertTrue(updater.dir_writable(self.install))

    def test_download_verifies_sha256(self):
        src = self._zip({"AuthKeyManager.exe": b"new"})
        with open(src, "rb") as fh:
            digest = "sha256:" + hashlib.sha256(fh.read()).hexdigest()
        url = "file:///" + src.replace("\\", "/")
        out = updater.download(url, digest, log=lambda *_: None)
        self.assertTrue(os.path.exists(out))
        self.assertGreater(os.path.getsize(out), 0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python win/tests/test_updater.py`
Expected: `ModuleNotFoundError: No module named 'app.updater'`

- [ ] **Step 3: 写 `win/app/updater.py`**

```python
# -*- coding: utf-8 -*-
"""In-app updater: check GitHub, download the full zip, replace the install tree.

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

UP_API = "https://api.github.com/repos/fenghuo6183/HousamoAuthKeyManager/releases/latest"
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


def fetch_latest(timeout=15):
    request = urllib.request.Request(UP_API, headers={"User-Agent": _UA,
                                                      "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


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
            subprocess.Popen([exe], cwd=install)
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
```

- [ ] **Step 4: 跑测试**

Run: `python win/tests/test_updater.py`
Expected: `OK`（11 个用例）

---

### Task 9: 设置页更新卡 + 启动检查 + `--apply-update` + 单实例

**Files:**
- Modify: `win/main.py`（单实例、`--apply-update`）
- Modify: `win/app/ui.py`:326-399（设置页加卡）、:546-561（启动后检查）、新方法
- Test: `win/tests/test_ui_update.py`

**Interfaces:**
- Consumes: `updater` 全部、`Segmented`
- Produces:
  - `App.check_update(manual=False)`、`App.do_update()`、`App._apply_update_state()`
  - `main._single_instance() -> bool`

- [ ] **Step 1: 写失败测试** `win/tests/test_ui_update.py`

```python
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["HOUSAMO_DATA_DIR"] = tempfile.mkdtemp(prefix="hak-updui-")
os.environ["HOUSAMO_NO_ADB"] = "1"

import tkinter as tk

from app import theme, updater
from app.ui import App


class UpdateCardTest(unittest.TestCase):
    def setUp(self):
        theme.set_ui_scale(1.0)
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = App(self.root)
        self.root.update()

    def tearDown(self):
        self.root.destroy()

    def test_update_card_exists(self):
        self.assertIsNotNone(self.app.btn_check_update)
        self.assertIn(theme.APP_VERSION, self.app.update_version_label.cget("text"))

    def test_check_update_shows_new_version(self):
        release = {"tag_name": "v9.9.9", "html_url": "https://example/r",
                   "assets": [{"name": updater.ASSET_NAME,
                               "browser_download_url": "https://example/z"}]}
        with mock.patch.object(updater, "fetch_latest", return_value=release):
            self.app.check_update(manual=False)
            for _ in range(100):
                self.root.update()
                if self.app.update_asset is not None:
                    break
                time.sleep(0.02)
        self.assertIsNotNone(self.app.update_asset)
        self.assertEqual(self.app.btn_install_update.winfo_manager(), "pack")

    def test_apply_update_state_banner(self):
        updater.write_state(stage="failed", error="磁盘满了")
        self.app._apply_update_state()
        self.root.update()
        self.assertIn("磁盘满了", self.app.update_status.cget("text"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python win/tests/test_ui_update.py`
Expected: `AttributeError: 'App' object has no attribute 'btn_check_update'`

- [ ] **Step 3: 实现 UI**

`_build_settings_page` 在 `data_card` 之前插第三张卡（并把 `pages["settings"]` 改成三张）：
```python
        update_card = RoundCard(self)
        ub = update_card.body
        SectionTitle.build(self, ub, "更新", "检查到新版本会自己下载，重启后生效").pack(fill="x")
        row = tk.Frame(ub, bg=pal["card"])
        row.pack(fill="x", pady=(theme.px(12), theme.px(0)))
        self.update_version_label = label(row, self, "当前版本 v" + theme.APP_VERSION,
                                          size=10, weight="bold")
        self.update_version_label.pack(side="left")
        self.update_source_seg = Segmented(
            self, row, [("auto", "自动"), ("github", "GitHub"), ("mirror", "镜像")],
            active=self.settings.get("update_source"), command=self._on_update_source)
        self.update_source_seg.pack(side="left", padx=(theme.px(16), theme.px(0)))
        self.btn_check_update = PillButton(self, row, "检查更新", command=lambda: self.check_update(True),
                                           kind="ghost", width=104, height=32)
        self.btn_check_update.pack(side="right")

        status_row = tk.Frame(ub, bg=pal["card"])
        status_row.pack(fill="x", pady=(theme.px(10), theme.px(0)))
        self.update_status = label(status_row, self, "启动时会自动检查一次", size=9,
                                   color="text_muted")
        self.update_status.pack(side="left")
        self.btn_install_update = PillButton(self, status_row, "立即更新", command=self.do_update,
                                             kind="primary", width=104, height=30)
        self.btn_install_update.pack_forget()
        self.btn_view_log = PillButton(self, status_row, "查看日志", command=self.open_update_log,
                                       kind="ghost", width=88, height=30)
        self.btn_view_log.pack_forget()

        self.pages["settings"] = [(card, max(theme.px(356), card.required_height())),
                                  (update_card, max(theme.px(150), update_card.required_height())),
                                  (data_card, None)]
```
新增方法（放在 `reset_appearance` 之后）：
```python
    def _on_update_source(self, value):
        self.settings.set("update_source", value)
        self.update_source_seg.set_active(value)
        self.log("更新", "更新源：%s" % {"auto": "自动", "github": "GitHub", "mirror": "镜像"}.get(value, value))

    def check_update(self, manual=False):
        self.update_asset = None
        self.update_release = None
        self.btn_install_update.pack_forget()
        self.btn_view_log.pack_forget()
        self.update_status.configure(text="正在检查…", fg=self.pal["text_muted"])

        def worker():
            try:
                release = updater.fetch_latest()
            except Exception as exc:
                return None, exc
            return release, None

        def done(result):
            release, error = result
            self.settings.set("last_update_check", int(time.time()))
            if error is not None:
                self.update_status.configure(text="检查失败：%s" % error, fg=self.pal["err"])
                if manual:
                    messagebox.showwarning(APP_TITLE, "检查更新失败：%s" % error)
                return
            tag = release.get("tag_name") or ""
            if not updater.is_newer(tag, theme.APP_VERSION):
                self.update_status.configure(text="已是最新版本（%s）" % tag,
                                             fg=self.pal["ok"])
                if manual:
                    messagebox.showinfo(APP_TITLE, "已是最新版本。")
                return
            asset = updater.pick_asset(release)
            if not asset:
                self.update_status.configure(text="发现 %s，但这个版本没有 Windows 包" % tag,
                                             fg=self.pal["warn"])
                return
            self.update_release = release
            self.update_asset = asset
            self.update_status.configure(text="发现新版本 %s" % tag, fg=self.pal["accent"])
            self.btn_install_update.pack(side="right")

        def runner():
            self.root.after(0, done, worker())

        threading.Thread(target=runner, daemon=True).start()

    def do_update(self):
        if not self.update_asset:
            return
        install = updater.install_dir()
        if not updater.dir_writable(install):
            messagebox.showwarning(APP_TITLE,
                                   "程序目录不可写（可能装在 Program Files），请手动下载更新包覆盖。")
            webbrowser.open("https://github.com/fenghuo6183/HousamoAuthKeyManager/releases/latest")
            return
        if not messagebox.askyesno(APP_TITLE,
                                   "将下载 %s 并在关闭本程序后替换安装目录，然后自动重启。\n继续吗？"
                                   % (self.update_release.get("tag_name") or "")):
            return
        self.btn_check_update.set_enabled(False)
        self.update_status.configure(text="正在下载…", fg=self.pal["text_muted"])

        def worker():
            zip_path = updater.download(self.update_asset["url"],
                                        self.update_asset.get("digest", ""),
                                        lambda m: self.log("更新", m))
            stage = updater.stage_copy(install, log=lambda m: self.log("更新", m))
            return zip_path, stage

        def done(result):
            zip_path, stage = result
            exe = os.path.join(stage, os.path.basename(sys.executable)
                               if getattr(sys, "frozen", False) else "AuthKeyManager.exe")
            if not os.path.isfile(exe):
                self.log("出错", "临时目录里没有可执行文件：%s" % exe)
                messagebox.showerror(APP_TITLE, "更新失败：临时目录里没有可执行文件。")
                return
            updater.write_state(stage="applying",
                                target_version=(self.update_release.get("tag_name") or ""),
                                zip=zip_path, install=install)
            subprocess.Popen([exe, "--apply-update", zip_path, install, str(os.getpid())],
                             cwd=stage, creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
            self.log("更新", "更新程序已启动，本程序即将退出")
            self.root.after(300, self.root.destroy)

        self._bg(worker, done)

    def _apply_update_state(self):
        state = updater.read_state()
        stage = state.get("stage")
        if stage == "failed":
            self.update_status.configure(text="上次更新失败：%s" % (state.get("error") or "未知原因"),
                                         fg=self.pal["err"])
            self.btn_view_log.pack(side="right")
        elif stage == "applying" and updater.is_newer(state.get("target_version", ""),
                                                      theme.APP_VERSION):
            self.update_status.configure(text="上次更新没有完成，可以再试一次", fg=self.pal["warn"])
            self.btn_view_log.pack(side="right")

    def open_update_log(self):
        path = updater.log_path()
        if not os.path.isfile(path):
            messagebox.showinfo(APP_TITLE, "还没有更新日志。")
            return
        try:
            os.startfile(path)
        except Exception as exc:
            self.log("错误", "打开日志失败：%s" % exc)
```
`__init__` 里 `self._init_backend()` 之后加：
```python
        self.update_asset = None
        self.update_release = None
        self._apply_update_state()
        self.root.after(3000, lambda: self.check_update(manual=False))
```
（`update_asset/update_release` 要在 `_build_settings_page` 之前就存在，挪到 `__init__` 顶部与 `self.vault = None` 一起。）
`ui.py` 顶部 import 增加 `import subprocess` 与 `from . import updater`。

- [ ] **Step 4: 改 `main.py`**

```python
def _single_instance():
    """Return False when another copy is already running (bring it forward)."""
    if sys.platform != "win32":
        return True
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW(None, False, "Global\\HousamoAuthKeyManager")
        if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            user32 = ctypes.windll.user32
            hwnd = user32.FindWindowW(None, theme.APP_NAME)
            if hwnd:
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                user32.SetForegroundWindow(hwnd)
            return False
    except Exception:
        pass
    return True


def _run_apply_update():
    index = sys.argv.index("--apply-update")
    zip_path = sys.argv[index + 1]
    install = sys.argv[index + 2]
    parent = int(sys.argv[index + 3]) if len(sys.argv) > index + 3 else 0
    from app import updater
    ok = updater.apply_update(zip_path, install, parent, log=updater.append_log)
    sys.exit(0 if ok else 1)
```
`main()` 开头：
```python
def main():
    _enable_dpi_awareness()
    if "--apply-update" in sys.argv:
        _run_apply_update()
        return
    if not _single_instance():
        return
    ...
```

- [ ] **Step 5: 跑测试与自检**

Run: `python win/tests/test_ui_update.py` → `OK`
Run: `python -m py_compile win/app/ui.py win/app/updater.py win/main.py`
Run: `python win/main.py --selftest` → `SELFTEST OK`

---

### Task 10: 版本号、README、打包与四档缩放复验

**Files:**
- Modify: `win/app/theme.py`（`APP_VERSION = "1.2.0"`）
- Modify: `README.md`、`win/build.bat`
- Verify: 全部测试 + `%TEMP%\sweep2.py`

- [ ] **Step 1: 版本与文档**

`theme.py`：`APP_VERSION = "1.2.0"`。
`README.md` 功能列表加：
```markdown
- 双游戏：东京放课后召唤师 / LiveAHero，账号库按游戏分开存放
- 导入前自动备份：备份单独分区，可随时还原
- 启动核对：游戏里正在用的 key 如果不在账号库，会提示存一份
- 自动更新：启动时检查新版本，下载后退出替换并自动重启
```
账号库路径说明改成 `%APPDATA%\HousamoAuthKeyManager\vault.housamo.dat`（LiveAHero 为 `vault.liveahero.dat`）。
更新日志顶部加 `**v1.2.0（Windows）**` 条目：双游戏、备份分区、启动核对、自动更新（整包替换 + 失败自修复 + 镜像回退）、单实例。

- [ ] **Step 2: 打包脚本**

`win/build.bat` 的 PyInstaller 行补隐藏导入（updater 用到 `ctypes / zipfile / urllib`，一般会被自动收，但 `app.updater` 必须显式声明）：
```bat
pyinstaller --noconfirm --clean --windowed --name AuthKeyManager ^
  --icon "..\docs\icon.png" ^
  --hidden-import PIL._tkinter_finder ^
  --hidden-import app.updater ^
  --add-data "assets\platform-tools;assets\platform-tools" ^
  --add-data "..\docs\icon.png;assets" ^
  main.py
```
保持纯 ASCII + CRLF。

- [ ] **Step 3: 全量验证**

```bash
python -m py_compile win/app/*.py win/main.py
python win/tests/test_game.py
python win/tests/test_vault.py
python win/tests/test_config.py
python win/tests/test_widgets.py
python win/tests/test_reconcile.py
python win/tests/test_updater.py
python win/tests/test_ui_games.py
python win/tests/test_ui_vault.py
python win/tests/test_ui_update.py
python win/main.py --selftest
```
Expected: 每个测试末行 `OK`，最后一行 `SELFTEST OK`。

四档缩放复验（沿用已有脚本，跑完看 `CLIPPED`）：
```bash
python %TEMP%\sweep2.py
```
Expected: `CLIPPED: 0`（1.00 / 1.25 / 1.50 / 2.00 四档）。若设置页因为多了更新卡而超高的，把 `pages["settings"]` 里更新卡的高度改成 `max(theme.px(150), update_card.required_height())` 的实际值（打印 `required_height()` 后填），不要改 `_relayout` 的削日志逻辑。

- [ ] **Step 4: 截图确认**

Run: `python %TEMP%\housamo_pw3.py`
Expected: `%TEMP%\housamo_shots\hidpi_*.png` 六张图，任务页能看到游戏切换器、账号页能看到「账号 / 备份」、设置页能看到更新卡，三页均无裁切。
