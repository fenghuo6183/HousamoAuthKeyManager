# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import bgfx, theme
pal = theme.palette("light")
b = bgfx.Backdrop(pal)
src = os.path.join(os.environ["APPDATA"], "HousamoAuthKeyManager", "background.jpg")
print("exists", os.path.isfile(src))
b.configure(path=src, blur=0, alpha=100)
a = b.full(1100, 900).copy(); b.invalidate()
b.blur = 12
c = b.full(1100, 900).copy()
from PIL import ImageChops
diff = ImageChops.difference(a, c)
print("bbox", diff.getbbox(), "max", max(diff.convert("L").getdata()))
