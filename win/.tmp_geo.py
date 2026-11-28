import os, sys, json, shutil, tempfile, time
ctypes_hint = None
os.environ["HOUSAMO_NO_TRAY"] = "1"
os.environ["HOUSAMO_NO_ADB"] = "1"
src = os.path.join(os.environ["APPDATA"], "HousamoAuthKeyManager")
tmp = tempfile.mkdtemp(prefix="hak-geo-")
for name in ("settings.json", "background.jpg", "background.png"):
    p = os.path.join(src, name)
    if os.path.isfile(p):
        shutil.copy2(p, tmp)
sp = os.path.join(tmp, "settings.json")
blob = {}
if os.path.isfile(sp):
    blob = json.load(open(sp, encoding="utf-8"))
blob["glass"] = int(sys.argv[1]) if len(sys.argv) > 1 else 100
json.dump(blob, open(sp, "w", encoding="utf-8"))
os.environ["HOUSAMO_DATA_DIR"] = tmp
sys.path.insert(0, ".")
import tkinter as tk
from app import theme
from app.ui import App
root = tk.Tk()
theme.set_ui_scale(root.winfo_fpixels("1i") / 96.0)
root.geometry("1100x900")
app = App(root)
app._show_page("tasks")
for _ in range(30):
    root.update(); time.sleep(0.02)
print("root", root.winfo_width(), root.winfo_height(), "scale", round(theme.UI_SCALE, 3))
print("canvas", app.canvas.winfo_width(), app.canvas.winfo_height(), "yview", app.canvas.yview(), "scrollregion", app.canvas.cget("scrollregion"))
print("rail", app.rail.winfo_x(), app.rail.winfo_y(), app.rail.winfo_width(), app.rail.winfo_height(), "bg", app.rail.cget("bg"))
for i, entry in enumerate(app.pages["tasks"]):
    card = entry[0]
    print("card", i, card.winfo_x(), card.winfo_y(), card.winfo_width(), card.winfo_height(), "mix", round(getattr(card, "face_mix", 0), 2), "fill", card.fill_color, "bodysize", card.body.winfo_width(), card.body.winfo_height())
