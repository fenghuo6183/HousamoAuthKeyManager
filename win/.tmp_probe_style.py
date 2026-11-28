# -*- coding: utf-8 -*-
import ctypes, json, os, shutil, sys, tempfile, time
ctypes.windll.shcore.SetProcessDpiAwareness(1)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tkinter as tk
from tkinter import ttk
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
app = App(root)
for _ in range(40):
    root.update(); time.sleep(0.02)
st = ttk.Style()
for name in ("TCombobox", "TEntry", "TScrollbar", "Vertical.TScrollbar", "TFrame"):
    print(name, "config:", st.configure(name))
    print(name, "map:", st.map(name))
combo = None
stack = [app.canvas]
while stack:
    w = stack.pop(); stack.extend(w.winfo_children())
    if w.__class__.__name__ == "Combobox":
        combo = w; break
if combo is not None:
    print("combo app style", combo.cget("style"), "->", st.lookup("TCombobox", "fieldbackground"))
root.destroy()
