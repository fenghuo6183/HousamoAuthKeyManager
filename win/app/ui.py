# -*- coding: utf-8 -*-
"""Tkinter desktop client for the Housamo AuthKey manager."""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import filedialog, font as tkfont, messagebox, simpledialog, ttk

from . import adb as adb_mod
from . import applock
from . import bgfx
from . import bulk
from . import config
from . import dialogs
from . import dnd
from . import game
from . import keyscan
from . import lanshare
from . import qr
from . import reconcile
from . import theme
from . import updater
from . import vault as vault_mod
from .widgets import (DeviceList, MiniSlider, NavButton, PillButton, RoundCard,
                      SectionTitle, Segmented, chip, entry, label)

EMULATOR_PORTS = list(config.EMULATOR_PORTS)

# 参考 MAA 的连接配置：选一个预设就把地址填好，自定义则手填。
CONNECT_PROFILES = (
    ("auto", "自动检测（扫端口）", ""),
    ("mumu", "MuMu 模拟器", "127.0.0.1:16384"),
    ("ld", "雷电模拟器", "127.0.0.1:5555"),
    ("nox", "夜神模拟器", "127.0.0.1:62001"),
    ("bst", "蓝叠模拟器", "127.0.0.1:5555"),
    ("custom", "自定义地址", None),
)

APP_TITLE = theme.APP_NAME
# Authored at 96 dpi; _relayout scales them through theme.px() so hi-dpi
# monitors get a bigger window instead of a blurred bitmap stretch.
RAIL_W = 258
PAGE_PAD = 16
GAP = 12
LOG_H = 156


class App:
    def __init__(self, root):
        self.root = root
        self.settings = config.Settings()
        self.pal = theme.palette(self.settings.get("theme"))
        # The vault holds plaintext keys, so ask for the PIN before anything
        # is drawn. A failed unlock leaves the window empty and the caller
        # closes it.
        self.locked_out = False
        if applock.is_enabled(self.settings):
            if not applock.prompt_unlock(self.root, self.settings, self.pal):
                self.locked_out = True
                return
        self.active_game = game.game_by_id(self.settings.get("active_game") or "housamo")
        self.backdrop = bgfx.Backdrop(self.pal)
        self.backdrop.configure(path=self.settings.get("bg_image"),
                                blur=self.settings.get("bg_blur"),
                                alpha=self.settings.get("bg_alpha"))

        self.adb = None
        self.devices = []
        self._selected_serial = self.settings.get("preferred_serial") or ""
        self.vault = None
        self.vaults = {}
        self.update_asset = None
        self.update_release = None
        # 启动检查到新版本时弹一次更新框；记下已经提示过的版本，同一个
        # 版本在本次运行里不再重复弹（点「稍后再说」就真的稍后）。
        self._prompted_update = None
        self._update_prompt_win = None
        self.vault_kind = "account"
        self._busy = False
        self.save_dir = self.settings.get("save_dir") or ""
        self.cards = []
        self.pages = {}
        self.page = "tasks"
        self.nav = {}
        self._resize_job = None
        self._visual_job = None
        self._last_size = (0, 0)
        self._bg_photo = None
        self._closing = False
        self._first_job = None
        self._probe = {}
        self._dnd = None
        self._poll_job = None
        self._quiet_job = None
        self._quiet_pending = None
        self._quiet_wait = 0
        self._flash_id = None
        self._flash_job = None
        self._scroll = {}
        self._overflow = 0
        self._scroll_job = None
        self._settle_job = None
        self._bg_key = None

        root.title(APP_TITLE)
        # Scale the window with the monitor, but never past the desktop.
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        win_w = min(theme.px(1100), max(theme.px(900), sw - theme.px(40)))
        # 900 rather than 800: the settings page (appearance + update + data
        # cards) needs the extra room, otherwise it always relies on the
        # scroll fallback even on a large screen.
        win_h = min(theme.px(900), max(theme.px(640), sh - theme.px(90)))
        root.geometry("%dx%d+%d+%d" % (win_w, win_h,
                                       max(0, (sw - win_w) // 2),
                                       max(0, (sh - win_h) // 2)))
        root.minsize(min(theme.px(1020), win_w), min(theme.px(786), win_h))
        root.configure(bg=self.pal["window"])
        self._apply_window_icon()
        self._build_styles()
        self._build_shell()
        self._build_task_page()
        self._build_vault_page()
        self._build_settings_page()
        self._build_log()
        self._refresh_bg_panel()
        self._show_page("tasks")
        root.bind("<Configure>", self._on_configure)
        root.bind_all("<MouseWheel>", self._on_wheel, add="+")
        root.bind("<Destroy>", self._on_destroy, add="+")
        self._first_job = self.root.after(30, self._first_paint)
        self._init_backend()
        self._apply_update_state()
        self._apply_capture_guard()
        self._refresh_capture_button()
        self._auto_check = self.root.after(3000, self._auto_update_check)
        self.root.bind("<Destroy>", self._on_destroy, add="+")
        self._install_drop_target()
        self._start_poll()

    # -- window chrome -------------------------------------------------
    def _on_destroy(self, event=None):
        if event is not None and event.widget is not self.root:
            return
        self._closing = True
        for attr in ("_first_job", "_poll_job", "_poll_after", "_flash_job",
                     "_quiet_job", "_auto_check"):
            job = getattr(self, attr, None)
            setattr(self, attr, None)
            if job is not None:
                try:
                    self.root.after_cancel(job)
                except Exception:
                    pass
        target, self._dnd = getattr(self, "_dnd", None), None
        if target is not None:
            try:
                target.close()
            except Exception:
                pass

    def _apply_window_icon(self):
        candidates = []
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            candidates.append(os.path.join(meipass, "assets", "icon.png"))
        here = os.path.dirname(os.path.abspath(__file__))
        candidates.append(os.path.join(here, "..", "..", "docs", "icon.png"))
        candidates.append(os.path.join(here, "..", "assets", "icon.png"))
        for path in candidates:
            try:
                if path and os.path.isfile(path):
                    self._icon_photo = tk.PhotoImage(file=path)
                    self.root.iconphoto(True, self._icon_photo)
                    return
            except Exception:
                continue

    def _first_paint(self):
        self._first_job = None
        if self._closing:
            return
        self._last_size = (self.root.winfo_width(), self.root.winfo_height())
        self._relayout()
        self.refresh_visuals()

    # -- theme / privacy -----------------------------------------------
    def _apply_theme(self, value=None):
        """Switch light/dark in place: rebuild every widget from the new palette."""
        if value is not None:
            self.settings.set("theme", value)
            self.settings.save()
        self.pal = theme.palette(self.settings.get("theme"))
        self.backdrop = bgfx.Backdrop(self.pal)
        self.backdrop.configure(path=self.settings.get("bg_image"),
                                blur=self.settings.get("bg_blur"),
                                alpha=self.settings.get("bg_alpha"))
        history = ""
        text = getattr(self, "log_text", None)
        if text is not None:
            try:
                history = text.get("1.0", "end-1c")
            except tk.TclError:
                history = ""
        page = self.page
        for child in list(self.root.winfo_children()):
            child.destroy()
        self.cards = []
        self.pages = {}
        self.nav = {}
        self.stat_labels = {}
        self.data_rows = {}
        self._scroll = {}
        self._overflow = 0
        self.root.configure(bg=self.pal["window"])
        self._build_styles()
        self._build_shell()
        self._build_task_page()
        self._build_vault_page()
        self._build_settings_page()
        self._build_log()
        self._refresh_bg_panel()
        self._show_page(page if page in self.pages else "tasks")
        self._last_size = (self.root.winfo_width(), self.root.winfo_height())
        self._relayout()
        self.refresh_visuals()
        if history:
            self.log_text.configure(state="normal")
            self.log_text.insert("1.0", history)
            self.log_text.configure(state="disabled")
            self.log_empty.place_forget()
        if self.vault:
            self.refresh_vault()
        if self.devices:
            try:
                self._devices_done(self.devices)
            except Exception:
                pass
        self._apply_capture_guard()
        self._refresh_capture_button()

    def _on_theme_change(self, value):
        if value == self.settings.get("theme"):
            return
        self._apply_theme(value)
        self.log("设置", "主题已切到%s" % ("深色" if value == "dark" else "浅色"))

    def _apply_capture_guard(self):
        """Hide the window from screen capture (Windows 10 2004+)."""
        if not sys.platform.startswith("win"):
            return False
        enabled = bool(self.settings.get("capture_guard"))
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
            return bool(user32.SetWindowDisplayAffinity(hwnd, 0x11 if enabled else 0x0))
        except Exception:
            return False

    def _refresh_capture_button(self):
        button = getattr(self, "btn_capture", None)
        if button is None:
            return
        on = bool(self.settings.get("capture_guard"))
        button.set_text("已开启" if on else "开启")
        button.configure(state="disabled" if on and not sys.platform.startswith("win") else "normal")

    def toggle_capture_guard(self):
        on = bool(self.settings.get("capture_guard"))
        self.settings.set("capture_guard", not on)
        self.settings.save()
        applied = self._apply_capture_guard()
        if applied:
            self.log("设置", "防止截屏已%s（系统截图和录屏里这个窗口会是黑的）"
                     % ("关闭" if on else "开启"))
        else:
            self.log("提示", "这台系统不支持隐藏窗口捕获")
        self._refresh_capture_button()

    # -- ttk styling ---------------------------------------------------
    def _build_styles(self):
        pal = self.pal
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", font=theme.font(10), background=pal["card"],
                        foreground=pal["text"], borderwidth=0,
                        focuscolor=pal["card"])
        style.configure("Treeview", background=pal["card"], fieldbackground=pal["card"],
                        foreground=pal["text"], borderwidth=0, rowheight=theme.px(30),
                        font=theme.font(10))
        try:
            style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        except tk.TclError:
            pass
        style.configure("Treeview.Heading", background=pal["card_soft"],
                        foreground=pal["text_muted"], borderwidth=0, relief="flat",
                        anchor="w", font=theme.font(9, "bold"),
                        padding=(theme.px(10), theme.px(8)))
        style.map("Treeview.Heading", background=[("active", pal["head_hover"])])
        # clam draws headings through the base Heading style; align it there too
        # so the header text lines up with the (left aligned) cell text.
        try:
            style.configure("Heading", anchor="w", justify="left",
                            font=theme.font(9, "bold"), padding=(theme.px(10), theme.px(8)))
        except tk.TclError:
            pass
        style.map("Treeview",
                  background=[("selected", pal["accent_soft"])],
                  foreground=[("selected", pal["text"])])
        style.configure("Vertical.TScrollbar", gripcount=0, relief="flat",
                        background=pal["scroll_hover"], darkcolor=pal["card_soft"],
                        lightcolor=pal["card_soft"], troughcolor=pal["card_soft"],
                        bordercolor=pal["card_soft"], arrowcolor=pal["text_muted"],
                        arrowsize=theme.px(12), width=theme.px(11))
        style.map("Vertical.TScrollbar", background=[("active", pal["text_faint"])])
        style.configure("TCombobox", fieldbackground=pal["card_soft"],
                        background=pal["card_soft"], foreground=pal["text"],
                        arrowcolor=pal["text_muted"], bordercolor=pal["border"],
                        lightcolor=pal["border"], darkcolor=pal["border"],
                        padding=(theme.px(6), theme.px(4)))
        style.map("TCombobox",
                  fieldbackground=[("readonly", pal["card_soft"]),
                                    ("disabled", pal["card"])],
                  foreground=[("readonly", pal["text"]),
                              ("disabled", pal["text_faint"])],
                  selectbackground=[("readonly", pal["accent_soft"])],
                  selectforeground=[("readonly", pal["text"])])
        for option, value in (("background", pal["card"]),
                              ("foreground", pal["text"]),
                              ("selectBackground", pal["accent_soft"]),
                              ("selectForeground", pal["accent"]),
                              ("font", theme.font(10))):
            self.root.option_add("*TCombobox*Listbox." + option, value)

    # -- shell (wallpaper + rail) --------------------------------------
    def _build_shell(self):
        pal = self.pal
        self.canvas = tk.Canvas(self.root, bg=pal["window"], highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.bg_item = self.canvas.create_image(0, 0, anchor="nw")

        # A page taller than the window gets a slim scroll indicator; without
        # one the settings page just looked cut off at the bottom.
        self.page_scroll = tk.Canvas(self.canvas, width=theme.px(6), bg=pal["window"],
                                     highlightthickness=0, bd=0)
        self.page_scroll_thumb = self.page_scroll.create_rectangle(
            0, 0, 0, 0, fill=pal["text_faint"], outline="")
        self.page_scroll.bind("<Button-1>", self._on_scroll_drag)
        self.page_scroll.bind("<B1-Motion>", self._on_scroll_drag)
        self._scroll_geom = (1, 1)

        self.rail = tk.Frame(self.canvas, bg=pal["rail"], bd=0, highlightthickness=0)
        self.rail_line = tk.Frame(self.canvas, bg=pal["border"], bd=0, highlightthickness=0)

        brand = tk.Frame(self.rail, bg=pal["rail"])
        brand.pack(fill="x", padx=theme.px(14), pady=(theme.px(22), theme.px(18)))
        self._brand_icon(brand)
        text_box = tk.Frame(brand, bg=pal["rail"])
        text_box.pack(side="left", padx=(theme.px(10), theme.px(0)))
        self._brand_title = label(text_box, self, theme.APP_NAME, size=10, weight="bold",
                                  bg="rail")
        self._brand_title.pack(anchor="w")
        self._brand_sub = label(text_box, self, theme.APP_SUBTITLE, size=8,
                                color="text_muted", bg="rail")
        self._brand_sub.pack(anchor="w", pady=(theme.px(1), theme.px(0)))

        nav = tk.Frame(self.rail, bg=pal["rail"])
        nav.pack(fill="x", padx=theme.px(14))
        for key, text, glyph in (("tasks", "任务", "▣"),
                                 ("vault", "账号库", "☰"),
                                 ("settings", "设置", "⚙")):
            button = NavButton(self, nav, text, glyph, command=lambda k=key: self._show_page(k))
            button.pack(fill="x", pady=theme.px(3))
            self.nav[key] = button

        footer = tk.Frame(self.rail, bg=pal["rail"])
        footer.pack(side="bottom", fill="x", padx=theme.px(18), pady=theme.px(16))
        label(footer, self, "v" + theme.APP_VERSION, size=9, color="text_faint",
              bg="rail").pack(anchor="w")
        repo = tk.Label(footer, text="项目主页  ↗", font=theme.font(9),
                        fg=pal["accent"], bg=pal["rail"], bd=0, cursor="hand2")
        repo.pack(anchor="w", pady=(theme.px(2), theme.px(0)))
        repo.bind("<Button-1>", lambda e: self.open_repo())

    def _brand_icon(self, parent):
        pal = self.pal
        size = theme.px(38)
        box = tk.Canvas(parent, width=size, height=size, bg=pal["rail"],
                        highlightthickness=0, bd=0)
        box.pack(side="left")
        photo = None
        if bgfx.PIL_OK:
            try:
                from PIL import ImageTk
                photo = ImageTk.PhotoImage(bgfx.rounded_rgba(
                    size, size, theme.px(13), theme.hex_to_rgb(pal["accent"]) + (255,), scale=3))
            except Exception:
                photo = None
        if photo is not None:
            box.create_image(0, 0, anchor="nw", image=photo)
            box.image = photo
        else:
            box.configure(bg=pal["accent"])
        box.create_text(size // 2, size // 2 - 1, text="东", font=theme.font(15, "bold"),
                        fill=pal["on_accent"])
        return box

    # -- page: tasks ---------------------------------------------------
    def _build_task_page(self):
        pal = self.pal

        card = RoundCard(self)
        self._task_card = card
        body = card.body

        head = tk.Frame(body, bg=pal["card"])
        head.pack(fill="x")
        self.game_seg = Segmented(self, head, [(g.id, g.label) for g in game.GAMES],
                                  active=self.active_game.id, command=self.switch_game)
        self.game_seg.pack(side="left")
        self.adb_chip = label(head, self, "正在检测 adb…", size=9, color="text_muted")
        self.adb_chip.pack(side="right")

        self.reconcile_bar = tk.Frame(body, bg=pal["warn_soft"])
        inner = tk.Frame(self.reconcile_bar, bg=pal["warn_soft"])
        inner.pack(fill="x", padx=theme.px(12), pady=theme.px(8))
        self.reconcile_text = label(inner, self, "", size=9, color="warn", bg="warn_soft")
        self.reconcile_text.pack(side="left")
        PillButton(self, inner, "不用管", command=self.dismiss_reconcile, kind="ghost",
                   width=70, height=28, bg="warn_soft").pack(side="right")
        PillButton(self, inner, "存到账号库", command=self.save_reconcile_entry, kind="primary",
                   width=100, height=28).pack(side="right", padx=(theme.px(0), theme.px(8)))
        PillButton(self, inner, "更新已有账号", command=self.update_reconcile_entry, kind="soft",
                   width=106, height=28, bg="warn_soft").pack(side="right", padx=(theme.px(0), theme.px(8)))

        pick = tk.Frame(body, bg=pal["card"])
        pick.pack(fill="x", pady=(theme.px(18), theme.px(0)))
        label(pick, self, "设备", size=10, weight="bold").pack(
            side="left", padx=(theme.px(0), theme.px(10)))
        self.btn_refresh_device = PillButton(self, pick, "刷新", command=self.scan_emulators,
                                             kind="ghost", width=58, height=34)
        self.btn_refresh_device.pack(side="right")
        PillButton(self, pick, "连接设置", command=self.open_connect_settings, kind="ghost",
                   width=88, height=34).pack(side="right", padx=(theme.px(0), theme.px(8)))
        self.device_list = DeviceList(self, pick, command=self._on_device_row)
        self.tree_box = self.device_list
        self.device_list.pack(side="left", fill="x", expand=True)

        info = tk.Frame(body, bg=pal["card"])
        info.pack(fill="x", pady=(theme.px(8), theme.px(0)))
        self.dev_detail = label(info, self, "正在查找设备…", size=9, color="text_muted")
        self.dev_detail.pack(side="left")
        self.device_hint = label(info, self, "", size=9, color="text_faint")
        self.device_hint.pack(side="right")

        row = tk.Frame(body, bg=pal["card"])
        row.pack(fill="x", pady=(theme.px(18), theme.px(0)))
        self.btn_extract = PillButton(self, row, "提取 %s 的 key" % self.active_game.label,
                                      command=self.do_extract,
                                      kind="primary", width=196, height=44,
                                      autosize=True)
        self.btn_extract.pack(side="left")
        self.btn_import = PillButton(self, row, "导入到 %s" % self.active_game.label,
                                     command=self.do_import,
                                     kind="soft", width=180, height=44,
                                     autosize=True)
        self.btn_import.pack(side="left", padx=(theme.px(10), theme.px(0)))
        PillButton(self, row, "打开游戏", command=self.launch_game, kind="ghost",
                   width=104, height=44).pack(side="left", padx=(theme.px(10), theme.px(0)))

        save_row = tk.Frame(body, bg=pal["card"])
        save_row.pack(fill="x", pady=(theme.px(14), theme.px(0)))
        label(save_row, self, "保存文件夹", size=9, color="text_muted").pack(side="left")
        self.save_dir_var = tk.StringVar(value=self.save_dir or "未选择（提取后会自动导出到该文件夹）")
        # Buttons first: a packed fill+expand entry would otherwise eat the
        # whole row and squeeze them down to a sliver.
        PillButton(self, save_row, "打开", command=self.open_save_dir, kind="ghost",
                   width=62, height=32).pack(side="right")
        PillButton(self, save_row, "选择文件夹", command=self.choose_save_dir, kind="ghost",
                   width=98, height=32).pack(side="right", padx=(theme.px(0), theme.px(8)))
        self.save_entry = entry(save_row, self, self.save_dir_var, width=32)
        self.save_entry.configure(state="readonly", readonlybackground=pal["card_soft"])
        self.save_entry.pack(side="left", fill="x", expand=True,
                             padx=(theme.px(10), theme.px(10)), ipady=theme.px(5))

        stats = tk.Frame(body, bg=pal["card"])
        stats.pack(fill="x", pady=(theme.px(16), theme.px(0)))
        self.stat_labels = {}
        tiles = (("game_key", "游戏内 key"), ("last_import", "上次导入"),
                 ("accounts", "账号"), ("backups", "备份"))
        for index, (key, title) in enumerate(tiles):
            if index:
                label(stats, self, "·", size=9, color="text_faint").pack(
                    side="left", padx=theme.px(10))
            label(stats, self, title, size=9, color="text_muted").pack(side="left")
            value = label(stats, self, "—", size=10, weight="bold")
            value.pack(side="left", padx=(theme.px(6), theme.px(0)))
            self.stat_labels[key] = value

        hint = label(body, self, "换号：在账号库里选中要用的账号再点导入，导入前会自动备份当前 key",
                     size=9, color="text_faint")
        hint.pack(anchor="w", pady=(theme.px(10), theme.px(0)))

        recent = RoundCard(self)
        self._recent_card = recent
        rb = recent.body
        SectionTitle.build(self, rb, "最近导入", "换号记录，最多 5 条").pack(fill="x")
        self.recent_box = tk.Frame(rb, bg=pal["card"])
        self.recent_box.pack(fill="x", pady=(theme.px(10), theme.px(0)))
        self.recent_rows = []
        self.recent_empty = label(self.recent_box, self, "还没有导入记录", size=9,
                                  color="text_faint")
        self.recent_empty.pack(anchor="w")

        self.pages["tasks"] = [(card, self._task_card_height), (recent, None)]

    # -- page: vault ---------------------------------------------------
    def _build_vault_page(self):
        pal = self.pal
        card = RoundCard(self)
        body = card.body
        self.vault_toolbars = []
        SectionTitle.build(self, body, "账号库",
                           "选中后可以导入、复制或导出 · F2 直接改名").pack(fill="x")

        # Row 1: kind switch, count and the search box each get their own
        # space, so the search field is never squeezed to nothing.
        head = tk.Frame(body, bg=pal["card"])
        head.pack(fill="x", pady=(theme.px(12), theme.px(0)))
        self.kind_seg = Segmented(self, head, [("account", "账号"), ("backup", "备份")],
                                  active=self.vault_kind, command=self.switch_vault_kind)
        self.kind_seg.pack(side="left")
        self.count_chip = chip(head, self, "0 个账号", tone="muted")
        self.count_chip.pack(side="left", padx=(theme.px(10), theme.px(0)))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh_vault())
        self.vault_search = entry(head, self, self.search_var, width=20)
        self.vault_search.pack(side="right", ipady=theme.px(4))
        label(head, self, "搜索", size=9, color="text_muted").pack(
            side="right", padx=(theme.px(0), theme.px(8)))
        self.vault_toolbars.append(head)

        bulk_bar = tk.Frame(body, bg=pal["card"])
        bulk_bar.pack(fill="x", pady=(theme.px(10), theme.px(0)))
        for text, command in (("批量导入文件夹", self.import_folder),
                              ("从剪贴板导入", self.import_clipboard),
                              ("打包导出全部", self.export_bundle),
                              ("局域网传输", self.open_lan_share)):
            PillButton(self, bulk_bar, text, command=command, kind="ghost",
                       width=34, height=32).pack(side="left", padx=(theme.px(0), theme.px(6)))
        self.vault_toolbars.append(bulk_bar)

        keep_bar = tk.Frame(body, bg=pal["card"])
        keep_bar.pack(fill="x", pady=(theme.px(8), theme.px(0)))
        label(keep_bar, self, "备份保留", size=9, color="text_muted").pack(side="left")
        self.backup_seg = Segmented(
            self, keep_bar, [("all", "全部"), ("10", "最近 10 份"), ("30d", "最近 30 天")],
            active=self.settings.get("backup_keep"), command=self._on_backup_keep,
            pad_x=theme.px(10))
        self.backup_seg.pack(side="left", padx=(theme.px(8), theme.px(0)))
        self.vault_history_label = label(keep_bar, self, "还没有导入记录", size=9,
                                         color="text_muted")
        self.vault_history_label.pack(side="left", padx=(theme.px(14), theme.px(0)))
        self.btn_undo_import = PillButton(self, keep_bar, "撤销上次导入",
                                          command=self.undo_last_import, kind="ghost",
                                          width=34, height=28)
        self.btn_undo_import.pack(side="right")
        self.vault_toolbars.append(keep_bar)

        tree_box = tk.Frame(body, bg=pal["card"])
        tree_box.pack(fill="both", expand=True, pady=(theme.px(12), theme.px(0)))
        vcols = ("name", "note", "fingerprint", "source", "created")
        self.vault_tree = ttk.Treeview(tree_box, columns=vcols, show="headings", height=8)
        titles = (("name", "名称", 140), ("note", "备注", 100), ("fingerprint", "Key 指纹", 138),
                  ("source", "来源", 170), ("created", "添加时间", 132))
        for col, title, width in titles:
            self.vault_tree.heading(col, text=title, anchor="w")
            self.vault_tree.column(col, width=theme.px(width), anchor="w", stretch=(col == "source"))
        self.vault_tree.pack(side="left", fill="both", expand=True)
        vsb = ttk.Scrollbar(tree_box, orient="vertical", command=self.vault_tree.yview)
        vsb.pack(side="right", fill="y", padx=(theme.px(6), theme.px(0)))
        self.vault_tree.configure(yscrollcommand=vsb.set)
        self.vault_tree.tag_configure("odd", background=pal["card_sunken"])
        self.vault_tree.tag_configure("flash", background=pal["accent_soft"],
                                      foreground=pal["accent"])
        self.vault_tree.bind("<Double-1>", lambda e: self.show_key())
        self.vault_tree.bind("<F2>", self._on_vault_f2)
        self.vault_tree.bind("<<TreeviewSelect>>", lambda e: self._update_vault_actions())

        divider = tk.Frame(body, bg=pal["border_soft"], height=theme.px(1))
        divider.pack(fill="x", pady=(theme.px(14), theme.px(12)))

        # Two action rows: eight buttons on one line never fit 774px and the
        # captions used to be clipped into each other.
        toolbar = tk.Frame(body, bg=pal["card"])
        toolbar.pack(fill="x")
        self.btn_rename = PillButton(self, toolbar, "重命名", command=self.rename_entry,
                                     kind="ghost", width=78, height=34)
        self.btn_rename.pack(side="left", padx=(theme.px(0), theme.px(6)))
        self.btn_note = PillButton(self, toolbar, "编辑备注", command=self.edit_note,
                                   kind="ghost", width=78, height=34)
        self.btn_note.pack(side="left", padx=(theme.px(0), theme.px(6)))
        for text, command in (("复制 Key", self.copy_key), ("显示 Key", self.show_key)):
            PillButton(self, toolbar, text, command=command, kind="ghost",
                       width=78, height=34).pack(side="left", padx=(theme.px(0), theme.px(6)))
        PillButton(self, toolbar, "删除", command=self.delete_entry, kind="danger",
                   width=70, height=34).pack(side="right")
        self.vault_toolbars.append(toolbar)

        toolbar2 = tk.Frame(body, bg=pal["card"])
        toolbar2.pack(fill="x", pady=(theme.px(6), theme.px(0)))
        for text, command in (("生成二维码", self.show_qr),
                              ("存到文件夹", self.export_selected_to_dir),
                              ("导出 .hak", self.export_hak),
                              ("导入 .hak", self.import_hak)):
            PillButton(self, toolbar2, text, command=command, kind="ghost",
                       width=78, height=34).pack(side="left", padx=(theme.px(0), theme.px(6)))
        self.vault_toolbars.append(toolbar2)

        self.pages["vault"] = [(card, None)]

    # -- page: settings ------------------------------------------------
    def _build_settings_page(self):
        pal = self.pal

        conn_card = RoundCard(self)
        cb = conn_card.body
        SectionTitle.build(self, cb, "连接", "选模拟器或填地址，任务页用这里连上的设备").pack(fill="x")

        line = tk.Frame(cb, bg=pal["card"])
        line.pack(fill="x", pady=(theme.px(14), theme.px(0)))
        label(line, self, "连接配置", size=10, weight="bold").pack(
            side="left", padx=(theme.px(0), theme.px(10)))
        self.connect_profile = ttk.Combobox(
            line, state="readonly", font=theme.font(10), width=20,
            values=[text for _key, text, _addr in CONNECT_PROFILES])
        saved = self.settings.get("connect_profile") or "auto"
        self.connect_profile.current(next(
            (i for i, (key, _t, _a) in enumerate(CONNECT_PROFILES) if key == saved), 0))
        self.connect_profile.pack(side="left")
        self.connect_profile.bind("<<ComboboxSelected>>", self._on_connect_profile)
        self.btn_rescan = PillButton(self, line, "重新扫描", command=self.scan_emulators,
                                     kind="ghost", width=92, height=32)
        self.btn_rescan.pack(side="right")

        addr = tk.Frame(cb, bg=pal["card"])
        addr.pack(fill="x", pady=(theme.px(10), theme.px(0)))
        label(addr, self, "连接地址", size=10, weight="bold").pack(
            side="left", padx=(theme.px(0), theme.px(10)))
        self.btn_get_device = PillButton(self, addr, "获取设备", command=self.connect_address,
                                        kind="soft", width=96, height=32)
        self.btn_get_device.pack(side="right")
        self.addr_var = tk.StringVar()
        self.addr_entry = entry(addr, self, self.addr_var, width=20)
        self.addr_entry.pack(side="left", fill="x", expand=True,
                             padx=(theme.px(0), theme.px(8)), ipady=theme.px(4))
        self.addr_entry.bind("<Return>", lambda _e: self.connect_address())
        label(cb, self, "多开时端口不同：填 127.0.0.1:端口，也可以只填端口", size=9,
              color="text_faint").pack(anchor="w", pady=(theme.px(6), theme.px(0)))

        line = tk.Frame(cb, bg=pal["card"])
        line.pack(fill="x", pady=(theme.px(12), theme.px(0)))
        label(line, self, "只显示模拟器", size=10, weight="bold").pack(side="left")
        self.only_emu_seg = Segmented(
            self, line, [("off", "关"), ("on", "开")],
            active="on" if self.settings.get("only_emulators") else "off",
            command=self._on_only_emulators, pad_x=theme.px(12))
        self.only_emu_seg.pack(side="right")

        line = tk.Frame(cb, bg=pal["card"])
        line.pack(fill="x", pady=(theme.px(8), theme.px(0)))
        label(line, self, "启动时自动连接", size=10, weight="bold").pack(side="left")
        self.auto_connect_seg = Segmented(
            self, line, [("off", "关"), ("on", "开")],
            active="on" if self.settings.get("auto_connect") else "off",
            command=self._on_auto_connect, pad_x=theme.px(12))
        self.auto_connect_seg.pack(side="right")

        line = tk.Frame(cb, bg=pal["card"])
        line.pack(fill="x", pady=(theme.px(12), theme.px(0)))
        label(line, self, "扫描端口", size=10, weight="bold").pack(side="left")
        self.btn_edit_ports = PillButton(self, line, "编辑", command=self.edit_scan_ports,
                                         kind="ghost", width=62, height=28)
        self.btn_edit_ports.pack(side="right")
        # A 14-port list never fits one line; show a short summary instead and
        # edit the whole list in the themed dialog.
        self.ports_var = tk.StringVar(value=self.settings.get("emulator_ports") or "")
        self.ports_summary = label(line, self, "", size=9, color="text_muted")
        self.ports_summary.pack(side="left", padx=(theme.px(10), theme.px(10)),
                                fill="x", expand=True)
        self._update_ports_summary()

        line = tk.Frame(cb, bg=pal["card"])
        line.pack(fill="x", pady=(theme.px(12), theme.px(0)))
        label(line, self, "记住的设备", size=10, weight="bold").pack(side="left")
        self.conn_device_label = label(line, self, "-", size=9, color="text_muted")
        self.conn_device_label.pack(side="left", padx=(theme.px(10), theme.px(0)))
        PillButton(self, line, "清除", command=self.forget_device, kind="ghost",
                   width=70, height=28).pack(side="right")

        card = RoundCard(self)
        body = card.body
        SectionTitle.build(self, body, "外观 · 背景图",
                           "上传一张图片做窗口背景，模糊和不透明度可以实时调").pack(fill="x")

        row = tk.Frame(body, bg=pal["card"])
        row.pack(fill="x", pady=(theme.px(14), theme.px(0)))
        self.thumb_holder = tk.Frame(row, bg=pal["card_soft"], width=theme.px(132),
                                     height=theme.px(74),
                                     highlightthickness=1, highlightbackground=pal["border"])
        self.thumb_holder.pack(side="left")
        self.thumb_holder.pack_propagate(False)
        self.thumb_label = tk.Label(self.thumb_holder, bg=pal["card_soft"], bd=0,
                                    fg=pal["text_faint"], font=theme.font(9),
                                    text="无背景图")
        self.thumb_label.pack(fill="both", expand=True)

        info = tk.Frame(row, bg=pal["card"])
        info.pack(side="left", fill="x", expand=True, padx=(theme.px(18), theme.px(0)))
        self.bg_name_label = label(info, self, "还没有选择背景图", size=10, weight="bold")
        self.bg_name_label.pack(anchor="w")
        self.bg_note_label = label(info, self, "支持 png / jpg / bmp / webp，选择后会复制一份到应用数据目录",
                                   size=9, color="text_muted")
        self.bg_note_label.pack(anchor="w", pady=(theme.px(4), theme.px(0)))
        btn_row = tk.Frame(info, bg=pal["card"])
        btn_row.pack(anchor="w", pady=(theme.px(10), theme.px(0)))
        PillButton(self, btn_row, "选择图片", command=self.choose_background, kind="primary",
                   width=112, height=36).pack(side="left")
        PillButton(self, btn_row, "清除", command=self.clear_background, kind="ghost",
                   width=78, height=36).pack(side="left", padx=(theme.px(8), theme.px(0)))

        self.blur_value = tk.IntVar(value=int(self.settings.get("bg_blur")))
        self.blur_slider, self.blur_readout = self._slider_block(
            body, "模糊", "数值越大背景越虚化", self.blur_value.get(), 0, 60,
            self._on_blur_change, " px")

        self.alpha_value = tk.IntVar(value=int(self.settings.get("bg_alpha")))
        self.alpha_slider, self.alpha_readout = self._slider_block(
            body, "不透明度", "越低背景越接近纯色，文字更好读", self.alpha_value.get(), 0, 100,
            self._on_alpha_change, " %")

        pref = tk.Frame(body, bg=pal["card"])
        pref.pack(fill="x", pady=(theme.px(10), theme.px(10)))
        label(pref, self, "主题", size=9, color="text_muted").pack(side="left")
        self.theme_seg = Segmented(
            self, pref, [("light", "浅色"), ("dark", "深色")],
            active=self.settings.get("theme"), command=self._on_theme_change,
            pad_x=theme.px(10))
        self.theme_seg.pack(side="left", padx=(theme.px(8), theme.px(18)))
        self.btn_capture = PillButton(self, pref, "开启", command=self.toggle_capture_guard,
                                      kind="ghost", width=76, height=28)
        self.btn_capture.pack(side="right")
        label(pref, self, "防止截屏", size=9, color="text_muted").pack(
            side="right", padx=(theme.px(0), theme.px(8)))
        label(pref, self, "系统截图 / 录屏里这个窗口会变黑", size=9, color="text_faint").pack(
            side="right", padx=(theme.px(14), theme.px(10)))

        bottom = tk.Frame(body, bg=pal["card"])
        bottom.pack(fill="x", side="bottom", pady=(theme.px(4), theme.px(0)))
        PillButton(self, bottom, "恢复默认外观", command=self.reset_appearance, kind="ghost",
                   width=132, height=32).pack(side="left")
        label(bottom, self, "背景图会复制一份到应用数据目录，移动原图不影响显示",
              size=9, color="text_faint").pack(side="left", padx=(theme.px(12), theme.px(0)))

        update_card = RoundCard(self)
        ub = update_card.body
        SectionTitle.build(self, ub, "更新", "启动时自动检查，发现新版本会弹窗提示").pack(fill="x")
        row = tk.Frame(ub, bg=pal["card"])
        row.pack(fill="x", pady=(theme.px(12), theme.px(0)))
        self.update_version_label = label(row, self, "当前版本 v" + theme.APP_VERSION,
                                          size=10, weight="bold")
        self.update_version_label.pack(side="left")
        label(row, self, "更新源", size=9, color="text_muted").pack(
            side="left", padx=(theme.px(18), theme.px(6)))
        self.update_source_seg = Segmented(
            self, row, [("auto", "自动"), ("github", "GitHub"), ("mirror", "镜像")],
            active=self.settings.get("update_source"), command=self._on_update_source,
            pad_x=theme.px(10))
        self.update_source_seg.pack(side="left")
        self.btn_check_update = PillButton(self, row, "检查更新",
                                           command=lambda: self.check_update(True),
                                           kind="ghost", width=104, height=32)
        self.btn_check_update.pack(side="right")

        status_row = tk.Frame(ub, bg=pal["card"])
        status_row.pack(fill="x", pady=(theme.px(10), theme.px(0)))
        self.update_status = label(status_row, self, "启动时会自动检查一次", size=9,
                                   color="text_muted")
        self.update_status.pack(side="left")
        self.btn_view_log = PillButton(self, status_row, "查看日志", command=self.open_update_log,
                                       kind="ghost", width=88, height=30)
        self.btn_view_log.pack_forget()
        self.btn_install_update = PillButton(self, status_row, "立即更新",
                                             command=self.do_update, kind="primary",
                                             width=104, height=30)
        self.btn_install_update.pack_forget()

        data_card = RoundCard(self)
        db = data_card.body
        SectionTitle.build(self, db, "数据与存储", "全部读写都在本机完成，不上传任何数据").pack(fill="x")
        self.data_rows = {}
        for key, title in (("data_dir", "应用数据目录"), ("vault", "当前游戏库"),
                           ("save_dir", "保存位置"), ("adb", "adb 组件")):
            line = tk.Frame(db, bg=pal["card"])
            line.pack(fill="x", pady=(theme.px(7), theme.px(0)))
            label(line, self, title, size=9, color="text_muted", width=10,
                  anchor="w").pack(side="left")
            value = label(line, self, "-", size=9, color="text")
            value.pack(side="left", padx=(theme.px(6), theme.px(0)))
            self.data_rows[key] = value
        label(db, self, "「保存位置」既是提取时的导出目录，也是「打包导出全部」的 zip 落点"
                        "（每个游戏一个子文件夹）",
              size=9, color="text_faint", wraplength=theme.px(520)).pack(
            anchor="w", fill="x", pady=(theme.px(6), theme.px(0)))
        about_line = tk.Frame(db, bg=pal["card"])
        about_line.pack(fill="x", pady=(theme.px(7), theme.px(0)))
        label(about_line, self, "关于", size=9, color="text_muted", width=10,
              anchor="w").pack(side="left")
        self.about_version_label = label(about_line, self, "版本 v" + theme.APP_VERSION,
                                        size=9, color="text")
        self.about_version_label.pack(side="left", padx=(theme.px(6), theme.px(0)))
        PillButton(self, about_line, "项目主页",
                   command=lambda: self.open_url(theme.REPO_URL), kind="ghost",
                   width=88, height=26).pack(side="right")

        lock_line = tk.Frame(db, bg=pal["card"])
        lock_line.pack(fill="x", pady=(theme.px(7), theme.px(0)))
        label(lock_line, self, "应用锁", size=9, color="text_muted", width=10,
              anchor="w").pack(side="left")
        self.lock_value = label(lock_line, self, "未开启", size=9, color="text")
        self.lock_value.pack(side="left", padx=(theme.px(6), theme.px(0)))
        self.btn_lock = PillButton(self, lock_line, "开启", command=self.toggle_app_lock,
                                   kind="ghost", width=76, height=26)
        self.btn_lock.pack(side="right")

        data_actions = tk.Frame(db, bg=pal["card"])
        data_actions.pack(fill="x", pady=(theme.px(10), theme.px(0)))
        PillButton(self, data_actions, "打开数据目录", command=self.open_data_dir, kind="ghost",
                   width=118, height=32).pack(side="left")
        PillButton(self, data_actions, "复制路径", command=self.copy_data_dir, kind="ghost",
                   width=88, height=32).pack(side="left", padx=(theme.px(8), theme.px(0)))

        self.pages["settings"] = [(conn_card, max(theme.px(252), conn_card.required_height())),
                                  (card, max(theme.px(356), card.required_height())),
                                  (update_card,
                                   max(theme.px(150), update_card.required_height())),
                                  (data_card, None)]

    def _slider_block(self, parent, title, hint, value, from_, to, callback, unit):
        pal = self.pal
        block = tk.Frame(parent, bg=pal["card"])
        block.pack(fill="x", pady=(theme.px(12), theme.px(0)))
        top = tk.Frame(block, bg=pal["card"])
        top.pack(fill="x")
        label(top, self, title, size=10, weight="bold").pack(side="left")
        label(top, self, hint, size=9, color="text_muted").pack(side="left", padx=(theme.px(10), theme.px(0)))
        readout = label(top, self, "%d%s" % (int(value), unit), size=10, weight="bold",
                        color="accent")
        readout.pack(side="right")
        slider = MiniSlider(self, block, value=value, from_=from_, to=to,
                            on_change=callback, width=300, height=26)
        slider.pack(fill="x", pady=(theme.px(8), theme.px(0)))
        return slider, readout

    # -- page: log -----------------------------------------------------
    def _build_log(self):
        pal = self.pal
        card = RoundCard(self, fill="log_bg")
        body = card.body
        head = tk.Frame(body, bg=pal["log_bg"])
        head.pack(fill="x")
        label(head, self, "运行日志", size=11, weight="bold", color="log_fg",
              bg="log_bg").pack(side="left")
        label(head, self, "出问题先看这里", size=9, color="log_dim",
              bg="log_bg").pack(side="left", padx=(theme.px(10), theme.px(0)))
        PillButton(self, head, "清空", command=self.clear_log, kind="ghost",
                   width=66, height=28, bg="log_bg").pack(side="right")

        box = tk.Frame(body, bg=pal["log_bg"])
        box.pack(fill="both", expand=True, pady=(theme.px(10), theme.px(0)))
        self.log_text = tk.Text(box, height=6, wrap="word", bd=0, highlightthickness=0,
                                font=theme.mono(9), bg=pal["log_bg"], fg=pal["log_fg"],
                                insertbackground=pal["log_fg"], padx=theme.px(2), pady=theme.px(2))
        self.log_text.pack(side="left", fill="both", expand=True)
        # 深色卡片上系统滚动条是浅色的一整条，很扎眼；改为纯滚轮滚动
        self.log_text.configure(state="disabled")
        self.log_empty = tk.Label(box, text="操作记录会显示在这里，出问题时先看这里", bd=0,
                                  bg=pal["log_bg"], fg=pal["log_dim"], font=theme.font(9))
        self.log_empty.place(relx=0.5, rely=0.45, anchor="center")
        self.log_text.tag_configure("time", foreground=pal["log_dim"])
        self.log_text.tag_configure("ok", foreground=pal["log_ok"])
        self.log_text.tag_configure("err", foreground=pal["log_err"])
        self.log_text.tag_configure("hint", foreground=pal["log_hint"])
        self.log_card = card

    # -- layout --------------------------------------------------------
    @staticmethod
    def _spec_height(spec):
        """Page specs may carry a fixed height or a callable that measures it."""
        return spec() if callable(spec) else spec

    def _task_card_height(self):
        card = getattr(self, "_task_card", None)
        if card is None:
            return theme.px(320)
        return max(theme.px(300), card.required_height())

    def _relayout(self):
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if width <= 1 or height <= 1:
            return
        rail_w = theme.px(RAIL_W)
        page_pad = theme.px(PAGE_PAD)
        gap = theme.px(GAP)
        specs = self.pages.get(self.page, ())
        fixed = sum(self._spec_height(h) for _, h in specs if h)
        fills = [card for card, h in specs if not h]
        need = 0
        for card in fills:
            card.body.update_idletasks()
            need += card.body.winfo_reqheight() + 2 * (card.margin + card.pad)
        wanted = fixed + need + gap * max(0, len(specs) - 1)
        log_h = theme.px(LOG_H)
        # A window squashed below the authored minimum starves the page: first
        # give the log panel the space back, then drop it, then scroll.
        top_area = height - 2 * page_pad - gap - log_h
        log_visible = True
        if top_area < wanted:
            log_h = max(theme.px(96), log_h - (wanted - top_area))
            top_area = height - 2 * page_pad - gap - log_h
        if top_area < wanted:
            log_visible = False
            log_h = 0
            top_area = height - 2 * page_pad
        overflow = max(0, wanted - top_area)
        offset = self._scroll.get(self.page, 0)
        offset = max(0, min(offset, overflow))
        self._scroll[self.page] = offset
        self._overflow = overflow
        log_y = height - page_pad - log_h
        if not log_visible:
            self.log_card.place_forget()

        self._place_page_scrollbar(width, page_pad, top_area, overflow, offset, log_h, log_visible)
        self.rail.place(x=0, y=0, width=rail_w, relheight=1)
        self.rail_line.place(x=rail_w - 1, y=0, width=theme.px(1), relheight=1)
        x0 = rail_w + page_pad
        content_w = max(theme.px(360), width - rail_w - 2 * page_pad)
        if log_visible:
            self.log_card.layout(x0, log_y, content_w, log_h)

        for key, page_specs in self.pages.items():
            if key != self.page:
                for card, _ in page_specs:
                    card.place_forget()
                continue
            spare = top_area - fixed - gap * max(0, len(page_specs) - 1)
            fill_count = len(fills) or 1
            if fills:
                # When everything fits, fills share the slack; when the page is
                # taller than the window, give each fill its natural height and
                # let the page scroll instead of squashing them.
                fill_h = max(int(spare / fill_count), int(need / fill_count))
            else:
                fill_h = 0
            y = page_pad - offset
            for card, h in page_specs:
                card_h = self._spec_height(h) or fill_h
                card.layout(x0, y, content_w, card_h)
                y += card_h + gap

    def _place_page_scrollbar(self, width, page_pad, top_area, overflow, offset,
                              log_h, log_visible):
        if overflow <= 0 or top_area <= theme.px(80):
            self.page_scroll.place_forget()
            return
        track_h = top_area
        bar_w = theme.px(6)
        thumb_h = max(theme.px(36), int(round(track_h * track_h / float(track_h + overflow))))
        span = max(1, track_h - thumb_h)
        thumb_y = int(round(span * offset / float(overflow)))
        self._scroll_geom = (track_h, thumb_h)
        self.page_scroll.coords(self.page_scroll_thumb, 0, thumb_y, bar_w, thumb_y + thumb_h)
        self.page_scroll.place(x=width - page_pad - bar_w, y=page_pad,
                               width=bar_w, height=track_h)

    def _on_scroll_drag(self, event):
        if self._overflow <= 0:
            return
        track_h, thumb_h = self._scroll_geom
        span = max(1, track_h - thumb_h)
        ratio = max(0.0, min(1.0, (event.y - thumb_h / 2.0) / span))
        self._scroll[self.page] = int(round(ratio * self._overflow))
        self._queue_relayout()

    def _queue_relayout(self):
        """Coalesce a burst of wheel events into one layout pass.

        A wheel event used to run the whole relayout synchronously, so a
        fast wheel queued them faster than they could finish, which is what
        made scrolling look frozen and then jump.
        """
        if self._scroll_job:
            return
        self._scroll_job = self.root.after(12, self._flush_scroll)

    def _flush_scroll(self):
        self._scroll_job = None
        self._relayout()
        if self._settle_job:
            try:
                self.root.after_cancel(self._settle_job)
            except Exception:
                pass
        self._settle_job = self.root.after(140, self._settle_scroll)

    def _settle_scroll(self):
        """Repaint the wallpaper crop under every card once the wheel stops."""
        self._settle_job = None
        for card in self.cards:
            if card.winfo_manager():
                card.render(force=True)

    def refresh_visuals(self):
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if width <= 1 or height <= 1:
            return
        if bgfx.PIL_OK:
            # The wallpaper photo is a full-window Tk image; rebuilding it on
            # every relayout costs about as much as a card. Only a size,
            # wallpaper or palette change needs a fresh one.
            key = (width, height, getattr(self.backdrop, "rev", 0), id(self.pal))
            if key != self._bg_key:
                try:
                    self._bg_photo = bgfx.ImageTk.PhotoImage(self.backdrop.full(width, height))
                    self.canvas.itemconfigure(self.bg_item, image=self._bg_photo)
                    self._bg_key = key
                except Exception:
                    pass
        else:
            self.canvas.configure(bg=self.pal["window"])
        for card in self.cards:
            if card is self.log_card or card.winfo_manager():
                card.render()

    def _on_wheel(self, event):
        """Scroll the page only when it is taller than the window."""
        if self._overflow <= 0:
            return None
        widget = event.widget
        if widget is self.log_text or getattr(widget, "winfo_class", lambda: "")() == "Text":
            return None
        step = max(1, int(theme.px(56)))
        delta = -1 if getattr(event, "delta", 0) > 0 else 1
        offset = self._scroll.get(self.page, 0) + delta * step
        self._scroll[self.page] = max(0, min(offset, self._overflow))
        self._queue_relayout()
        return "break"

    def _on_configure(self, event):
        if event.widget is not self.root:
            return
        size = (event.width, event.height)
        if size == self._last_size:
            return
        self._last_size = size
        if self._resize_job:
            try:
                self.root.after_cancel(self._resize_job)
            except Exception:
                pass
        self._resize_job = self.root.after(60, self._apply_layout)

    def _apply_layout(self):
        self._resize_job = None
        self._relayout()
        self.refresh_visuals()

    def _show_page(self, key):
        self.page = key
        self._scroll[key] = 0
        for name, button in self.nav.items():
            button.set_active(name == key)
        if key == "settings":
            self._refresh_data_card()
        elif key == "tasks":
            self.refresh_overview()
        self._relayout()
        self.refresh_visuals()

    def open_connect_settings(self):
        """Jump from the task page to the connection card in Settings."""
        self._show_page("settings")

    def open_repo(self):
        try:
            webbrowser.open(theme.REPO_URL)
        except Exception as exc:
            self.log("提示", "打开仓库失败：%s" % exc)

    # -- backend bootstrap --------------------------------------------
    def _init_backend(self):
        if os.environ.get("HOUSAMO_NO_ADB") == "1":
            self.adb = None
            self._set_adb_chip("测试模式", "muted")
        else:
            try:
                self.adb = adb_mod.Adb()
                self.adb.ensure_server()
                self._set_adb_chip("adb 就绪", "ok")
            except Exception as exc:
                self.adb = None
                self._set_adb_chip("adb 不可用", "err")
                self.log("错误", str(exc))
        vault_mod.migrate_legacy_vault()
        for g in game.GAMES:
            try:
                self.vaults[g.id] = vault_mod.Vault(game_id=g.id)
            except Exception as exc:
                self.log("错误", "账号库加载失败（%s）：%s" % (g.label, exc))
        self.vault = self.vaults.get(self.active_game.id)
        self.refresh_vault()
        self._refresh_conn_card()
        if self.adb:
            if self.settings.get("auto_connect"):
                self.scan_emulators()
            else:
                self.refresh_devices()

    def _set_adb_chip(self, text, tone):
        tones = {"ok": "ok", "err": "err", "warn": "warn"}
        try:
            self.adb_chip.configure(text=text, fg=self.pal[tones.get(tone, "text_muted")])
        except Exception:
            pass

    # -- settings / folder export --------------------------------------
    def _save_settings(self):
        self.settings.set("save_dir", self.save_dir)
        self.settings.save()

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
        """Write <保存文件夹>/<游戏>/<名字>/AuthKey.txt; returns path or None."""
        if not self.save_dir:
            return None
        folder = os.path.join(self.save_dir, self._safe_name(self.active_game.label),
                              self._safe_name(name))
        try:
            os.makedirs(folder, exist_ok=True)
            target = os.path.join(folder, "AuthKey.txt")
            with open(target, "wb") as fh:
                fh.write(bytes(key))
            return target
        except Exception as exc:
            self.log("导出", "写入失败：%s" % exc)
            return None

    # -- background image settings -------------------------------------
    def choose_background(self):
        path = filedialog.askopenfilename(
            parent=self.root, title="选择背景图片",
            filetypes=[("图片", "*.png *.jpg *.jpeg *.bmp *.webp *.gif"),
                       ("所有文件", "*.*")])
        if not path:
            return
        try:
            stored = config.store_background(path)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, "无法使用这张图片：%s" % exc)
            return
        self.settings.set("bg_image", stored)
        self.backdrop.configure(path=stored)
        self._refresh_bg_panel()
        self.refresh_visuals()
        self.log("设置", "背景图已更新：%s" % os.path.basename(path))

    def clear_background(self):
        if not self.settings.get("bg_image"):
            return
        config.clear_background()
        self.settings.set("bg_image", "")
        self.backdrop.configure(path="")
        self._refresh_bg_panel()
        self.refresh_visuals()
        self.log("设置", "已清除背景图")

    def _on_blur_change(self, value):
        value = int(round(value))
        self.blur_value.set(value)
        self.blur_readout.configure(text="%d px" % value)
        self.settings.set("bg_blur", value, save=False)
        self.backdrop.configure(blur=value)
        self._schedule_visual_refresh()

    def _on_alpha_change(self, value):
        value = int(round(value))
        self.alpha_value.set(value)
        self.alpha_readout.configure(text="%d %%" % value)
        self.settings.set("bg_alpha", value, save=False)
        self.backdrop.configure(alpha=value)
        self._schedule_visual_refresh()

    def _schedule_visual_refresh(self):
        if self._visual_job:
            try:
                self.root.after_cancel(self._visual_job)
            except Exception:
                pass
        self._visual_job = self.root.after(70, self._flush_visual)

    def _flush_visual(self):
        self._visual_job = None
        self.refresh_visuals()
        self.settings.save()

    def reset_appearance(self):
        self.settings.set("bg_blur", config.DEFAULTS["bg_blur"], save=False)
        self.settings.set("bg_alpha", config.DEFAULTS["bg_alpha"], save=False)
        self.backdrop.configure(blur=config.DEFAULTS["bg_blur"],
                               alpha=config.DEFAULTS["bg_alpha"])
        self.blur_slider.set(config.DEFAULTS["bg_blur"])
        self.alpha_slider.set(config.DEFAULTS["bg_alpha"])
        self.blur_readout.configure(text="%d px" % config.DEFAULTS["bg_blur"])
        self.alpha_readout.configure(text="%d %%" % config.DEFAULTS["bg_alpha"])
        self.settings.save()
        self.refresh_visuals()
        self.log("设置", "外观已恢复默认")

    # -- updater -------------------------------------------------------
    def _on_update_source(self, value):
        self.settings.set("update_source", value)
        self.update_source_seg.set_active(value)
        self.log("更新", "更新源：%s"
                 % {"auto": "自动", "github": "GitHub", "mirror": "镜像"}.get(value, value))

    def check_update(self, manual=False):
        self.update_asset = None
        self.update_release = None
        try:
            self.btn_install_update.pack_forget()
            self.btn_view_log.pack_forget()
            self.btn_check_update.set_enabled(False)
            self.update_status.configure(text="正在检查…", fg=self.pal["text_muted"])
        except Exception:
            pass

        def worker():
            try:
                return updater.fetch_latest()
            except Exception as exc:
                return exc

        def done(result):
            try:
                self.btn_check_update.set_enabled(True)
            except Exception:
                pass
            self.settings.set("last_update_check", int(time.time()))
            if isinstance(result, Exception):
                reason = self._update_error_text(result)
                if manual:
                    self.update_status.configure(text="检查失败：%s" % reason, fg=self.pal["err"])
                    messagebox.showwarning(APP_TITLE,
                                           "检查更新失败：%s\n\n也可以直接去项目主页下载新版。"
                                           % reason)
                else:
                    # A background check that cannot reach GitHub is not an
                    # error the user needs to fix; keep it quiet.
                    self.update_status.configure(text="暂时查不到更新（可点「检查更新」再试）",
                                                 fg=self.pal["text_muted"])
                return
            if not result:
                self.update_status.configure(text="暂时查不到 Windows 版（可点「检查更新」再试）",
                                             fg=self.pal["text_muted"])
                return
            tag = result.get("tag_name") or ""
            if not updater.is_newer(tag, theme.APP_VERSION):
                self.update_status.configure(text="已是最新版本（%s）" % (tag or "?"),
                                             fg=self.pal["ok"])
                if manual:
                    messagebox.showinfo(APP_TITLE, "已是最新版本。")
                return
            asset = updater.pick_asset(result)
            if not asset:
                self.update_status.configure(text="发现 %s，但这个版本没有 Windows 包" % tag,
                                             fg=self.pal["warn"])
                return
            self.update_release = result
            self.update_asset = asset
            self.update_status.configure(text="发现新版本 %s" % tag, fg=self.pal["accent"])
            self.btn_install_update.pack(side="right")
            if manual:
                # 手动点「检查更新」时哪怕这次启动已经提示过，也再弹一次。
                self._prompted_update = None
            if updater.is_forced(result):
                self.show_force_update(tag)
            elif tag != self._prompted_update:
                # 启动时的自动检查也要主动弹窗，不能只在设置页留一行小字。
                self.show_update_prompt(tag)

        # Fetch on a worker thread, but deliver on the Tk thread through a
        # poller scheduled here: Tk refuses cross-thread calls when the
        # interpreter is not inside mainloop (which is the case in tests).
        box = []

        def fetch():
            box.append(worker())

        threading.Thread(target=fetch, daemon=True).start()

        def poll():
            self._poll_after = None
            if box:
                done(box[0])
                return
            try:
                self._poll_after = self.root.after(100, poll)
            except Exception:
                pass

        self._poll_after = self.root.after(100, poll)

    def _auto_update_check(self):
        self._auto_check = None
        self.check_update(manual=False)

    @staticmethod
    def _update_error_text(exc):
        text = str(exc)
        if "403" in text or "rate limit" in text.lower():
            return "GitHub 访问太频繁（限流），过一会儿再试"
        if "timed out" in text.lower() or "timeout" in text.lower():
            return "连不上 GitHub（超时）"
        if "urlopen" in text or "getaddrinfo" in text or "Connection" in text:
            return "连不上 GitHub（网络不通）"
        return text

    def show_update_prompt(self, tag):
        """发现新版本（非强制）时弹出来的更新框。

        启动时的自动检查也走这里：用户不用自己去设置页找「检查更新」。
        点「稍后再说」只关掉本次提示，同一个版本这次运行里不再弹。
        """
        pal = self.pal
        existing = getattr(self, "_update_prompt_win", None)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    existing.lift()
                    existing.focus_force()
                    return
            except Exception:
                pass
        self._prompted_update = tag
        win = tk.Toplevel(self.root)
        self._update_prompt_win = win
        win.title("发现新版本")
        win.configure(bg=pal["window"])
        win.transient(self.root)
        win.grab_set()
        win.protocol("WM_DELETE_WINDOW", self._close_update_prompt)
        card = tk.Frame(win, bg=pal["card"])
        card.pack(fill="both", expand=True, padx=theme.px(16), pady=theme.px(16))
        label(card, self, "发现新版本 %s" % tag, size=12, color="text").pack(
            anchor="w", padx=theme.px(18), pady=(theme.px(16), theme.px(6)))
        label(card, self,
              "当前版本 %s。可以直接在这里下载覆盖安装，装好之后账号库、备份、\n"
              "导出路径都不动；点「稍后再说」就去掉了，之后也能在「设置 → 更新」里装。"
              % theme.APP_VERSION,
              size=9, color="text_muted", wraplength=theme.px(430),
              justify="left").pack(anchor="w", padx=theme.px(18),
                                   pady=(theme.px(0), theme.px(14)))
        row = tk.Frame(card, bg=pal["card"])
        row.pack(fill="x", padx=theme.px(18), pady=(theme.px(0), theme.px(16)))
        PillButton(self, row, "立即更新", kind="primary", width=120, height=34,
                   command=self._update_now).pack(side="left")
        PillButton(self, row, "去网页下载", kind="ghost", width=112, height=34,
                   command=self._open_releases_page).pack(
                       side="left", padx=(theme.px(8), 0))
        PillButton(self, row, "稍后再说", kind="ghost", width=100, height=34,
                   command=self._close_update_prompt).pack(side="right")
        width = theme.px(520)
        height = win.winfo_reqheight()
        x = y = 0
        try:
            # 盖在程序窗口中间偏上，别跑到屏幕左上角去。
            rx, ry = self.root.winfo_rootx(), self.root.winfo_rooty()
            rw, rh = self.root.winfo_width(), self.root.winfo_height()
            x = rx + max(0, (rw - width) // 2)
            y = ry + max(0, (rh - height) // 3)
        except Exception:
            pass
        win.geometry("%dx%d+%d+%d" % (width, height, x, y))
        win.lift()
        try:
            win.focus_force()
        except Exception:
            pass
        self.log("更新", "发现新版本 %s，已弹出更新提示" % tag)

    def _close_update_prompt(self):
        win, self._update_prompt_win = getattr(self, "_update_prompt_win", None), None
        if win is None:
            return
        try:
            win.grab_release()
        except Exception:
            pass
        try:
            win.destroy()
        except Exception:
            pass

    def _update_now(self):
        """更新框里的「立即更新」：关掉弹窗，直接开始下载（不再二次确认）。"""
        self._close_update_prompt()
        self.do_update(confirm=False)

    def _open_releases_page(self):
        webbrowser.open("https://github.com/fenghuo6183/HousamoAuthKeyManager/releases/latest")

    def show_force_update(self, tag):
        """重要/安全修复：不给「稍后」，不更新就用不了。"""
        pal = self.pal
        win = tk.Toplevel(self.root)
        win.title("必须更新")
        win.configure(bg=pal["window"])
        win.transient(self.root)
        win.grab_set()
        win.protocol("WM_DELETE_WINDOW", lambda: None)
        card = tk.Frame(win, bg=pal["card"])
        card.pack(fill="both", expand=True, padx=theme.px(16), pady=theme.px(16))
        label(card, self, "必须更新到 %s" % tag, size=12, color="text").pack(
            anchor="w", padx=theme.px(18), pady=(theme.px(16), theme.px(6)))
        label(card, self,
              "这一版修的是重要问题（安全或数据相关），旧版会一直带着它跑，\n"
              "所以这个版本不能跳过。装好之后账号库、备份、导出路径都还在原地。\n"
              "如果自动更新失败，点「手动下载」拿压缩包覆盖安装。",
              size=9, color="warn", wraplength=theme.px(420), justify="left").pack(
            anchor="w", padx=theme.px(18), pady=(theme.px(0), theme.px(14)))
        row = tk.Frame(card, bg=pal["card"])
        row.pack(fill="x", padx=theme.px(18), pady=(theme.px(0), theme.px(16)))
        PillButton(self, row, "立即更新", command=self.do_update, kind="primary",
                   width=120, height=34).pack(side="left")
        PillButton(self, row, "手动下载", kind="ghost", width=104, height=34,
                   command=lambda: webbrowser.open(
                       "https://github.com/fenghuo6183/HousamoAuthKeyManager/releases/latest")
                   ).pack(side="left", padx=(theme.px(8), 0))
        PillButton(self, row, "退出程序", command=self.root.destroy, kind="ghost",
                   width=96, height=34).pack(side="right")
        win.geometry("%dx%d" % (theme.px(500), win.winfo_reqheight()))
        self.log("更新", "这是强制更新版本 %s，已弹出必须更新的提示" % tag)

    def do_update(self, confirm=True):
        if not self.update_asset:
            return
        install = updater.install_dir()
        if not updater.dir_writable(install):
            messagebox.showwarning(
                APP_TITLE, "程序目录不可写（可能装在 Program Files），请手动下载更新包覆盖。")
            webbrowser.open("https://github.com/fenghuo6183/HousamoAuthKeyManager/releases/latest")
            return
        tag = (self.update_release or {}).get("tag_name") or ""
        if confirm and not messagebox.askyesno(
                APP_TITLE,
                "将下载 %s 并在关闭本程序后替换安装目录，然后自动重启。\n继续吗？" % tag):
            return
        self.btn_install_update.set_enabled(False)
        self.btn_check_update.set_enabled(False)
        self.update_status.configure(text="正在下载…", fg=self.pal["text_muted"])

        def worker():
            zip_path = updater.download(self.update_asset["url"],
                                        self.update_asset.get("digest", ""),
                                        lambda m: self.log("更新", m))
            stage = updater.stage_copy(install, log=lambda m: self.log("更新", m))
            return zip_path, stage

        def done(result):
            if not result:
                self.btn_install_update.set_enabled(True)
                self.btn_check_update.set_enabled(True)
                self.update_status.configure(text="下载失败，可以看日志或再试一次",
                                             fg=self.pal["err"])
                self.btn_view_log.pack(side="right")
                return
            zip_path, stage = result
            name = os.path.basename(sys.executable) if getattr(sys, "frozen", False) \
                else "AuthKeyManager.exe"
            exe = os.path.join(stage, name)
            if not os.path.isfile(exe):
                self.log("错误", "临时目录里没有可执行文件：%s" % exe)
                messagebox.showerror(APP_TITLE, "更新失败：临时目录里没有可执行文件。")
                return
            updater.write_state(stage="applying", target_version=tag,
                                zip=zip_path, install=install)
            subprocess.Popen([exe, "--apply-update", zip_path, install, str(os.getpid())],
                             cwd=stage,
                             creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
            self.log("更新", "更新程序已启动，本程序即将退出")
            self.root.after(300, self.root.destroy)

        self._bg(worker, done)

    def _apply_update_state(self):
        state = updater.read_state()
        stage = state.get("stage")
        try:
            if stage == "failed":
                self.update_status.configure(
                    text="上次更新失败：%s" % (state.get("error") or "未知原因"),
                    fg=self.pal["err"])
                self.btn_view_log.pack(side="right")
            elif stage == "applying" and updater.is_newer(state.get("target_version", ""),
                                                          theme.APP_VERSION):
                self.update_status.configure(text="上次更新没有完成，可以再试一次",
                                             fg=self.pal["warn"])
                self.btn_view_log.pack(side="right")
        except Exception:
            pass

    def open_update_log(self):
        path = updater.log_path()
        if not os.path.isfile(path):
            messagebox.showinfo(APP_TITLE, "还没有更新日志。")
            return
        try:
            os.startfile(path)
        except Exception as exc:
            self.log("错误", "打开日志失败：%s" % exc)

    def _refresh_bg_panel(self):
        path = self.settings.get("bg_image") or ""
        if path and os.path.isfile(path):
            name = os.path.basename(path)
            try:
                from PIL import ImageTk
                photo = ImageTk.PhotoImage(self.backdrop.thumbnail(132, 74, 8))
                self.thumb_label.configure(image=photo, text="", bg=self.pal["card_soft"])
                self.thumb_label.image = photo
            except Exception:
                self.thumb_label.configure(image="", text=name[:18])
            self.bg_name_label.configure(text=name)
            self.bg_note_label.configure(text="已复制到应用数据目录，原始文件移动或删除都不影响")
        else:
            self.thumb_label.configure(image="", text="无背景图")
            self.thumb_label.image = None
            self.bg_name_label.configure(text="还没有选择背景图")
            self.bg_note_label.configure(text="支持 png / jpg / bmp / webp，选择后会复制一份到应用数据目录")
        self.blur_slider.set(self.settings.get("bg_blur"))
        self.alpha_slider.set(self.settings.get("bg_alpha"))
        self.blur_readout.configure(text="%d px" % int(self.settings.get("bg_blur")))
        self.alpha_readout.configure(text="%d %%" % int(self.settings.get("bg_alpha")))

    def _refresh_data_card(self):
        rows = getattr(self, "data_rows", None)
        if not rows:
            return
        folder = config.app_dir()
        rows["data_dir"].configure(text=folder)
        g = self.active_game
        accounts = len(self.vault.by_kind("account")) if self.vault else 0
        backups = len(self.vault.by_kind("backup")) if self.vault else 0
        rows["vault"].configure(text="vault.%s.dat · %d 个账号 · %d 个备份（DPAPI 加密）"
                                     % (g.id, accounts, backups))
        rows["save_dir"].configure(
            text=os.path.join(self.save_dir, g.label) if self.save_dir else "未选择")
        rows["adb"].configure(text="就绪" if self.adb else "不可用（缺少 platform-tools）",
                              fg=self.pal["ok"] if self.adb else self.pal["err"])
        self._refresh_lock_row()
        self._refresh_conn_card()

    def _refresh_lock_row(self):
        if not getattr(self, "lock_value", None):
            return
        on = applock.is_enabled(self.settings)
        self.lock_value.configure(text="已开启 · 启动时要输 4-6 位数字" if on else "未开启",
                                  fg=self.pal["text"] if on else self.pal["text_muted"])
        self.btn_lock.set_text("关闭" if on else "开启")

    def toggle_app_lock(self):
        if applock.is_enabled(self.settings):
            pin = simpledialog.askstring(
                "关闭应用锁", "先输入当前密码：", show="*", parent=self.root)
            if pin is None:
                return
            if not applock.check_pin(self.settings, pin):
                messagebox.showerror("关闭应用锁", "密码不对，应用锁没有变动。", parent=self.root)
                return
            applock.clear_pin(self.settings)
            self.log("设置", "应用锁已关闭")
            self._refresh_lock_row()
            return
        pin = simpledialog.askstring(
            "开启应用锁", "设一个 4-6 位数字密码：\n下次打开程序要先输入它。",
            show="*", parent=self.root)
        if pin is None:
            return
        again = simpledialog.askstring(
            "开启应用锁", "再输一次确认：", show="*", parent=self.root)
        if again is None:
            return
        if pin != again:
            messagebox.showwarning("开启应用锁", "两次输入不一样，请重新设置。", parent=self.root)
            return
        try:
            applock.set_pin(self.settings, pin)
        except ValueError as exc:
            messagebox.showwarning("开启应用锁", str(exc), parent=self.root)
            return
        self.log("设置", "应用锁已开启（4-6 位数字，启动时校验）")
        self._refresh_lock_row()

    def open_data_dir(self):
        try:
            os.startfile(config.app_dir())
        except Exception as exc:
            self.log("错误", "打开数据目录失败：%s" % exc)

    def copy_data_dir(self):
        folder = config.app_dir()
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(folder)
            self.log("完成", "数据目录已复制：%s" % folder)
        except Exception as exc:
            self.log("错误", "复制失败：%s" % exc)

    # -- logging -------------------------------------------------------
    def log(self, tag, message):
        if threading.current_thread() is not threading.main_thread():
            self.root.after(0, self.log, tag, message)
            return
        try:
            self.log_empty.place_forget()
        except Exception:
            pass
        try:
            self.log_text.configure(state="normal")
            self.log_text.insert("end", time.strftime("%H:%M:%S  "), ("time",))
            kind = "err" if tag in ("错误", "失败") else "ok" if tag == "完成" else \
                "hint" if tag in ("提示", "设置") else ""
            self.log_text.insert("end", "[%s] %s\n" % (tag, message), (kind,) if kind else ())
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        except Exception:
            pass

    def clear_log(self):
        try:
            self.log_empty.place(relx=0.5, rely=0.45, anchor="center")
        except Exception:
            pass
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

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
        self._set_buttons("normal")
        if error is not None:
            self.log("失败", str(error))
            messagebox.showerror(APP_TITLE, str(error))
            return
        if on_done:
            on_done(result)

    def _set_buttons(self, state):
        enabled = state != "disabled"
        for btn in (self.btn_extract, self.btn_import):
            btn.set_enabled(enabled)

    # -- devices -------------------------------------------------------
    def _device_by_serial(self, serial):
        for dev in self.devices:
            if dev.serial == serial:
                return dev
        return None

    def selected_device(self):
        dev = self._device_by_serial(self._selected_serial)
        if dev is not None:
            return dev
        remembered = self.settings.get("preferred_serial")
        dev = self._device_by_serial(remembered)
        if dev is not None:
            return dev
        for dev in self.devices:
            if dev.online:
                return dev
        return self.devices[0] if self.devices else None

    def _on_device_row(self, device):
        self.select_device(device.serial)

    def select_device(self, serial, persist=True, refresh_reconcile=True):
        """Switch the device every action uses; remember it across restarts."""
        dev = self._device_by_serial(serial)
        if dev is None:
            return
        self._selected_serial = serial
        if persist:
            self.settings.set("preferred_serial", serial)
            self._refresh_conn_card()
            self.log("设备", "已切换到 %s（%s）" % (dev.short_label, serial))
        if getattr(self, "device_list", None) is not None:
            self.device_list.set_selected(serial)
        self._refresh_current_device()
        self._apply_device_state(dev)
        if refresh_reconcile:
            self.refresh_reconcile()

    def _pick_device(self, devices):
        """Keep the user's pick; a remembered device only wins when online."""
        online = [d for d in devices if d.online]
        for serial in (self._selected_serial, self.settings.get("preferred_serial")):
            if not serial:
                continue
            for dev in online:
                if dev.serial == serial:
                    return dev
        if online:
            return online[0]
        for serial in (self._selected_serial, self.settings.get("preferred_serial")):
            dev = self._device_by_serial(serial)
            if dev is not None and dev in devices:
                return dev
        return devices[0] if devices else None

    def _paint_chip(self, label_widget, text, tone="muted"):
        tones = {"ok": ("ok_soft", "ok"), "err": ("err_soft", "err"),
                 "accent": ("accent_soft", "accent"), "muted": ("card_soft", "text_muted")}
        bg, fg = tones.get(tone, tones["muted"])
        try:
            label_widget.configure(text=text, bg=self.pal[bg], fg=self.pal[fg])
        except Exception:
            pass

    def _extract_label(self, dev=None):
        dev = dev or self.selected_device()
        if dev is None:
            return "提取 %s 的 key" % self.active_game.label
        return "提取 %s 的 key" % dev.short_label

    def _apply_device_state(self, dev):
        self.btn_extract.set_text(self._extract_label(dev))
        if dev is None:
            self.btn_extract.set_enabled(False)
            return
        # None = the probe has not answered yet; stay clickable rather than
        # blocking the user while we check.
        self.btn_extract.set_enabled(bool(dev.online) and dev.game_installed is not False)

    def _refresh_current_device(self):
        dev = self.selected_device()
        if dev is None:
            self.dev_detail.configure(text="没有可用设备，点「刷新」扫描，或到连接设置填地址")
            return
        bits = [dev.serial, "在线" if dev.online else "离线"]
        if dev.game_installed is True:
            bits.append("已装游戏")
        elif dev.game_installed is False:
            bits.append("未装游戏")
        if dev.root == "是":
            bits.append("Root")
        self.dev_detail.configure(text=" · ".join(bits))

    # -- game switching ------------------------------------------------
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
        self._apply_device_state(self.selected_device())
        self.btn_import.set_text("导入到 %s" % g.label)
        self._update_device_hint()
        self.refresh_vault()
        self._refresh_data_card()
        self._check_game_installed()
        self.refresh_reconcile()
        self.log("设备", "已切换到 %s" % g.label)

    def _update_device_hint(self):
        try:
            if not self.devices:
                self.device_hint.configure(text="")
                return
            online = sum(1 for dev in self.devices if dev.online)
            text = "共 %d 台 · %d 台在线" % (len(self.devices), online)
            if self.settings.get("only_emulators"):
                hidden = [dev for dev in self.devices if not dev.is_emulator]
                if hidden:
                    text += " · 已隐藏 %d 台 USB" % len(hidden)
            self.device_hint.configure(text=text)
        except Exception:
            pass

    def _check_game_installed(self, quiet=False):
        """Probe every online row, so no device is stuck on 「检测游戏…」."""
        if not self.adb:
            return
        g = self.active_game
        for dev in list(self.devices):
            if not dev.online:
                continue
            serial = dev.serial
            token = (g.id, serial)
            # A background poll must not re-probe devices we already know.
            if quiet and dev.game_installed is not None:
                continue
            if token in self._probe and dev.game_installed is not None:
                continue

            def runner(serial=serial, token=token):
                try:
                    ok = game.game_installed(self.adb, serial, g)
                except Exception:
                    ok = None
                self._probe[token] = ok
                self.root.after(0, self._installed_done, g.id, serial, ok)

            threading.Thread(target=runner, daemon=True).start()

    def _installed_done(self, game_id, serial, ok):
        if game_id != self.active_game.id:
            return
        dev = self._device_by_serial(serial)
        if dev is not None:
            dev.game_installed = bool(ok) if ok is not None else None
        try:
            self.device_list.set_game_state(serial, ok)
        except Exception:
            pass
        if dev is not None and dev.serial == self._selected_serial:
            self._apply_device_state(dev)
            self._refresh_current_device()
        if (ok is False and dev is not None
                and dev.serial == self._selected_serial):
            # Probe runs for every row; only nag about the device in use, once.
            seen = getattr(self, "_missing_logged", None)
            if seen is None:
                seen = self._missing_logged = set()
            token = (game_id, serial)
            if token not in seen:
                seen.add(token)
                self.log("设备", "%s 上没有安装 %s，换一台或先装好游戏"
                         % (dev.short_label, self.active_game.label))

    def refresh_devices(self, quiet=False):
        if not self.adb:
            if quiet:
                return
            # No modal here: this also runs on startup and after toggles.
            self._set_adb_chip("adb 不可用", "err")
            self.log("错误", "adb 不可用，请检查 platform-tools 是否放在 assets/platform-tools 下")
            return
        if quiet:
            # Polling never touches the busy flag, buttons or the log. The
            # worker only stores its result; this (main) thread collects it,
            # because root.after() is not safe from a worker thread.
            self._quiet_pending = None
            self._quiet_wait = 0
            threading.Thread(target=self._quiet_refresh, daemon=True).start()
            self._check_quiet(60)
            return
        self._set_adb_chip("正在检测设备…", "muted")
        self._bg(self._devices_worker, self._devices_done)

    def _quiet_refresh(self):
        try:
            devices = self._devices_worker(quiet=True)
        except Exception:
            devices = None
        if not self._closing:
            self._quiet_pending = devices

    def _check_quiet(self, delay=120):
        """Main-thread collector for the background poll result."""
        if self._closing:
            return
        pending = getattr(self, "_quiet_pending", None)
        if pending is not None:
            self._quiet_pending = None
            self._devices_done(pending, True)
            return
        self._quiet_wait = getattr(self, "_quiet_wait", 0) + delay
        if self._quiet_wait < 8000:
            self._quiet_job = self.root.after(
                delay, lambda: self._check_quiet(max(delay, 80)))

    def _devices_worker(self, quiet=False):
        if not self.adb:
            return list(self.devices)
        devices = list(self.adb.devices())
        known = {dev.serial: dev for dev in self.devices}
        for dev in devices:
            previous = known.get(dev.serial)
            if quiet and previous is not None:
                # Keep answers we already have: a poll must not run
                # `adb shell su` for every device every few seconds.
                dev.root = previous.root
                dev.game_installed = previous.game_installed
                continue
            dev.root = "?"
            dev.game_installed = None
            if dev.online:
                try:
                    dev.root = "是" if self.adb.su_available(dev.serial) else "否"
                except Exception:
                    dev.root = "?"
        return devices

    def _devices_done(self, devices, quiet=False):
        self.devices = list(devices)
        only = bool(self.settings.get("only_emulators"))
        visible = [dev for dev in self.devices if not only or dev.is_emulator]
        try:
            if quiet:
                self.device_list.update(visible, self._selected_serial)
            else:
                self.device_list.set_devices(visible, self._selected_serial)
        except Exception:
            pass
        pending = getattr(self, "_pending_select", "")
        if pending:
            self._pending_select = ""
            for dev in visible:
                if dev.serial == pending:
                    self.select_device(dev.serial, persist=True, refresh_reconcile=False)
                    break
            else:
                self._pick_and_apply(visible, quiet=quiet)
        else:
            self._pick_and_apply(visible, quiet=quiet)
        online = sum(1 for dev in visible if dev.online)
        if visible:
            self._set_adb_chip("%d 台在线" % online if online else "%d 台离线" % len(visible),
                               "ok" if online else "warn")
        else:
            self._set_adb_chip("未发现设备", "warn")
        if not quiet:
            if visible:
                self.log("设备", "发现 %d 台设备" % len(visible))
            elif self.devices:
                self.log("设备", "设备都被「只显示模拟器」过滤掉了，可以在设置里关掉")
            else:
                self.log("设备", "没有发现设备。请打开 USB 调试，或先启动模拟器再点「扫描模拟器」。")
        self._update_device_hint()
        self._check_game_installed(quiet=quiet)
        if not quiet:
            self.refresh_reconcile()

    def _pick_and_apply(self, visible, quiet=False):
        pick = None
        if quiet:
            # A blink offline must not steal the selection; stay on the
            # device the user picked as long as it is still listed.
            for dev in visible:
                if dev.serial == self._selected_serial:
                    pick = dev
                    break
        if pick is None:
            pick = self._pick_device(visible)
        if pick is not None:
            self.select_device(pick.serial, persist=False, refresh_reconcile=False)
        else:
            self._selected_serial = ""
            self._refresh_current_device()
            self._apply_device_state(None)

    # -- background poll -----------------------------------------------
    # Nine seconds: fast enough that an emulator restart shows up while the
    # user is still looking at the window, slow enough that adb is not
    # hammered while they browse the vault.
    POLL_MS = 9000

    def _start_poll(self):
        if self._closing:
            return
        self._poll_job = self.root.after(self.POLL_MS, self._poll_tick)

    def _poll_tick(self):
        self._poll_job = None
        if self._closing:
            return
        try:
            if self.adb and not self._busy:
                self.refresh_devices(quiet=True)
        except Exception:
            pass
        self._start_poll()

    # -- drag & drop ---------------------------------------------------
    def _install_drop_target(self):
        try:
            self._dnd = dnd.install(self.root, self.handle_dropped_files)
        except Exception:
            self._dnd = None

    def handle_dropped_files(self, paths):
        if self._closing:
            return
        picked = dnd.hak_paths(paths)
        if not picked:
            self.log("导入", "拖进来的不是 .hak 备份，没有导入")
            return
        self.log("导入", "拖入 %d 个 .hak 文件" % len(picked))
        for path in picked:
            self._import_hak_path(path)

    # -- emulator discovery --------------------------------------------
    @staticmethod
    def _parse_ports(raw):
        ports = []
        for part in str(raw or "").replace(";", ",").replace(" ", ",").split(","):
            part = part.strip()
            if part.isdigit() and 0 < int(part) < 65536:
                value = int(part)
                if value not in ports:
                    ports.append(value)
        return ports

    def emulator_ports(self):
        raw = self.settings.get("emulator_ports") or ""
        return self._parse_ports(raw) or list(EMULATOR_PORTS)

    def _update_ports_summary(self):
        widget = getattr(self, "ports_summary", None)
        if widget is None:
            return
        ports = self.emulator_ports()
        head = ", ".join(str(port) for port in ports[:3])
        if len(ports) > 3:
            head += " …"
        widget.configure(text="%d 个端口 · %s" % (len(ports), head))

    def edit_scan_ports(self):
        raw = self.ports_var.get() if getattr(self, "ports_var", None) is not None else ""
        text = dialogs.ask_text(
            self, "扫描端口", hint="逗号分隔；清空就恢复默认端口列表",
            initial=raw, max_len=400, allow_empty=True)
        if text is None:
            return
        if getattr(self, "ports_var", None) is None:
            self.ports_var = tk.StringVar()
        self.ports_var.set(text)
        self._on_ports_change()

    def _on_ports_change(self):
        raw = self.ports_var.get() if getattr(self, "ports_var", None) is not None else ""
        ports = self._parse_ports(raw) or list(EMULATOR_PORTS)
        text = ",".join(str(port) for port in ports)
        self.settings.set("emulator_ports", text)
        try:
            if self.ports_var.get() != text:
                self.ports_var.set(text)
        except Exception:
            pass
        self._update_ports_summary()
        self.log("设置", "模拟器端口：%s" % text)
        return ports

    def scan_emulators(self):
        if not self.adb:
            self.log("错误", "adb 不可用，没法扫描模拟器")
            return
        ports = self.emulator_ports()
        self._set_adb_chip("正在扫描模拟器…", "muted")

        def worker():
            # Probe a handful at a time: 14 serial connects take minutes.
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
                        ok, _text = self.adb.connect("127.0.0.1:%d" % port)
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

        def done(hits):
            for port in hits or ():
                self.log("模拟器", "已连接 127.0.0.1:%d" % port)
            self.log("模拟器", "扫描结束，新连接 %d 个" % len(hits or []))
            self.refresh_devices()

        self._bg(worker, done)

    def _on_connect_profile(self, _event=None):
        index = self.connect_profile.current()
        if not (0 <= index < len(CONNECT_PROFILES)):
            return
        key, _text, address = CONNECT_PROFILES[index]
        self.settings.set("connect_profile", key)
        if key == "auto":
            self.addr_var.set("")
            self.scan_emulators()
        elif address is None:
            self.addr_var.set("")
            self.addr_entry.focus_set()
        else:
            self.addr_var.set(address)
            self.connect_address()

    def connect_address(self):
        raw = self.addr_var.get() if getattr(self, "addr_var", None) is not None else ""
        addr = adb_mod.normalize_address(raw)
        if not addr:
            self.log("提示", "先填一个地址，例如 127.0.0.1:16384")
            return
        if not self.adb:
            self.log("错误", "adb 不可用，没法连接设备")
            return
        self._set_adb_chip("正在连接 %s…" % addr, "muted")

        def worker():
            ok, text = self.adb.connect(addr)
            return ok, text, addr

        def done(result):
            ok, text, target = result
            if ok:
                self.log("设备", "已连接 %s" % target)
                self._pending_select = target
                self.addr_var.set("")
            else:
                self.log("失败", "连接 %s 失败：%s" % (target, text))
            self.refresh_devices()

        self._bg(worker, done)

    def forget_device(self):
        self.settings.set("preferred_serial", "")
        self._selected_serial = ""
        if getattr(self, "device_list", None) is not None:
            self.device_list.set_selected("")
        self._refresh_conn_card()
        self.log("设置", "已清除记住的设备，下次启动不再自动选它")

    def _on_only_emulators(self, key):
        self.settings.set("only_emulators", key == "on")
        self.log("设置", "只显示模拟器：%s" % ("开" if key == "on" else "关"))
        self.refresh_devices()

    def _on_auto_connect(self, key):
        self.settings.set("auto_connect", key == "on")
        self.log("设置", "启动时自动连接模拟器：%s" % ("开" if key == "on" else "关"))

    def _refresh_conn_card(self):
        widget = getattr(self, "conn_device_label", None)
        if widget is None:
            return
        serial = self.settings.get("preferred_serial") or ""
        if serial:
            dev = self._device_by_serial(serial)
            text = "%s · %s" % (dev.short_label if dev else "未连接", serial)
        else:
            text = "还没记，点任务页的设备行就会记住"
        widget.configure(text=text)

    def open_url(self, url):
        try:
            webbrowser.open(url)
        except Exception:
            self.log("提示", "没法打开浏览器，地址是：%s" % url)

    # -- vault view ----------------------------------------------------
    def _cell_font(self):
        font = getattr(self, "_cell_font_cache", None)
        if font is None:
            family, size, weight = theme.font(10)
            font = tkfont.Font(family=family, size=size, weight=weight)
            self._cell_font_cache = font
        return font

    def _fit_cell(self, tree, col, text, pad=16, keep_tail=""):
        """Trim a cell to the column width with an ellipsis instead of hard clipping.

        keep_tail keeps a meaningful suffix (e.g. the " (128)" of a fingerprint)
        visible after the ellipsis instead of truncating it away.
        """
        text = "" if text is None else str(text)
        tail = ""
        if keep_tail and text.endswith(keep_tail) and len(text) > len(keep_tail):
            tail = keep_tail
            text = text[:-len(keep_tail)]
        try:
            width = int(tree.column(col, "width"))
        except Exception:
            return text
        avail = max(theme.px(24), width - theme.px(pad))
        font = self._cell_font()
        try:
            if font.measure(text) <= avail:
                return text
        except Exception:
            return text
        ell = "…"
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if font.measure(text[:mid] + ell + tail) <= avail:
                lo = mid
            else:
                hi = mid - 1
        if lo:
            return text[:lo].rstrip() + ell + tail
        keep = ell + tail
        return keep if font.measure(keep) <= avail else ell

    @staticmethod
    def _source_label(source):
        """把 "序列号 /data/data/.../x.xml" 压成 "模拟器 · x.xml"，避免列里被硬截断。"""
        text = (source or "").strip()
        if not text:
            return "—"
        head, _sep, tail = text.partition(" ")
        path = tail or head
        serial = head if tail else ""
        node = path.rstrip("/").rsplit("/", 1)[-1] or path
        if serial:
            low = serial.lower()
            where = "模拟器" if (low.startswith("127.0.0.1")
                                or low.startswith("emulator")) else "设备"
            return "%s · %s" % (where, node)
        if "/data/data/" in path:
            return "本机 · " + node
        return node if len(node) <= 24 else node[:23] + "…"

    def refresh_vault(self):
        if not self.vault:
            return
        keyword = ""
        try:
            keyword = self.search_var.get().strip().lower()
        except Exception:
            keyword = ""
        entries = self.vault.by_kind(self.vault_kind)
        if keyword:
            entries = [e for e in entries
                       if keyword in (e.get("name", "").lower()
                                      or "") or keyword in (e.get("note", "").lower() or "")
                       or keyword in (e.get("fingerprint", "").lower() or "")
                       or keyword in (e.get("source", "").lower() or "")]
        self.vault_tree.delete(*self.vault_tree.get_children())
        def cell(col, text):
            tail = ""
            if col == "fingerprint":
                match = re.search(r"\s*\(\d+\)$", str(text))
                tail = match.group(0) if match else ""
            return self._fit_cell(self.vault_tree, col, text, keep_tail=tail)

        for index, e in enumerate(entries):
            self.vault_tree.insert("", "end", iid=e["id"], values=(
                cell("name", e.get("name", "")),
                cell("note", e.get("note", "")),
                cell("fingerprint", e.get("fingerprint", "")),
                cell("source", self._source_label(e.get("source", ""))),
                cell("created", e.get("created_at", ""))),
                tags=self._vault_tags(e, index))
        self._refresh_import_history()
        self.refresh_overview()
        label_text = "账号" if self.vault_kind == "account" else "备份"
        total = len(self.vault.by_kind(self.vault_kind))
        all_total = len(self.vault.entries)
        if keyword:
            self.count_chip.configure(text="%d / %d 个%s" % (len(entries), total, label_text),
                                     bg=self.pal["accent_soft"], fg=self.pal["accent"])
        else:
            self.count_chip.configure(text="%d 个%s · 共 %d" % (total, label_text, all_total),
                                     bg=self.pal["card_soft"], fg=self.pal["text_muted"])
        self._update_vault_actions()

    def _vault_tags(self, entry, index):
        tags = ("odd",) if index % 2 else ()
        if getattr(self, "_flash_id", None) and entry.get("id") == self._flash_id:
            tags = tags + ("flash",)
        return tags

    def switch_vault_kind(self, kind):
        self.vault_kind = kind
        if getattr(self, "kind_seg", None):
            self.kind_seg.set_active(kind)
        self.refresh_vault()

    def _update_vault_actions(self):
        entry = self.selected_entry()
        backup = bool(entry and entry.get("kind") == "backup")
        for name in ("btn_rename", "btn_note"):
            button = getattr(self, name, None)
            if button is None:
                continue
            try:
                button.set_enabled(not backup)
            except Exception:
                pass

    def _on_vault_f2(self, _event=None):
        if self.vault_tree.selection():
            self.rename_entry()
        return "break"

    def reveal_entry(self, entry_id, page=True):
        """Show one entry: jump to the vault, select it and flash it briefly."""
        if not entry_id:
            return
        self._flash_id = entry_id
        if page and self.page != "vault":
            self._show_page("vault")
        self.refresh_vault()
        try:
            if self.vault_tree.exists(entry_id):
                self.vault_tree.selection_set(entry_id)
                self.vault_tree.focus(entry_id)
                self.vault_tree.see(entry_id)
        except Exception:
            pass
        job, self._flash_job = getattr(self, "_flash_job", None), None
        if job is not None:
            try:
                self.root.after_cancel(job)
            except Exception:
                pass
        self._flash_job = self.root.after(2600, lambda: self.clear_flash(entry_id))

    def clear_flash(self, entry_id=None):
        entry_id = entry_id or getattr(self, "_flash_id", None)
        self._flash_job = None
        if not entry_id:
            return
        if getattr(self, "_flash_id", None) == entry_id:
            self._flash_id = None
        try:
            if self.vault_tree.exists(entry_id):
                tags = [tag for tag in self.vault_tree.item(entry_id, "tags")
                        if tag != "flash"]
                self.vault_tree.item(entry_id, tags=tags)
        except Exception:
            pass

    def selected_entry(self):
        sel = self.vault_tree.selection()
        if not sel or not self.vault:
            return None
        return self.vault.get(sel[0])

    def _require(self, device=True, entry=True):
        if device:
            dev = self.selected_device()
            if dev is None or not dev.online:
                messagebox.showwarning(APP_TITLE, "请先在任务页选一台在线的设备。")
                return False
        if entry and not self.selected_entry():
            messagebox.showwarning(APP_TITLE, "请先在账号库里选中一个账号。")
            return False
        return True

    # -- startup reconcile ---------------------------------------------
    def refresh_reconcile(self):
        try:
            self.reconcile_bar.pack_forget()
        except Exception:
            pass
        self._reconcile_key = None
        if not self.adb:
            return
        dev = self.selected_device()
        if dev is None or not dev.online:
            return
        g = self.active_game
        serial = dev.serial
        token = getattr(self, "_reconcile_token", 0) + 1
        self._reconcile_token = token

        def done(key):
            if key is None or token != self._reconcile_token:
                return
            self._reconcile_key = key
            self.refresh_overview()
            ignored = (self.settings.get("reconcile_ignored") or {}).get(g.id, [])
            flag, digest = reconcile.should_prompt(self.vault, key, ignored)
            if not flag:
                return
            self._reconcile_digest = digest
            self._reconcile_serial = serial
            self.reconcile_text.configure(
                text="%s 里正在用的 key（%s）不在账号库里，要不要存一份？"
                     % (g.label, game.fingerprint(key)))
            self.reconcile_bar.pack(fill="x", pady=(theme.px(12), theme.px(0)),
                                    before=self.tree_box)
            self.log("设备", "发现账号库里没有的 key：%s" % game.fingerprint(key))

        def runner():
            try:
                key, _source = game.extract(self.adb, serial, g)
            except Exception:
                key = None
            self.root.after(0, done, key)

        threading.Thread(target=runner, daemon=True).start()

    def save_reconcile_entry(self):
        key = getattr(self, "_reconcile_key", None)
        if not key:
            self.reconcile_bar.pack_forget()
            return
        name = "游戏内快照 %s" % time.strftime("%Y-%m-%d %H:%M")
        entry, created = self.vault.add(
            name=name, key=key, note="启动核对时发现",
            source=getattr(self, "_reconcile_serial", ""),
            device=getattr(self, "_reconcile_serial", ""), kind="account")
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

    # -- actions -------------------------------------------------------
    def export_tip_shown(self):
        try:
            return max(0, int(self.settings.get("export_tip_shown", 0) or 0))
        except (TypeError, ValueError):
            return 0

    def _maybe_show_export_tip(self):
        """前三次从游戏提取到 key：先读满 3 秒「这个 key 极其重要」再继续。"""
        shown = self.export_tip_shown()
        if shown >= 3:
            return
        self.settings.set("export_tip_shown", shown + 1)
        dialogs.show_export_reminder(self, game_label=self.active_game.label)

    def do_extract(self):
        if not self._require(device=True, entry=False):
            return
        dev = self.selected_device()
        self.log("提取", "开始从 %s 提取 AuthKey" % dev.serial)

        def worker():
            g = self.active_game
            key, source = game.extract(self.adb, dev.serial, g, lambda m: self.log("提取", m))
            return key, source

        def done(result):
            key, source = result
            self._maybe_show_export_tip()
            entry, created = self.vault.add(name="待命名账号", key=key, source=source,
                                             device=dev.serial, kind="account",
                                             game=self.active_game.id)
            if created:
                taken = [row.get("name") for row in self.vault.by_kind("account")]
                name = dialogs.ask_text(
                    self, "给这个账号起个名字",
                    hint="存进账号库，以后按这个名字找；留空也行，之后在账号库里改",
                    initial=entry.get("name") or "", max_len=24, taken=taken)
                if name:
                    self.vault.update(entry["id"], name=name)
            else:
                self.log("提取", "这个 key 已经在账号库里了：%s" % entry.get("name"))
            self.reveal_entry(entry["id"])
            self.log("完成", "已保存 %s 账号，指纹 %s"
                     % (self.active_game.label, entry.get("fingerprint")))
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
        if entry.get("kind") == "backup":
            self.log("导入", "正在还原备份：%s" % entry.get("name"))
        self.log("导入", "目标设备 %s，账号 %s" % (dev.serial, entry.get("name")))

        def worker():
            g = self.active_game
            backup = game.backup_current(self.adb, dev.serial, self.vault, g,
                                         lambda m: self.log("备份", m))
            if backup:
                self.log("备份", "已备份原 key：%s" % backup.get("name"))
            target = game.import_key(self.adb, dev.serial, key, g,
                                     lambda m: self.log("导入", m))
            return {"target": target, "backup": backup}

        def done(result):
            target = result.get("target", "")
            backup = result.get("backup") or {}
            bulk.record_import(self.settings, self.active_game.id, entry,
                               backup.get("id", ""))
            self.settings.save()
            policy = self.settings.get("backup_keep", "all")
            removed = bulk.prune_backups(self.vault, policy)
            if removed:
                self.log("备份", "按保留策略（%s）清理了 %d 份旧备份"
                         % (bulk.KEEP_LABELS.get(policy, policy), len(removed)))
            self.refresh_vault()
            self.log("完成", "写入完成：%s，可以打开游戏了。" % target)
            messagebox.showinfo(APP_TITLE, "导入完成，打开游戏即可登录该账号。")

        self._bg(worker, done)

    # -- bulk import / export -----------------------------------------
    def import_folder(self):
        folder = filedialog.askdirectory(title="选择要扫描的文件夹", parent=self.root)
        if not folder:
            return
        self.log("扫描", "开始扫描 %s" % folder)

        def worker():
            return keyscan.scan_folder(folder, log=lambda m: self.log("扫描", m))

        self._bg(worker, lambda items: self._import_scanned(items, source=folder))

    def import_clipboard(self):
        try:
            text = self.root.clipboard_get()
        except Exception:
            messagebox.showinfo(APP_TITLE, "剪贴板里没有文本，先复制一条 AuthKey 试试。")
            return
        self._import_scanned(keyscan.parse_text(text), source="剪贴板")

    def _import_scanned(self, items, source=""):
        items = [i for i in (items or []) if i.get("key")]
        if not items:
            messagebox.showinfo(APP_TITLE, "没有找到可导入的 AuthKey。\n\n"
                                           "支持 auth.xml、*.txt，或直接粘贴一条 key。")
            self.log("提示", "没有找到可导入的 key")
            return
        preview = "\n".join("· %s  %s" % ((i.get("name") or "未命名")[:24],
                                           i.get("fingerprint", "")) for i in items[:6])
        more = "" if len(items) <= 6 else "\n… 还有 %d 个" % (len(items) - 6)
        if not messagebox.askyesno(APP_TITLE, "找到 %d 个 key：\n\n%s%s\n\n全部导入账号库？"
                                              % (len(items), preview, more)):
            return
        added, skipped = bulk.import_items(self.vault, items, source=source)
        self.vault_kind = "account"
        if getattr(self, "kind_seg", None):
            self.kind_seg.set_active("account")
        self.refresh_vault()
        self.log("完成", "批量导入：新增 %d 个，跳过 %d 个重复" % (len(added), skipped))
        messagebox.showinfo(APP_TITLE, "导入完成：新增 %d 个，跳过 %d 个重复。"
                              % (len(added), skipped))

    def export_bundle(self):
        if not self.vault:
            return
        kind = self.vault_kind
        word = "账号" if kind == "account" else "备份"
        if not self.vault.by_kind(kind):
            messagebox.showinfo(APP_TITLE, "这个分区还没有可以导出的%s。" % word)
            return
        if not self.save_dir:
            messagebox.showinfo(APP_TITLE, "还没选择保存位置。\n\n"
                                           "到 设置 → 数据与存储 → 保存位置 选一个文件夹即可，"
                                           "打包的 zip 会写进那里的游戏子文件夹。")
            self._show_page("settings")
            return
        g = self.active_game
        folder = os.path.join(self.save_dir, self._safe_name(g.label))
        stamp = time.strftime("%Y%m%d-%H%M")
        target = os.path.join(folder, "%s-%s-%s.zip"
                              % (g.id, "accounts" if kind == "account" else "backups", stamp))
        try:
            os.makedirs(folder, exist_ok=True)
            count = bulk.export_all(self.vault, target, g.label, kind)
        except Exception as exc:
            self.log("错误", "打包导出失败：%s" % exc)
            messagebox.showerror(APP_TITLE, "打包导出失败：%s" % exc)
            return
        self.log("完成", "已打包 %d 个%s到 %s" % (count, word, target))
        messagebox.showinfo(APP_TITLE, "已导出 %d 个%s。\n\n%s\n\n"
                                       "压缩包里每个%s一个文件夹（AuthKey.txt），另有 manifest.txt 清单。\n"
                                       "落点就是「设置 → 保存位置」里的游戏子文件夹，不用每次再问。"
                              % (count, word, target, word))

    # -- 局域网传输 -----------------------------------------------------
    def _lan_rows(self):
        rows = []
        for entry in self.vault.by_kind("account"):
            try:
                key = self.vault.key_of(entry).decode("utf-8", "replace")
            except Exception:
                continue
            rows.append({"name": entry.get("name", ""), "note": entry.get("note", ""),
                         "fingerprint": entry.get("fingerprint", ""),
                         "created_at": entry.get("created_at", ""), "key": key})
        return rows

    def open_lan_share(self):
        if not self.vault:
            return
        if not self.vault.by_kind("account"):
            messagebox.showinfo(APP_TITLE, "账号库还是空的，先导入或提取一个 key 再开传输。")
            return
        if getattr(self, "lan_win", None) and self.lan_win.winfo_exists():
            self.lan_win.lift()
            self.lan_win.focus_force()
            return
        server = lanshare.LanServer(self._lan_rows, self.active_game.label)
        try:
            url = server.start()
        except Exception as exc:
            self.log("错误", "局域网传输启动失败：%s" % exc)
            messagebox.showerror(APP_TITLE, "启动失败：%s" % exc)
            return
        self.lan = server
        pal = self.pal
        win = tk.Toplevel(self.root)
        self.lan_win = win
        win.title("局域网传输 - " + self.active_game.label)
        win.configure(bg=pal["window"])
        win.transient(self.root)
        win.geometry("%dx%d" % (theme.px(560), theme.px(300)))
        win.resizable(False, False)
        card = tk.Frame(win, bg=pal["card"])
        card.pack(fill="both", expand=True, padx=theme.px(16), pady=theme.px(16))
        label(card, self, "在手机上打开这个地址", size=13, weight="bold").pack(
            anchor="w", padx=theme.px(16), pady=(theme.px(14), theme.px(2)))
        label(card, self, "手机和电脑连同一个 Wi-Fi，用浏览器打开；地址里已经带了配对码。",
              size=9, color="text_muted").pack(anchor="w", padx=theme.px(16))
        url_box = tk.Entry(card, font=theme.mono(10), bd=0, readonlybackground=pal["card_soft"],
                           fg=pal["text"], highlightthickness=0, justify="left")
        url_box.insert(0, url)
        url_box.configure(state="readonly")
        url_box.pack(fill="x", padx=theme.px(16), pady=(theme.px(12), theme.px(6)),
                     ipady=theme.px(7))
        url_box.bind("<FocusIn>", lambda e: url_box.selection_range(0, "end"))
        label(card, self, "共 %d 个账号 · 关掉这个窗口就停止传输" % len(self._lan_rows()),
              size=9, color="text_muted").pack(anchor="w", padx=theme.px(16))
        row = tk.Frame(card, bg=pal["card"])
        row.pack(fill="x", padx=theme.px(16), pady=(theme.px(12), theme.px(14)))
        PillButton(self, row, "复制地址", command=lambda: self._copy_lan_url(url),
                   kind="primary", width=104, height=32).pack(side="left")
        PillButton(self, row, "在浏览器打开",
                   command=lambda: webbrowser.open(url), kind="ghost",
                   width=118, height=32).pack(side="left", padx=(theme.px(8), theme.px(0)))
        PillButton(self, row, "停止", command=win.destroy, kind="danger",
                   width=84, height=32).pack(side="right")
        win.protocol("WM_DELETE_WINDOW", win.destroy)
        win.bind("<Destroy>", self._on_lan_closed, add="+")
        win.update_idletasks()
        win.geometry("%dx%d" % (theme.px(560), max(theme.px(300), win.winfo_reqheight())))
        self.log("传输", "局域网传输已开启：%s" % url)

    def _copy_lan_url(self, url):
        self.root.clipboard_clear()
        self.root.clipboard_append(url)
        messagebox.showinfo(APP_TITLE, "地址已复制，发到手机上用浏览器打开即可。\n\n%s" % url)

    def _on_lan_closed(self, event=None):
        win = getattr(self, "lan_win", None)
        if event is not None and event.widget is not win:
            return
        server = getattr(self, "lan", None)
        self.lan = None
        self.lan_win = None
        if server is not None:
            server.stop()
            self.log("传输", "局域网传输已停止")

    def _on_backup_keep(self, value):
        self.settings.set("backup_keep", value)
        self.settings.save()
        if getattr(self, "backup_seg", None):
            self.backup_seg.set_active(value)
        text = bulk.KEEP_LABELS.get(value, value)
        removed = bulk.prune_backups(self.vault, value)
        if removed:
            self.refresh_vault()
            self.log("设置", "备份保留：%s，清理了 %d 份旧备份" % (text, len(removed)))
        else:
            self.log("设置", "备份保留：%s，暂时没有需要清理的备份" % text)

    def undo_last_import(self):
        if not self.vault:
            return
        last = bulk.last_import(self.settings, self.active_game.id)
        if not last:
            messagebox.showinfo(APP_TITLE, "还没有导入记录。")
            return
        entry = self.vault.get(last.get("entry_id")) if last.get("entry_id") else None
        if entry is None:
            bulk.forget_import(self.settings, self.active_game.id)
            self._refresh_import_history()
            messagebox.showinfo(APP_TITLE, "那条记录对应的账号已经不在库里，已清掉这条历史。")
            return
        if not messagebox.askyesno(APP_TITLE,
                                   "把「%s」这条账号导入撤销掉？\n\n"
                                   "只会移除账号库里的这一份，设备上的 key 不受影响。"
                                   % entry.get("name")):
            return
        self.vault.delete(entry["id"])
        bulk.forget_import(self.settings, self.active_game.id)
        self.refresh_vault()
        self.log("完成", "已撤销上次导入：%s" % entry.get("name"))

    def _refresh_import_history(self):
        widget = getattr(self, "vault_history_label", None)
        if widget is None or not self.vault:
            return
        last = bulk.last_import(self.settings, self.active_game.id)
        if not last:
            widget.configure(text="还没有导入记录")
            return
        widget.configure(text="上次导入 %s · %s"
                              % ((last.get("at") or "")[5:16],
                                 (last.get("name") or "账号")[:16]))

    def _refresh_recent_history(self):
        box = getattr(self, "recent_box", None)
        if box is None:
            return
        for row in getattr(self, "recent_rows", []):
            row.destroy()
        self.recent_rows = []
        empty = getattr(self, "recent_empty", None)
        items = []
        if self.vault is not None:
            items = bulk.import_history(self.settings, self.active_game.id, 5)
        if not items:
            if empty is not None:
                empty.pack(anchor="w")
            return
        if empty is not None:
            empty.pack_forget()
        for item in items:
            stamp = (item.get("at") or "")[5:16]
            name = (item.get("name") or "账号")[:20]
            fp = (item.get("fingerprint") or "")[:8]
            text = "%s   %s" % (stamp, name)
            if fp:
                text += "   " + fp
            row = label(box, self, text, size=9, color="text_muted")
            row.pack(anchor="w", pady=(theme.px(4), theme.px(0)))
            self.recent_rows.append(row)

    def refresh_overview(self):
        self._refresh_recent_history()
        stats = getattr(self, "stat_labels", None)
        if not stats or not self.vault:
            return
        key = getattr(self, "_reconcile_key", None)
        stats["game_key"].configure(text=game.fingerprint(key) if key else "—")
        last = bulk.last_import(self.settings, self.active_game.id)
        stats["last_import"].configure(
            text="%s · %s" % ((last.get("at") or "")[5:16], (last.get("name") or "账号")[:10])
            if last else "—")
        stats["accounts"].configure(text=str(len(self.vault.by_kind("account"))))
        stats["backups"].configure(text=str(len(self.vault.by_kind("backup"))))

    def launch_game(self):
        if not self._require(device=True, entry=False):
            return
        dev = self.selected_device()
        try:
            self.adb.shell(dev.serial, "monkey -p %s -c android.intent.category.LAUNCHER 1"
                           % self.active_game.pkg, timeout=25)
            self.log("设备", "已请求启动游戏")
        except Exception as exc:
            self.log("失败", "启动游戏失败：%s" % exc)

    # -- vault actions -------------------------------------------------
    def rename_entry(self):
        entry = self.selected_entry()
        if not entry:
            return
        if entry.get("kind") == "backup":
            messagebox.showinfo(APP_TITLE, "备份条目不能改名；需要的话先导入回游戏，再存成账号。")
            return
        taken = [row.get("name") for row in self.vault.by_kind(entry.get("kind") or "account")]
        name = dialogs.ask_text(
            self, "重命名账号", hint="只改显示名，不影响 key 本身",
            initial=entry.get("name", ""), max_len=24, taken=taken)
        if name:
            self.vault.update(entry["id"], name=name)
            self.refresh_vault()
            self.log("账号", "已改名为「%s」" % name)

    def edit_note(self):
        entry = self.selected_entry()
        if not entry:
            return
        if entry.get("kind") == "backup":
            messagebox.showinfo(APP_TITLE, "备份条目不能改备注。")
            return
        note = dialogs.ask_text(
            self, "编辑备注", hint="给自己看的说明，比如「主号」「给朋友」",
            initial=entry.get("note", ""), max_len=200, multiline=True,
            allow_empty=True)
        if note is not None:
            self.vault.update(entry["id"], note=note)
            self.refresh_vault()
            self.log("账号", "备注已更新")

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
        pal = self.pal
        text = self.vault.key_of(entry).decode("utf-8", "replace")
        win = tk.Toplevel(self.root)
        win.title("Key - " + entry.get("name", ""))
        win.geometry("%dx%d" % (theme.px(660), theme.px(240)))
        win.configure(bg=pal["window"])
        win.transient(self.root)
        frame = tk.Frame(win, bg=pal["card"])
        frame.pack(fill="both", expand=True, padx=theme.px(16), pady=theme.px(16))
        box = tk.Text(frame, wrap="char", font=theme.mono(10), bd=0, highlightthickness=0,
                      bg=pal["card_soft"], fg=pal["text"], padx=theme.px(12), pady=theme.px(10))
        box.insert("1.0", text)
        box.configure(state="disabled")
        box.pack(fill="both", expand=True)
        PillButton(self, win, "关闭", command=win.destroy, kind="soft",
                   width=96, height=34).pack(pady=(theme.px(0), theme.px(14)))

    def show_qr(self):
        """Show the selected key as a QR code so a phone can scan the screen."""
        entry = self.selected_entry()
        if not entry:
            messagebox.showwarning(APP_TITLE, "请先在账号库里选中一个账号。")
            return
        if not bgfx.PIL_OK:
            messagebox.showerror(APP_TITLE, "缺少 Pillow 组件，生成不了二维码。")
            return
        pal = self.pal
        name = entry.get("name") or "账号"
        raw = self.vault.key_of(entry)
        try:
            image = qr.render(raw.decode("utf-8", "replace"))
        except Exception as exc:
            self.log("错误", "生成二维码失败：%s" % exc)
            messagebox.showerror(APP_TITLE,
                                 "这个 key 太长或者不规整，画不成二维码（%s）。\n"
                                 "可以先用「存到文件夹」导出，再换别的办法传。" % exc)
            return
        if image is None:
            messagebox.showerror(APP_TITLE, "生成二维码失败，详见运行日志。")
            return
        win = tk.Toplevel(self.root)
        win.title("二维码 - " + name)
        win.configure(bg=pal["window"])
        win.transient(self.root)
        card = tk.Frame(win, bg=pal["card"])
        card.pack(fill="both", expand=True, padx=theme.px(16), pady=theme.px(16))
        label(card, self, name, size=12, color="text").pack(
            anchor="w", padx=theme.px(18), pady=(theme.px(16), theme.px(0)))
        label(card, self, "用手机 App 的「扫一扫」对准这个二维码", size=9,
              color="text_muted").pack(anchor="w", padx=theme.px(18),
                                       pady=(theme.px(4), theme.px(12)))
        holder = tk.Label(card, bg="#FFFFFF", bd=0, highlightthickness=0)
        holder.pack(padx=theme.px(18))
        photo = bgfx.ImageTk.PhotoImage(image)
        holder.configure(image=photo)
        holder.image = photo  # keep a reference, or Tk drops the image
        label(card, self, "指纹 %s · %d 字节" % ((entry.get("fingerprint") or "")[:16], len(raw)),
              size=9, color="text_muted").pack(anchor="w", padx=theme.px(18),
                                               pady=(theme.px(12), theme.px(0)))
        label(card, self,
              "发给别人 = 把账号交出去：对方能一直用，你这边没法远程收回。\n"
              "想让他以后失效：在你自己手机的游戏里改继承码，旧 key 就作废了；\n"
              "改完你也要在这里把 key 更新一遍，否则会把自己顶下线。",
              size=9, color="warn", wraplength=image.width, justify="left").pack(
            anchor="w", padx=theme.px(18), pady=(theme.px(8), theme.px(0)))
        row = tk.Frame(card, bg=pal["card"])
        row.pack(fill="x", padx=theme.px(18), pady=(theme.px(14), theme.px(16)))
        PillButton(self, row, "另存为 PNG", command=lambda: self.save_qr(entry),
                   kind="soft", width=112, height=34).pack(side="left")
        PillButton(self, row, "关闭", command=win.destroy, kind="ghost",
                   width=88, height=34).pack(side="right")
        width = max(theme.px(400), image.width + theme.px(70))
        win.geometry("%dx%d" % (width, win.winfo_reqheight()))
        win.minsize(width, win.winfo_reqheight())

    def save_qr(self, entry):
        if entry is None:
            return
        default = (entry.get("name") or "account").replace("/", "_") + "-qr.png"
        path = filedialog.asksaveasfilename(
            parent=self.root, defaultextension=".png", initialfile=default,
            filetypes=[("PNG 图片", "*.png")])
        if not path:
            return
        try:
            qr.save_png(self.vault.key_of(entry).decode("utf-8", "replace"), path)
        except Exception as exc:
            self.log("错误", "二维码保存失败：%s" % exc)
            messagebox.showerror(APP_TITLE, "保存失败：%s" % exc)
            return
        self.log("账号", "已保存二维码 %s" % path)
        messagebox.showinfo(APP_TITLE, "二维码已保存：\n%s" % path)

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
        self._import_hak_path(path)

    def _import_hak_path(self, path):
        """Import one .hak file (button or drag & drop)."""
        try:
            payload, key = self.vault.read_hak(path)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, "导入失败：%s" % exc)
            self.log("失败", "读取 %s 失败：%s" % (os.path.basename(path), exc))
            return
        self.show_received(key, payload.get("name") or "导入的账号", payload.get("note", ""))

    def update_reconcile_entry(self):
        """Game key changed -> point an existing vault entry at the new key."""
        key = getattr(self, "_reconcile_key", None)
        if not key:
            self.reconcile_bar.pack_forget()
            return
        entry = self.pick_vault_entry(
            "把现在这个 key 更新到哪个账号？",
            "游戏里的 key 变了（改过继承码、重装过都算）。选中原来的账号，"
            "旧 key 会自动留一份备份。")
        if not entry:
            return
        updated, _backup = self.vault.replace_key(entry["id"], key)
        if updated is None:
            messagebox.showwarning(APP_TITLE, "这条账号已经不在库里了，再试一次。")
            return
        self.vault_kind = "account"
        if getattr(self, "kind_seg", None):
            self.kind_seg.set_active("account")
        self.refresh_vault()
        self.reconcile_bar.pack_forget()
        self._reconcile_key = None
        self.log("完成", "已把「%s」换成现在的 key（旧 key 存为备份）"
                         % (updated.get("name") or ""))

    def pick_vault_entry(self, title, hint):
        """Modal list of account entries; returns the chosen entry or None."""
        pal = self.pal
        picked = {"id": None}
        entries = [e for e in self.vault.entries if e.get("kind", "account") == "account"]
        if not entries:
            messagebox.showinfo(APP_TITLE, "账号库里还没有账号，先点「存到账号库」。")
            return None
        win = tk.Toplevel(self.root)
        win.title(title)
        win.configure(bg=pal["window"])
        win.transient(self.root)
        win.grab_set()
        card = tk.Frame(win, bg=pal["card"])
        card.pack(fill="both", expand=True, padx=theme.px(16), pady=theme.px(16))
        label(card, self, title, size=11, color="text").pack(
            anchor="w", padx=theme.px(16), pady=(theme.px(14), theme.px(2)))
        label(card, self, hint, size=9, color="text_muted",
              wraplength=theme.px(420)).pack(anchor="w", padx=theme.px(16),
                                             pady=(theme.px(0), theme.px(10)))
        lb = tk.Listbox(card, height=min(10, max(3, len(entries))), activestyle="none",
                        bg=pal["card_soft"], fg=pal["text"],
                        selectbackground=pal["accent_soft"], selectforeground=pal["text"],
                        highlightthickness=0, bd=0, font=theme.font(10))
        for e in entries:
            lb.insert("end", "%s  ·  %s" % (e.get("name") or "未命名",
                                            e.get("fingerprint") or ""))
        lb.pack(fill="both", expand=True, padx=theme.px(16))
        lb.selection_set(0)

        def ok(_evt=None):
            sel = lb.curselection()
            if not sel:
                return
            picked["id"] = entries[sel[0]].get("id")
            win.destroy()

        row = tk.Frame(card, bg=pal["card"])
        row.pack(fill="x", padx=theme.px(16), pady=(theme.px(12), theme.px(14)))
        PillButton(self, row, "更新这个账号", command=ok, kind="primary",
                   width=128, height=34).pack(side="left")
        PillButton(self, row, "取消", command=win.destroy, kind="ghost",
                   width=84, height=34).pack(side="right")
        lb.bind("<Double-Button-1>", ok)
        win.geometry("%dx%d" % (theme.px(480), win.winfo_reqheight()))
        self.root.wait_window(win)
        return self.vault.get(picked["id"]) if picked["id"] else None

    def show_received(self, key, name, note=""):
        """Incoming key (.hak now, QR later): strong warning + 5s read gate."""
        key = bytes(key)
        digest = hashlib.sha256(key).hexdigest()
        dup = next((e for e in self.vault.entries if e.get("sha256") == digest), None)
        same_name = next((e for e in self.vault.entries
                          if e.get("kind", "account") == "account"
                          and (e.get("name") or "") == name), None)
        pal = self.pal
        win = tk.Toplevel(self.root)
        win.title("收到一份 key")
        win.configure(bg=pal["window"])
        win.transient(self.root)
        win.grab_set()
        card = tk.Frame(win, bg=pal["card"])
        card.pack(fill="both", expand=True, padx=theme.px(16), pady=theme.px(16))
        label(card, self, "收到一份 key 分享", size=12, color="text").pack(
            anchor="w", padx=theme.px(18), pady=(theme.px(16), theme.px(6)))
        label(card, self,
              "这是一把长期有效的登录钥匙（AuthKey），给出去就收不回。\n"
              "想让对方以后失效：在你自己的手机游戏里改继承码，旧 key 就作废了；\n"
              "改完你也要把这里的 key 更新一遍，否则会把自己顶下线。",
              size=9, color="warn", wraplength=theme.px(420), justify="left").pack(
            anchor="w", padx=theme.px(18), pady=(theme.px(0), theme.px(10)))
        label(card, self, "%s · 指纹 %s · %d 字节" % (name, digest[:16], len(key)),
              size=9, color="text_muted").pack(anchor="w", padx=theme.px(18))
        if dup is not None:
            label(card, self, "账号库里已经有这个 key：「%s」" % (dup.get("name") or ""),
                  size=9, color="warn").pack(anchor="w", padx=theme.px(18),
                                             pady=(theme.px(4), theme.px(0)))
        replace_target = same_name if (same_name is not None and same_name is not dup) else None
        primary_text = ("替换「%s」的 key" % (replace_target.get("name") or "")
                        if replace_target is not None else "存到账号库")
        holder = {}

        def do_primary():
            if replace_target is not None:
                entry, _bak = self.vault.replace_key(replace_target["id"], key)
                self.log("账号", "已把「%s」更新为新的 key" % (entry.get("name") or ""))
            else:
                entry, created = self.vault.add(name=name, key=key, note=note,
                                                source="hak")
                self.log("账号", ("已导入 " if created else "已存在 ")
                                 + (entry.get("name") or ""))
            win.destroy()
            self.refresh_vault()
            try:
                self.vault_tree.selection_set(entry["id"])
            except Exception:
                pass

        def do_second():
            base = name or "导入的账号"
            cand, n = base, 2
            while any((e.get("name") or "") == cand for e in self.vault.entries):
                cand = "%s (%d)" % (base, n)
                n += 1
            entry, _created = self.vault.add(name=cand, key=key, note=note, source="hak")
            win.destroy()
            self.refresh_vault()
            self.log("账号", "已另存为「%s」" % cand)

        row = tk.Frame(card, bg=pal["card"])
        row.pack(fill="x", padx=theme.px(18), pady=(theme.px(14), theme.px(16)))
        btn = PillButton(self, row, "请先读上面的提醒（5 秒）", command=do_primary,
                         kind="primary", width=170, height=34)
        btn.set_enabled(False)
        btn.pack(side="left")
        btn2 = None
        if dup is not None or replace_target is not None:
            btn2 = PillButton(self, row, "另存为新条目", command=do_second,
                              kind="ghost", width=118, height=34)
            btn2.set_enabled(False)
            btn2.pack(side="left", padx=(theme.px(8), 0))
        PillButton(self, row, "取消", command=win.destroy, kind="ghost",
                   width=80, height=34).pack(side="right")
        left = [5]

        def tick():
            left[0] -= 1
            if left[0] > 0:
                btn.set_text("请先读上面的提醒（%d 秒）" % left[0])
                win.after(1000, tick)
            else:
                btn.set_text(primary_text)
                btn.set_enabled(True)
                if btn2 is not None:
                    btn2.set_enabled(True)
        win.after(1000, tick)
        win.geometry("%dx%d" % (theme.px(500), win.winfo_reqheight()))

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
