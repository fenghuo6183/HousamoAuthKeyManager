"""Minimal system tray icon built on ctypes - no third-party packages."""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import os
import threading

user32 = ctypes.windll.user32 if hasattr(ctypes, "windll") else None
kernel32 = ctypes.windll.kernel32 if hasattr(ctypes, "windll") else None
shell32 = ctypes.windll.shell32 if hasattr(ctypes, "windll") else None

WM_APP = 0x8000
WM_TRAYICON = WM_APP + 21
WM_COMMAND = 0x0111
WM_HOTKEY = 0x0312
WM_CLOSE = 0x0010
WM_DESTROY = 0x0002
WM_LBUTTONUP = 0x0202
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONUP = 0x0205

NIF_MESSAGE = 0x01
NIF_ICON = 0x02
NIF_TIP = 0x04
NIF_INFO = 0x10
NIM_ADD = 0x00
NIM_MODIFY = 0x01
NIM_DELETE = 0x02
NIIF_INFO = 0x01
MF_STRING = 0x0000
MF_SEPARATOR = 0x0800
TPM_RETURNCMD = 0x0100
TPM_NONOTIFY = 0x0080
ID_SHOW = 1001
ID_QUIT = 1002

WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wt.HWND, wt.UINT,
                             wt.WPARAM, wt.LPARAM)

if user32 is not None and shell32 is not None:
    # Default ctypes argument types assume c_int, which overflows on 64-bit
    # message params; be explicit so window messages never raise.
    user32.DefWindowProcW.restype = ctypes.c_ssize_t
    user32.DefWindowProcW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
    user32.CreateWindowExW.restype = wt.HWND
    user32.CreateWindowExW.argtypes = [
        wt.DWORD, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, ctypes.c_int, wt.HWND, wt.HMENU, wt.HINSTANCE,
        wt.LPVOID]
    user32.DispatchMessageW.argtypes = [ctypes.POINTER(wt.MSG)]
    user32.GetMessageW.argtypes = [ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT,
                                   wt.UINT]
    user32.RegisterHotKey.argtypes = [wt.HWND, ctypes.c_int, ctypes.c_uint,
                                      ctypes.c_uint]


class WNDCLASSW(ctypes.Structure):
    _fields_ = [("style", wt.UINT), ("lpfnWndProc", WNDPROC),
                ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                ("hInstance", wt.HINSTANCE), ("hIcon", wt.HICON),
                ("hCursor", wt.HANDLE), ("hbrBackground", wt.HBRUSH),
                ("lpszMenuName", wt.LPCWSTR), ("lpszClassName", wt.LPCWSTR)]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("hWnd", wt.HWND), ("uID", wt.UINT),
                ("uFlags", wt.UINT), ("uCallbackMessage", wt.UINT),
                ("hIcon", wt.HICON), ("szTip", wt.WCHAR * 128),
                ("dwState", wt.DWORD), ("dwStateMask", wt.DWORD),
                ("szInfo", wt.WCHAR * 256), ("uTimeoutOrVersion", wt.UINT),
                ("szInfoTitle", wt.WCHAR * 64), ("dwInfoFlags", wt.DWORD)]


def available():
    return user32 is not None and shell32 is not None


class Tray:
    """A tray icon that calls back into the app; every failure is non-fatal."""

    def __init__(self, tip="东放 AuthKey 管家", on_show=None, on_quit=None,
                 on_hotkey=None, icon_path=None, hotkey=None):
        self.tip = tip[:120]
        self.on_show = on_show
        self.on_quit = on_quit
        self.on_hotkey = on_hotkey
        self.icon_path = icon_path
        self.hotkey = hotkey          # (modifiers, vk) or None
        self.hwnd = None
        self.hicon = None
        self.ok = False
        self.ready = threading.Event()
        self._thread = None
        self._ready_event = self.ready
        self._wndproc = None

    # -- public --------------------------------------------------------
    def start(self, wait=2.0):
        if not available() or self._thread is not None:
            return self.ok
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self.ready.wait(wait)
        return self.ok

    def stop(self):
        try:
            if self.hwnd:
                user32.PostMessageW(self.hwnd, WM_CLOSE, 0, 0)
        except Exception:
            pass

    def set_hotkey(self, hotkey):
        """(modifiers, vk) or None; applied on the tray's own window thread."""
        self.hotkey = hotkey
        try:
            if self.hwnd:
                user32.PostMessageW(self.hwnd, WM_APP + 22, 0, 0)
        except Exception:
            pass

    def notify(self, title, text):
        if not self.ok or not self.hwnd:
            return False
        try:
            data = self._data(NIF_INFO)
            data.szInfo = (text or "")[:250]
            data.szInfoTitle = (title or "")[:60]
            data.dwInfoFlags = NIIF_INFO
            shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(data))
            return True
        except Exception:
            return False

    def set_tip(self, tip):
        self.tip = (tip or "")[:120]
        if not self.ok or not self.hwnd:
            return
        try:
            shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(self._data(NIF_TIP)))
        except Exception:
            pass

    # -- internals -----------------------------------------------------
    def _data(self, flags):
        data = NOTIFYICONDATAW()
        data.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        data.hWnd = self.hwnd
        data.uID = 7
        data.uFlags = flags
        data.uCallbackMessage = WM_TRAYICON
        data.hIcon = self.hicon or 0
        data.szTip = self.tip
        return data

    def _load_icon(self):
        try:
            if self.icon_path and os.path.exists(self.icon_path):
                large = wt.HICON()
                small = wt.HICON()
                if shell32.ExtractIconExW(self.icon_path, 0,
                                          ctypes.byref(large),
                                          ctypes.byref(small), 1) > 0:
                    return large.value or small.value
        except Exception:
            pass
        try:
            return user32.LoadIconW(None, ctypes.c_void_p(32512))  # IDI_APPLICATION
        except Exception:
            return None

    def _menu(self):
        menu = user32.CreatePopupMenu()
        user32.AppendMenuW(menu, MF_STRING, ID_SHOW, "显示窗口")
        user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
        user32.AppendMenuW(menu, MF_STRING, ID_QUIT, "退出")
        user32.SetForegroundWindow(self.hwnd)
        cmd = user32.TrackPopupMenu(
            menu, TPM_RETURNCMD | TPM_NONOTIFY, *self._cursor_pos(), 0,
            self.hwnd, None)
        user32.DestroyMenu(menu)
        if cmd == ID_SHOW:
            self._call(self.on_show)
        elif cmd == ID_QUIT:
            self._call(self.on_quit)

    def _cursor_pos(self):
        point = wt.POINT()
        try:
            user32.GetCursorPos(ctypes.byref(point))
        except Exception:
            pass
        return point.x, point.y

    @staticmethod
    def _call(callback):
        if callback is None:
            return
        try:
            callback()
        except Exception:
            pass

    def _wndproc_impl(self, hwnd, msg, wparam, lparam):
        try:
            if msg == WM_TRAYICON:
                code = lparam & 0xFFFF
                if code in (WM_LBUTTONUP, WM_LBUTTONDBLCLK):
                    self._call(self.on_show)
                elif code == WM_RBUTTONUP:
                    self._menu()
                return 0
            if msg == WM_HOTKEY:
                self._call(self.on_hotkey)
                return 0
            if msg == WM_APP + 22:
                try:
                    user32.UnregisterHotKey(hwnd, 1)
                except Exception:
                    pass
                if self.hotkey:
                    try:
                        modifiers, vk = self.hotkey
                        user32.RegisterHotKey(hwnd, 1, modifiers, vk)
                    except Exception:
                        pass
                return 0
            if msg == WM_CLOSE:
                try:
                    shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._data(0)))
                except Exception:
                    pass
                self.ok = False
                user32.DestroyWindow(hwnd)
                return 0
            if msg == WM_DESTROY:
                user32.PostQuitMessage(0)
                return 0
        except Exception:
            pass
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _run(self):
        try:
            self._wndproc = WNDPROC(self._wndproc_impl)
            instance = kernel32.GetModuleHandleW(None)
            klass = WNDCLASSW()
            klass.lpfnWndProc = self._wndproc
            klass.hInstance = instance
            klass.lpszClassName = "HousamoAuthKeyTrayWnd"
            user32.RegisterClassW(ctypes.byref(klass))
            self.hwnd = user32.CreateWindowExW(
                0, klass.lpszClassName, "HousamoAuthKeyTray", 0, 0, 0, 0, 0,
                None, None, instance, None)
            if not self.hwnd:
                return
            self.hicon = self._load_icon()
            shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(self._data(
                NIF_MESSAGE | NIF_ICON | NIF_TIP)))
            if self.hotkey:
                try:
                    modifiers, vk = self.hotkey
                    user32.RegisterHotKey(self.hwnd, 1, modifiers, vk)
                except Exception:
                    pass
            self.ok = True
            self.ready.set()
            msg = wt.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        except Exception:
            self.ok = False
        finally:
            self.ready.set()
