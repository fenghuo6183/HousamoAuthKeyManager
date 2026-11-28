
import os, sys, tkinter as tk
from PIL import Image, ImageTk, ImageGrab

WALL = os.path.join(os.environ.get("APPDATA", ""), "HousamoAuthKeyManager", "background.jpg")
KEY = "#FF00FE"

root = tk.Tk()
root.geometry("700x460+80+60")
root.configure(bg="#222")

img = Image.open(WALL).convert("RGB")
sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
# cover crop
ratio = max(700/img.width, 460/img.height)
img = img.resize((int(img.width*ratio)+1, int(img.height*ratio)+1), Image.LANCZOS)
img = img.crop(((img.width-700)//2, (img.height-460)//2, (img.width-700)//2+700, (img.height-460)//2+460))
photo = ImageTk.PhotoImage(img)
cv = tk.Canvas(root, width=700, height=460, highlightthickness=0, bd=0)
cv.place(x=0, y=0)
cv.create_image(0, 0, image=photo, anchor="nw")

top = tk.Toplevel(root)
top.overrideredirect(True)
top.geometry("420x200+200+180")
top.attributes("-transparentcolor", KEY)
top.configure(bg=KEY)
try:
    top.attributes("-alpha", 1.0)
except Exception as e:
    print("alpha fail", e)

frame = tk.Frame(top, bg=KEY)
frame.place(x=0, y=0, relwidth=1, relheight=1)
tk.Label(frame, text="The quick brown fox 你好，世界 123", bg=KEY, fg="#ffffff",
         font=("Microsoft YaHei UI", 14)).place(x=20, y=20)
tk.Label(frame, text="第二行文字，用来检查边缘有没有洋红色描边。", bg=KEY, fg="#ffe9c0",
         font=("Microsoft YaHei UI", 12)).place(x=20, y=60)

run = tk.Canvas(frame, width=140, height=36, bg=KEY, highlightthickness=0, bd=0)
run.place(x=20, y=110)
run.create_oval(2, 2, 34, 34, fill="#2F6BFF", outline="")
run.create_oval(6, 6, 30, 30, fill="#2F6BFF", outline="")
run.create_rectangle(18, 2, 34, 34, fill="#2F6BFF", outline="")
run.create_text(78, 18, text="打开游戏", fill="#ffffff", font=("Microsoft YaHei UI", 12))

root.after(900, lambda: shot())
def shot():
    root.update()
    x, y = root.winfo_rootx(), root.winfo_rooty()
    im = ImageGrab.grab(bbox=(x, y, x+700, y+460))
    im.save("../.tmp/transkey.png")
    print("saved", im.size)
    root.destroy()

root.mainloop()
