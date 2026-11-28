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
for _ in range(40):
    root.update(); time.sleep(0.02)
print("canvas", app.canvas.winfo_width(), app.canvas.winfo_height(), "cards", len(app.cards))
hits = []
for card in app.cards:
    rows, redraw, segs = app._glass_targets(card)
    watched = {str(w) for w, o, b in rows}
    stack = [card]
    while stack:
        w = stack.pop()
        stack.extend(w.winfo_children())
        box = app._widget_box(w, app.canvas)
        if not box:
            continue
        x, y, ww, hh = box
        if ww < 30 or hh < 10:
            continue
        if 150 <= y <= 260:
            try:
                bg = str(w.cget("bg"))
            except Exception:
                bg = "?"
            hits.append((y, x, ww, hh, w.__class__.__name__, str(w)[-30:], bg, str(w) in watched))
for h in sorted(hits):
    print(h)
root.destroy()
