# -*- coding: utf-8 -*-
"""Global hotkey (Ctrl+Alt+A) through the Win32 RegisterHotKey API."""

from __future__ import annotations

import ctypes
import sys

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, Signal
from PySide6.QtWidgets import QApplication

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
VK_A = 0x41
WM_HOTKEY = 0x0312
HOTKEY_ID = 0xB0A1
HOTKEY_TEXT = "Ctrl+Alt+A"


class _MessageFilter(QAbstractNativeEventFilter):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def nativeEventFilter(self, event_type, message):
        if event_type in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
            try:
                from ctypes import wintypes
                msg = ctypes.cast(int(message), ctypes.POINTER(wintypes.MSG)).contents
            except Exception:
                return False, 0
            if msg.message == WM_HOTKEY and int(msg.wParam) == HOTKEY_ID:
                self.callback()
                return True, 0
        return False, 0


class Hotkey(QObject):
    """Registers one system-wide hotkey and emits triggered() on the GUI thread."""

    triggered = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._filter = None
        self._registered = False

    def active(self):
        return self._registered

    def register(self):
        if self._registered or sys.platform != "win32":
            return self._registered
        user32 = ctypes.windll.user32
        if not user32.RegisterHotKey(None, HOTKEY_ID, MOD_CONTROL | MOD_ALT, VK_A):
            return False
        application = QApplication.instance()
        if application is None:
            user32.UnregisterHotKey(None, HOTKEY_ID)
            return False
        self._filter = _MessageFilter(lambda: self.triggered.emit())
        application.installNativeEventFilter(self._filter)
        self._registered = True
        return True

    def unregister(self):
        if not self._registered:
            return
        try:
            ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_ID)
        except Exception:
            pass
        application = QApplication.instance()
        if application is not None and self._filter is not None:
            application.removeNativeEventFilter(self._filter)
        self._filter = None
        self._registered = False