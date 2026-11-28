
import os, tkinter as tk
from PIL import Image, ImageTk, ImageGrab, ImageChops

WALL = os.path.join(os.environ.get("APPDATA",""), "HousamoAuthKeyManager", "background.jpg")
KEY = "#FF00FE"
root = tk.Tk(); root.geometry("700x460+80+60"); root.configure(bg="#222")
img = Image.open(WALL).convert("RGB")
ratio = max(700/img.width, 460/img.height)
img = img.resize((int(img.width*ratio)+1, int(img.height*ratio)+1), Image.LANCZOS)
img = img.crop(((img.width-700)//2,(img.height-460)//2,(img.width-700)//2+700,(img.height-460)//2+460))
photo = ImageTk.PhotoImage(img)
cv = tk.Canvas(root, width=700, height=460, highlightthickness=0, bd=0); cv.place(x=0,y=0)
cv.create_image(0,0,image=photo,anchor="nw")

top = tk.Toplevel(root); top.overrideredirect(True); top.geometry("420x200+200+180")
top.attributes("-transparentcolor", KEY); top.configure(bg=KEY)
f = tk.Frame(top, bg=KEY); f.place(x=0,y=0,relwidth=1,relheight=1)
tk.Label(f, text="The quick brown fox 你好，世界 123", bg=KEY, fg="#ffffff",
         font=("Microsoft YaHei UI", 14)).place(x=20,y=20)
run = tk.Canvas(f, width=140, height=36, bg=KEY, highlightthickness=0, bd=0); run.place(x=20,y=110)
run.create_rectangle(2,2,34,34, fill="#2F6BFF", outline="")
run.create_text(78,18, text="打开游戏", fill="#ffffff", font=("Microsoft YaHei UI",12))

def grab(name):
    root.update(); root.after(120); root.update()
    x,y = root.winfo_rootx(), root.winfo_rooty()
    im = ImageGrab.grab(bbox=(x,y,x+700,y+460)); im.save(name); return im

root.after(800, lambda: step())
def step():
    a = grab("../.tmp/tk_on.png")
    top.withdraw(); root.update(); root.after(150); root.update()
    b = grab("../.tmp/tk_off.png")
    d = ImageChops.difference(a.convert("RGB"), b.convert("RGB"))
    # region inside card but away from any drawn text: sample columns 300-380, rows 200-300
    import statistics
    vals=[]
    for yy in range(210,300,7):
        for xx in range(300,400,7):
            vals.append(d.getpixel((xx,yy)))
    print("diff inside card blank area: max", max(max(v) for v in vals), "mean", sum(sum(v) for v in vals)/len(vals)/3)
    # text region
    vals2=[]
    for yy in range(195,240):
        for xx in range(220,520):
            vals2.append(d.getpixel((xx,yy)))
    print("diff text band: max", max(max(v) for v in vals2))
    root.destroy()
root.mainloop()
