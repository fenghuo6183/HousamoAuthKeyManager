# -*- coding: utf-8 -*-
"""App lock PIN dialogs and the Windows screenshot guard."""

from __future__ import annotations

import ctypes
import sys

from app import applock

from . import dialogs


def ask_pin(parent, pal, title, prompt):
    text = dialogs.ask_text(parent, pal, title, prompt, password=True)
    return text or None


def unlock(parent, settings, pal, attempts=3):
    """Return True when the app may open."""
    if not applock.is_enabled(settings):
        return True
    for _ in range(attempts):
        pin = ask_pin(parent, pal, "应用锁", "输入 PIN 解锁：")
        if pin is None:
            return False
        if applock.check_pin(settings, pin):
            return True
    return False


def set_capture_guard(widget, enabled):
    """WDA_EXCLUDEFROMCAPTURE keeps the window out of screenshots/recordings."""
    if not sys.platform.startswith("win"):
        return False
    try:
        hwnd = int(widget.winId())
        affinity = 0x11 if enabled else 0x00
        return bool(ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, affinity))
    except Exception:
        return False
