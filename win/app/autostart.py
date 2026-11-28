"""Run-at-logon toggle: HKCU\\...\\Run, no admin rights and no extra files."""

from __future__ import annotations

import os
import sys

try:
    import winreg
except Exception:  # pragma: no cover - non-Windows
    winreg = None

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "HousamoAuthKeyManager"


def launcher_command():
    """The command Windows should run at logon, or "" when we cannot guess it."""
    if getattr(sys, "frozen", False):
        target = sys.executable
    else:
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        entry = os.path.join(here, "main.py")
        if not os.path.exists(entry):
            return ""
        exe = sys.executable
        console = exe.lower().endswith("python.exe")
        if console:
            guess = os.path.join(os.path.dirname(exe), "pythonw.exe")
            if os.path.exists(guess):
                exe = guess
        target = '%s "%s"' % (exe, entry)
    return '"%s"' % target if not target.startswith('"') else target


def enabled():
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _kind = winreg.QueryValueEx(key, VALUE_NAME)
            return bool(value)
    except Exception:
        return False


def set_enabled(flag):
    """Returns (ok, detail)."""
    if winreg is None:
        return False, "只有 Windows 支持开机自启"
    try:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                                winreg.KEY_SET_VALUE) as key:
            if flag:
                command = launcher_command()
                if not command:
                    return False, "找不到程序自己的路径"
                winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, command)
                return True, command
            try:
                winreg.DeleteValue(key, VALUE_NAME)
            except FileNotFoundError:
                pass
            return True, ""
    except Exception as exc:
        return False, str(exc)
