# -*- coding: utf-8 -*-
"""Dev screenshot harness v2: prefers PrintWindow so a foreground window cannot cover us.

usage: python .tmp_devshot.py <out.png> [page] [section] [width] [height]
"""
import ctypes, json, os, shutil, sys, tempfile, time
ctypes.windll.shcore.SetProcessDpiAwareness(1)

import tkinter as tk
from PIL import ImageGrab

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import theme  # noqa: E402
from app.ui import App  # noqa: E402
import app as app_pkg  # noqa: E402

out = sys.argv[1] if len(sys.argv) > 1 else "shot.png"
page = sys.argv[2] if len(sys.argv) > 2 else "settings"
section = sys.argv[3] if len(sys.argv) > 3 else ""
W = int(sys.argv[4]) if len(sys.argv) > 4 else 0
glass = sys.argv[6] if len(sys.argv) > 6 else ""
H = int(sys.argv[5]) if len(sys.argv) > 5 else 0

src = os.path.join(os.environ["APPDATA"], "HousamoAuthKeyManager")
tmp = tempfile.mkdtemp(prefix="hak-dev-")
for name in ("settings.json", "background.jpg", "background.png"):
    p = os.path.join(src, name)
    if os.path.isfile(p):
        shutil.copy2(p, tmp)
os.environ["HOUSAMO_DATA_DIR"] = tmp
os.environ["HOUSAMO_NO_ADB"] = "1"
os.environ["HOUSAMO_NO_TRAY"] = "1"

root = tk.Tk()
dpi = float(root.winfo_fpixels("1i")) or 96.0
theme.set_ui_scale(dpi / 96.0)
root.tk.call("tk", "scaling", dpi / 72.0)
if W and H:
    root.geometry("%dx%d" % (W, H))
if glass:
    with open(os.path.join(tmp, "settings.json"), "r", encoding="utf-8") as fh:
        blob = json.load(fh)
    blob["glass"] = int(glass)
    with open(os.path.join(tmp, "settings.json"), "w", encoding="utf-8") as fh:
        json.dump(blob, fh)
app = App(root)
print('glass-in-app', app.settings.get('glass'), 'datadir', __import__('os').environ.get('HOUSAMO_DATA_DIR'))
if page in app.pages:
    app._show_page(page)
if section and hasattr(app, "show_settings_section"):
    app.show_settings_section(section)
root.deiconify()
for _ in range(40):
    root.update()
    time.sleep(0.02)
hwnd = ctypes.windll.user32.GetParent(root.winfo_id()) or root.winfo_id()
user32 = ctypes.windll.user32
user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040)
user32.SetForegroundWindow(hwnd)
time.sleep(0.9)
for _ in range(20):
    root.update()
    time.sleep(0.02)
r = (ctypes.c_long * 4)()
user32.GetWindowRect(hwnd, r)
img = None
try:
    cand = ImageGrab.grab(window=hwnd)
    if cand.size[0] > 200 and cand.size[1] > 200:
        px = cand.convert("RGB").resize((32, 32))
        colors = set(px.getdata())
        if len(colors) > 8:
            img = cand
except Exception as exc:
    print("printwindow failed:", exc)
if img is None:
    img = ImageGrab.grab(bbox=(r[0], r[1], r[2], r[3]))
img.save(out)
user32.SetWindowPos(hwnd, -2, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040)
print("saved", out, img.size, "scaled", round(theme.UI_SCALE, 3))
root.destroy()