# -*- coding: utf-8 -*-
import ctypes, json, os, shutil, sys, tempfile, time
ctypes.windll.shcore.SetProcessDpiAwareness(1)
import tkinter as tk
from PIL import ImageGrab
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
root.deiconify()
for _ in range(40):
    root.update(); time.sleep(0.02)
hwnd = ctypes.windll.user32.GetParent(root.winfo_id()) or root.winfo_id()
user32 = ctypes.windll.user32
user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040)
user32.SetForegroundWindow(hwnd)
time.sleep(0.8)

def shoot(tag):
    for _ in range(20):
        root.update(); time.sleep(0.02)
    img = ImageGrab.grab(window=hwnd).convert("RGB")
    img.save("../.tmp/nudge_%s.png" % tag)
    print(tag, [img.getpixel((820, y)) for y in (300, 330, 420, 440, 520)])

shoot("a")
root.geometry("1101x900")
root.update()
time.sleep(0.4)
root.geometry("1100x900")
shoot("b")
# force a full repaint of every widget
def repaint(w):
    try:
        w.event_generate("<Configure>", width=w.winfo_width(), height=w.winfo_height())
    except Exception:
        pass
    for c in w.winfo_children():
        repaint(c)
repaint(app.canvas)
shoot("c")
root.destroy()
