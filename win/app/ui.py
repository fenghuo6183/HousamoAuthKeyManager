# -*- coding: utf-8 -*-
"""Tkinter desktop client for the Housamo AuthKey manager."""
from __future__ import annotations

import json
import os
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from . import adb as adb_mod
from . import game
from . import vault as vault_mod

EMULATOR_PORTS = [7555, 16384, 5555, 62001, 62025, 21503, 5557, 5559,
                  5565, 16416, 16448, 58526, 7556, 62026]

APP_TITLE = "东京放课后 AuthKey 管家"
FONT = ("Microsoft YaHei UI", 10)


class App:
    def __init__(self, root):
        self.root = root
        self.adb = None
        self.devices = []
        self.vault = None
        self._busy = False
        self.save_dir = ""
        self._load_settings()

        root.title(APP_TITLE)
        root.geometry("980x720")
        root.minsize(860, 640)
        self._build_ui()
        self._init_backend()

    # -- setup ---------------------------------------------------------
    def _build_ui(self):
        style = ttk.Style()
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass
        style.configure("Treeview", font=FONT, rowheight=24)
        style.configure("Treeview.Heading", font=("Microsoft YaHei UI", 10, "bold"))
        style.configure("Big.TButton", font=("Microsoft YaHei UI", 11, "bold"), padding=(12, 8))

        top = ttk.Frame(self.root, padding=(12, 10, 12, 4))
        top.pack(fill="x")
        ttk.Label(top, text="① 选择设备", font=("Microsoft YaHei UI", 11, "bold")).pack(side="left")
        self.adb_status = ttk.Label(top, text="正在检测 adb…", foreground="#666")
        self.adb_status.pack(side="left", padx=(12, 0))
        ttk.Button(top, text="刷新设备", command=self.refresh_devices).pack(side="right")
        ttk.Button(top, text="扫描模拟器", command=self.scan_emulators).pack(side="right", padx=(0, 6))

        dev_frame = ttk.Frame(self.root, padding=(12, 0, 12, 8))
        dev_frame.pack(fill="x")
        cols = ("label", "state", "root", "serial")
        self.dev_tree = ttk.Treeview(dev_frame, columns=cols, show="headings", height=4)
        for col, title, width in (("label", "设备", 300), ("state", "状态", 90),
                                  ("root", "Root", 70), ("serial", "序列号", 220)):
            self.dev_tree.heading(col, text=title)
            self.dev_tree.column(col, width=width, anchor="w")
        self.dev_tree.pack(side="left", fill="x", expand=True)
        sb = ttk.Scrollbar(dev_frame, orient="vertical", command=self.dev_tree.yview)
        sb.pack(side="right", fill="y")
        self.dev_tree.configure(yscrollcommand=sb.set)

        actions = ttk.Frame(self.root, padding=(12, 0, 12, 8))
        actions.pack(fill="x")
        self.btn_extract = ttk.Button(actions, text="提取 AuthKey 到账号库", style="Big.TButton", command=self.do_extract)
        self.btn_extract.pack(side="left")
        self.btn_import = ttk.Button(actions, text="把选中账号导入设备", style="Big.TButton", command=self.do_import)
        self.btn_import.pack(side="left", padx=(10, 0))
        ttk.Button(actions, text="打开游戏", command=self.launch_game).pack(side="left", padx=(10, 0))

        save_row = ttk.Frame(self.root, padding=(12, 0, 12, 8))
        save_row.pack(fill="x")
        ttk.Label(save_row, text="保存文件夹：").pack(side="left")
        self.save_dir_var = tk.StringVar(value=self.save_dir or "未选择（点右侧「选择文件夹」）")
        ttk.Entry(save_row, textvariable=self.save_dir_var, state="readonly", width=64).pack(side="left", fill="x", expand=True)
        ttk.Button(save_row, text="选择文件夹", command=self.choose_save_dir).pack(side="left", padx=(6, 0))
        ttk.Button(save_row, text="打开", command=self.open_save_dir).pack(side="left", padx=(6, 0))

        ttk.Separator(self.root).pack(fill="x", padx=12, pady=(2, 6))

        head = ttk.Frame(self.root, padding=(12, 0, 12, 2))
        head.pack(fill="x")
        ttk.Label(head, text="② 账号库", font=("Microsoft YaHei UI", 11, "bold")).pack(side="left")
        self.count_label = ttk.Label(head, text="", foreground="#666")
        self.count_label.pack(side="left", padx=(12, 0))

        vault_frame = ttk.Frame(self.root, padding=(12, 0, 12, 6))
        vault_frame.pack(fill="both", expand=True)
        vcols = ("name", "note", "fingerprint", "source", "created")
        self.vault_tree = ttk.Treeview(vault_frame, columns=vcols, show="headings", height=8)
        for col, title, width in (("name", "名称", 190), ("note", "备注", 180),
                                  ("fingerprint", "Key 指纹", 170), ("source", "来源", 200),
                                  ("created", "添加时间", 150)):
            self.vault_tree.heading(col, text=title)
            self.vault_tree.column(col, width=width, anchor="w")
        self.vault_tree.pack(side="left", fill="both", expand=True)
        vsb = ttk.Scrollbar(vault_frame, orient="vertical", command=self.vault_tree.yview)
        vsb.pack(side="right", fill="y")
        self.vault_tree.configure(yscrollcommand=vsb.set)
        self.vault_tree.bind("<Double-1>", lambda e: self.show_key())

        row = ttk.Frame(self.root, padding=(12, 0, 12, 8))
        row.pack(fill="x")
        for text, cmd in (("重命名", self.rename_entry), ("编辑备注", self.edit_note),
                          ("复制 Key", self.copy_key), ("显示 Key", self.show_key),
                          ("导出到文件夹", self.export_selected_to_dir),
                          ("导出 .hak", self.export_hak), ("导入 .hak", self.import_hak),
                          ("删除", self.delete_entry)):
            ttk.Button(row, text=text, command=cmd).pack(side="left", padx=(0, 6))

        log_frame = ttk.LabelFrame(self.root, text="运行日志", padding=6)
        log_frame.pack(fill="both", expand=False, padx=12, pady=(0, 12))
        self.log_text = tk.Text(log_frame, height=9, font=("Consolas", 9), wrap="word",
                                bg="#1e1e1e", fg="#d6d6d6", insertbackground="#d6d6d6")
        self.log_text.pack(side="left", fill="both", expand=True)
        lsb = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        lsb.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=lsb.set)

    def _init_backend(self):
        try:
            self.adb = adb_mod.Adb()
            self.adb.ensure_server()
            self.adb_status.configure(text="adb: " + (self.adb.version or self.adb.path), foreground="#2e7d32")
        except Exception as exc:
            self.adb = None
            self.adb_status.configure(text="adb 不可用", foreground="#c62828")
            self.log("错误", str(exc))
        try:
            self.vault = vault_mod.Vault()
            self.refresh_vault()
        except Exception as exc:
            self.log("错误", "账号库加载失败：%s" % exc)
        if self.adb:
            self.refresh_devices()

    # -- settings / folder export --------------------------------------
    def _settings_path(self):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        folder = os.path.join(base, "HousamoAuthKeyManager")
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, "settings.json")

    def _load_settings(self):
        try:
            with open(self._settings_path(), "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self.save_dir = data.get("save_dir", "") or ""
        except Exception:
            self.save_dir = ""

    def _save_settings(self):
        try:
            with open(self._settings_path(), "w", encoding="utf-8") as fh:
                json.dump({"save_dir": self.save_dir}, fh, ensure_ascii=False, indent=1)
        except Exception as exc:
            self.log("设置", "保存设置失败：%s" % exc)

    def choose_save_dir(self):
        path = filedialog.askdirectory(parent=self.root, title="选择 key 保存到的文件夹")
        if not path:
            return
        self.save_dir = path
        self._save_settings()
        self.save_dir_var.set(path)
        self.log("设置", "保存文件夹：%s" % path)

    def open_save_dir(self):
        if not self.save_dir or not os.path.isdir(self.save_dir):
            messagebox.showwarning(APP_TITLE, "请先选择一个存在的文件夹。")
            return
        try:
            os.startfile(self.save_dir)   # noqa: S606 - Windows only
        except Exception as exc:
            self.log("设置", "打开文件夹失败：%s" % exc)

    def _safe_name(self, name):
        text = re.sub(r'[\\/:*?"<>|\r\n\t]', "_", name or "").strip()
        if not text:
            text = "账号"
        return text[:40]

    def export_to_dir(self, name, key):
        """Write <保存文件夹>/<名字>/AuthKey.txt; returns path or None."""
        if not self.save_dir:
            return None
        folder = os.path.join(self.save_dir, self._safe_name(name))
        try:
            os.makedirs(folder, exist_ok=True)
            target = os.path.join(folder, "AuthKey.txt")
            with open(target, "wb") as fh:
                fh.write(bytes(key))
            return target
        except Exception as exc:
            self.log("导出", "写入失败：%s" % exc)
            return None

    # -- logging -------------------------------------------------------
    def log(self, tag, message):
        if threading.current_thread() is not threading.main_thread():
            self.root.after(0, self.log, tag, message)
            return
        line = "[%s] %s\n" % (tag, message)
        self.log_text.insert("end", line)
        self.log_text.see("end")

    def _bg(self, worker, on_done=None):
        if self._busy:
            self.log("提示", "上一个操作还没结束，请稍等。")
            return
        self._busy = True
        self._set_buttons("disabled")

        def runner():
            try:
                result = worker()
                error = None
            except Exception as exc:
                result, error = None, exc
            self.root.after(0, self._finish, result, error, on_done)

        threading.Thread(target=runner, daemon=True).start()

    def _finish(self, result, error, on_done):
        self._busy = False
        self.save_dir = ""
        self._load_settings()
        self._set_buttons("normal")
        if error is not None:
            self.log("失败", str(error))
            messagebox.showerror(APP_TITLE, str(error))
            return
        if on_done:
            on_done(result)

    def _set_buttons(self, state):
        for btn in (self.btn_extract, self.btn_import):
            btn.configure(state=state)

    # -- devices -------------------------------------------------------
    def selected_device(self):
        sel = self.dev_tree.selection()
        if sel:
            serial = self.dev_tree.item(sel[0], "values")[3]
            for dev in self.devices:
                if dev.serial == serial:
                    return dev
        for dev in self.devices:
            if dev.online:
                return dev
        return None

    def refresh_devices(self):
        if not self.adb:
            messagebox.showerror(APP_TITLE, "adb 不可用，请检查 platform-tools 是否放在 assets/platform-tools 下。")
            return
        self._bg(self._devices_worker, self._devices_done)

    def _devices_worker(self):
        devices = [d for d in self.adb.devices()]
        for dev in devices:
            dev.root = "?" 
            if dev.online:
                try:
                    dev.root = "是" if self.adb.su_available(dev.serial) else "否"
                except Exception:
                    dev.root = "?"
        return devices

    def _devices_done(self, devices):
        self.devices = devices
        self.dev_tree.delete(*self.dev_tree.get_children())
        for dev in devices:
            self.dev_tree.insert("", "end", values=(dev.label, dev.state, dev.root, dev.serial))
        if devices:
            self.dev_tree.selection_set(self.dev_tree.get_children()[0])
            self.log("设备", "发现 %d 台设备" % len(devices))
        else:
            self.log("设备", "没有发现设备。请打开 USB 调试，或先启动模拟器再点「扫描模拟器」。")

    def scan_emulators(self):
        if not self.adb:
            messagebox.showerror(APP_TITLE, "adb 不可用。")
            return

        def worker():
            hits = 0
            for port in EMULATOR_PORTS:
                ok, text = self.adb.connect("127.0.0.1:%d" % port)
                if ok:
                    hits += 1
                    self.log("模拟器", "已连接 127.0.0.1:%d" % port)
            return hits

        def done(hits):
            self.log("模拟器", "扫描结束，新连接 %d 个" % hits)
            self.refresh_devices()

        self._bg(worker, done)

    # -- vault view ----------------------------------------------------
    def refresh_vault(self):
        if not self.vault:
            return
        self.vault_tree.delete(*self.vault_tree.get_children())
        for entry in self.vault.entries:
            self.vault_tree.insert("", "end", iid=entry["id"], values=(
                entry.get("name", ""), entry.get("note", ""), entry.get("fingerprint", ""),
                entry.get("source", ""), entry.get("created_at", "")))
        self.count_label.configure(text="共 %d 个账号" % len(self.vault.entries))

    def selected_entry(self):
        sel = self.vault_tree.selection()
        if not sel or not self.vault:
            return None
        return self.vault.get(sel[0])

    def _require(self, device=True, entry=True):
        if device and not self.selected_device():
            messagebox.showwarning(APP_TITLE, "请先选择一台在线设备。")
            return False
        if entry and not self.selected_entry():
            messagebox.showwarning(APP_TITLE, "请先在账号库里选中一个账号。")
            return False
        return True

    # -- actions -------------------------------------------------------
    def do_extract(self):
        if not self._require(device=True, entry=False):
            return
        dev = self.selected_device()
        self.log("提取", "开始从 %s 提取 AuthKey" % dev.serial)

        def worker():
            key, source = game.extract(self.adb, dev.serial, lambda m: self.log("提取", m))
            return key, source

        def done(result):
            key, source = result
            entry, created = self.vault.add(name="待命名账号", key=key, source=source, device=dev.serial)
            if created:
                name = simpledialog.askstring(APP_TITLE, "给这个账号起个名字：", parent=self.root)
                if name and name.strip():
                    self.vault.update(entry["id"], name=name.strip())
            else:
                self.log("提取", "这个 key 已经在账号库里了：%s" % entry.get("name"))
            self.refresh_vault()
            self.vault_tree.selection_set(entry["id"])
            self.log("完成", "已保存账号，指纹 %s" % entry.get("fingerprint"))
            out = self.export_to_dir(entry.get("name"), key)
            if out:
                self.log("导出", "已写出 %s" % out)
            elif not self.save_dir:
                self.log("导出", "还没有选择保存文件夹，可在上方「保存文件夹」里选一个。")

        self._bg(worker, done)

    def do_import(self):
        if not self._require():
            return
        dev = self.selected_device()
        entry = self.selected_entry()
        if not messagebox.askyesno(APP_TITLE,
                                   "将把「%s」的 AuthKey 写入设备 %s。\n\n"
                                   "这会覆盖该设备当前的登录账号（写入前会自动备份现有 key）。\n"
                                   "继续吗？" % (entry.get("name"), dev.serial)):
            return
        key = self.vault.key_of(entry)
        self.log("导入", "目标设备 %s，账号 %s" % (dev.serial, entry.get("name")))

        def worker():
            backup = game.backup_current(self.adb, dev.serial, self.vault, lambda m: self.log("备份", m))
            if backup:
                self.log("备份", "已备份原 key：%s" % backup.get("name"))
            target = game.import_key(self.adb, dev.serial, key, lambda m: self.log("导入", m))
            return target

        def done(target):
            self.refresh_vault()
            self.log("完成", "写入完成：%s，可以打开游戏了。" % target)
            messagebox.showinfo(APP_TITLE, "导入完成，打开游戏即可登录该账号。")

        self._bg(worker, done)

    def launch_game(self):
        if not self._require(device=True, entry=False):
            return
        dev = self.selected_device()
        try:
            self.adb.shell(dev.serial, "monkey -p %s -c android.intent.category.LAUNCHER 1" % game.PKG, timeout=25)
            self.log("设备", "已请求启动游戏")
        except Exception as exc:
            self.log("失败", "启动游戏失败：%s" % exc)

    # -- vault actions -------------------------------------------------
    def rename_entry(self):
        entry = self.selected_entry()
        if not entry:
            return
        name = simpledialog.askstring(APP_TITLE, "新名称：", initialvalue=entry.get("name", ""), parent=self.root)
        if name and name.strip():
            self.vault.update(entry["id"], name=name.strip())
            self.refresh_vault()

    def edit_note(self):
        entry = self.selected_entry()
        if not entry:
            return
        note = simpledialog.askstring(APP_TITLE, "备注：", initialvalue=entry.get("note", ""), parent=self.root)
        if note is not None:
            self.vault.update(entry["id"], note=note)
            self.refresh_vault()

    def copy_key(self):
        entry = self.selected_entry()
        if not entry:
            return
        text = self.vault.key_of(entry).decode("utf-8", "replace")
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()
        self.log("账号", "已复制「%s」的 Key 到剪贴板" % entry.get("name"))

    def show_key(self):
        entry = self.selected_entry()
        if not entry:
            return
        text = self.vault.key_of(entry).decode("utf-8", "replace")
        win = tk.Toplevel(self.root)
        win.title("Key - " + entry.get("name", ""))
        win.geometry("640x220")
        box = tk.Text(win, wrap="char", font=("Consolas", 10))
        box.insert("1.0", text)
        box.configure(state="disabled")
        box.pack(fill="both", expand=True, padx=10, pady=10)
        ttk.Button(win, text="关闭", command=win.destroy).pack(pady=(0, 10))

    def export_selected_to_dir(self):
        entry = self.selected_entry()
        if entry is None:
            messagebox.showwarning(APP_TITLE, "请先在账号库里选中一个账号。")
            return
        if not self.save_dir:
            if not messagebox.askyesno(APP_TITLE, "还没有选择保存文件夹，现在选一个吗？"):
                return
            self.choose_save_dir()
            if not self.save_dir:
                return
        out = self.export_to_dir(entry.get("name"), self.vault.key_of(entry))
        if out:
            self.log("导出", "已写出 %s" % out)
            messagebox.showinfo(APP_TITLE, "已导出到：\n%s" % out)
        else:
            messagebox.showerror(APP_TITLE, "导出失败，详见运行日志。")

    def export_hak(self):
        entry = self.selected_entry()
        if not entry:
            return
        path = filedialog.asksaveasfilename(
            parent=self.root, defaultextension=".hak",
            initialfile=(entry.get("name") or "account").replace("/", "_") + ".hak",
            filetypes=[("AuthKey 备份", "*.hak"), ("所有文件", "*.*")])
        if not path:
            return
        self.vault.export_hak(entry["id"], path)
        self.log("账号", "已导出 %s" % path)
        messagebox.showwarning(APP_TITLE, "导出成功。\n\n.hak 文件里是明文 key，请当作密码保管，不要发到公开地方。")

    def import_hak(self):
        path = filedialog.askopenfilename(parent=self.root, filetypes=[("AuthKey 备份", "*.hak"), ("所有文件", "*.*")])
        if not path:
            return
        try:
            entry, created = self.vault.import_hak(path)
            self.refresh_vault()
            self.vault_tree.selection_set(entry["id"])
            self.log("账号", ("已导入 " if created else "已存在 ") + entry.get("name", ""))
        except Exception as exc:
            messagebox.showerror(APP_TITLE, "导入失败：%s" % exc)

    def delete_entry(self):
        entry = self.selected_entry()
        if not entry:
            return
        if messagebox.askyesno(APP_TITLE, "确定删除「%s」？\n（删除前建议先导出 .hak 备份）" % entry.get("name")):
            self.vault.delete(entry["id"])
            self.refresh_vault()


def run():
    root = tk.Tk()
    App(root)
    root.mainloop()
