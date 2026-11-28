# -*- coding: utf-8 -*-
"""PIN gate for the Windows client.

Mirrors the Android app's 应用锁: a 4-6 digit code is asked for before the
window opens. Only a PBKDF2 digest and its random salt are stored, so the
settings file never holds the PIN itself.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os

from . import theme

ITERATIONS = 120000
MAX_ATTEMPTS = 5


def _digest(pin, salt):
    return hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, ITERATIONS)


def valid_pin(pin):
    pin = (pin or "").strip()
    return pin.isdigit() and 4 <= len(pin) <= 6


def is_enabled(settings):
    record = settings.get("app_lock") or {}
    return bool(record.get("hash"))


def set_pin(settings, pin):
    pin = (pin or "").strip()
    if not valid_pin(pin):
        raise ValueError("密码要是 4-6 位数字")
    salt = os.urandom(16)
    settings.set("app_lock", {
        "salt": base64.b64encode(salt).decode("ascii"),
        "hash": base64.b64encode(_digest(pin, salt)).decode("ascii"),
    })
    settings.save()


def clear_pin(settings):
    settings.set("app_lock", {})
    settings.save()


def check_pin(settings, pin):
    record = settings.get("app_lock") or {}
    if not record.get("hash"):
        return True
    try:
        salt = base64.b64decode(record.get("salt") or "")
        expected = base64.b64decode(record["hash"])
    except Exception:
        return False
    return hmac.compare_digest(_digest((pin or "").strip(), salt), expected)


def prompt_unlock(root, settings, pal):
    """Ask for the PIN in a modal window; False means the app should close."""
    result = {"ok": False}
    win = tk.Toplevel(root)
    win.title("应用锁 - " + theme.APP_NAME)
    win.configure(bg=pal["window"])
    win.transient(root)
    win.resizable(False, False)
    win.attributes("-topmost", True)
    frame = tk.Frame(win, bg=pal["card"], padx=theme.px(22), pady=theme.px(20))
    frame.pack(fill="both", expand=True, padx=theme.px(14), pady=theme.px(14))
    tk.Label(frame, text="输入应用锁密码", bg=pal["card"], fg=pal["text"],
             font=theme.font(13, "bold"), anchor="w").pack(fill="x")
    tk.Label(frame, text="账号库里存着明文 key，先确认是你本人。", bg=pal["card"],
             fg=pal["text_muted"], font=theme.font(9), anchor="w").pack(
        fill="x", pady=(theme.px(4), theme.px(12)))
    entry = tk.Entry(frame, show="*", font=theme.font(13), bd=0,
                     bg=pal["card_soft"], fg=pal["text"], justify="center",
                     highlightthickness=1, highlightbackground=pal["border"],
                     highlightcolor=pal["accent"])
    entry.pack(fill="x", ipady=theme.px(6))
    status = tk.Label(frame, text="", bg=pal["card"], fg=pal["err"],
                      font=theme.font(9), anchor="w")
    status.pack(fill="x", pady=(theme.px(6), theme.px(4)))
    attempts = {"left": MAX_ATTEMPTS}

    def submit(_event=None):
        if check_pin(settings, entry.get()):
            result["ok"] = True
            win.destroy()
            return
        attempts["left"] -= 1
        entry.delete(0, "end")
        if attempts["left"] <= 0:
            win.destroy()
            return
        status.configure(text="密码不对，还能试 %d 次" % attempts["left"])

    def cancel(_event=None):
        win.destroy()

    row = tk.Frame(frame, bg=pal["card"])
    row.pack(fill="x", pady=(theme.px(4), theme.px(0)))
    tk.Button(row, text="退出", command=cancel, font=theme.font(10), bd=0,
              bg=pal["card_soft"], fg=pal["text"], activebackground=pal["btn_hover"],
              relief="flat", padx=theme.px(14), pady=theme.px(6)).pack(side="left")
    tk.Button(row, text="解锁", command=submit, font=theme.font(10, "bold"), bd=0,
              bg=pal["accent"], fg=pal["on_accent"],
              activebackground=pal["accent_hover"], relief="flat",
              padx=theme.px(20), pady=theme.px(6)).pack(side="right")
    win.bind("<Return>", submit)
    win.bind("<Escape>", cancel)
    win.protocol("WM_DELETE_WINDOW", cancel)
    # size to the content so a 150% display cannot clip the buttons
    win.update_idletasks()
    win.geometry("%dx%d" % (max(theme.px(360), win.winfo_reqwidth()),
                            max(theme.px(232), win.winfo_reqheight())))
    entry.focus_set()
    win.grab_set()
    root.wait_window(win)
    return result["ok"]
