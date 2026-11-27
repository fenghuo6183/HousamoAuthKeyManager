"""Entry point for the Windows client."""
import sys
import os
import tkinter as tk

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import theme  # noqa: E402
from app.ui import App  # noqa: E402


def _enable_dpi_awareness():
    """Tell Windows we scale ourselves.

    Without this the shell renders the window at 96 dpi and bitmap-stretches it
    on 125/150% displays, which is what makes everything look soft with ragged
    edges.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
    except Exception:
        return
    try:
        # 1 = system DPI aware, the safe choice for a fixed-size desktop app
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def _tune_scaling(root):
    """Match our pixel scale to the monitor and let Tk scale point fonts."""
    try:
        dpi = float(root.winfo_fpixels("1i"))
    except Exception:
        dpi = 96.0
    if dpi <= 0:
        dpi = 96.0
    theme.set_ui_scale(dpi / 96.0)
    try:
        root.tk.call("tk", "scaling", dpi / 72.0)
    except Exception:
        pass


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


def main():
    _enable_dpi_awareness()
    if "--apply-update" in sys.argv:
        sys.exit(_run_apply_update())
    if not _single_instance():
        return
    if "--selftest" in sys.argv:
        import tempfile
        os.environ.setdefault("HOUSAMO_DATA_DIR", tempfile.mkdtemp(prefix="hak-selftest-"))
        os.environ.setdefault("HOUSAMO_NO_ADB", "1")
        root = tk.Tk()
        root.withdraw()
        _tune_scaling(root)
        app = App(root)
        if getattr(app, "locked_out", False):
            root.destroy()
            return
        root.update()
        root.destroy()
        print("SELFTEST OK")
        return
    root = tk.Tk()
    _tune_scaling(root)
    app = App(root)
    if getattr(app, "locked_out", False):
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
