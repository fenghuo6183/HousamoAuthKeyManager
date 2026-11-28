# -*- coding: utf-8 -*-
"""Themed modal dialogs: rename / note / account name.

simpledialog looks like a 1995 OS dialog and cannot show hints, a length
counter or a duplicate-name warning, so the app uses these instead.
"""

from __future__ import annotations

import tkinter as tk

from . import theme
from .widgets import PillButton, label


class TextDialog:
    """One-field modal (single-line entry or multiline note)."""

    MIN_WIDTH = 460

    def __init__(self, app, title="", hint="", initial="", max_len=24,
                 multiline=False, taken=(), confirm="保存", placeholder="",
                 allow_empty=False):
        self.app = app
        self.pal = app.pal
        self.title_text = title
        self.max_len = int(max_len)
        self.multiline = bool(multiline)
        self.allow_empty = bool(allow_empty)
        self.taken = {str(t).strip() for t in taken if str(t or "").strip()}
        self._initial = (initial or "").strip()
        self.result = None
        self.entry = None
        self.text_widget = None
        self._closed = False

        self._drag_origin = None
        self.window = tk.Toplevel(app.root)
        self.window.title(title)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.configure(bg=self.pal["border"])
        self.window.bind("<Escape>", lambda _e: self.cancel())

        body = tk.Frame(self.window, bg=self.pal["card"], bd=0, highlightthickness=0)
        body.pack(fill="both", expand=True, padx=theme.px(1), pady=theme.px(1))
        pad = theme.px(20)

        head = tk.Frame(body, bg=self.pal["card"])
        head.pack(fill="x", padx=pad, pady=(pad - theme.px(6), theme.px(0)))
        label(head, app, title, size=12, weight="bold").pack(side="left")
        self._close_btn = label(head, app, "✕", size=10, color="text_faint")
        self._close_btn.configure(cursor="hand2")
        self._close_btn.pack(side="right")
        self._close_btn.bind("<Button-1>", lambda _e: self.cancel())
        self._close_btn.bind("<Enter>",
                             lambda _e: self._close_btn.configure(fg=self.pal["err"]))
        self._close_btn.bind("<Leave>",
                             lambda _e: self._close_btn.configure(fg=self.pal["text_faint"]))
        self._bind_drag(head)
        if hint:
            label(body, app, hint, size=9, color="text_muted").pack(
                anchor="w", padx=pad, pady=(theme.px(2), theme.px(0)))

        self.var = tk.StringVar(value=initial or "")
        if self.multiline:
            self.text_widget = tk.Text(
                body, height=4, wrap="word", font=theme.font(10),
                bg=self.pal["card_soft"], fg=self.pal["text"],
                insertbackground=self.pal["text"], relief="flat", bd=0,
                highlightthickness=1, highlightbackground=self.pal["border"],
                highlightcolor=self.pal["accent"], padx=theme.px(8), pady=theme.px(6))
            self.text_widget.insert("1.0", initial or "")
            self.text_widget.pack(fill="x", padx=pad, pady=(theme.px(12), 0))
            self.text_widget.bind("<KeyRelease>", lambda _e: self._sync())
            self.text_widget.bind("<Control-Return>", self._on_return)
        else:
            self.entry = tk.Entry(
                body, textvariable=self.var, font=theme.font(11),
                bg=self.pal["card_soft"], fg=self.pal["text"],
                insertbackground=self.pal["text"], relief="flat", bd=0,
                highlightthickness=1, highlightbackground=self.pal["border"],
                highlightcolor=self.pal["accent"])
            self.entry.pack(fill="x", padx=pad, pady=(theme.px(12), 0), ipady=theme.px(7))
            self.entry.bind("<Return>", self._on_return)
            self.var.trace_add("write", lambda *_a: self._sync())

        meta = tk.Frame(body, bg=self.pal["card"])
        meta.pack(fill="x", padx=pad, pady=(theme.px(6), 0))
        self.error_label = label(meta, app, "", size=9, color="err")
        self.error_label.pack(side="left")
        self.counter_label = label(meta, app, "", size=9, color="text_faint")
        self.counter_label.pack(side="right")

        buttons = tk.Frame(body, bg=self.pal["card"])
        buttons.pack(fill="x", padx=pad, pady=(theme.px(14), pad))
        self.btn_save = PillButton(app, buttons, confirm, command=self.ok, kind="primary",
                                   width=96, height=36)
        self.btn_save.pack(side="right")
        PillButton(app, buttons, "取消", command=self.cancel, kind="ghost",
                   width=84, height=36).pack(side="right", padx=(theme.px(0), theme.px(8)))

        self._sync()
        self.window.update_idletasks()
        self._center()
        self.window.grab_set()
        try:
            self.window.transient(app.root)
        except Exception:
            pass
        try:
            self.window.focus_force()
        except Exception:
            pass
        if self.entry is not None:
            self.entry.focus_set()
            self.entry.selection_range(0, "end")
        else:
            self.text_widget.focus_set()

    # -- helpers -----------------------------------------------------
    def _text(self):
        if self.multiline:
            return self.text_widget.get("1.0", "end-1c")
        return self.var.get()

    def _on_return(self, _event=None):
        self.ok()
        return "break"

    def _center(self):
        win_w = max(theme.px(self.MIN_WIDTH), self.window.winfo_reqwidth())
        win_h = self.window.winfo_reqheight()
        root = self.app.root
        try:
            root.update_idletasks()
            x = root.winfo_rootx() + (root.winfo_width() - win_w) // 2
            y = root.winfo_rooty() + (root.winfo_height() - win_h) // 3
        except Exception:
            x = y = 0
        self.window.geometry("%dx%d+%d+%d" % (win_w, win_h, max(0, x), max(0, y)))
        self.window.deiconify()
        self.window.lift()

    def _bind_drag(self, widget):
        widget.bind("<ButtonPress-1>", self._drag_start, add="+")
        widget.bind("<B1-Motion>", self._drag_move, add="+")

    def _drag_start(self, event):
        self._drag_origin = (event.x_root - self.window.winfo_rootx(),
                             event.y_root - self.window.winfo_rooty())

    def _drag_move(self, event):
        if not self._drag_origin:
            return
        dx, dy = self._drag_origin
        self.window.geometry("+%d+%d" % (event.x_root - dx, event.y_root - dy))

    def _show_error(self, text):
        self.error_label.configure(text=text)

    def _sync(self):
        length = len(self._text().strip())
        over = length > self.max_len
        self.counter_label.configure(text="%d/%d" % (length, self.max_len),
                                     fg=self.pal["err"] if over else self.pal["text_faint"])
        if over:
            self._show_error("最多 %d 个字符" % self.max_len)

    # -- actions -----------------------------------------------------
    def ok(self):
        text = self._text().strip()
        if not text and not self.allow_empty:
            self._show_error("这里不能是空的，写点什么再保存")
            return
        if not text:
            self.result = ""
            self.close()
            return
        if len(text) > self.max_len:
            self._show_error("最多 %d 个字符" % self.max_len)
            return
        if text in self.taken and text != self._initial:
            self._show_error("账号库里已经有叫「%s」的了，换一个吧" % text)
            return
        self.result = text
        self.close()

    def cancel(self):
        self.result = None
        self.close()

    def close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self.window.grab_release()
        except Exception:
            pass
        try:
            self.window.destroy()
        except Exception:
            pass


class InfoDialog:
    """只读提醒弹窗：倒计时读满之前，确认按钮点不动、Esc 也关不掉。"""

    WIDTH = 520

    def __init__(self, app, title="", lines=(), seconds=3, confirm="我知道了"):
        self.app = app
        self.pal = app.pal
        self.result = None
        self._closed = False
        self._after_id = None
        self.seconds = max(0, int(seconds))
        self.confirm = confirm

        self.window = tk.Toplevel(app.root)
        self.window.title(title)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.configure(bg=self.pal["border"])
        # 强制阅读：读完之前按 Esc / 关窗口都不算数
        self.window.bind("<Escape>", lambda _e: "break")
        try:
            self.window.protocol("WM_DELETE_WINDOW", lambda: None)
        except Exception:
            pass

        body = tk.Frame(self.window, bg=self.pal["card"], bd=0, highlightthickness=0)
        body.pack(fill="both", expand=True, padx=theme.px(1), pady=theme.px(1))
        pad = theme.px(20)

        label(body, app, title, size=13, weight="bold").pack(
            anchor="w", padx=pad, pady=(pad, theme.px(8)))
        wrap = theme.px(self.WIDTH - 48)
        for text in lines:
            label(body, app, text, size=10, color="text_muted", wraplength=wrap,
                  justify="left").pack(anchor="w", padx=pad, pady=(0, theme.px(8)))

        buttons = tk.Frame(body, bg=self.pal["card"])
        buttons.pack(fill="x", padx=pad, pady=(theme.px(10), pad))
        self.btn = PillButton(app, buttons, self._countdown_text(self.seconds),
                              command=self.ok, kind="primary", width=236, height=38)
        self.btn.pack(side="right")
        self.btn.set_enabled(self.seconds <= 0)

        self.window.update_idletasks()
        self._center()
        self.window.grab_set()
        try:
            self.window.transient(app.root)
        except Exception:
            pass
        try:
            self.window.focus_force()
        except Exception:
            pass
        self._tick(self.seconds)

    # -- helpers -----------------------------------------------------
    def _countdown_text(self, left):
        return "请先读完（%d 秒）" % left if left > 0 else self.confirm

    def _center(self):
        win_w = theme.px(self.WIDTH)
        win_h = self.window.winfo_reqheight()
        root = self.app.root
        try:
            root.update_idletasks()
            x = root.winfo_rootx() + (root.winfo_width() - win_w) // 2
            y = root.winfo_rooty() + (root.winfo_height() - win_h) // 3
        except Exception:
            x = y = 0
        self.window.geometry("%dx%d+%d+%d" % (win_w, win_h, max(0, x), max(0, y)))
        self.window.deiconify()
        self.window.lift()

    def _tick(self, left):
        if self._closed:
            return
        if self._after_id is not None:
            try:
                self.window.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        if left <= 0:
            self.btn.set_text(self.confirm)
            self.btn.set_enabled(True)
            return
        self.btn.set_text(self._countdown_text(left))
        self._after_id = self.window.after(1000, self._tick, left - 1)

    # -- actions -----------------------------------------------------
    def ok(self):
        self.result = True
        self.close()

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._after_id is not None:
            try:
                self.window.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        try:
            self.window.grab_release()
        except Exception:
            pass
        try:
            self.window.destroy()
        except Exception:
            pass


def show_export_reminder(app, game_label="", seconds=3):
    """从游戏提取到 key 后的强提醒：读满 seconds 秒才能点继续。

    前三次提取会弹这个；提醒本身强调 key 是这个号唯一的登录凭证，
    手机、电脑各存一份，别只留一处。
    """
    folder = "%s/<名字>/AuthKey.txt" % (game_label or "游戏")
    dialog = InfoDialog(
        app,
        title="这个 key 极其重要，请先读完",
        lines=[
            "它是这个账号唯一的登录凭证。丢了、被覆盖了，号就没了——官方找回很麻烦，很多情况找不回来。",
            "电脑上：下面保存后会导出到保存文件夹的 %s，别删这个文件夹。" % folder,
            "手机上也存一份：用手机 App 再提取一次，或把这个 AuthKey.txt 拷进手机。",
            "网盘、邮箱再各放一份更稳；换手机、重装、清数据、刷机之前，先确认这两份都还在。",
        ],
        confirm="我知道了，去保存",
        seconds=seconds,
    )
    app.root.wait_window(dialog.window)
    return dialog.result


def ask_text(app, title, hint="", initial="", max_len=24, multiline=False,
             taken=(), confirm="保存", allow_empty=False):
    """Show a themed modal and block until the user saves or cancels."""
    dialog = TextDialog(app, title=title, hint=hint, initial=initial, max_len=max_len,
                        multiline=multiline, taken=taken, confirm=confirm,
                        allow_empty=allow_empty)
    app.root.wait_window(dialog.window)
    return dialog.result
