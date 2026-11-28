import os, sys, json, tempfile, shutil
sys.path.insert(0, os.getcwd())
os.environ["HOUSAMO_NO_ADB"] = "1"
os.environ["HOUSAMO_NO_TRAY"] = "1"
import tkinter as tk
from app import ui, theme

tmp = tempfile.mkdtemp(prefix="hak-probe-")
os.environ["HOUSAMO_DATA_DIR"] = tmp
import app.config as config
cfg = config.Settings()
cfg.set("glass", 100, save=True)

root = tk.Tk()
root.geometry("1100x900")
app = ui.App(root)
root.update(); app._show_page("tasks"); root.update()
app._maybe_tint_cards(); root.update()

def walk(w):
    for c in w.winfo_children():
        yield c
        yield from walk(c)

for c in walk(app.canvas):
    if c.__class__.__name__ == "PillButton":
        txt = getattr(c, "text", "")
        if "清空" in txt or "刷新" in txt or "连接设置" in txt:
            pal = getattr(c, "glass_pal", None)
            print(txt, "bg=", c.cget("bg"), "glass_pal=", None if pal is None else pal.get("card_soft"), "kind=", c.kind)
root.destroy()
