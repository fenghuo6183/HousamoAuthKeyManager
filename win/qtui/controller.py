# -*- coding: utf-8 -*-
"""Threaded glue between the headless Service and the Qt widgets.

Blocking adb/game work runs on worker threads; results come back through
queued signals, so widgets are only ever touched on the GUI thread.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time

from PySide6.QtCore import QObject, Qt, QTimer, Signal

from app import config, reconcile, updater

from .service import Service


class Controller(QObject):
    logged = Signal(str, str)          # tag, message
    devices_ready = Signal(object)     # list[adb.Device]
    state_changed = Signal(str, str, str)   # dot key, title, detail
    busy_changed = Signal(bool)
    vault_changed = Signal(object)     # list[dict]
    game_changed = Signal(object)      # game.Game
    update_checked = Signal(str, bool)  # tag, newer?
    current_changed = Signal(str)      # digest of the key the game is using
    reconcile_ready = Signal(object)   # payload dict, or None when all clear
    _job_done = Signal(object)         # (done, result, error)

    def __init__(self, settings=None, parent=None):
        super().__init__(parent)
        self.settings = settings if settings is not None else config.Settings()
        self.service = None
        self.busy = False
        self.latest_tag = ""
        self.latest_asset = None
        self._prefetched = ""
        self._prefetch_tag = ""
        self._notified_update = ""
        self.current_digest = ""
        self._reconcile_serial = ""
        self._job_done.connect(self._on_job_done, Qt.QueuedConnection)
        self._backup_timer = QTimer(self)
        self._backup_timer.setInterval(60000)
        self._backup_timer.timeout.connect(self._backup_tick)
        self._backup_timer.start()

    # -- plumbing ------------------------------------------------------
    def log(self, tag, message):
        self.logged.emit(tag, message)

    def notify(self, title, text):
        """Desktop notification: tray balloon and/or webhook, per settings."""
        if self.settings.get("notify_balloon"):
            shell = self.parent()
            tray = getattr(shell, "tray", None) if shell is not None else None
            if tray is not None and getattr(tray, "ok", False):
                try:
                    tray.notify(title, text)
                except Exception:
                    pass
        if self.settings.get("notify_webhook"):
            url = (self.settings.get("webhook_url") or "").strip()
            if url:
                from app import notify as notify_mod

                def post():
                    try:
                        notify_mod.post_webhook(url, title, text)
                    except Exception:
                        pass

                threading.Thread(target=post, daemon=True).start()

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
        preferred = self.settings.get("preferred_serial") or ""
        if self.settings.get("auto_connect") and preferred and service.adb is not None:
            self.log("连接", "启动时自动连接记住的设备 %s" % preferred)
            self.connect(preferred)

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
                if self.settings.get("auto_reconnect") and not any(d.online for d in devices):
                    preferred = self.settings.get("preferred_serial") or ""
                    now = time.time()
                    if preferred and now - getattr(self, "_last_reconnect", 0.0) > 20.0:
                        self._last_reconnect = now
                        try:
                            self.service._need_adb().connect(preferred, timeout=3)
                            devices = self.service.refresh_devices()
                        except Exception:
                            pass
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
            if getattr(self, "_reconcile_serial", "") != dev.serial:
                self._reconcile_serial = dev.serial
                QTimer.singleShot(1200, lambda: self.check_reconcile())
        elif devices:
            self.state_changed.emit("warn", "%d 台设备离线" % len(devices),
                                    "看看模拟器有没有开、端口对不对")
        else:
            self.state_changed.emit("warn", "未发现设备", "打开模拟器，或点「扫描端口」")
            self.reconcile_ready.emit(None)

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

    def test_connection(self, serial):
        """Probe one address without adopting it as the active device."""
        if self.service is None:
            self.log("提示", "adb 还在准备，稍等一下")
            return
        serial = (serial or "").strip()
        if not serial:
            self.log("提示", "先填一个地址再测试")
            return
        self.state_changed.emit("muted", "正在测试连接…", serial)

        def work():
            adb = self.service._need_adb()
            ok, text = adb.connect(serial, timeout=6)
            return ok, (text or "").strip()

        def done(payload):
            ok, text = payload
            if ok:
                self.log("连接", "连接测试成功：%s" % serial)
                self.state_changed.emit("ok", "连接测试成功", serial)
                self.refresh_devices()
            else:
                reason = text or "连不上 %s" % serial
                self.log("失败", "连接测试失败：%s" % reason)
                self.state_changed.emit("err", "连接测试失败", reason)

        self._bg(work, done)

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
    def backup(self, auto=False, name=None):
        if self.service is None:
            return
        self.state_changed.emit("muted", "正在读取 AuthKey…", "")

        def done(payload):
            entry, created, serial = payload
            self.vault_changed.emit(self.service.vault.entries)
            if created:
                self.log("完成", "已%s：%s" % ("自动备份" if auto else "备份", entry.get("name")))
                self.state_changed.emit("ok", "备份完成", entry.get("name"))
                if self.settings.get("notify_on_backup"):
                    self.notify("备份完成", "%s 已存进账号库" % (entry.get("name") or "AuthKey"))
            else:
                self.log("备份", "这个 key 已经在账号库里了")
                self.state_changed.emit("ok", "已连接", serial)
            if created:
                self.check_reconcile(force=True)

        self._bg(lambda: self.service.backup(name=name), done)

    def _backup_tick(self):
        if not self.settings.get("auto_backup") or self.service is None or self.busy:
            return
        try:
            hours = max(1, min(48, int(self.settings.get("auto_backup_hours") or 6)))
            last = float(self.settings.get("last_backup_at") or 0)
        except (TypeError, ValueError):
            hours, last = 6, 0.0
        if time.time() - last < hours * 3600:
            return
        if not any(dev.online for dev in (self.service.devices or [])):
            return
        self.log("备份", "自动备份时间到了（每 %d 小时一次）" % hours)
        self.backup(auto=True)

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
            asset = updater.pick_asset(release)
            return tag, updater.is_newer(tag, theme_mod.APP_VERSION), asset

        def done(payload):
            if payload is None:
                self.log("更新", "没查到这个版本的更新信息")
                return
            tag, newer, asset = payload
            self.latest_tag = tag
            self.latest_asset = asset
            self.update_checked.emit(tag, bool(newer))
            if newer:
                self.log("更新", "发现新版本 %s" % tag)
                self.state_changed.emit("ok", "有新版本 %s" % tag, "设置里可以一键更新")
                if (self.settings.get("auto_download_update")
                        and self._prefetch_tag != tag):
                    self._prefetch_update(tag, asset)
                if (self.settings.get("notify_on_update")
                        and self._notified_update != tag):
                    self._notified_update = tag
                    self.notify("发现新版本", "%s 可以更新了" % (tag or "新版本"))
            else:
                self.log("更新", "已经是最新版本（%s）" % tag)

        self.state_changed.emit("muted", "正在检查更新…", "")
        self._bg(work, done)

    # -- reconcile / account parity ------------------------------------
    def _prefetch_update(self, tag, asset):
        """Background download so 「立即更新」 only has to stage and relaunch."""
        if not asset:
            return
        self._prefetch_tag = tag
        url = asset.get("url", "")
        digest = asset.get("digest", "")

        def work():
            try:
                path = updater.download(url, digest, lambda m: self.log("更新", m))
            except Exception as exc:
                self.log("更新", "预下载失败：%s" % exc)
                return
            self._prefetched = path or ""
            if path:
                self.log("更新", "新版本已下载好，点「立即更新」直接安装")

        threading.Thread(target=work, daemon=True).start()

    def check_reconcile(self, force=False):
        """Read the key the game is running and tell the UI if it is unknown."""
        if self.service is None or self.busy:
            return
        if not any(dev.online for dev in (self.service.devices or [])):
            return
        self.state_changed.emit("muted", "正在核对游戏里的 key…", "")

        def work():
            key, source, serial = self.service.current_key(quiet=True)
            digest = reconcile.digest_of(key)
            known = reconcile.is_known(self.service.vault, digest)
            ignored = set(self.settings.get("reconcile_ignored") or [])
            return {"key": key, "source": source, "serial": serial,
                    "digest": digest, "known": known, "ignored": digest in ignored}

        def done(payload):
            self.current_digest = payload.get("digest") or ""
            self.current_changed.emit(self.current_digest)
            if payload.get("known") or payload.get("ignored"):
                self.reconcile_ready.emit(None)
                self.state_changed.emit("ok", "游戏里的 key 已在账号库里", "")
            else:
                self.log("核对", "游戏里现在用的 key 不在账号库里")
                self.reconcile_ready.emit(payload)

        self._bg(work, done)

    def save_reconcile(self, payload, name):
        if self.service is None or not payload:
            return
        self.state_changed.emit("muted", "正在保存快照…", "")

        def done(result):
            entry, created = result
            self.vault_changed.emit(self.service.vault.entries)
            self.reconcile_ready.emit(None)
            self.log("完成", "已存进账号库：%s" % entry.get("name"))
            self.state_changed.emit("ok", "已保存游戏内快照", entry.get("name"))

        self._bg(lambda: self.service.save_key(payload["key"], name=name,
                                               source=payload.get("source", ""),
                                               device=payload.get("serial", "")), done)

    def dismiss_reconcile(self, digest):
        if not digest:
            return
        ignored = list(self.settings.get("reconcile_ignored") or [])
        if digest not in ignored:
            ignored.append(digest)
            self.settings.set("reconcile_ignored", ignored[-50:])
            self.settings.save()
        self.reconcile_ready.emit(None)

    def set_note(self, entry_id, note):
        if self.service is None:
            return

        def done(entry):
            self.vault_changed.emit(self.service.vault.entries)
            if entry:
                self.log("账号", "备注已保存：%s" % (entry.get("note") or "（清空）"))

        self._bg(lambda: self.service.set_note(entry_id, note), done)

    def restore_entry(self, entry_id):
        if self.service is None:
            return
        self.state_changed.emit("muted", "正在写回游戏…", "")

        def done(payload):
            entry, target = payload
            self.vault_changed.emit(self.service.vault.entries)
            self.log("完成", "已把「%s」写进游戏" % entry.get("name"))
            self.state_changed.emit("ok", "还原完成", entry.get("name"))

        self._bg(lambda: self.service.restore_entry(entry_id), done)

    def bulk_export(self, path, kind="account"):
        if self.service is None:
            return
        self.state_changed.emit("muted", "正在打包导出…", "")

        def done(count):
            self.log("完成", "已打包导出 %d 条到 %s" % (count, path))
            self.state_changed.emit("ok", "打包导出完成", "%d 条" % count)

        self._bg(lambda: self.service.bulk_export(path, kind), done)

    def import_clipboard(self):
        if self.service is None:
            return
        from PySide6.QtWidgets import QApplication
        text = QApplication.clipboard().text()
        if not text.strip():
            self.log("提示", "剪贴板是空的")
            return

        def done(payload):
            entry, created = payload
            self.vault_changed.emit(self.service.vault.entries)
            self.log("完成" if created else "账号",
                     ("已从剪贴板导入：%s" % entry.get("name")) if created
                     else "这个 key 已经在账号库里了")

        self._bg(lambda: self.service.import_clipboard(text), done)

    # -- update --------------------------------------------------------
    def install_update(self):
        if not self.latest_asset:
            self.log("更新", "先点「立即检查」拿到新版下载地址")
            return
        install = updater.install_dir()
        if not updater.dir_writable(install):
            self.log("错误", "程序目录不可写（可能装在 Program Files），请手动下载覆盖")
            self.state_changed.emit("err", "无法自动更新", "程序目录不可写")
            return
        tag = self.latest_tag
        asset = dict(self.latest_asset)
        self.state_changed.emit("muted", "正在下载更新…", tag)

        def work():
            if self._prefetched and self._prefetch_tag == tag and os.path.isfile(self._prefetched):
                zip_path = self._prefetched
                self.log("更新", "用已经下载好的安装包")
            else:
                zip_path = updater.download(asset.get("url", ""), asset.get("digest", ""),
                                            lambda m: self.log("更新", m))
            stage = updater.stage_copy(install, log=lambda m: self.log("更新", m))
            name = os.path.basename(sys.executable) if getattr(sys, "frozen", False) \
                else "AuthKeyManager.exe"
            exe = os.path.join(stage, name)
            if not os.path.isfile(exe):
                raise RuntimeError("临时目录里没有可执行文件：%s" % exe)
            updater.write_state(stage="applying", target_version=tag,
                                zip=zip_path, install=install)
            subprocess.Popen([exe, "--apply-update", zip_path, install, str(os.getpid())],
                             cwd=stage,
                             creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
            return zip_path

        def done(zip_path):
            self.log("更新", "更新程序已启动，本程序即将退出并重启")
            self.state_changed.emit("ok", "正在安装更新", tag)
            parent = self.parent()
            if parent is not None and hasattr(parent, "quit_app"):
                QTimer.singleShot(500, parent.quit_app)

        self._bg(work, done)

    # -- bulk / maintenance -------------------------------------------
    def import_folder(self, path):
        def done(payload):
            added, skipped = payload
            self.vault_changed.emit(self.service.vault.entries)
            self.log("完成", "批量导入：新增 %d 个，跳过 %d 个重复" % (added, skipped))
            self.state_changed.emit("ok", "导入完成", "新增 %d 个" % added if added else "没有新账号")

        self._bg(lambda: self.service.import_folder(path), done)

    def clear_vault(self):
        count = self.service.clear_all()
        self.vault_changed.emit(self.service.vault.entries)
        self.current_digest = ""
        self.current_changed.emit("")
        self.log("账号", "已清空账号库（%d 条）" % count)
        self.state_changed.emit("ok", "账号库已清空", "")

    def switch_game(self, game_id):
        if self.service is None:
            return
        game = self.service.set_game(game_id)
        self.game_changed.emit(game)
        self.vault_changed.emit(self.service.vault.entries)
        self.log("设置", "切换到 %s" % game.label)
