
import ctypes, os, tkinter as tk
from ctypes import wintypes
from PIL import Image

KEY = "#FF00FE"
user32 = ctypes.windll.user32; gdi32 = ctypes.windll.gdi32
try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception: pass

def capture(hwnd, path):
    rect = wintypes.RECT(); user32.GetWindowRect(hwnd, ctypes.byref(rect))
    w, h = rect.right-rect.left, rect.bottom-rect.top
    hdc = user32.GetWindowDC(hwnd); mdc = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h); gdi32.SelectObject(mdc, bmp)
    user32.PrintWindow(hwnd, mdc, 2)
    class BMI(ctypes.Structure):
        _fields_=[("biSize",wintypes.DWORD),("biWidth",wintypes.LONG),("biHeight",wintypes.LONG),
                  ("biPlanes",wintypes.WORD),("biBitCount",wintypes.WORD),("biCompression",wintypes.DWORD),
                  ("biSizeImage",wintypes.DWORD),("biXPelsPerMeter",wintypes.LONG),("biYPelsPerMeter",wintypes.LONG),
                  ("biClrUsed",wintypes.DWORD),("biClrImportant",wintypes.DWORD)]
    bi = BMI(); bi.biSize=ctypes.sizeof(bi); bi.biWidth=w; bi.biHeight=-h; bi.biPlanes=1
    bi.biBitCount=32; bi.biCompression=0
    buf = ctypes.create_string_buffer(w*h*4)
    gdi32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bi), 0)
    img = Image.frombuffer("RGBA", (w,h), buf, "raw", "BGRA", 0, 1).convert("RGB")
    img.save(path)
    gdi32.DeleteObject(bmp); gdi32.DeleteDC(mdc); user32.ReleaseDC(hwnd, hdc)
    return img

root = tk.Tk(); root.geometry("400x200+100+100"); root.configure(bg="#2b2b2b")
tk.Label(root, text="parent", bg="#2b2b2b", fg="#fff").pack()

top = tk.Toplevel(root); top.overrideredirect(True); top.geometry("360x140+120+120")
top.attributes("-transparentcolor", KEY); top.configure(bg=KEY)
tk.Label(top, text="The quick brown fox 你好世界 Housamo", bg=KEY, fg="#ffffff",
         font=("Microsoft YaHei UI", 15)).place(x=16, y=20)
tk.Label(top, text="第二行 mixed 中文 English 12345", bg=KEY, fg="#ffd9a0",
         font=("Microsoft YaHei UI", 13)).place(x=16, y=64)

def go():
    root.update(); top.update()
    a = capture(top.winfo_id(), "../.tmp/tk_key.png")
    print("size", a.size)
    # analyze text band colors
    from collections import Counter
    c = Counter()
    for y in range(18, 50):
        for x in range(14, 340):
            c[a.getpixel((x,y))] += 1
    print("top colors:", c.most_common(6))
    key = (255,0,254)
    odd = [ (p,n) for p,n in c.items() if max(abs(p[0]-key[0]),abs(p[1]-key[1]),abs(p[2]-key[2]))>18 and min(p)<245 ]
    print("suspect fringe colors:", odd[:8], "total", sum(n for _,n in odd))
    root.destroy()
root.after(700, go)
root.mainloop()
