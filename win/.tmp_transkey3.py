
import os, tkinter as tk
from PIL import Image, ImageTk, ImageGrab

KEY = "#FF00FE"
root = tk.Tk(); root.geometry("700x460+80+60"); root.configure(bg="#336")
cv = tk.Canvas(root, width=700, height=460, highlightthickness=0, bd=0); cv.place(x=0,y=0)
cv.configure(bg="#336")
cv.create_rectangle(0,0,700,460, fill="#4a7")

top = tk.Toplevel(root); top.overrideredirect(True); top.geometry("420x200+200+180")
top.attributes("-transparentcolor", KEY)
top.configure(bg=KEY)
c2 = tk.Canvas(top, bg=KEY, highlightthickness=0, bd=0); c2.place(x=0,y=0,relwidth=1,relheight=1)
c2.create_rectangle(10,10,110,110, fill="#ff0000", outline="")
c2.create_text(30,150, text="HELLO", fill="#ffffff", font=("Microsoft YaHei UI",16), anchor="nw")

def step():
    root.update(); root.after(400); root.update()
    print("viewable", top.winfo_viewable(), "geom", top.winfo_geometry(), "rootxy", top.winfo_rootx(), top.winfo_rooty())
    im = ImageGrab.grab(); im.save("../.tmp/tk_full.png")
    # crop around expected area
    x,y = top.winfo_rootx(), top.winfo_rooty()
    im.crop((x-20,y-20,x+440,y+220)).save("../.tmp/tk_card.png")
    print("px at red center", im.getpixel((x+60,y+60)))
    print("px at green bg behind", im.getpixel((x+300,y+150)))
    root.destroy()
root.after(900, step)
root.mainloop()
