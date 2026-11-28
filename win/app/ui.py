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
from . import autostart
from . import bgfx
from . import bulk
from . import config
from . import diag
from . import dialogs
from . import dnd
from . import logfile
from . import game
from . import keyscan
from . import lanshare
from . import notify as notify_mod
from . import qr
from . import reconcile
from . import theme
from . import tray as tray_mod
from . import updater
from . import vault as vault_mod
from .widgets import (CheckToggle, DeviceList, MiniSlider, NavButton, PillButton,
                      RoundCard, SectionTitle, Segmented, SettingRow, SubNav, chip,
                      entry, label)

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

# 设置页左栏的四个分区，顺序就是界面上从上到下的顺序。
SETTINGS_SECTIONS = (
    ("connect", "连接"),
    ("start", "启动"),
    ("backup", "备份"),
    ("notify", "通知"),
    ("appearance", "外观"),
    ("update", "更新"),
    ("data", "数据"),
)

APP_TITLE = theme.APP_NAME
# Authored at 96 dpi; _relayout scales them through theme.px() so hi-dpi
# monitors get a bigger window instead of a blurred bitmap stretch.
RAIL_W = 180
PAGE_PAD = 16
GAP = 12
LOG_H = 156
# 页面顶部那条「壁纸横幅」：标题压在图上，背景图才是真的看得见
HERO_H = 92
CONTENT_MAX = 1080

HERO_TEXT = {
    "tasks": ("任务", "连接设备，提取或导入 AuthKey"),
    "vault": ("账号库", "保存下来的 key，选中后直接导入"),
    "settings": ("设置", "连接 · 启动 · 备份 · 通知 · 外观 · 更新 · 数据"),
}

# 面板颜色从壁纸平均色里借多少，按 glass 设置（0-100）缩放。
# 左栏面积最大，所以比卡片更吃色；描边只借一点点。

def _glass_tone(base, tone, depth=1.0):
    """Wallpaper colour rescaled to the base colour's brightness.

    Blending straight towards the picture's average turned every panel grey on
    a dark wallpaper, which killed the light theme. Rescaling keeps the panel
    as light as it was and borrows only the hue, so the panels look tinted by
    the picture instead of dirty. depth lets the card also follow a little of
    the picture's brightness (0 keeps it as light as the base, 1 pulls ~30%),
    which is what makes a card read as glass over a dark patch.
    """
    b = theme.hex_to_rgb(base)
    t = theme.hex_to_rgb(tone)
    base_lum = max(8.0, 0.299 * b[0] + 0.587 * b[1] + 0.114 * b[2])
    tone_lum = max(1.0, 0.299 * t[0] + 0.587 * t[1] + 0.114 * t[2])
    k = base_lum / tone_lum
    # pull the brightness towards the wallpaper a bit, but never below 72% or
    # above 128% of the panel's own brightness, so text stays readable
    pull = 1.0 + (tone_lum / base_lum - 1.0) * (0.18 * max(0.0, min(1.0, depth)))
    pull = max(0.86, min(1.12, pull))
    return theme.rgb_to_hex((t[0] * k * pull, t[1] * k * pull, t[2] * k * pull))


# 只有卡片这一层借壁纸色：左栏和整窗保持主题原色，免得整个界面被染灰。
CARD_GLASS_KEYS = (
    ("card", 1.0), ("card_soft", 0.55), ("card_sunken", 0.4),
    ("border", 0.45), ("border_soft", 0.3), ("check_border", 0.4),
    ("btn_hover", 0.7), ("btn_press", 0.7),
    ("soft_hover", 0.6), ("soft_press", 0.6),
    ("head_hover", 0.65),
    # 分段控件的选中胶囊、提示底色：跟着壁纸走才不会在暗处刺眼
    ("accent_soft", 0.8), ("ok_soft", 0.5), ("warn_soft", 0.5), ("err_soft", 0.5),
    ("glyph_off", 0.7),
    # 左栏也吃壁纸色，但它比卡片更“实”一点，导航才压得住
    ("rail", 0.92), ("rail_hover", 0.76),
)

# 这些是“面”，不是“线”：到最透时整块要落到壁纸色上。只换色相、保住原来的
# 亮度是不够的——输入框、分段控件的胶囊照着自己的底色画，一大块浅色板看着
# 还是实心的。
FLAT_GLASS_KEYS = (
    "card", "card_soft", "card_sunken", "btn_hover", "btn_press",
    "soft_hover", "soft_press", "head_hover", "accent_soft", "ok_soft",
    "warn_soft", "err_soft", "rail", "rail_hover", "glyph_off",
)


def _env_float(name, default):
    try:
        return float(os.environ.get(name, ""))
    except (TypeError, ValueError):
        return default


# 玻璃的模糊档位：糊得太轻，行色和背后的图对不上就会露出接缝；糊得太重，
# 卡片就变回一块看不出内容的色板。做成环境变量只为一次拍几组对比图。
GLASS_BLUR = _env_float("HAK_GLASS_BLUR", 22.0)
GLASS_BLUR_SLOPE = _env_float("HAK_GLASS_SLOPE", 14.0)
GLASS_FLAT_X = os.environ.get("HAK_GLASS_FLATX", "0").lower() not in ("0", "false", "no")


class App:
    def __init__(self, root):
        self.root = root
        self.settings = config.Settings()
        # 主题色的底子；_glass_palette() 再从壁纸取色覆盖成磨砂玻璃版
        self.base_pal = theme.palette(self.settings.get("theme"))
        self.pal = self.base_pal
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
        # 卡片通透度只作用在卡片自己身上（_maybe_tint_cards），
        # 整窗调色板保持主题原色。
        self.pal = dict(self.base_pal)
        self.backdrop.palette = self.pal

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
        self._prefetched_zip = ""
        self._prefetch_tag = ""
        self._notified_update = ""
        self.vault_kind = "account"
        self._busy = False
        self.save_dir = self.settings.get("save_dir") or ""
        self.cards = []
        self.glass_extra = None
        self.glass_flat = GLASS_FLAT_X
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
        self._glass_job = None
        self._bg_key = None
        self._hero_photo = None
        self._hero_key = None
        self._hero_geom = None

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
        self.root.bind("<Map>", self._on_first_map, add="+")
        self._init_tray()
        if self.settings.get("low_mode"):
            self._apply_low_mode()
        self._backup_job = None
        self._start_backup_loop()

    # -- window chrome -------------------------------------------------
    def _on_destroy(self, event=None):
        if event is not None and event.widget is not self.root:
            return
        self._closing = True
        for attr in ("_first_job", "_poll_job", "_poll_after", "_flash_job",
                     "_quiet_job", "_auto_check", "_backup_job"):
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
    def _card_palette(self, tone, amount):
        """The palette a card uses when it pretends to be glass.

        Only the card surfaces are mixed towards the wallpaper colour under
        that card, so the left rail stays clean and each card picks up the
        picture right behind it. amount is glass/100.
        """
        pal = dict(self.base_pal)
        if not tone or amount <= 0:
            return pal
        for key, weight in CARD_GLASS_KEYS:
            current = pal.get(key)
            if isinstance(current, str) and current.startswith("#"):
                tinted = _glass_tone(current, tone, amount)
                tinted = theme.blend(current, tinted, min(1.0, amount * weight))
                if key in FLAT_GLASS_KEYS:
                    tinted = theme.blend(tinted, tone, amount)
                pal[key] = tinted
        return pal

    # 这些控件把颜色画进自己的画布里，光改 configure 不够，得让它们重画
    _RENDERABLE = ("PillButton", "CheckToggle", "NavButton", "SubNav")

    def _glass_targets(self, root):
        """One-time index of (widget, option, base colour) inside a surface.

        The settings card alone holds ~370 widgets; walking them with cget()
        for every slider change cost ~150ms. The list is stable, so build it
        once and only replay configure() calls afterwards.
        """
        cached = getattr(root, "_glass_targets", None)
        if cached is not None and cached[3] == self._widget_count(root):
            return cached[:3]
        wanted = set()
        for value in self.base_pal.values():
            if isinstance(value, str) and value.startswith("#"):
                wanted.add(value.lower())
        rows, redraw, segs = [], [], []
        stack = [root]
        stack.extend(root.winfo_children())
        while stack:
            child = stack.pop()
            stack.extend(child.winfo_children())
            for option in ("background", "readonlybackground", "foreground",
                           "highlightbackground", "highlightcolor"):
                try:
                    current = str(child.cget(option)).lower()
                except Exception:
                    continue
                if current in wanted:
                    rows.append((child, option, current))
            name = child.__class__.__name__
            if name == "Segmented":
                segs.append(child)
            elif name in self._RENDERABLE:
                redraw.append(child)
        root._glass_targets = (rows, redraw, segs, self._widget_count(root))
        return rows, redraw, segs

    def _base_key(self):
        """Base colour -> palette key, for the colours that carry meaning."""
        cached = getattr(self, "_key_map", None)
        if cached is not None and cached[0] is self.base_pal:
            return cached[1]
        table = {}
        for key, value in self.base_pal.items():
            if isinstance(value, str) and value.startswith("#"):
                table.setdefault(value.lower(), key)
        self._key_map = (self.base_pal, table)
        return table

    def _hex_weights(self):
        """Map every glassy base colour to (palette key, transparency weight)."""
        cached = getattr(self, "_hex_map", None)
        if cached is not None and cached[0] is self.base_pal:
            return cached[1]
        table = {}
        for key, weight in CARD_GLASS_KEYS:
            value = self.base_pal.get(key)
            if not isinstance(value, str) or not value.startswith("#"):
                continue
            low = value.lower()
            if low not in table or weight > table[low][1]:
                table[low] = (key, weight)
        self._hex_map = (self.base_pal, table)
        return table

    @staticmethod
    def _widget_box(widget, origin):
        """Rectangle of one widget in canvas coordinates (None if unmapped)."""
        x = y = 0
        node = widget
        while node is not None and node is not origin:
            try:
                x += node.winfo_x()
                y += node.winfo_y()
            except Exception:
                return None
            node = node.master
        if node is not origin:
            return None
        return (x, y, widget.winfo_width(), widget.winfo_height())

    @staticmethod
    def _glass_blur(amount):
        """Blur radius used for both the card's patch and the per-widget tint."""
        return GLASS_BLUR + GLASS_BLUR_SLOPE * amount if amount > 0 else 0.0

    def _paint_glass(self, root, amount, tone=None, uniform=False):
        """Retint one surface and everything inside it towards the wallpaper.

        A Tk widget is a rectangle painted in one colour, so "transparency"
        has to be built per widget: each one is pulled towards the picture
        right behind *its own* box, not the card's average. Neighbouring
        rectangles then land on nearly the same colour and the panel stops
        reading as a slab.
        """
        size = (self.canvas.winfo_width(), self.canvas.winfo_height())
        pal = self._card_palette(tone, amount)
        rows, redraw, segs = self._glass_targets(root)
        table = self._hex_weights()
        extra = self._glass_blur(amount)
        sample_extra = extra
        keys = self._base_key()
        panel = self._tinted_panel(pal, tone, amount)
        painted = {}
        # 只要有一个控件还没排好版，这一遍就是半成品：不能把结果当成
        # 「已染过」缓存下来，否则没染上的行会一直亮着
        complete = True
        for widget, option, base in rows:
            if option == "foreground":
                continue
            hit = table.get(base)
            if hit is None:
                continue
            key, weight = hit
            target = base
            if amount > 0:
                local = None
                if not uniform:
                    box = self._widget_box(widget, self.canvas)
                    if box and box[2] > 2 and box[3] > 2:
                        local = self.backdrop.mean(size, box, extra,
                                                   flat=GLASS_FLAT_X)
                    else:
                        complete = False
                    if local is None:
                        # 取不到它底下的颜色，宁可放过这一遍，下次重排再来
                        complete = False
                        continue
                else:
                    local = tone or pal.get(key)
                if not local:
                    complete = False
                    continue
                # 越小比例时越要留住原本的面子，否则界面一开始就散架
                if tone and amount < 0.999:
                    local = theme.blend(local, tone, 0.45 * (1.0 - amount) ** 1.5)
                # 权重只在小比例时有用；滑到底必须让位给壁纸，否则卡片
                # 永远是一块盖住画面的色板
                mix = min(1.0, amount * (weight + (1.0 - weight) * amount))
                target = theme.blend(base, local, mix)
                if key in ("border", "border_soft", "check_border"):
                    # 全透明后描边和底同色，卡片的轮廓会整个消失
                    target = theme.blend(target, "#000000", 0.12 * amount)
                painted[str(widget)] = target
            if not target or target.lower() == base:
                continue
            try:
                widget.configure(**{option: target})
            except Exception:
                pass
        for widget, option, base in rows:
            if option != "foreground":
                continue
            target = base
            if amount > 0:
                # 用这一行最终铺出来的底色判断，而不是整张卡的平均色，
                # 否则浅色的行上会留下白字
                under = self._surface_under(widget, painted)
                if under:
                    target = self._ink(keys.get(base.lower()), under, base)
            if not target or target.lower() == base:
                continue
            try:
                widget.configure(foreground=target)
            except Exception:
                pass
        if amount > 0:
            self._mop_bright(root, amount, sample_extra, tone)
            self._paint_ttk(root, amount, sample_extra)
        saved, self.pal = self.pal, panel
        try:
            for widget in segs:
                widget.pal = self._widget_pal(panel, size, widget, amount,
                                              sample_extra, tone)
                widget._paint()
                # 分段控件里没选中的胶囊是自己的底色，白字压在上面就看不见了
                for lab in getattr(widget, "labels", {}).values():
                    try:
                        lab_bg = str(lab.cget("bg"))
                    except Exception:
                        continue
                    if lab_bg == str(widget.pal.get("accent")):
                        continue
                    try:
                        lab.configure(fg=self._ink("text", lab_bg))
                    except Exception:
                        pass
            for widget in redraw:
                widget.glass_pal = self._widget_pal(panel, size, widget, amount,
                                                    sample_extra, tone)
                # 画布自己的底色也要落在同一块壁纸色上，否则圆角外面那
                # 一圈还是调色板的实色，透出来就是一个个方框
                local = widget.glass_pal.get("_local")
                if local:
                    try:
                        widget.configure(bg=local)
                    except Exception:
                        pass
                else:
                    # 这一遍没拿到它底下的颜色（刚建好、还没排版），自绘控件
                    # 仍然是调色板的实色；别把这张卡记成染好了
                    complete = False
                if isinstance(getattr(widget, "_photos", None), dict):
                    widget._photos.clear()
                widget._render()
        finally:
            self.pal = saved
        return complete

    def _paint_ttk(self, root, amount, extra):
        """Give ttk widgets a style whose colours follow the wallpaper.

        ttk paints through Tk style database entries, not through the
        background option, so the configure() pass above cannot reach it: a
        combobox stayed a flat slab of the card colour in the middle of a
        see-through card. Each widget gets its own derived style name so it
        can use the colour of the patch it actually sits on.
        """
        size = (self.canvas.winfo_width(), self.canvas.winfo_height())
        style = ttk.Style()
        stack = list(root.winfo_children())
        while stack:
            widget = stack.pop()
            stack.extend(widget.winfo_children())
            try:
                klass = widget.winfo_class()
            except Exception:
                continue
            if klass != "TCombobox":
                continue
            box = self._widget_box(widget, self.canvas)
            if not box or box[2] < 4 or box[3] < 4:
                continue
            local = self.backdrop.mean(size, box, extra, flat=GLASS_FLAT_X)
            if not local:
                continue
            name = getattr(widget, "_glass_style", None)
            if not name:
                self._ttk_seq = getattr(self, "_ttk_seq", 0) + 1
                name = "Hak%d.TCombobox" % self._ttk_seq
                widget._glass_style = name
                try:
                    widget.configure(style=name)
                except Exception:
                    continue
            ink = self._ink("text", local)
            edge = theme.blend(local, ink, 0.3)
            accent = self.base_pal.get("accent") or "#2F6BFF"
            sel = theme.blend(local, accent, 0.35)
            style.configure(name, fieldbackground=local, background=local,
                            foreground=ink, arrowcolor=ink, bordercolor=edge,
                            lightcolor=edge, darkcolor=edge, relief="flat",
                            borderwidth=1,
                            padding=(theme.px(6), theme.px(4)))
            style.map(name,
                      fieldbackground=[("readonly", local), ("disabled", local)],
                      foreground=[("readonly", ink), ("disabled", ink)],
                      background=[("active", local), ("pressed", local)],
                      selectbackground=[("readonly", sel)],
                      selectforeground=[("readonly", local)])

    _MOP_SKIP = ("PillButton", "CheckToggle", "NavButton", "SubNav", "Segmented",
                 "RoundCard")

    def _mop_bright(self, root, amount, extra, tone):
        """最后一道清场：把还没被染上的亮底控件压向它底下的壁纸。

        界面里总有些控件的底色不在调色板里（运行时新建的输入框、提示条、
        空态块），逐一遍历调色板抓不到它们，它们就成了一块惨白方片。
        这里只处理「亮到扎眼」的那些，颜色统一走同一套混合，结果和别的
        行一致。
        """
        size = (self.canvas.winfo_width(), self.canvas.winfo_height())
        stack = list(root.winfo_children())
        while stack:
            widget = stack.pop()
            stack.extend(widget.winfo_children())
            if widget.__class__.__name__ in self._MOP_SKIP:
                continue
            try:
                bg = str(widget.cget("bg"))
            except Exception:
                continue
            rgb = theme.hex_to_rgb(bg) if isinstance(bg, str) and bg.startswith("#") else None
            if not rgb:
                continue
            if 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2] < 205:
                continue
            box = self._widget_box(widget, self.canvas)
            local = tone or (self.backdrop.mean(size, box, extra,
                                                flat=GLASS_FLAT_X) if box else None)
            if not local:
                continue
            try:
                widget.configure(bg=theme.blend(bg, local, amount))
            except Exception:
                pass

    def _tinted_panel(self, pal, tone, amount):
        """Palette the hand-drawn widgets paint from: text flips with the panel."""
        panel = dict(pal)
        if not tone or amount <= 0:
            return panel
        for key in ("text", "text_muted", "text_faint"):
            if key in panel:
                panel[key] = theme.blend(panel[key], self._ink(key, tone), amount)
        return panel

    def _widget_pal(self, panel, size, widget, amount, extra, tone=None):
        """Palette for one hand-drawn widget, keyed off its own background.

        Buttons sit on their own colour (accent_soft, card_soft, ...), so they
        cannot borrow the card's average tone: a pale button on a dark card
        would get white text and turn invisible.
        """
        if amount <= 0:
            return panel
        box = self._widget_box(widget, self.canvas)
        local = tone or (self.backdrop.mean(size, box, extra,
                                            flat=GLASS_FLAT_X) if box else None)
        if not local:
            return panel
        out = dict(panel)
        out["_local"] = local
        # 自绘控件（按钮、分段控件）画的是自己那份调色板里的面，而 panel 是按
        # 整张卡的 tone 算的；一个整行宽的胶囊就会比它所在的那一行亮一截，
        # 看起来又是一条横带。让它们也落到自己那块壁纸色上。
        for key, weight in CARD_GLASS_KEYS:
            value = out.get(key)
            if not isinstance(value, str) or not value.startswith("#"):
                continue
            mix = min(1.0, amount * (weight + (1.0 - weight) * amount))
            out[key] = theme.blend(value, local, mix)
        for key in ("text", "text_muted", "text_faint"):
            if key in out:
                out[key] = theme.blend(out[key], self._ink(key, local), amount)
        # 禁用按钮是浅底浅字，字色得按它自己的底色反推，不然白底白字
        if "glyph_off" in out:
            out["glyph_off_line"] = self._ink("text", out["glyph_off"])
        return out

    _INK_LIGHT = {"text": "#EAF0FA", "text_muted": "#BCC7D9", "text_faint": "#A3AEC2"}
    _INK_DARK = {"text": "#13203A", "text_muted": "#5C6B84", "text_faint": "#7E8AA0"}

    def _ink(self, key, background, base=None):
        """Text colour that stays readable on the given background."""
        try:
            rgb = theme.hex_to_rgb(background)
        except Exception:
            return base or self._INK_DARK["text"]
        lum = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
        table = self._INK_DARK if lum > 132 else self._INK_LIGHT
        pick = table.get(key) or base or table["text"]
        # 壁纸平均色正好卡在中间灰度时，按阈值挑出来的那一种会糊在底上；
        # 换到另一边，宁可对比过头也别看不见
        try:
            prgb = theme.hex_to_rgb(pick)
        except Exception:
            return pick
        plum = 0.299 * prgb[0] + 0.587 * prgb[1] + 0.114 * prgb[2]
        if abs(plum - lum) < 62:
            # 同名的淡字色在两边的亮度都靠不住，直接换到对面最重的那一档
            other = self._INK_LIGHT if table is self._INK_DARK else self._INK_DARK
            pick = other["text"]
        return pick

    def _surface_under(self, widget, painted):
        """Colour actually painted behind one widget after retinting."""
        node = widget
        while node is not None:
            hit = painted.get(str(node))
            if hit:
                return hit
            try:
                bg = node.cget("bg")
            except Exception:
                bg = None
            if isinstance(bg, str) and bg.startswith("#") and bg != "":
                return bg
            node = node.master
        return None

    def _paint_card(self, card, tone, amount):
        """Apply (or clear) the see-through look on one card."""
        pal = self._card_palette(tone, amount)
        card.fill_color = pal[card.fill]
        # 描边要跟着玻璃压暗一点：全透明时它按原调色板走，会在卡片外圈
        # 留一道比壁纸亮的线，看着像实心边框
        card.border_color = theme.blend(pal[card.border], "#000000",
                                        0.16 * amount)
        # 卡面铺的就是脚底下那块壁纸：行底都是按位置取的纯色，底下垫上同一
        # 档模糊的图，两者才对得上，卡片才真的透出画面
        card.face_mix = amount
        card.face_extra = self._glass_blur(amount)
        self.glass_extra = card.face_extra
        self.glass_flat = GLASS_FLAT_X
        # 投影是"实心卡片"的语言：全透明时留一圈发黑的边，看着像粗边框
        card.shadow = int(round(44 * (1.0 - amount) ** 2))
        complete = self._paint_glass(card, amount, tone)
        card._key = None
        card.render(force=True)
        return complete

    def _paint_rail(self, amount):
        tone = None
        if amount > 0:
            size = (self.canvas.winfo_width(), self.canvas.winfo_height())
            tone = self.backdrop.sample(size, (0, 0, theme.px(RAIL_W), size[1]),
                                        1.5 + 2.5 * amount)
        self._paint_glass(self.rail, amount, tone, uniform=True)

    @staticmethod
    def _widget_count(widget):
        total = 0
        stack = list(widget.winfo_children())
        while stack:
            child = stack.pop()
            total += 1
            stack.extend(child.winfo_children())
        return total

    def _maybe_tint_cards(self):
        """Retint a card only when its tint inputs changed (not per scroll)."""
        try:
            glass = int(self.settings.get("glass") or 0)
        except (TypeError, ValueError):
            glass = 0
        if not bgfx.PIL_OK:
            return
        amount = max(0.0, min(1.0, glass / 100.0))
        try:
            # 每个控件要按自己所在的位置取色，几何没算完之前 winfo_x 还是旧值
            self.canvas.update_idletasks()
        except Exception:
            pass
        size = (self.canvas.winfo_width(), self.canvas.winfo_height())
        sig = (glass, getattr(self.backdrop, "rev", 0), size, id(self.base_pal))
        ttk_pal = None
        incomplete = 0
        for card in getattr(self, "cards", []):
            if not (card.winfo_exists() and card.winfo_manager()):
                continue
            # 卡片内容会变（导入记录、设备列表），新加的控件不在缓存里，
            # 数量一变就重建一次索引，免得留下没染色的白块
            count = self._widget_count(card)
            if getattr(card, "_glass_count", None) != count:
                card._glass_count = count
                card._glass_targets = None
                card._tint_sig = None
            x, y, width, height = card._box
            if width < 20 or height < 20:
                continue
            if getattr(card, "_tint_sig", None) == sig:
                continue
            tone = None
            if amount > 0:
                # 卡片的平均色必须和它内部铺的那张图用同一档模糊取：一个取
                # 原图、一个取模糊图，在高对比的地方能差出一大截，卡片就会
                # 比它背后那片壁纸亮/暗一整块
                try:
                    tone = self.backdrop.mean(size, (x, y, x + width, y + height),
                                              self._glass_blur(amount))
                except Exception:
                    tone = None
            if self._paint_card(card, tone, amount if tone else 0.0):
                # 只有整张卡都真的染上了才算数，否则下一次重排还得再来
                card._tint_sig = sig
            elif amount > 0:
                # 刚建好的卡片还没排版，取不到它底下的壁纸色：补一次重绘，
                # 否则那一页会一直停在没染色的模样。限次数，别死循环
                incomplete += 1
            if ttk_pal is None and tone:
                ttk_pal = pal = self._card_palette(tone, amount)
        if incomplete:
            self._glass_retry = getattr(self, "_glass_retry", 0) + 1
            if self._glass_retry <= 3:
                self._schedule_visual_refresh()
        else:
            self._glass_retry = 0
        rail = getattr(self, "rail", None)
        if rail is not None and rail.winfo_exists():
            if getattr(self, "_rail_sig", None) != sig:
                self._rail_sig = sig
                self._paint_rail(amount)
        # ttk 控件（设备下拉、滚动条、列表）不吃 configure()，颜色全在 style
        # 里。样式是全局的，必须在所有卡片和左栏都画完之后再定，否则最后
        # 画的左栏会把开关框染成它的深色。
        ttk_pal = ttk_pal or getattr(self, "_ttk_pal", None)
        if ttk_pal is not None and ttk_pal is not getattr(self, "_ttk_pal", None):
            self._ttk_pal = ttk_pal
        try:
            self._build_styles(ttk_pal or self.pal)
        except tk.TclError:
            pass

    def _apply_theme(self, value=None):
        """Switch light/dark in place: rebuild every widget from the new palette."""
        if value is not None:
            self.settings.set("theme", value)
            self.settings.save()
        self.base_pal = theme.palette(self.settings.get("theme"))
        self.pal = self.base_pal
        self.backdrop = bgfx.Backdrop(self.pal)
        self.backdrop.configure(path=self.settings.get("bg_image"),
                                blur=self.settings.get("bg_blur"),
                                alpha=self.settings.get("bg_alpha"))
        self.pal = dict(self.base_pal)
        self.backdrop.palette = self.pal
        self._ttk_pal = None
        self._hero_key = None
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
        button.set(on)
        # A checked box the OS cannot honour would be a lie; grey it out.
        button.set_enabled(not (on and not sys.platform.startswith("win")))

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
    def _build_styles(self, pal=None):
        pal = pal or self.pal
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
                        background=theme.blend(pal["card_soft"], pal["text"], 0.32),
                        darkcolor=pal["card_soft"],
                        lightcolor=pal["card_soft"], troughcolor=pal["card_soft"],
                        bordercolor=pal["card_soft"], arrowcolor=pal["text_muted"],
                        arrowsize=theme.px(12), width=theme.px(11))
        style.map("Vertical.TScrollbar", background=[("active", pal["text_faint"])])
        # 边框用比字段略深一点的同色系：主题的浅边在透出去的卡上会变成
        # 一圈刺眼的白线，纯字段色又会让输入框整个消失
        edge = theme.blend(pal["card_soft"], pal["text"], 0.28)
        style.configure("TCombobox", fieldbackground=pal["card_soft"],
                        background=pal["card_soft"], foreground=pal["text"],
                        arrowcolor=pal["text"],
                        bordercolor=edge, lightcolor=edge, darkcolor=edge,
                        relief="flat", borderwidth=1,
                        padding=(theme.px(6), theme.px(4)))
        style.map("TCombobox",
                  fieldbackground=[("readonly", pal["card_soft"]),
                                    ("disabled", pal["card"])],
                  foreground=[("readonly", pal["text"]),
                              ("disabled", pal["text_faint"])],
                  background=[("active", pal["card_soft"]),
                              ("pressed", pal["card_soft"])],
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

        # 页头横幅：直接把窗口壁纸裁一块贴在原位，再压一层从左到右的暗色
        # 渐变，标题就压在图上。它不透明、也不需要，因为画的就是同一张图。
        self.hero = tk.Canvas(self.canvas, highlightthickness=0, bd=0,
                              bg=pal["window"])
        self.hero_item = self.hero.create_image(0, 0, anchor="nw")
        self.hero_title = self.hero.create_text(
            theme.px(26), theme.px(28), anchor="nw", text="任务",
            fill="#FFFFFF", font=theme.font(17, "bold"))
        self.hero_hint = self.hero.create_text(
            theme.px(28), theme.px(60), anchor="nw", text="",
            fill="#DCE6FF", font=theme.font(9))

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
        brand.pack(fill="x", padx=theme.px(12), pady=(theme.px(20), theme.px(16)))
        self._brand_icon(brand, size=34)
        text_box = tk.Frame(brand, bg=pal["rail"])
        text_box.pack(side="left", padx=(theme.px(9), theme.px(0)))
        self._brand_title = label(text_box, self, theme.APP_NAME, size=9, weight="bold",
                                  bg="rail")
        self._brand_title.pack(anchor="w")
        self._brand_sub = label(text_box, self, theme.APP_SUBTITLE, size=8,
                                color="text_muted", bg="rail")
        self._brand_sub.pack(anchor="w", pady=(theme.px(1), theme.px(0)))

        nav = tk.Frame(self.rail, bg=pal["rail"])
        nav.pack(fill="x", padx=theme.px(10))
        for key, text, glyph in (("tasks", "任务", "▣"),
                                 ("vault", "账号库", "☰"),
                                 ("settings", "设置", "⚙")):
            button = NavButton(self, nav, text, glyph, width=160,
                               command=lambda k=key: self._show_page(k))
            button.pack(fill="x", pady=theme.px(3))
            self.nav[key] = button

        footer = tk.Frame(self.rail, bg=pal["rail"])
        footer.pack(side="bottom", fill="x", padx=theme.px(14), pady=theme.px(14))
        label(footer, self, "v" + theme.APP_VERSION, size=9, color="text_faint",
              bg="rail").pack(anchor="w")
        repo = tk.Label(footer, text="项目主页  ↗", font=theme.font(9),
                        fg=pal["accent"], bg=pal["rail"], bd=0, cursor="hand2")
        repo.pack(anchor="w", pady=(theme.px(2), theme.px(0)))
        repo.bind("<Button-1>", lambda e: self.open_repo())

    def _brand_icon(self, parent, size=38):
        pal = self.pal
        size = theme.px(size)
        box = tk.Canvas(parent, width=size, height=size, bg=pal["rail"],
                        highlightthickness=0, bd=0)
        box.pack(side="left")
        photo = None
        if bgfx.PIL_OK:
            try:
                from PIL import ImageTk
                photo = ImageTk.PhotoImage(bgfx.rounded_rgba(
                    size, size, max(theme.px(8), int(size * 0.34)),
                    theme.hex_to_rgb(pal["accent"]) + (255,), scale=3))
            except Exception:
                photo = None
        if photo is not None:
            box.create_image(0, 0, anchor="nw", image=photo)
            box.image = photo
        else:
            box.configure(bg=pal["accent"])
        box.create_text(size // 2, size // 2 - 1, text="东", font=theme.font(13, "bold"),
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

        # 最近导入不再撑满整页：内容有多高原样多高（最多 5 条），剩下的
        # 空间留给壁纸，否则窗口下半截永远是一大块空白面板。
        self.pages["tasks"] = [(card, self._task_card_height),
                              (recent, self._recent_height)]

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
        card = RoundCard(self)
        body = card.body

        # One card that behaves like a settings window: a short section list
        # on the left, rows on the right, instead of four stacked cards.
        shell = tk.Frame(body, bg=pal["card"])
        shell.pack(fill="both", expand=True)

        side = tk.Frame(shell, bg=pal["card"], width=theme.px(128))
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        label(side, self, "设置", size=9, color="text_faint").pack(
            anchor="w", padx=theme.px(4), pady=(theme.px(4), theme.px(10)))
        self.setting_nav = {}
        for key, text in SETTINGS_SECTIONS:
            item = SubNav(self, side, text,
                          command=lambda k=key: self.show_settings_section(k))
            item.pack(fill="x", pady=theme.px(2))
            self.setting_nav[key] = item

        rule = tk.Frame(shell, bg=pal["border_soft"], width=theme.px(1))
        rule.pack(side="left", fill="y", padx=(theme.px(14), theme.px(0)),
                  pady=theme.px(2))

        self.settings_host = tk.Frame(shell, bg=pal["card"])
        self.settings_host.pack(side="left", fill="both", expand=True,
                                padx=(theme.px(20), theme.px(2)))
        self.settings_sections = {}
        for key, builder in (("connect", self._build_settings_connect),
                             ("start", self._build_settings_start),
                             ("backup", self._build_settings_backup),
                             ("notify", self._build_settings_notify),
                             ("appearance", self._build_settings_appearance),
                             ("update", self._build_settings_update),
                             ("data", self._build_settings_data)):
            frame = tk.Frame(self.settings_host, bg=pal["card"])
            self.settings_sections[key] = frame
            builder(frame)
        # A theme switch rebuilds every page; keep the user on the pane they
        # were looking at instead of jumping back to 连接.
        previous = getattr(self, "settings_section", None)
        self.settings_section = None
        self.show_settings_section(previous or "connect", relayout=False)
        self.pages["settings"] = [(card, None)]

    def show_settings_section(self, key, relayout=True):
        """Swap the settings pane; only the active section stays packed."""
        if key not in self.settings_sections:
            key = "connect"
        self.settings_section = key
        for name, frame in self.settings_sections.items():
            if name == key:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()
        for name, item in self.setting_nav.items():
            item.set_active(name == key)
        if relayout and self.pages.get("settings"):
            self._relayout()
            self.refresh_visuals()

    def _settings_head(self, parent, title, hint):
        pal = self.pal
        box = tk.Frame(parent, bg=pal["card"])
        box.pack(fill="x", pady=(theme.px(2), theme.px(2)))
        label(box, self, title, size=12, weight="bold").pack(anchor="w")
        if hint:
            label(box, self, hint, size=9, color="text_muted").pack(
                anchor="w", pady=(theme.px(3), theme.px(0)))
        return box

    def _settings_group(self, parent, title):
        """MAA-style divider: a hairline plus a small caps section label."""
        pal = self.pal
        box = tk.Frame(parent, bg=pal["card"])
        box.pack(fill="x", pady=(theme.px(20), theme.px(0)))
        tk.Frame(box, bg=pal["border_soft"], height=theme.px(1),
                 bd=0, highlightthickness=0).pack(fill="x")
        label(box, self, title, size=9, weight="bold", color="text_muted").pack(
            anchor="w", pady=(theme.px(8), theme.px(0)))
        return box

    def _settings_row(self, parent, title, hint="", help_text="", top=16,
                      right_expand=False):
        row = SettingRow(self, parent, title, hint, help_text, pad_top=top,
                         right_expand=right_expand)
        row.pack(fill="x", pady=(theme.px(top), theme.px(0)))
        return row

    def _on_auto_reconnect(self, key):
        self.settings.set("auto_reconnect", key == "on")
        self.settings.save()
        self.log("设置", "断线自动重连：%s" % ("开" if key == "on" else "关"))

    def _refresh_adb_path_row(self):
        path = self.settings.get("adb_path") or ""
        if path:
            text = path if len(path) <= 52 else "…" + path[-50:]
            tone = "text"
        else:
            text = "内置 platform-tools（默认）"
            tone = "text_muted"
        try:
            self.adb_path_label.configure(text=text, fg=self.pal[tone])
        except Exception:
            pass
        try:
            self.btn_adb_default.set_enabled(bool(path))
        except Exception:
            pass

    def choose_adb_path(self):
        path = filedialog.askopenfilename(
            parent=self.root, title="选择 adb.exe",
            filetypes=[("adb", "adb.exe"), ("可执行文件", "*.exe"),
                       ("所有文件", "*.*")])
        if not path:
            return
        if os.path.basename(path).lower() != "adb.exe":
            if not messagebox.askyesno(
                    "确认", "选的不是 adb.exe，仍要用它吗？", parent=self.root):
                return
        self._use_adb_path(path)

    def reset_adb_path(self):
        self._use_adb_path("")

    def _use_adb_path(self, path):
        self.settings.set("adb_path", path)
        self.settings.save()
        self._refresh_adb_path_row()
        try:
            self.adb = adb_mod.Adb(path or None)
            self.adb.ensure_server()
        except Exception as exc:
            self.adb = None
            self._set_adb_chip("adb 不可用", "err")
            self.log("错误", "adb 启动失败：%s" % exc)
            return
        self.log("设置", "adb 已切换：%s" % (path or "内置 platform-tools"))
        self.refresh_devices()

    # -- tray / autostart / backup / notify ----------------------------
    def _icon_path(self):
        candidates = []
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            candidates.append(os.path.join(meipass, "assets", "icon.ico"))
        here = os.path.dirname(os.path.abspath(__file__))
        candidates.append(os.path.join(here, "..", "assets", "icon.ico"))
        candidates.append(os.path.join(here, "..", "docs", "icon.ico"))
        for path in candidates:
            if os.path.exists(path):
                return path
        return sys.executable if getattr(sys, "frozen", False) else ""

    @staticmethod
    def _hotkey_combo():
        # MOD_ALT | MOD_CONTROL, 'A'
        return (0x0001 | 0x0002, 0x41)

    def _tray_allowed(self):
        if os.environ.get("HOUSAMO_NO_TRAY") == "1":
            return False
        if os.environ.get("HOUSAMO_NO_ADB") == "1":
            return False  # tests / dev runs: no tray icons piling up
        return tray_mod.available()

    def _init_tray(self):
        self.tray = None
        if not self._tray_allowed():
            return
        try:
            tray = tray_mod.Tray(
                tip="%s · v%s" % (APP_TITLE, theme.APP_VERSION),
                on_show=self._restore_from_tray, on_quit=self._quit_app,
                on_hotkey=self._toggle_window, icon_path=self._icon_path(),
                hotkey=self._hotkey_combo() if self.settings.get("hotkey") else None)
            if not tray.start():
                self.log("托盘", "托盘图标没能创建，关闭窗口仍会直接退出")
                return
            self.tray = tray
            self.root.protocol("WM_DELETE_WINDOW", self._on_close_request)
            self.root.bind("<Unmap>", self._on_unmap, add="+")
            self.log("托盘", "托盘图标已就位，右键有「显示窗口 / 退出」")
        except Exception as exc:
            self.tray = None
            self.log("托盘", "托盘不可用：%s" % exc)

    def _restore_from_tray(self):
        try:
            self.root.deiconify()
            self.root.state("normal")
            self.root.lift()
            self.root.attributes("-topmost", True)
            self.root.after(120, lambda: self.root.attributes("-topmost", False))
            self.root.focus_force()
        except Exception:
            pass

    def _hide_to_tray(self):
        try:
            self.root.withdraw()
        except Exception:
            pass

    def _toggle_window(self):
        try:
            if self.root.state() == "withdrawn":
                self._restore_from_tray()
            else:
                self._hide_to_tray()
        except Exception:
            pass

    def _on_unmap(self, event=None):
        if event is not None and event.widget is not self.root:
            return
        if not self.settings.get("minimize_to_tray") or not getattr(self, "tray", None):
            return
        try:
            if self.root.state() == "iconic":
                self.root.after(1, self._hide_to_tray)
        except Exception:
            pass

    def _on_close_request(self):
        if not self.settings.get("close_to_tray") or not getattr(self, "tray", None):
            self._quit_app()
            return
        self._hide_to_tray()
        try:
            self.tray.notify(APP_TITLE, "还在后台运行，右键托盘图标可以退出。")
        except Exception:
            pass

    def _quit_app(self):
        try:
            if getattr(self, "tray", None):
                self.tray.stop()
        except Exception:
            pass
        try:
            self.log("退出", "程序退出")
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def _on_close_to_tray(self, key):
        self.settings.set("close_to_tray", key == "on")
        self.settings.save()
        self.log("设置", "关闭时留在托盘：%s" % ("开" if key == "on" else "关"))

    def _on_minimize_to_tray(self, key):
        self.settings.set("minimize_to_tray", key == "on")
        self.settings.save()
        self.log("设置", "最小化到托盘：%s" % ("开" if key == "on" else "关"))

    def _on_autostart(self, key):
        ok, detail = autostart.set_enabled(key == "on")
        if not ok:
            self.autostart_seg.set(False)
            self.log("错误", "开机自启没设置成功：%s" % detail)
            messagebox.showwarning(APP_TITLE, "开机自启没设置成功：%s" % detail,
                                   parent=self.root)
        else:
            self.log("设置", "开机自启：%s" % ("开" if key == "on" else "关"))
        self._refresh_autostart_hint()

    def _on_low_mode(self, key):
        self.settings.set("low_mode", key == "on")
        self.settings.save()
        self._apply_low_mode()
        self.log("设置", "低配模式：%s" % ("开" if key == "on" else "关"))

    def _apply_low_mode(self):
        low = bool(self.settings.get("low_mode"))
        for card in getattr(self, "cards", []):
            try:
                card.shadow = 0 if low else 44
            except Exception:
                pass
        try:
            blur = 0 if low else self.settings.get("bg_blur")
            self.backdrop.configure(blur=blur, alpha=self.settings.get("bg_alpha"))
        except Exception:
            pass
        self._bg_key = None
        self._hero_key = None
        self.refresh_visuals()

    def _on_hotkey(self, key):
        want = key == "on"
        if want and getattr(self, "tray", None) is None:
            self._init_tray()
        tray = getattr(self, "tray", None)
        if want and tray is None:
            self.hotkey_seg.set(False)
            self.log("提示", "托盘没起来，全局热键用不了（可以试试以管理员身份运行）")
            return
        self.settings.set("hotkey", want)
        self.settings.save()
        if tray is not None:
            tray.set_hotkey(self._hotkey_combo() if want else None)
        self.log("设置", "全局热键 Ctrl+Alt+A：%s" % ("开" if want else "关"))

    def _on_auto_backup(self, key):
        self.settings.set("auto_backup", key == "on")
        self.settings.save()
        self.log("设置", "定时自动备份：%s" % ("开" if key == "on" else "关"))

    def _on_backup_hours(self, _event=None):
        index = self.backup_hours.current()
        hours = (1, 3, 6, 12, 24)[index] if index >= 0 else 6
        self.settings.set("auto_backup_hours", hours)
        self.settings.save()
        self.log("设置", "备份间隔改成 %d 小时" % hours)

    def _start_backup_loop(self):
        if self._closing:
            return
        self._backup_job = self.root.after(15000, self._backup_tick)

    def _backup_tick(self):
        self._backup_job = None
        if self._closing:
            return
        try:
            if self.settings.get("auto_backup") and self.adb and not self._busy:
                last = float(self.settings.get("last_backup_at") or 0)
                hours = max(1, min(48, int(self.settings.get("auto_backup_hours") or 6)))
                if time.time() - last >= hours * 3600:
                    self.backup_now(True)
        except Exception:
            pass
        try:
            self._backup_job = self.root.after(60000, self._backup_tick)
        except Exception:
            pass

    def backup_now(self, auto=False):
        if not self.adb:
            if not auto:
                self.log("提示", "adb 不可用，没法备份")
            return
        if self._busy:
            if not auto:
                self.log("提示", "正忙着，等这次操作结束再备份")
            return
        dev = self.selected_device()
        if dev is None or not dev.online:
            dev = next((item for item in self.devices if item.online), None)
        if dev is None:
            if not auto:
                self.log("提示", "现在没有在线设备，先连上再备份")
            return
        self.log("备份", "开始自动备份 %s 上的 key" % dev.serial)

        def worker():
            g = self.active_game
            key, source = game.extract(self.adb, dev.serial, g,
                                       lambda m: self.log("备份", m))
            return key, source

        def done(result):
            key, source = result
            name = time.strftime("自动备份 %m-%d %H:%M")
            entry, created = self.vault.add(name=name, key=key, source=source,
                                            device=dev.serial, kind="account",
                                            game=self.active_game.id)
            self.settings.set("last_backup_at", time.time())
            self.settings.save()
            self.refresh_vault()
            self.refresh_overview()
            self._refresh_last_backup()
            if created:
                self.log("完成", "已自动备份：%s" % entry.get("name"))
                if self.settings.get("notify_on_backup"):
                    self._notify("备份完成",
                                 "%s：%s" % (self.active_game.label,
                                            entry.get("name")))
            else:
                self.log("备份", "这个 key 已经在账号库里了")

        self._bg(worker, done)

    def _notify(self, title, text):
        tray = getattr(self, "tray", None)
        if tray is not None and self.settings.get("notify_balloon", True):
            try:
                tray.notify(title, text)
            except Exception:
                pass
        url = self.settings.get("webhook_url") or ""
        if self.settings.get("notify_webhook") and url:
            threading.Thread(
                target=notify_mod.post_webhook, args=(url, title, text),
                daemon=True).start()

    def _on_notify_balloon(self, key):
        self.settings.set("notify_balloon", key == "on")
        self.settings.save()

    def _on_notify_webhook(self, key):
        self.settings.set("notify_webhook", key == "on")
        self.settings.save()
        if key == "on":
            self.test_webhook()

    def test_webhook(self):
        url = self.webhook_entry.get().strip()
        self.settings.set("webhook_url", url)
        self.settings.save()
        if not url:
            self.log("提示", "先填 webhook 地址")
            return
        self.btn_test_webhook.set_enabled(False)
        self.log("通知", "正在发测试消息…")

        def work():
            return notify_mod.post_webhook(
                url, APP_TITLE, "这是一条测试消息，收到说明 webhook 配好了。")

        def done(result):
            ok, detail = result
            self.btn_test_webhook.set_enabled(True)
            if ok:
                self.log("完成", "测试消息已发出：%s" % detail)
            else:
                self.log("错误", "webhook 发送失败：%s" % detail)
                messagebox.showwarning(
                    APP_TITLE, "发送失败：%s" % detail, parent=self.root)

        self._bg(work, done)

    def open_log_folder(self):
        path = logfile.log_dir()
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)
            else:
                webbrowser.open("file://" + path)
        except Exception as exc:
            self.log("错误", "打不开日志目录：%s" % exc)

    def copy_diagnostics(self):
        self.log("提示", "正在生成诊断包…")

        def work():
            dest = os.path.join(logfile.log_dir(), "diagnostics.zip")
            return diag.build_bundle(dest, extra=self._diag_extra())

        def done(result):
            ok, detail = result
            if not ok:
                self.log("错误", "诊断包生成失败：%s" % detail)
                return
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(detail)
            except Exception:
                pass
            self.log("完成", "诊断包已生成，路径已复制：%s" % detail)
            messagebox.showinfo(
                APP_TITLE, "诊断包已生成，路径已复制到剪贴板：\n%s" % detail,
                parent=self.root)

        self._bg(work, done)

    def _diag_extra(self):
        lines = ["在线设备：%d" % sum(1 for d in self.devices if d.online)]
        for dev in self.devices[:8]:
            lines.append("  - %s  online=%s  emulator=%s"
                         % (dev.serial, dev.online, dev.is_emulator))
        return "\n".join(lines)

    # -- settings: connection ------------------------------------------
    def _build_settings_connect(self, parent):
        self._settings_head(parent, "连接", "选模拟器或填地址，任务页用这里连上的设备")

        self._settings_group(parent, "连接方式")
        row = self._settings_row(
            parent, "连接配置", top=8, right_expand=True,
            help_text="自动检测会依次试常见模拟器端口；选具体模拟器会先把地址填好再连。")
        self.connect_profile = ttk.Combobox(
            row.right, state="readonly", font=theme.font(10), width=20,
            values=[text for _key, text, _addr in CONNECT_PROFILES])
        saved = self.settings.get("connect_profile") or "auto"
        self.connect_profile.current(next(
            (i for i, (key, _t, _a) in enumerate(CONNECT_PROFILES) if key == saved), 0))
        self.connect_profile.pack(in_=row.right, side="right",
                                  padx=(theme.px(8), theme.px(0)))
        self.connect_profile.bind("<<ComboboxSelected>>", self._on_connect_profile)
        self.btn_rescan = PillButton(self, row.right, "重新扫描",
                                     command=self.scan_emulators, kind="ghost",
                                     width=92, height=32)
        self.btn_rescan.pack(in_=row.right, side="right")

        row = self._settings_row(
            parent, "连接地址", "多开时端口不同：填 127.0.0.1:端口，也可以只填端口",
            right_expand=True,
            help_text="留空就只连已经连上的设备；回车等同于点「获取设备」。")
        self.addr_var = tk.StringVar()
        self.addr_entry = entry(row.right, self, self.addr_var, width=18)
        self.addr_entry.pack(in_=row.right, side="left", fill="x", expand=True,
                             ipady=theme.px(4))
        self.addr_entry.bind("<Return>", lambda _e: self.connect_address())
        self.btn_get_device = PillButton(self, row.right, "获取设备",
                                        command=self.connect_address, kind="soft",
                                        width=96, height=32)
        self.btn_get_device.pack(in_=row.right, side="right",
                                 padx=(theme.px(8), theme.px(0)))

        self._settings_group(parent, "设备")
        row = self._settings_row(
            parent, "只显示模拟器", "连接里只列模拟器，插着的真机不进列表", top=8)
        self.only_emu_seg = CheckToggle(
            self, row.right, value=bool(self.settings.get("only_emulators")),
            command=self._on_only_emulators)
        self.only_emu_seg.pack(in_=row.right, side="right")

        row = self._settings_row(
            parent, "启动时自动连接", "打开软件就按上面的配置连一次")
        self.auto_connect_seg = CheckToggle(
            self, row.right, value=bool(self.settings.get("auto_connect")),
            command=self._on_auto_connect)
        self.auto_connect_seg.pack(in_=row.right, side="right")

        row = self._settings_row(
            parent, "断线自动重连", "设备掉线后自动按记住的地址重连一次",
            help_text="只在原来连上过的设备消失时生效，每 20 秒最多试一次，"
            "不会一直刷 adb。")
        self.auto_reconnect_seg = CheckToggle(
            self, row.right, value=bool(self.settings.get("auto_reconnect")),
            command=self._on_auto_reconnect)
        self.auto_reconnect_seg.pack(in_=row.right, side="right")

        row = self._settings_row(
            parent, "扫描端口", right_expand=True,
            help_text="重新扫描和自动检测都只试这些端口，逗号分隔；自建多开端口可以加进来。")
        # A 14-port list never fits one line; show a summary and edit the
        # whole list in the themed dialog instead.
        self.ports_var = tk.StringVar(value=self.settings.get("emulator_ports") or "")
        self.ports_summary = label(row.right, self, "", size=9, color="text_muted")
        self.ports_summary.pack(in_=row.right, side="left", fill="x", expand=True,
                                padx=(theme.px(0), theme.px(10)))
        self.btn_edit_ports = PillButton(self, row.right, "编辑",
                                         command=self.edit_scan_ports, kind="ghost",
                                         width=62, height=28)
        self.btn_edit_ports.pack(in_=row.right, side="right")
        self._update_ports_summary()

        row = self._settings_row(
            parent, "记住的设备", "上次连上的设备会记在这里，下次优先连它",
            right_expand=True)
        self.conn_device_label = label(row.right, self, "-", size=9,
                                       color="text_muted", anchor="e")
        self.conn_device_label.pack(in_=row.right, side="left", fill="x", expand=True)
        PillButton(self, row.right, "清除", command=self.forget_device, kind="ghost",
                   width=70, height=28).pack(in_=row.right, side="right")

        self._settings_group(parent, "高级")
        row = self._settings_row(
            parent, "adb 路径", "默认用程序目录里的 platform-tools", top=8,
            right_expand=True,
            help_text="想用本机装好的 adb（比如 Android Studio 自带的）就选它的 "
            "adb.exe；改完立刻启用，不用重启。")
        self.adb_path_label = label(row.right, self, "", size=9, color="text_muted",
                                    anchor="e")
        self.adb_path_label.pack(in_=row.right, side="left", fill="x", expand=True)
        PillButton(self, row.right, "浏览", command=self.choose_adb_path,
                   kind="ghost", width=62, height=28).pack(
            in_=row.right, side="right", padx=(theme.px(8), theme.px(0)))
        self.btn_adb_default = PillButton(self, row.right, "默认",
                                          command=self.reset_adb_path, kind="ghost",
                                          width=56, height=28)
        self.btn_adb_default.pack(in_=row.right, side="right")
        self._refresh_adb_path_row()

        row = self._settings_row(
            parent, "连接测试", "实测一次 adb 往返，确认地址真的连得上",
            right_expand=True,
            help_text="只在这台电脑上跑一次 adb，不会读写任何存档。"
            "耗时包含 adb 启动和一次设备列表查询，是冷启动的真实开销。")
        self.conn_latency_label = label(row.right, self, "--- ms", size=10,
                                        weight="bold", color="text_faint")
        self.conn_latency_label.pack(in_=row.right, side="left",
                                     padx=(theme.px(0), theme.px(10)))
        self.btn_test_conn = PillButton(self, row.right, "连接测试",
                                        command=self.test_connection, kind="soft",
                                        width=100, height=32)
        self.btn_test_conn.pack(in_=row.right, side="right")

    # -- settings: start -----------------------------------------------
    def _check_row(self, parent, title, hint="", help_text="", value=False,
                   command=None, top=14):
        row = self._settings_row(parent, title, hint, help_text=help_text, top=top)
        toggle = CheckToggle(self, row.right, value=bool(value), command=command)
        toggle.pack(in_=row.right, side="right")
        return toggle

    def _build_settings_start(self, parent):
        self._settings_head(parent, "启动", "关窗口、开机自启和性能开关")

        self._settings_group(parent, "托盘")
        self.close_to_tray_seg = self._check_row(
            parent, "关闭时留在托盘", "点右上角 × 只是收进托盘，不退出程序",
            help_text="托盘图标上点右键可以「显示窗口」或「退出」；"
            "没有托盘图标时关窗口就是真的退出。", top=8,
            value=self.settings.get("close_to_tray"),
            command=self._on_close_to_tray)
        self.minimize_to_tray_seg = self._check_row(
            parent, "最小化时收进托盘", "点最小化就直接藏起来，任务栏上不留按钮",
            value=self.settings.get("minimize_to_tray"),
            command=self._on_minimize_to_tray)
        label(parent, self,
              "托盘图标不显示，多半是被 Windows 收进了「^」溢出区；"
              "在任务栏设置里把它拖出来固定住就行。",
              size=9, color="text_faint", wraplength=theme.px(520)).pack(
            anchor="w", pady=(theme.px(10), theme.px(0)))

        self._settings_group(parent, "开机")
        self.autostart_seg = self._check_row(
            parent, "开机自动启动", "登录 Windows 时在后台打开，不弹窗打扰",
            help_text="只写当前用户的注册表 Run 项，不需要管理员权限，"
            "关掉这个开关就从注册表里删掉。", top=8,
            value=autostart.enabled(), command=self._on_autostart)
        self.autostart_hint = label(parent, self, "", size=9,
                                    color="text_muted")
        self.autostart_hint.pack(anchor="w", pady=(theme.px(4), theme.px(0)))
        self._refresh_autostart_hint()

        self._settings_group(parent, "性能")
        self.low_mode_seg = self._check_row(
            parent, "低配模式", "关掉卡片阴影和壁纸模糊，老机器更顺滑",
            help_text="只影响绘制，不影响功能；开着壁纸时会自动降低取色开销。",
            top=8, value=self.settings.get("low_mode"),
            command=self._on_low_mode)
        self.hotkey_seg = self._check_row(
            parent, "全局热键", "Ctrl+Alt+A 显示或隐藏窗口",
            help_text="在任何程序里都能用。如果热键被别的软件占了，"
            "开关会自己弹回去。", value=self.settings.get("hotkey"),
            command=self._on_hotkey)

    def _refresh_autostart_hint(self):
        try:
            command = autostart.launcher_command()
            if autostart.enabled():
                text = "已写进注册表：" + (command or "")
            else:
                text = "未开启"
            self.autostart_hint.configure(text=text)
        except Exception:
            pass

    # -- settings: backup ----------------------------------------------
    def _build_settings_backup(self, parent):
        self._settings_head(parent, "备份", "定时把设备上的 AuthKey 存进账号库")

        self.auto_backup_seg = self._check_row(
            parent, "定时自动备份", "开着的时候每隔一段时间自动提取一次",
            help_text="只在北京时间整点后第一次检查时触发；没连设备或正忙"
            "就跳过，不会堆任务。", top=10,
            value=self.settings.get("auto_backup"), command=self._on_auto_backup)

        row = self._settings_row(parent, "备份间隔", "两次自动备份之间的小时数")
        self.backup_hours = ttk.Combobox(
            row.right, state="readonly", font=theme.font(10), width=10,
            values=["1 小时", "3 小时", "6 小时", "12 小时", "24 小时"])
        hours = int(self.settings.get("auto_backup_hours") or 6)
        choice = {1: 0, 3: 1, 6: 2, 12: 3, 24: 4}.get(hours, 2)
        self.backup_hours.current(choice)
        self.backup_hours.pack(in_=row.right, side="right")
        self.backup_hours.bind("<<ComboboxSelected>>", self._on_backup_hours)

        row = self._settings_row(
            parent, "上次备份", "自动备份成功后会更新", right_expand=True)
        self.last_backup_label = label(row.right, self, "", size=9,
                                       color="text_muted", anchor="e")
        self.last_backup_label.pack(in_=row.right, side="left", fill="x",
                                    expand=True, padx=(theme.px(0), theme.px(10)))
        self.btn_backup_now = PillButton(self, row.right, "立即备份",
                                         command=lambda: self.backup_now(False),
                                         kind="primary", width=96, height=30)
        self.btn_backup_now.pack(in_=row.right, side="right")
        self._refresh_last_backup()

        row = self._settings_row(parent, "旧备份保留",
                                 "导入新账号时自动存的那份「导入前备份」")
        self.backup_seg2 = Segmented(
            self, row.right,
            [("all", "全部"), ("10", "最近 10 份"), ("30d", "最近 30 天")],
            active=self.settings.get("backup_keep"), command=self._on_backup_keep,
            pad_x=theme.px(10))
        self.backup_seg2.pack(in_=row.right, side="right")

        label(parent, self,
              "自动备份会在账号库里记一条「自动备份 月-日 时:分」，"
              "和其它账号一样可以导入、导出和删除。",
              size=9, color="text_faint", wraplength=theme.px(520)).pack(
            anchor="w", pady=(theme.px(14), theme.px(0)))

    def _refresh_last_backup(self):
        try:
            last = float(self.settings.get("last_backup_at") or 0)
        except Exception:
            last = 0
        if last <= 0:
            text = "还没有备份过"
        else:
            text = time.strftime("%m-%d %H:%M", time.localtime(last))
            self.last_backup_label.configure(fg=self.pal["text"])
            self.last_backup_label.configure(text=text)
            return
        self.last_backup_label.configure(text=text, fg=self.pal["text_muted"])

    # -- settings: notify ----------------------------------------------
    def _build_settings_notify(self, parent):
        self._settings_head(parent, "通知", "备份完成、发现新版本时提醒你")

        self._settings_group(parent, "提醒方式")
        self.notify_balloon_seg = self._check_row(
            parent, "托盘气泡", "在右下角弹一条气泡，几秒后自动消失",
            top=8, value=self.settings.get("notify_balloon"),
            command=self._on_notify_balloon)
        self.notify_webhook_seg = self._check_row(
            parent, "网页通知", "把消息发到群里，人不在电脑前也能看到",
            help_text="支持飞书、钉钉、Discord、Slack 和 Telegram 的"
            "机器人 webhook；地址只存在本机。",
            value=self.settings.get("notify_webhook"),
            command=self._on_notify_webhook)

        row = self._settings_row(parent, "Webhook 地址", right_expand=True,
                                 help_text="在群聊里添加「自定义机器人」拿到的"
                                 "那条 https:// 地址，整条复制进来。")
        self.webhook_entry = entry(row.right, self)
        self.webhook_entry.pack(in_=row.right, side="left", fill="x", expand=True)
        self.webhook_entry.insert(0, self.settings.get("webhook_url") or "")
        self.btn_test_webhook = PillButton(self, row.right, "发测试",
                                           command=self.test_webhook, kind="ghost",
                                           width=76, height=28)
        self.btn_test_webhook.pack(in_=row.right, side="right",
                                   padx=(theme.px(8), theme.px(0)))

        self._settings_group(parent, "什么时候提醒")
        self.notify_backup_seg = self._check_row(
            parent, "备份完成", "自动备份成功后发一条", top=8,
            value=self.settings.get("notify_on_backup"),
            command=lambda key: self._set_notify_flag("notify_on_backup", key))
        self.notify_update_seg = self._check_row(
            parent, "发现新版本", "启动检查到新版本时发一条",
            value=self.settings.get("notify_on_update"),
            command=lambda key: self._set_notify_flag("notify_on_update", key))

    def _set_notify_flag(self, key, value):
        self.settings.set(key, value == "on")
        self.settings.save()

    # -- settings: appearance ------------------------------------------
    def _build_settings_appearance(self, parent):
        pal = self.pal
        self._settings_head(parent, "外观", "背景图、模糊度、主题，改完立刻生效")

        block = tk.Frame(parent, bg=pal["card"])
        block.pack(fill="x", pady=(theme.px(12), theme.px(0)))
        left = tk.Frame(block, bg=pal["card"])
        left.pack(side="left", fill="x", expand=True)
        label(left, self, "背景图", size=10, weight="bold").pack(anchor="w")
        self.bg_name_label = label(left, self, "还没有选择背景图", size=9,
                                   color="text_muted")
        self.bg_name_label.pack(anchor="w", pady=(theme.px(3), theme.px(0)))
        self.bg_note_label = label(
            left, self, "支持 png / jpg / bmp / webp，会复制一份到应用数据目录",
            size=9, color="text_faint", wraplength=theme.px(300))
        self.bg_note_label.pack(anchor="w", pady=(theme.px(2), theme.px(0)))

        right = tk.Frame(block, bg=pal["card"])
        right.pack(side="right")
        self.thumb_holder = tk.Frame(right, bg=pal["card_soft"],
                                     width=theme.px(132), height=theme.px(74),
                                     highlightthickness=1,
                                     highlightbackground=pal["border"])
        self.thumb_holder.pack(side="left")
        self.thumb_holder.pack_propagate(False)
        self.thumb_label = tk.Label(self.thumb_holder, bg=pal["card_soft"], bd=0,
                                    fg=pal["text_faint"], font=theme.font(9),
                                    text="无背景图")
        self.thumb_label.pack(fill="both", expand=True)
        col = tk.Frame(right, bg=pal["card"])
        col.pack(side="left", padx=(theme.px(12), theme.px(0)))
        PillButton(self, col, "选择图片", command=self.choose_background,
                   kind="primary", width=104, height=32).pack()
        PillButton(self, col, "清除", command=self.clear_background, kind="ghost",
                   width=104, height=30).pack(pady=(theme.px(6), theme.px(0)))

        self.blur_value = tk.IntVar(value=int(self.settings.get("bg_blur")))
        row = self._settings_row(
            parent, "模糊", "数值越大背景越虚化", right_expand=True,
            help_text="背景会先按窗口尺寸裁切再虚化，模糊越大越省事，"
            "文字也更好读。")
        self.blur_readout = label(row.right, self, "%d px" % self.blur_value.get(),
                                  size=10, weight="bold", color="accent")
        self.blur_readout.pack(in_=row.right, side="right",
                               padx=(theme.px(10), theme.px(0)))
        self.blur_slider = MiniSlider(self, row.right, value=self.blur_value.get(),
                                      from_=0, to=60, on_change=self._on_blur_change,
                                      width=200, height=24)
        self.blur_slider.pack(in_=row.right, side="right", fill="x", expand=True)

        self.alpha_value = tk.IntVar(value=int(self.settings.get("bg_alpha")))
        row = self._settings_row(
            parent, "不透明度", "越低背景越接近纯色，文字更好读", right_expand=True,
            help_text="调低一点，深色文字压在花哨背景上也看得清。")
        self.alpha_readout = label(row.right, self, "%d %%" % self.alpha_value.get(),
                                   size=10, weight="bold", color="accent")
        self.alpha_readout.pack(in_=row.right, side="right",
                                padx=(theme.px(10), theme.px(0)))
        self.alpha_slider = MiniSlider(self, row.right, value=self.alpha_value.get(),
                                       from_=0, to=100, on_change=self._on_alpha_change,
                                       width=200, height=24)
        self.alpha_slider.pack(in_=row.right, side="right", fill="x", expand=True)

        self.glass_value = tk.IntVar(value=int(self.settings.get("glass")))
        row = self._settings_row(
            parent, "卡片透明度", "越大卡片越透，底下壁纸的色调越明显",
            right_expand=True,
            help_text="卡片本身是一块面板，Tk 的控件不能按像素透明，"
            "所以这里让它取底下那块壁纸的颜色来染，看起来像磨砂玻璃；"
            "调到 100 基本就和背景同一个色调了。")
        self.glass_readout = label(row.right, self, "%d %%" % self.glass_value.get(),
                                   size=10, weight="bold", color="accent")
        self.glass_readout.pack(in_=row.right, side="right",
                                padx=(theme.px(10), theme.px(0)))
        self.glass_slider = MiniSlider(self, row.right, value=self.glass_value.get(),
                                       from_=0, to=100, on_change=self._on_glass_change,
                                       width=200, height=24)
        self.glass_slider.pack(in_=row.right, side="right", fill="x", expand=True)
        # 松手才重建界面：拖动过程中重建会把正在拖的滑块直接销毁
        self.glass_slider.bind("<ButtonRelease-1>",
                               lambda e: self._commit_glass(), add="+")

        row = self._settings_row(parent, "主题", "浅色和深色两套配色")
        self.theme_seg = Segmented(
            self, row.right, [("light", "浅色"), ("dark", "深色")],
            active=self.settings.get("theme"), command=self._on_theme_change,
            pad_x=theme.px(10))
        self.theme_seg.pack(in_=row.right, side="right")

        row = self._settings_row(
            parent, "防止截屏", "系统截图 / 录屏里这个窗口会变黑",
            help_text="用的是 Windows 10 2004 起的窗口捕获隐藏；只对系统截图"
            "和录屏有效，手机拍屏幕挡不住。")
        self.btn_capture = CheckToggle(
            self, row.right, value=bool(self.settings.get("capture_guard")),
            command=lambda _k: self.toggle_capture_guard())
        self.btn_capture.pack(in_=row.right, side="right")

        row = self._settings_row(
            parent, "恢复默认外观", "模糊、不透明度和卡片透明度一起复位")
        PillButton(self, row.right, "恢复默认外观", command=self.reset_appearance,
                   kind="ghost", width=132, height=32).pack(in_=row.right, side="right")

        label(parent, self, "这些选项只影响界面显示，不会改动原图文件",
              size=9, color="text_faint", wraplength=theme.px(520)).pack(
            anchor="w", pady=(theme.px(14), theme.px(0)))

    # -- settings: update ----------------------------------------------
    def _build_settings_update(self, parent):
        self._settings_head(parent, "更新", "启动时自动检查，发现新版本会弹窗提示")

        row = self._settings_row(parent, "版本", top=10, right_expand=True)
        self.update_version_label = label(
            row.right, self, "当前版本 v" + theme.APP_VERSION, size=9,
            color="text_muted", anchor="e")
        self.update_version_label.pack(in_=row.right, side="left", fill="x",
                                       expand=True)
        self.btn_check_update = PillButton(
            self, row.right, "检查更新", command=lambda: self.check_update(True),
            kind="ghost", width=104, height=32)
        self.btn_check_update.pack(in_=row.right, side="right")

        row = self._settings_row(parent, "更新源", "自动会在 GitHub 和镜像之间择优")
        self.update_source_seg = Segmented(
            self, row.right,
            [("auto", "自动"), ("github", "GitHub"), ("mirror", "镜像")],
            active=self.settings.get("update_source"),
            command=self._on_update_source, pad_x=theme.px(10))
        self.update_source_seg.pack(in_=row.right, side="right")

        row = self._settings_row(
            parent, "自动检查更新", "打开软件时在后台查一次，有新版本才提示",
            help_text="只查版本号，不会自动下载；点「检查更新」才会马上去查。")
        self.auto_check_seg = CheckToggle(
            self, row.right, value=bool(self.settings.get("auto_check_update")),
            command=self._on_auto_check_update)
        self.auto_check_seg.pack(in_=row.right, side="right")

        row = self._settings_row(
            parent, "自动下载新版本", "查到新版本就在后台把安装包下好",
            help_text="只是提前下载，什么时候装还是你自己点「立即更新」。")
        self.auto_download_seg = CheckToggle(
            self, row.right, value=bool(self.settings.get("auto_download_update")),
            command=self._on_auto_download_update)
        self.auto_download_seg.pack(in_=row.right, side="right")

        row = self._settings_row(parent, "状态", right_expand=True)
        self.update_status = label(row.right, self, "启动时会自动检查一次", size=9,
                                   color="text_muted", anchor="e")
        self.update_status.pack(in_=row.right, side="left", fill="x", expand=True)
        self.btn_view_log = PillButton(self, row.right, "查看日志",
                                       command=self.open_update_log, kind="ghost",
                                       width=88, height=30)
        self.btn_install_update = PillButton(
            self, row.right, "立即更新", command=self.do_update, kind="primary",
            width=104, height=30)

        label(parent, self,
              "Windows 版会下载新包并原地替换，不用手动装；发现新版本时"
              "任务页顶部也会出现提示条。",
              size=9, color="text_faint", wraplength=theme.px(520)).pack(
            anchor="w", pady=(theme.px(14), theme.px(0)))

    # -- settings: data ------------------------------------------------
    def _build_settings_data(self, parent):
        pal = self.pal
        self._settings_head(parent, "数据", "全部读写都在本机完成，不上传任何数据")
        self.data_rows = {}
        rows = (("data_dir", "应用数据目录", "配置、背景图和 adb 组件都在这里"),
                ("vault", "当前游戏库", "备份的 AuthKey 存在这个目录"),
                ("save_dir", "保存位置", ""),
                ("adb", "adb 组件", "自带在应用目录里，不装系统 adb 也能用"))
        for key, title, hint in rows:
            row = self._settings_row(parent, title, hint, top=10,
                                     right_expand=True)
            value = label(row.right, self, "-", size=9, color="text", anchor="e")
            value.pack(in_=row.right, side="left", fill="x", expand=True)
            self.data_rows[key] = value
        label(parent, self,
              "「保存位置」既是提取时的导出目录，也是「打包导出全部」的 zip 落点"
              "（每个游戏一个子文件夹）",
              size=9, color="text_faint", wraplength=theme.px(520)).pack(
            anchor="w", pady=(theme.px(10), theme.px(0)))

        row = self._settings_row(parent, "打开与备份", top=12)
        PillButton(self, row.right, "复制路径", command=self.copy_data_dir,
                   kind="ghost", width=88, height=30).pack(
            in_=row.right, side="right")
        PillButton(self, row.right, "打开数据目录", command=self.open_data_dir,
                   kind="ghost", width=118, height=30).pack(
            in_=row.right, side="right", padx=(0, theme.px(8)))

        row = self._settings_row(parent, "应用锁", "开启后每次进软件要输密码")
        self.lock_value = label(row.right, self, "未开启", size=9, color="text",
                                anchor="e")
        self.lock_value.pack(in_=row.right, side="left", fill="x", expand=True,
                             padx=(theme.px(0), theme.px(10)))
        self.btn_lock = PillButton(self, row.right, "开启",
                                   command=self.toggle_app_lock, kind="ghost",
                                   width=76, height=30)
        self.btn_lock.pack(in_=row.right, side="right")

        row = self._settings_row(parent, "日志与诊断", right_expand=True,
                                 help_text="诊断包里有运行日志、环境信息和打码后的"
                                 "设置，出问题时发给开发者最快。")
        self.btn_open_log = PillButton(self, row.right, "打开日志",
                                       command=self.open_log_folder, kind="ghost",
                                       width=88, height=30)
        self.btn_open_log.pack(in_=row.right, side="right")
        self.btn_diag = PillButton(self, row.right, "生成诊断包",
                                   command=self.copy_diagnostics, kind="ghost",
                                   width=104, height=30)
        self.btn_diag.pack(in_=row.right, side="right",
                           padx=(0, theme.px(8)))

        row = self._settings_row(parent, "关于", "开源项目，反馈和更新都在项目主页",
                                 right_expand=True)
        self.about_version_label = label(row.right, self, "v" + theme.APP_VERSION,
                                        size=9, color="text_muted", anchor="e")
        self.about_version_label.pack(in_=row.right, side="left", fill="x",
                                      expand=True)
        PillButton(self, row.right, "项目主页",
                   command=lambda: self.open_url(theme.REPO_URL), kind="ghost",
                   width=88, height=28).pack(in_=row.right, side="right")

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

    def _recent_height(self):
        """Recent-imports panel: as tall as its rows need, capped."""
        card = getattr(self, "_recent_card", None)
        if card is None:
            return theme.px(200)
        return min(max(theme.px(170), card.required_height()), theme.px(330))

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
        hero_h = theme.px(HERO_H)
        page_top = page_pad + hero_h + gap
        base = page_top + page_pad
        # A window squashed below the authored minimum starves the page: first
        # give the log panel the space back, then drop it, then scroll.
        top_area = height - base - gap - log_h
        log_visible = True
        if top_area < wanted:
            log_h = max(theme.px(96), log_h - (wanted - top_area))
            top_area = height - base - gap - log_h
        if top_area < wanted:
            log_visible = False
            log_h = 0
            top_area = height - base
        overflow = max(0, wanted - top_area)
        offset = self._scroll.get(self.page, 0)
        offset = max(0, min(offset, overflow))
        self._scroll[self.page] = offset
        self._overflow = overflow
        log_y = height - page_pad - log_h
        if not log_visible:
            self.log_card.place_forget()

        self._place_page_scrollbar(width, page_top, page_pad, top_area, overflow,
                                   offset)
        self.rail.place(x=0, y=0, width=rail_w, relheight=1)
        self.rail_line.place(x=rail_w - 1, y=0, width=theme.px(1), relheight=1)
        avail = max(theme.px(360), width - rail_w - 2 * page_pad)
        content_w = min(avail, theme.px(CONTENT_MAX))
        # 内容居中：窗口再宽，卡片也不会拉成一条，两边留着壁纸
        x0 = rail_w + page_pad + max(0, (avail - content_w) // 2)
        self._hero_geom = (x0, page_pad, content_w, hero_h)
        self.hero.place(x=x0, y=page_pad, width=content_w, height=hero_h)
        # 页头跟着页/尺寸走；放在这里，切页后即使没有整窗重绘也不会停在旧标题
        self._render_hero()
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
            y = page_top - offset
            for card, h in page_specs:
                card_h = self._spec_height(h) or fill_h
                card.layout(x0, y, content_w, card_h)
                y += card_h + gap
        # 卡片位置定了才知道它底下压着壁纸的哪一块，取色放在最后
        self._maybe_tint_cards()

    def _place_page_scrollbar(self, width, page_top, page_pad, top_area, overflow,
                              offset):
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
        self.page_scroll.place(x=width - page_pad - bar_w, y=page_top,
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
        self._render_hero()
        self._maybe_tint_cards()
        for card in self.cards:
            if card is self.log_card or card.winfo_manager():
                card.render()

    def _on_first_map(self, event=None):
        """First real map: sizes are only known now, so repaint once."""
        if event is not None and event.widget is not self.root:
            return
        if getattr(self, "_mapped_once", False):
            return
        self._mapped_once = True
        # Map fires before Tk has a real size for the canvas, so lay out once
        # more from the event loop once the window is actually on screen.
        self._later(self._apply_layout)

    def _render_hero(self):
        """Paint the page banner: the wallpaper itself, dark on the left."""
        title, hint = HERO_TEXT.get(self.page, ("", ""))
        self.hero.itemconfigure(self.hero_title, text=title)
        self.hero.itemconfigure(self.hero_hint, text=hint)
        # The geometry _relayout just applied is known before Tk has processed
        # the place(), so prefer it over winfo_* (which still reports 1x1 on
        # the very first pass and would leave the banner blank).
        geom = self._hero_geom
        if geom:
            x, y, width, height = geom
        else:
            x, y = self.hero.winfo_x(), self.hero.winfo_y()
            width = self.hero.winfo_width()
            height = self.hero.winfo_height()
        if width <= 8 or height <= 8:
            return
        if not bgfx.PIL_OK or bgfx.ImageTk is None:
            self.hero.configure(bg=self.pal["accent"])
            return
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        if canvas_w <= 1 or canvas_h <= 1:
            return
        key = (self.page, width, height, x, y, canvas_w, canvas_h,
               getattr(self.backdrop, "rev", 0), id(self.pal))
        if key == self._hero_key and self._hero_photo is not None:
            return
        try:
            img = self.backdrop.hero_image((canvas_w, canvas_h),
                                           (x, y, x + width, y + height),
                                           radius=theme.px(18))
            self._hero_photo = bgfx.ImageTk.PhotoImage(img)
            self.hero.itemconfigure(self.hero_item, image=self._hero_photo)
            self._hero_key = key
        except Exception:
            pass

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
                self.adb = adb_mod.Adb(
                    self.settings.get("adb_path") or None)
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
        # 壁纸换了，面板的取色也要跟着换 -> 整个界面重建一次
        self._apply_theme(None)
        self.log("设置", "背景图已更新：%s" % os.path.basename(path))

    def clear_background(self):
        if not self.settings.get("bg_image"):
            return
        config.clear_background()
        self.settings.set("bg_image", "")
        self.backdrop.configure(path="")
        self._apply_theme(None)
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

    def _on_glass_change(self, value):
        value = int(round(value))
        self.glass_value.set(value)
        self.glass_readout.configure(text="%d %%" % value)
        self.settings.set("glass", value, save=False)

    def _commit_glass(self):
        # 重染卡片要把卡里几百个控件重新上色，所以松手才做；
        # 拖动过程中只更新读数，手感反而更顺。
        self.settings.save()
        for card in self.cards:
            card._tint_sig = None
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
        self.settings.set("glass", config.DEFAULTS["glass"], save=False)
        self.backdrop.configure(blur=config.DEFAULTS["bg_blur"],
                               alpha=config.DEFAULTS["bg_alpha"])
        self.settings.save()
        self._apply_theme(None)
        self.show_settings_section("appearance", relayout=True)
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
            if (self.settings.get("auto_download_update")
                    and tag != getattr(self, "_prefetch_tag", None)):
                self._prefetch_update(tag)
            if tag != getattr(self, "_notified_update", None):
                self._notified_update = tag
                if self.settings.get("notify_on_update"):
                    self._notify("发现新版本", "%s 可以更新了。" % tag)
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
        if not self.settings.get("auto_check_update"):
            return
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

    def _prefetch_update(self, tag):
        """Download the new package in the background so 立即更新 feels instant."""
        asset = self.update_asset
        if not asset:
            return
        self._prefetch_tag = tag
        self._prefetched_zip = ""
        self.log("更新", "在后台下载 %s 的安装包…" % tag)

        def work():
            try:
                return updater.download(asset["url"], asset.get("digest", ""),
                                        lambda _m: None)
            except Exception:
                return ""

        def done(path):
            if self._prefetch_tag != tag:
                return
            if path:
                self._prefetched_zip = path
                self.update_status.configure(
                    text="发现新版本 %s（安装包已下好）" % tag, fg=self.pal["accent"])
                self.log("更新", "安装包已经下好，点「立即更新」会更快")
            else:
                self.log("更新", "后台下载没成功，点「立即更新」时会再试一次")

        def run():
            result = work()
            try:
                self._later(done, result)
            except Exception:
                pass

        threading.Thread(target=run, daemon=True).start()

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
            zip_path = ""
            cached = getattr(self, "_prefetched_zip", "")
            if cached and getattr(self, "_prefetch_tag", "") == tag \
                    and os.path.exists(cached):
                self.log("更新", "用已经下好的安装包")
                zip_path = cached
            if not zip_path:
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
            self._later(self.log, tag, message)
            return
        try:
            logfile.write(tag, message)
        except Exception:
            pass
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

    def _later(self, func, *args):
        """Schedule a UI callback from a worker thread, tolerating teardown."""
        try:
            self.root.after(0, func, *args)
        except Exception:
            pass

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
            self._later(self._finish, result, error, on_done)

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
                self._later(self._installed_done, g.id, serial, ok)

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
        if not any(dev.online for dev in self.devices):
            self._maybe_reconnect()
        # 设备列表/连接行会把控件换掉，新控件没进过染色索引，补一遍
        self._schedule_visual_refresh()

    def _maybe_reconnect(self):
        """One throttled / re-connect to the last good address when it vanishes."""
        if not self.adb or not self.settings.get("auto_reconnect"):
            return
        serial = self.settings.get("preferred_serial") or ""
        if not serial:
            return
        now = time.time()
        if now - getattr(self, "_reconnect_at", 0.0) < 20:
            return
        if ":" not in serial and not serial.startswith("emulator-"):
            return  # usb devices come back by themselves via the poll
        self._reconnect_at = now

        def work():
            try:
                ok, _text = self.adb.connect(serial, timeout=6)
            except Exception as exc:
                self.log("设备", "重连失败：%s" % exc)
                return
            if ok:
                self.log("设备", "设备掉线，已自动重连 %s" % serial)
                self._later(self.refresh_devices)
        threading.Thread(target=work, daemon=True).start()

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

    def test_connection(self):
        """Time one real adb call so the row can show a cold round trip."""
        widget = getattr(self, "conn_latency_label", None)
        button = getattr(self, "btn_test_conn", None)
        if widget is None:
            return
        if not self.adb:
            widget.configure(text="adb 不可用", fg=self.pal["err"])
            self.log("错误", "adb 组件不可用，没法测连接")
            return
        widget.configure(text="测量中…", fg=self.pal["text_muted"])
        if button is not None:
            button.set_enabled(False)

        def runner():
            started = time.time()
            ok = True
            count = 0
            try:
                count = len(self.adb.devices())
            except Exception:
                ok = False
            ms = (time.time() - started) * 1000.0

            def report():
                if button is not None:
                    button.set_enabled(True)
                if not ok:
                    widget.configure(text="测量失败", fg=self.pal["err"])
                    self.log("失败", "连接测试失败：adb 没有返回设备列表")
                    return
                if ms < 400:
                    tone = self.pal["ok"]
                elif ms < 1200:
                    tone = self.pal["accent"]
                else:
                    tone = self.pal["warn"]
                widget.configure(text="%d ms · %d 台在线设备" % (round(ms), count),
                                 fg=tone)
                self.log("设置", "连接测试：adb 往返 %d ms，%d 台设备在线"
                         % (round(ms), count))

            try:
                self._later(report)
            except Exception:
                pass

        threading.Thread(target=runner, daemon=True).start()

    def _on_only_emulators(self, key):
        self.settings.set("only_emulators", key == "on")
        self.log("设置", "只显示模拟器：%s" % ("开" if key == "on" else "关"))
        self.refresh_devices()

    def _on_auto_download_update(self, key):
        self.settings.set("auto_download_update", key == "on")
        self.settings.save()
        self.log("设置", "自动下载新版本：%s" % ("开" if key == "on" else "关"))

    def _on_auto_check_update(self, key):
        on = key == "on"
        self.settings.set("auto_check_update", on)
        self.settings.save()
        self.log("设置", "启动时自动检查更新：%s" % ("开" if on else "关"))

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
            self._later(done, key)

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
        if getattr(self, "backup_seg2", None):
            self.backup_seg2.set_active(value)
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
