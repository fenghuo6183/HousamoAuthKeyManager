
from PIL import Image
def lum(p): return 0.299*p[0]+0.587*p[1]+0.114*p[2]
box = (700, 340, 940, 390)  # around "未发现设备"
for name in ("diag25", "diag100"):
    im = Image.open(r"D:/123/4/.tmp/%s.png" % name).convert("RGB")
    px = list(im.crop(box).getdata())
    px.sort(key=lum)
    print(name, "darkest10:", px[:10])
    print("   count<80:", sum(1 for p in px if lum(p)<80), "count<120:", sum(1 for p in px if lum(p)<120), "count<160:", sum(1 for p in px if lum(p)<160))
