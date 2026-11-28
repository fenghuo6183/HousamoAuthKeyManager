# -*- coding: utf-8 -*-
import ctypes, json, os, shutil, sys, tempfile, time
ctypes.windll.shcore.SetProcessDpiAwareness(1)
import tkinter as tk
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import theme
from app.ui import App
src = os.path.join(os.environ["APPDATA"], "HousamoAuthKeyManager")
tmp = tempfile.mkdtemp(prefix="hak-dev-")
for name in ("settings.json", "background.jpg", "background.png"):
    p = os.path.join(src, name)
    if os.path.isfile(p):
        shutil.copy2(p, tmp)
os.environ["HOUSAMO_DATA_DIR"] = tmp
os.environ["HOUSAMO_NO_ADB"] = "1"
os.environ["HOUSAMO_NO_TRAY"] = "1"
with open(os.path.join(tmp, "settings.json"), "r", encoding="utf-8") as fh:
    blob = json.load(fh)
blob["glass"] = 100
with open(os.path.join(tmp, "settings.json"), "w", encoding="utf-8") as fh:
    json.dump(blob, fh)
root = tk.Tk()
dpi = float(root.winfo_fpixels("1i")) or 96.0
theme.set_ui_scale(dpi / 96.0)
root.tk.call("tk", "scaling", dpi / 72.0)
root.geometry("1100x900")
app = App(root)
root.update()
app._show_page("tasks")
for _ in range(40):
    root.update(); time.sleep(0.02)
size = (app.canvas.winfo_width(), app.canvas.winfo_height())
for extra in (0.0, 32.0):
    for flat in (False, True):
        img = app.backdrop.frost(size, extra, flat)
        prof = [img.getpixel((820, y)) for y in (200, 260, 330, 400, 470, 560, 620, 700)]
        print("extra", extra, "flat", flat, prof)
card = app.cards[0]
print("card", card._box, "body children y/bg")
for c in card.body.winfo_children():
    if getattr(c, "_glass_bg", False):
        print("  bg-label", c.winfo_y(), c.winfo_height(), c.cget("bg"), c.cget("image"))
    else:
        print("  ", c.__class__.__name__, c.winfo_y(), c.winfo_height(), c.cget("bg"))
root.destroy()
