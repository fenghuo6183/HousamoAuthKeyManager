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

card = app.cards[0]
def snap(tag):
    print("---", tag, "glass", app.glass_value, "card fill", card.fill_color)
    for c in card.body.winfo_children():
        if getattr(c, "_glass_bg", False):
            print("   glassbg", c.cget("bg"), c.winfo_width(), c.winfo_height())
            continue
        print("   ", c.__class__.__name__, str(c)[-18:], c.cget("bg"), c.winfo_y(), c.winfo_height())
snap("after app flow")
app._maybe_tint_cards()
for _ in range(10):
    root.update(); time.sleep(0.02)
snap("after manual tint")
root.destroy()
