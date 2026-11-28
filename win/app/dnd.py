"""Drag a .hak file onto the window and it is imported.

Tk has no native file-drop API, so this installs a tiny WM_DROPFILES hook on
the toplevel window with ctypes. Everything fails soft: when the hook cannot
be installed (non-Windows, odd shell, packaged build) the app just keeps its
import button and nothing breaks.
"""

import ctypes
import os
import sys

HAK_SUFFIXES = (".hak",)

WM_DROPFILES = 0x0233
GWLP_WNDPROC = -4

_user32 = None
_shell32 = None


def _libs():
    """Load user32/shell32 once, with explicit signatures.

    Without restype/argtypes ctypes truncates LPARAM to a C int on 64-bit
    Windows, which corrupts the message loop ("int too long" then access
    violations), so the prototypes matter more than they look.
    """
    global _user32, _shell32
    if _user32 is not None:
        return _user32, _shell32
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    shell32 = ctypes.WinDLL("shell32", use_last_error=True)

    user32.GetParent.argtypes = [wintypes.HWND]
    user32.GetParent.restype = wintypes.HWND
    user32.CallWindowProcW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT,
                                       wintypes.WPARAM, wintypes.LPARAM]
    user32.CallWindowProcW.restype = ctypes.c_ssize_t
    setter = getattr(user32, "SetWindowLongPtrW", None) or user32.SetWindowLongW
    setter.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
    setter.restype = ctypes.c_void_p

    shell32.DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]
    shell32.DragAcceptFiles.restype = None
    shell32.DragQueryFileW.argtypes = [ctypes.c_void_p, wintypes.UINT,
                                       wintypes.LPWSTR, wintypes.UINT]
    shell32.DragQueryFileW.restype = wintypes.UINT
    shell32.DragFinish.argtypes = [ctypes.c_void_p]
    shell32.DragFinish.restype = None

    _user32, _shell32 = user32, shell32
    return user32, shell32


def hak_paths(paths, suffixes=HAK_SUFFIXES):
    """Keep the existing files that look like AuthKey backups, in order."""
    picked = []
    for raw in paths or ():
        path = str(raw or "").strip().strip('"')
        if not path:
            continue
        if os.path.splitext(path)[1].lower() not in suffixes:
            continue
        if not os.path.isfile(path):
            continue
        if path not in picked:
            picked.append(path)
    return picked


class DropTarget(object):
    """Windows-only file drop target for one Tk toplevel."""

    def __init__(self, root, on_files):
        self.ok = False
        self._root = root
        self._on_files = on_files
        self._hwnd = None
        self._old_proc = None
        self._proc = None
        if sys.platform != "win32":
            return
        try:
            self._install()
            self.ok = True
        except Exception:
            self.ok = False
            self._hwnd = None

    # -- setup ------------------------------------------------------
    def _install(self):
        from ctypes import wintypes

        user32, shell32 = _libs()
        self._user32 = user32
        self._shell32 = shell32
        hwnd = user32.GetParent(self._root.winfo_id()) or self._root.winfo_id()
        self._hwnd = hwnd

        lresult = ctypes.c_ssize_t
        wndproc = ctypes.WINFUNCTYPE(lresult, wintypes.HWND, wintypes.UINT,
                                     wintypes.WPARAM, wintypes.LPARAM)

        def hook(hwnd_, msg, wparam, lparam):
            if msg == WM_DROPFILES:
                try:
                    self._deliver(wparam)
                except Exception:
                    pass
                return 0
            if msg == 0x0082:  # WM_NCDESTROY: the window is going away
                return user32.CallWindowProcW(self._old_proc, hwnd_, msg, wparam, lparam)
            return user32.CallWindowProcW(self._old_proc, hwnd_, msg, wparam, lparam)

        self._proc = wndproc(hook)
        setter = getattr(user32, "SetWindowLongPtrW", None) or user32.SetWindowLongW
        old = setter(hwnd, GWLP_WNDPROC, ctypes.cast(self._proc, ctypes.c_void_p))
        if not old:
            raise OSError("SetWindowLongPtrW failed")
        self._old_proc = old
        shell32.DragAcceptFiles(hwnd, True)

    def _deliver(self, drop_handle):
        shell32 = self._shell32
        handle = ctypes.c_void_p(drop_handle)
        count = shell32.DragQueryFileW(handle, 0xFFFFFFFF, None, 0)
        paths = []
        for index in range(int(count)):
            buffer = ctypes.create_unicode_buffer(1024)
            if shell32.DragQueryFileW(handle, index, buffer, 1024):
                paths.append(buffer.value)
        try:
            shell32.DragFinish(handle)
        except Exception:
            pass
        if paths:
            # Never touch widgets from inside the window procedure.
            self._root.after(0, self._on_files, paths)

    # -- teardown ---------------------------------------------------
    def close(self):
        if not self.ok:
            return
        try:
            self._shell32.DragAcceptFiles(self._hwnd, False)
        except Exception:
            pass
        try:
            setter = getattr(self._user32, "SetWindowLongPtrW", None) or \
                self._user32.SetWindowLongW
            if self._old_proc:
                setter(self._hwnd, GWLP_WNDPROC, self._old_proc)
        except Exception:
            pass
        self.ok = False


def install(root, on_files):
    """Best-effort; returns a target object whose .ok says whether it worked."""
    return DropTarget(root, on_files)
