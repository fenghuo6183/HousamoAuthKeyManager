# -*- coding: utf-8 -*-
import ctypes, json, os, shutil, sys, tempfile, time
ctypes.windll.shcore.SetProcessDpiAwareness(1)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tkinter as tk
from app import theme
from app.ui import App
src = os.path.join(os.environ["APPDATA"], "HousamoAuthKeyManager")
tmp = tempfile.mkdtemp(prefix="hak-dev-")
for name in ("settings.json", "background.jpg"):
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
t0 = time.time()
app = App(root)
root.update()
print("build %.0fms" % ((time.time() - t0) * 1000))
for name, page in (("tasks", "tasks"), ("settings", "settings")):
    t0 = time.time()
    app._show_page(page)
    root.update()
    print("switch->%s %.0fms" % (name, (time.time() - t0) * 1000))
    for card in app.cards:
        card._tint_sig = None
    app._rail_sig = None
    t0 = time.time()
    app._maybe_tint_cards()
    root.update()
    print("retint %s %.0fms" % (name, (time.time() - t0) * 1000))
root.destroy()
