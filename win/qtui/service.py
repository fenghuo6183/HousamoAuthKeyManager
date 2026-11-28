# -*- coding: utf-8 -*-
"""Headless backend bridge for the Qt shell.

Everything here is plain Python: no Qt imports, so it can be unit-tested
without an event loop. The Qt layer wraps it in qtui.controller.
"""

from __future__ import annotations

import threading
import time

from app import adb as adb_mod
from app import config, game as game_mod, vault as vault_mod


class ServiceError(RuntimeError):
    pass


def parse_ports(text):
    """'16384, 7555;62001' -> [16384, 7555, 62001] (order kept, dupes dropped)."""
    ports = []
    for part in (text or "").replace(";", ",").replace(" ", ",").split(","):
        part = part.strip()
        if not part.isdigit():
            continue
        value = int(part)
        if 0 < value < 65536 and value not in ports:
            ports.append(value)
    return ports


def blank_vault(game_id):
    """An empty stand-in when the real vault cannot be decrypted."""
    holder = vault_mod.Vault.__new__(vault_mod.Vault)
    holder.game_id = game_id
    holder.path = vault_mod.vault_path_for(game_id)
    holder.entries = []
    return holder


class Service:
    """Owns adb, the active game and its vault; every method may block."""

    def __init__(self, settings=None):
        self.settings = settings if settings is not None else config.Settings()
        self.log = None                # callable(tag, message), set by the controller
        self.adb_error = ""
        self.adb = None
        try:
            self.adb = adb_mod.Adb(self.settings.get("adb_path") or None)
            self.adb.ensure_server()
        except Exception as exc:       # adb missing is a normal, reportable state
            self.adb_error = str(exc)
            self.adb = None

        self.game = game_mod.game_by_id(self.settings.get("active_game") or "housamo")
        self.vault_error = ""
        self.vault = self._open_vault(self.game.id)

        self.devices = []
        self.serial = ""

    # -- helpers -------------------------------------------------------
    def _note(self, tag, message):
        if self.log:
            self.log(tag, message)

    def _open_vault(self, game_id):
        path = vault_mod.vault_path_for(game_id)
        try:
            return vault_mod.Vault(path, game_id=game_id)
        except Exception as exc:
            self.vault_error = str(exc)
            return blank_vault(game_id)

    def _need_adb(self):
        if self.adb is None:
            raise ServiceError(self.adb_error or "adb 不可用")
        return self.adb

    def ports(self):
        return parse_ports(self.settings.get("emulator_ports")) or list(config.EMULATOR_PORTS)

    # -- games ---------------------------------------------------------
    def set_game(self, game_id):
        game = game_mod.game_by_id(game_id)
        if game.id == self.game.id:
            return self.game
        self.game = game
        self.settings.set("active_game", game.id)
        self.settings.save()
        self.vault_error = ""
        self.vault = self._open_vault(game.id)
        return game

    # -- devices -------------------------------------------------------
    def refresh_devices(self, deep=False):
        adb = self._need_adb()
        fresh = list(adb.devices())
        known = {dev.serial: dev for dev in self.devices}
        for dev in fresh:
            previous = known.get(dev.serial)
            if previous is not None and not deep:
                dev.root = previous.root
                dev.game_installed = previous.game_installed
                continue
            dev.root = "?"
            dev.game_installed = None
            if dev.online:
                try:
                    dev.root = "是" if adb.su_available(dev.serial) else "否"
                except Exception:
                    dev.root = "?"
        self.devices = fresh
        if self.serial and self.serial not in [d.serial for d in fresh if d.online]:
            self.serial = ""
        return fresh

    def pick(self, serial=None):
        wanted = serial or self.serial
        for dev in self.devices:
            if dev.serial == wanted and dev.online:
                return dev
        for dev in self.devices:
            if dev.online:
                return dev
        return None

    def connect(self, serial, timeout=8):
        adb = self._need_adb()
        serial = (serial or "").strip()
        if not serial:
            raise ServiceError("先选一台设备")
        online = [dev.serial for dev in self.devices if dev.online]
        if serial not in online:
            ok, text = adb.connect(serial, timeout=timeout)
            if not ok:
                raise ServiceError(text.strip() or ("连不上 %s" % serial))
            self.refresh_devices()
            online = [dev.serial for dev in self.devices if dev.online]
            if serial not in online:
                raise ServiceError("已发起连接，但设备还没有上线")
        self.serial = serial
        self.settings.set("preferred_serial", serial)
        self.settings.save()
        return serial

    def scan_ports(self):
        adb = self._need_adb()
        ports = self.ports()
        hits = []
        lock = threading.Lock()
        queue = list(ports)

        def probe():
            while True:
                with lock:
                    if not queue:
                        return
                    port = queue.pop(0)
                try:
                    ok, _text = adb.connect("127.0.0.1:%d" % port)
                except Exception:
                    ok = False
                if ok:
                    with lock:
                        hits.append(port)

        threads = [threading.Thread(target=probe, daemon=True)
                   for _ in range(max(1, min(6, len(ports))))]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        return sorted(hits)

    # -- actions -------------------------------------------------------
    def backup(self, serial=None, name=None):
        dev = self.pick(serial)
        if dev is None:
            raise ServiceError("现在没有在线设备，先连上再备份")
        key, source = game_mod.extract(self.adb, dev.serial, self.game,
                                       lambda m: self._note("备份", m))
        label = name or time.strftime("备份 %m-%d %H:%M")
        entry, created = self.vault.add(name=label, key=key, source=source,
                                        device=dev.serial, kind="account",
                                        game=self.game.id)
        self.settings.set("last_backup_at", time.time())
        self.settings.save()
        return entry, created, dev.serial

    def launch_game(self, serial=None):
        dev = self.pick(serial)
        if dev is None:
            raise ServiceError("现在没有在线设备")
        self._need_adb().shell(
            dev.serial, "monkey -p %s -c android.intent.category.LAUNCHER 1" % self.game.pkg,
            timeout=25)
        self._note("设备", "已请求启动 " + self.game.label)
        return dev.serial

    def export_current(self, path, serial=None):
        """Back the device up into the vault, then write that entry as .hak."""
        entry, created, dev = self.backup(serial)
        self.vault.export_hak(entry["id"], path)
        return entry, created

    def import_to_device(self, path, serial=None):
        """Write a .hak key into the game, keeping the current key as a backup."""
        dev = self.pick(serial)
        if dev is None:
            raise ServiceError("现在没有在线设备")
        payload, key = self.vault.read_hak(path)
        game_mod.backup_current(self.adb, dev.serial, self.vault, self.game,
                                lambda m: self._note("导入", m))
        target = game_mod.import_key(self.adb, dev.serial, key, self.game,
                                     lambda m: self._note("导入", m))
        return payload.get("name") or "导入的账号", target

    def import_file(self, path):
        entry, created = self.vault.import_hak(path)
        return entry, created

    def export_entry(self, entry_id, path):
        payload = self.vault.export_hak(entry_id, path)
        self._note("账号", "已导出「%s」到 %s" % (payload.get("name") or "账号", path))
        return payload

    def delete_entry(self, entry_id):
        entry = self.vault.get(entry_id)
        self.vault.delete(entry_id)
        return entry

    def rename_entry(self, entry_id, name):
        self.vault.update(entry_id, name=name)
        return self.vault.get(entry_id)

    def accounts(self):
        return [e for e in self.vault.entries if e.get("kind", "account") == "account"]
