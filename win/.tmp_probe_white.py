import os, sys, json
sys.path.insert(0, os.getcwd())
import tkinter as tk
from app import theme, config
from app.ui import App
root = tk.Tk()
root.geometry("1100x900")
app = App(root)
root.update()
app._relayout(); root.update()
found = []
def walk(w, depth=0):
    try:
        if not w.winfo_ismapped():
            return
        x = w.winfo_rootx() - app.canvas.winfo_rootx()
        y = w.winfo_rooty() - app.canvas.winfo_rooty()
        ww, hh = w.winfo_width(), w.winfo_height()
    except Exception:
        return
    if 560 <= x <= 900 and 170 <= y <= 260:
        try:
            bg = str(w.cget("bg"))
        except Exception:
            bg = "?"
        found.append((w.__class__.__name__, str(w), x, y, ww, hh, bg))
    for c in w.winfo_children():
        walk(c, depth+1)
walk(root)
for f in found:
    print(f)
root.destroy()
