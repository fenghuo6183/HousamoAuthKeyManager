# -*- coding: utf-8 -*-
import ctypes, json, os, shutil, sys, tempfile, time
ctypes.windll.shcore.SetProcessDpiAwareness(1)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tkinter as tk
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
blob = json.load(open(os.path.join(tmp, "settings.json"), encoding="utf-8"))
blob["glass"] = 100
json.dump(blob, open(os.path.join(tmp, "settings.json"), "w", encoding="utf-8"))

root = tk.Tk()
dpi = float(root.winfo_fpixels("1i")) or 96.0
theme.set_ui_scale(dpi / 96.0)
root.tk.call("tk", "scaling", dpi / 72.0)
root.geometry("1100x900")
app = App(root)
root.deiconify()
for _ in range(40):
    root.update(); time.sleep(0.02)
ox, oy = app.canvas.winfo_rootx(), app.canvas.winfo_rooty()
rows = []
def walk(w):
    for c in list(w.winfo_children()):
        walk(c)
    try:
        x = w.winfo_rootx() - ox
        y = w.winfo_rooty() - oy
        ww, hh = w.winfo_width(), w.winfo_height()
        bg = str(w.cget("bg"))
    except Exception:
        return
    if ww < 6 or hh < 6:
        return
    if 120 <= y <= 260 and 600 <= x <= 1000:
        pal = getattr(w, "glass_pal", None)
        rows.append((y, x, w.__class__.__name__, str(w)[-34:], bg, (pal or {}).get("card_soft")))
walk(root)
for r in sorted(rows):
    print(r)
print("total widgets", len(rows))
root.destroy()
