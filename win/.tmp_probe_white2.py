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
root.update()
for _ in range(30):
    root.update(); time.sleep(0.02)
print("tone", app.backdrop.tone(), "rev", app.backdrop.rev)

def lum(hexv):
    h = hexv.lstrip("#")
    if len(h) != 6:
        return -1
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return 0.299*r + 0.587*g + 0.114*b

bright = []
def walk(w):
    for c in w.winfo_children():
        walk(c)
    try:
        x = w.winfo_rootx() - app.canvas.winfo_rootx()
        y = w.winfo_rooty() - app.canvas.winfo_rooty()
        ww, hh = w.winfo_width(), w.winfo_height()
        bg = str(w.cget("bg"))
    except Exception:
        return
    if ww > 20 and hh > 8 and lum(bg) > 205:
        bright.append((round(lum(bg)), w.__class__.__name__, str(w)[:70], x, y, ww, hh, bg))

for card in app.pages["tasks"]:
    pass
walk(root)
print("bright widgets:", len(bright))
for b in sorted(bright, reverse=True)[:25]:
    print(b)
root.destroy()
