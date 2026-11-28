# -*- coding: utf-8 -*-
"""User settings for the Windows client (JSON next to the encrypted vault)."""

from __future__ import annotations

import json
import os
import shutil

APP_FOLDER = "HousamoAuthKeyManager"

# 常见模拟器的 adb 端口，按命中率排序；设置页可以改成自己的列表。
EMULATOR_PORTS = [16384, 7555, 5555, 62001, 62025, 21503, 5557, 5559,
                  5565, 16416, 16448, 58526, 7556, 62026]

DEFAULTS = {
    "save_dir": "",
    "bg_image": "",
    "bg_blur": 12,
    "bg_alpha": 100,
    # 0 = 纯色面板，100 = 面板完全带壁纸的色调（磨砂玻璃感）
    "glass": 25,
    "active_game": "housamo",
    "update_source": "auto",
    "auto_check_update": True,
    "auto_download_update": False,
    "reconcile_ignored": {},
    "last_update_check": 0,
    "backup_keep": "all",
    "import_history": {},
    "theme": "light",
    "capture_guard": False,
    "app_lock": {},
    # 前三次从游戏提取到 key 后的强提醒，读过几次记在这里
    "export_tip_shown": 0,
    # 设备连接：记住上次用的设备、只看模拟器、启动时自动扫描、自定义端口
    "preferred_serial": "",
    "only_emulators": False,
    "auto_connect": False,
    "emulator_ports": ",".join(str(p) for p in EMULATOR_PORTS),
    # 参考 MAA 的连接配置预设：auto / mumu / ld / nox / bst / custom
    "connect_profile": "auto",
    "adb_path": "",
    "auto_reconnect": True,
    "tray_icon": True,
    "close_to_tray": False,
    "minimize_to_tray": False,
    "low_mode": False,
    "hotkey": False,
    "auto_backup": False,
    "auto_backup_hours": 6,
    "last_backup_at": 0,
    "notify_balloon": True,
    "notify_webhook": False,
    "webhook_url": "",
    "notify_on_backup": True,
    "notify_on_update": True,
}

BG_BASENAME = "background"


def _base_dir():
    for key in ("APPDATA", "LOCALAPPDATA"):
        value = os.environ.get(key)
        if value:
            return value
    home = os.path.expanduser("~")
    if home and home != "~" and os.path.isdir(home):
        return home
    import tempfile
    return tempfile.gettempdir()


def app_dir():
    override = os.environ.get("HOUSAMO_DATA_DIR")
    if override:
        os.makedirs(override, exist_ok=True)
        return override
    base = _base_dir()
    folder = os.path.join(base, APP_FOLDER)
    os.makedirs(folder, exist_ok=True)
    return folder


def settings_path():
    return os.path.join(app_dir(), "settings.json")


class Settings:
    def __init__(self, path=None):
        self.path = path or settings_path()
        self.data = dict(DEFAULTS)
        self.load()

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except Exception:
            return
        if not isinstance(raw, dict):
            return
        for key, default in DEFAULTS.items():
            value = raw.get(key, default)
            if isinstance(default, bool):
                if not isinstance(value, bool):
                    value = default
            elif isinstance(default, int) and not isinstance(value, bool):
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    value = default
            elif isinstance(default, str):
                value = value if isinstance(value, str) else default
            elif isinstance(default, dict):
                value = value if isinstance(value, dict) else dict(default)
            self.data[key] = value
        from .game import GAMES
        if self.data.get("active_game") not in [g.id for g in GAMES]:
            self.data["active_game"] = DEFAULTS["active_game"]
        if self.data.get("update_source") not in ("auto", "github", "mirror"):
            self.data["update_source"] = DEFAULTS["update_source"]

    def save(self):
        try:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self.data, fh, ensure_ascii=False, indent=1)
            os.replace(tmp, self.path)
            return True
        except Exception:
            return False

    def get(self, key, default=None):
        return self.data.get(key, DEFAULTS.get(key, default))

    def set(self, key, value, save=True):
        self.data[key] = value
        if save:
            self.save()


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


def _suffix(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif", ".tif", ".tiff"):
        return ext
    return ".png"


def store_background(source):
    """Copy the picked image into the app folder so it survives moving the original."""
    if not os.path.isfile(source):
        raise FileNotFoundError(source)
    target_dir = app_dir()
    suffix = _suffix(source)
    target = os.path.join(target_dir, BG_BASENAME + suffix)
    clear_background(keep=target)
    shutil.copyfile(source, target)
    return target


def clear_background(keep=None):
    folder = app_dir()
    for name in os.listdir(folder):
        stem, ext = os.path.splitext(name)
        if stem != BG_BASENAME:
            continue
        candidate = os.path.join(folder, name)
        if keep and os.path.normcase(candidate) == os.path.normcase(keep):
            continue
        try:
            os.remove(candidate)
        except OSError:
            pass
