import os, sys, tempfile
sys.path.insert(0, os.getcwd())
tmp = tempfile.mkdtemp(prefix="hak-probe-")
os.environ["HOUSAMO_DATA_DIR"] = tmp
os.environ["HOUSAMO_NO_ADB"] = "1"
os.environ["HOUSAMO_NO_TRAY"] = "1"
import json
os.makedirs(os.path.join(tmp, "HousamoAuthKeyManager"), exist_ok=True)
# Settings() resolves its own dir; ask it where, then write glass there
import app.config as config
cfg = config.Settings()
print("dir", getattr(cfg, "dir", None))
cfg.set("glass", 100, save=True)
import tkinter as tk
from app import ui
root = tk.Tk(); root.geometry("1100x900")
app = ui.App(root); root.update(); app._show_page("tasks"); root.update()
app._maybe_tint_cards(); root.update()
print("glass", app.settings.get("glass"))
def walk(w):
    for c in w.winfo_children():
        yield c
        yield from walk(c)
for c in walk(app.canvas):
    if c.__class__.__name__ == "PillButton":
        pal = getattr(c, "glass_pal", None)
        print(repr(getattr(c,"text","")), "kind", c.kind, "bg", c.cget("bg"), "pal_soft", None if pal is None else pal.get("card_soft"))

for c in walk(app.canvas):
    if c.__class__.__name__ == "PillButton" and getattr(c, "text", "") == "清空":
        box = app._widget_box(c, app.canvas)
        print("box", box)
        size = (app.canvas.winfo_width(), app.canvas.winfo_height())
        print("mean", app.backdrop.mean(size, box, 36) if box else None)
        print("glass_pal_local", getattr(c, "glass_pal", {}).get("_local"))
root.destroy()
