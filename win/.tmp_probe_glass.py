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
for _ in range(30):
    root.update(); time.sleep(0.02)
app._maybe_tint_cards()
root.update()
size = (app.canvas.winfo_width(), app.canvas.winfo_height())
extra = app._glass_blur(1.0)
print("size", size, "extra", extra, "flat", app.glass_flat)
card = app.cards[0]
print("card box", card._box, "fill", card.fill_color, "body bg", card.body.cget("bg"))
rows = app._glass_targets(card)[0]
for widget, option, base in rows:
    if option == "foreground":
        continue
    box = app._widget_box(widget, app.canvas)
    local = app.backdrop.mean(size, box, extra, flat=True) if box else None
    now = widget.cget(option)
    cls = widget.__class__.__name__
    if box and box[3] >= 20:
        print("%-10s %-22s %s base=%s local=%s now=%s" % (cls, str(widget)[-22:], box, base, local, now))
root.destroy()
