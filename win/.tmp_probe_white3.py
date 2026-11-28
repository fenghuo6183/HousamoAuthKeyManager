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
print("bg path", app.backdrop.path, "tone", app.backdrop.tone(), "glass", app.settings.get("glass"))
size = (app.canvas.winfo_width(), app.canvas.winfo_height())
for card in app.pages["tasks"][0][:1] if False else []:
    pass
def walk(w):
    for c in list(w.winfo_children()):
        walk(c)
    name = w.__class__.__name__
    if name in ("PillButton", "Segmented", "CheckToggle"):
        pal = getattr(w, "glass_pal", None)
        try:
            box = w.winfo_rootx() - app.canvas.winfo_rootx(), w.winfo_rooty() - app.canvas.winfo_rooty(), w.winfo_width(), w.winfo_height()
        except Exception:
            box = None
        sample = app.backdrop.mean(size, box, 3.0) if box else None
        print(name, str(w)[-28:], "bg", str(w.cget("bg")), "glass_card", (pal or {}).get("card_soft"), "local", sample)
walk(app.canvas)
root.destroy()
