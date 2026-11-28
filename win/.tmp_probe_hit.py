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
for _ in range(30):
    root.update(); time.sleep(0.02)
cx, cy = app.canvas.winfo_rootx(), app.canvas.winfo_rooty()
for pt in ((747, 205), (747, 215), (640, 120), (900, 400)):
    w = root.winfo_containing(cx + pt[0], cy + pt[1])
    path = str(w)
    print(pt, "->", path)
    node = w
    while node is not None:
        try:
            bg = str(node.cget("bg"))
        except Exception:
            bg = "?"
        pal = getattr(node, "glass_pal", None)
        print("   ", str(node)[-40:], node.__class__.__name__, "bg", bg,
              "pal_card", (pal or {}).get("card"), "has_pal", pal is not None)
        node = node.master
root.destroy()
