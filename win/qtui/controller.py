# -*- coding: utf-8 -*-
"""Threaded glue between the headless Service and the Qt widgets.

Blocking adb/game work runs on worker threads; results come back through
queued signals, so widgets are only ever touched on the GUI thread.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Qt, Signal

from app import config

from .service import Service


class Controller(QObject):
    logged = Signal(str, str)          # tag, message
    devices_ready = Signal(object)     # list[adb.Device]
    state_changed = Signal(str, str, str)   # dot key, title, detail
    busy_changed = Signal(bool)
    vault_changed = Signal(object)     # list[dict]
    game_changed = Signal(object)      # game.Game
    _job_done = Signal(object)         # (done, result, error)

    def __init__(self, settings=None, parent=None):
        super().__init__(parent)
        self.settings = settings if settings is not None else config.Settings()
        self.service = None
        self.busy = False
        self._job_done.connect(self._on_job_done, Qt.QueuedConnection)

    # -- plumbing ------------------------------------------------------
    def log(self, tag, message):
        self.logged.emit(tag, message)

    def _bg(self, work, done=None):
        if self.busy:
            self.log("提示", "正忙着，等这次操作结束再来")
            return False
        self.busy = True
        self.busy_changed.emit(True)

        def runner():
            try:
                result = work()
                error = None
            except Exception as exc:
                result = None
                error = str(exc) or exc.__class__.__name__
            self._job_done.emit((done, result, error))

        threading.Thread(target=runner, daemon=True).start()
        return True

    def _on_job_done(self, payload):
        done, result, error = payload
        self.busy = False
        self.busy_changed.emit(False)
        if error is not None:
            self.log("失败", error)
            self.state_changed.emit("err", "操作失败", error)
            return
        if done is not None:
            try:
                done(result)
            except Exception as exc:
                self.log("失败", str(exc))

    # -- lifecycle -----------------------------------------------------
    def boot(self):
        if self.service is not None or self.busy:
            return
        self.log("启动", "正在准备 adb…")

        def build():
            service = Service(self.settings)
            service.log = self.log
            return service

        self._bg(build, self._on_service)

    def _on_service(self, service):
        self.service = service
        if service.adb is None:
            self.log("错误", service.adb_error or "adb 不可用")
            self.state_changed.emit("err", "adb 不可用", "把 platform-tools 放进程序目录的 assets/ 下")
        else:
            self.log("启动", "adb 就绪")
        if service.vault_error:
            self.log("错误", "账号库打不开：%s" % service.vault_error)
        self.game_changed.emit(service.game)
        self.vault_changed.emit(service.vault.entries)
        self.refresh_devices()

    # -- devices -------------------------------------------------------
    def refresh_devices(self, quiet=False):
        if self.service is None:
            return
        if quiet:
            if self.busy:
                return

            def poll():
                try:
                    devices = self.service.refresh_devices()
                except Exception:
                    return
                self._job_done.emit((self._devices_done, devices, None))

            threading.Thread(target=poll, daemon=True).start()
            return
        self.state_changed.emit("muted", "正在检测设备…", "")
        self._bg(lambda: self.service.refresh_devices(deep=True), self._devices_done)

    def _devices_done(self, devices):
        online = [dev for dev in devices if dev.online]
        preferred = self.settings.get("preferred_serial") or ""
        if not self.service.serial:
            for dev in online:
                if dev.serial == preferred:
                    self.service.serial = dev.serial
                    break
        self.devices_ready.emit(list(devices))
        sig = tuple((dev.serial, dev.state) for dev in devices)
        if sig != getattr(self, "_device_sig", None):
            self._device_sig = sig
            if devices:
                names = "、".join(dev.short_label for dev in devices[:4])
                self.log("设备", "发现 %d 台：%s" % (len(devices), names))
            elif getattr(self, "_had_devices", False):
                self.log("设备", "设备都断开了")
            self._had_devices = bool(devices)
        if online:
            dev = next((d for d in online if d.serial == self.service.serial), online[0])
            self.service.serial = dev.serial
            self.state_changed.emit("ok", "已连接 %s" % dev.short_label, dev.serial)
        elif devices:
            self.state_changed.emit("warn", "%d 台设备离线" % len(devices),
                                    "看看模拟器有没有开、端口对不对")
        else:
            self.state_changed.emit("warn", "未发现设备", "打开模拟器，或点「扫描端口」")

    def connect(self, serial):
        if self.service is None:
            self.log("提示", "adb 还在准备，稍等一下")
            return
        serial = (serial or "").strip()
        self.state_changed.emit("muted", "正在连接…", serial)

        def done(value):
            self.log("连接", "已连接 %s" % value)
            self.refresh_devices()

        self._bg(lambda: self.service.connect(serial), done)

    def scan_ports(self):
        if self.service is None:
            self.log("提示", "adb 还在准备，稍等一下")
            return
        self.state_changed.emit("muted", "正在扫描模拟器…", "")

        def done(hits):
            if hits:
                self.log("设备", "扫描到 %d 个端口：%s"
                         % (len(hits), ", ".join("127.0.0.1:%d" % p for p in hits)))
            else:
                self.log("设备", "没扫描到模拟器，确认模拟器已经开好")
            self.refresh_devices()

        self._bg(self.service.scan_ports, done)

    # -- actions -------------------------------------------------------
    def backup(self):
        if self.service is None:
            return
        self.state_changed.emit("muted", "正在读取 AuthKey…", "")

        def done(payload):
            entry, created, serial = payload
            self.vault_changed.emit(self.service.vault.entries)
            if created:
                self.log("完成", "已备份：%s" % entry.get("name"))
                self.state_changed.emit("ok", "备份完成", entry.get("name"))
            else:
                self.log("备份", "这个 key 已经在账号库里了")
                self.state_changed.emit("ok", "已连接", serial)

        self._bg(self.service.backup, done)

    def launch_game(self):
        if self.service is None:
            return
        self._bg(self.service.launch_game)

    def export_current(self, path):
        if self.service is None:
            return
        self.state_changed.emit("muted", "正在导出 AuthKey…", "")

        def done(payload):
            entry, created = payload
            self.vault_changed.emit(self.service.vault.entries)
            self.log("完成", "已导出到 %s" % path)
            self.state_changed.emit("ok", "导出完成", entry.get("name"))

        self._bg(lambda: self.service.export_current(path), done)

    def import_to_device(self, path):
        if self.service is None:
            return
        self.state_changed.emit("muted", "正在写入 AuthKey…", "")

        def done(payload):
            name, target = payload
            self.vault_changed.emit(self.service.vault.entries)
            self.log("完成", "已把「%s」写进游戏，重新打开游戏即可登录" % name)
            self.state_changed.emit("ok", "导入完成", name)

        self._bg(lambda: self.service.import_to_device(path), done)

    def import_file(self, path):
        if self.service is None:
            return

        def done(payload):
            entry, created = payload
            self.vault_changed.emit(self.service.vault.entries)
            self.log("完成" if created else "账号",
                     ("已导入：%s" % entry.get("name")) if created
                     else ("「%s」已经在账号库里了" % entry.get("name")))

        self._bg(lambda: self.service.import_file(path), done)

    def export_entry(self, entry_id, path):
        if self.service is None:
            return
        self.state_changed.emit("muted", "正在导出…", "")

        def done(_payload):
            self.log("完成", "已导出到 %s" % path)
            self.state_changed.emit("ok", "导出完成", path)

        self._bg(lambda: self.service.export_entry(entry_id, path), done)

    def delete_entry(self, entry_id):
        if self.service is None:
            return
        if not self.service.vault.get(entry_id):
            return

        def done(entry):
            self.vault_changed.emit(self.service.vault.entries)
            self.log("账号", "已从账号库删除「%s」" % entry.get("name"))

        self._bg(lambda: self.service.delete_entry(entry_id), done)

    def rename_entry(self, entry_id, name):
        if self.service is None:
            return

        def done(entry):
            self.vault_changed.emit(self.service.vault.entries)
            if entry:
                self.log("账号", "改名为「%s」" % entry.get("name"))

        self._bg(lambda: self.service.rename_entry(entry_id, name), done)

    def check_update(self):
        def work():
            from app import theme as theme_mod
            from app import updater
            release = updater.fetch_latest()
            if not release:
                return None
            tag = release.get("tag_name") or release.get("name") or ""
            return tag, updater.is_newer(tag, theme_mod.APP_VERSION)

        def done(payload):
            if payload is None:
                self.log("更新", "没查到这个版本的更新信息")
                return
            tag, newer = payload
            if newer:
                self.log("更新", "发现新版本 %s" % tag)
                self.state_changed.emit("ok", "有新版本 %s" % tag, "去 GitHub Release 下载")
            else:
                self.log("更新", "已经是最新版本（%s）" % tag)

        self.state_changed.emit("muted", "正在检查更新…", "")
        self._bg(work, done)

    def switch_game(self, game_id):
        if self.service is None:
            return
        game = self.service.set_game(game_id)
        self.game_changed.emit(game)
        self.vault_changed.emit(self.service.vault.entries)
        self.log("设置", "切换到 %s" % game.label)
