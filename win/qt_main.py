# -*- coding: utf-8 -*-
"""Qt shell entry point (python qt_main.py)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication

from app import config, theme
from qtui.pages import settings_page, tasks_page, vault_page
from qtui.tray import Tray
from qtui.window import Shell


def _single_instance():
    """False when another copy is already running (and bring it forward)."""
    if sys.platform != "win32":
        return True
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW(None, False, "Global\\HousamoAuthKeyManager")
        if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            user32 = ctypes.windll.user32
            hwnd = user32.FindWindowW(None, theme.APP_NAME)
            if hwnd:
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                user32.SetForegroundWindow(hwnd)
            return False
    except Exception:
        pass
    return True


def _run_apply_update():
    """Entry point of the staged copy that replaces the install tree."""
    from app import updater
    args = sys.argv
    index = args.index("--apply-update")
    zip_path = args[index + 1] if len(args) > index + 1 else ""
    install = args[index + 2] if len(args) > index + 2 else ""
    try:
        parent = int(args[index + 3]) if len(args) > index + 3 else 0
    except ValueError:
        parent = 0
    ok = updater.apply_update(zip_path, install, parent,
                              log=lambda m: updater.append_log(m))
    return 0 if ok else 1


class TrayBridge(QObject):
    """Tray callbacks fire on the tray thread; these signals hop to the GUI one."""

    show_requested = Signal()
    quit_requested = Signal()


def build_shell(settings, live=True):
    shell = Shell(settings, live=live)
    shell.add_page("tasks", tasks_page(shell))
    shell.add_page("vault", vault_page(shell))
    shell.add_page("settings", settings_page(shell))
    return shell


def start_tray(settings, shell):
    if not settings.get("tray_icon"):
        return None
    tray = Tray(shell, shell.pal)
    if not tray.start():
        return None
    shell.tray = tray
    return tray


def main():
    if "--apply-update" in sys.argv:
        sys.exit(_run_apply_update())
    if not _single_instance():
        return 0

    settings = config.Settings()
    application = QApplication(sys.argv)
    application.setApplicationName(theme.APP_NAME)
    application.setApplicationDisplayName(theme.APP_NAME)
    application.setQuitOnLastWindowClosed(False)

    selftest = "--selftest" in sys.argv
    if selftest:
        import tempfile
        os.environ.setdefault("HOUSAMO_DATA_DIR", tempfile.mkdtemp(prefix="hak-selftest-"))
        os.environ.setdefault("HOUSAMO_NO_ADB", "1")
        settings = config.Settings()

    shell = build_shell(settings, live=not selftest)
    if selftest:
        application.processEvents()
        print("SELFTEST OK")
        return 0

    shell.show()
    start_tray(settings, shell)

    if shell.controller is not None:
        shell.controller.boot()
        poll = QTimer(shell)
        poll.setInterval(6000)
        poll.timeout.connect(lambda: shell.controller.refresh_devices(quiet=True))
        poll.start()
    return application.exec()


if __name__ == "__main__":
    sys.exit(main())
