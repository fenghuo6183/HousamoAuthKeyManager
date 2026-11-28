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
app._maybe_tint_cards()
for _ in range(10):
    root.update(); time.sleep(0.02)

card = app.cards[0]
print("card box", card._box, "fill", card.fill_color, "face", card.face_mix, card.face_extra)
print("body bg", card.body.cget("bg"), "body img?", card._body_bg.cget("image"), card._body_bg.place_info())

def walk(w, depth=0):
    try:
        bg = w.cget("bg")
    except Exception:
        bg = "-"
    if bg == card.fill_color or bg == "#6f6b65":
        box = app._widget_box(w, app.canvas)
        print("SAME-AS-FILL", "  "*depth, w.__class__.__name__, str(w)[-40:], "bg", bg, "box", box)
    for c in w.winfo_children():
        walk(c, depth+1)

walk(card)
print("body children:", [str(c)[-26:] for c in card.body.winfo_children()])
root.destroy()
