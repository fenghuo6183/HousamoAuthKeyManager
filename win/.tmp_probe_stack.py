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
card = app.cards[0]
print("label image", card._body_bg.cget("image"), "mapped", card._body_bg.winfo_ismapped(),
      "size", card._body_bg.winfo_width(), card._body_bg.winfo_height())
print("body size", card.body.winfo_width(), card.body.winfo_height())
print("stack order", [str(w)[-24:] for w in card.body.tk.splitlist(card.body.tk.call("winfo", "children", card.body))] if False else [str(w)[-24:] for w in card.body.winfo_children()])

def shoot(tag):
    for _ in range(20):
        root.update(); time.sleep(0.02)
    img = ImageGrab.grab(window=hwnd).convert("RGB")
    print(tag, [img.getpixel((820, y)) for y in (300, 330, 420, 520)])

shoot("a")
card._body_bg.destroy()
shoot("b")
root.destroy()
