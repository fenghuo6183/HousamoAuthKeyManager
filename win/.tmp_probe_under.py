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
root.deiconify()
for _ in range(40):
    root.update(); time.sleep(0.02)
ox, oy = root.winfo_rootx(), root.winfo_rooty()
scale = theme.UI_SCALE
for sx, sy in ((820, 300), (820, 330), (400, 330), (1500, 330), (820, 430), (820, 520)):
    x, y = int(sx / scale), int(sy / scale)
    w = root.winfo_containing(ox + x, oy + y)
    chain = []
    n = w
    while n is not None and n is not root:
        try:
            bg = n.cget("bg")
        except Exception:
            bg = "-"
        chain.append("%s(%s bg=%s)" % (n.__class__.__name__, str(n)[-14:], bg))
        n = n.master
    print(sx, sy, "->", " < ".join(chain))
root.destroy()
