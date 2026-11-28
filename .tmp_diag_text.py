
from PIL import Image
for name in ("diag25", "diag100"):
    im = Image.open(r"D:/123/4/.tmp/%s.png" % name).convert("RGB")
    print(name, im.size)
    # page title band and first card heading band
    for (label, box) in (("title", (140, 100, 700, 190)), ("card-head", (160, 250, 900, 330)), ("row", (160, 380, 1100, 460))):
        crop = im.crop(box)
        px = list(crop.getdata())
        dark = [p for p in px if 0.299*p[0]+0.587*p[1]+0.114*p[2] < 110]
        print("  ", label, "darkcount", len(dark), "min", min(px, key=lambda p: 0.299*p[0]+0.587*p[1]+0.114*p[2]) if px else None)
