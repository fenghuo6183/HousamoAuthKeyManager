# -*- coding: utf-8 -*-
import os, io
from PIL import Image, ImageDraw

SRC = r"C:/Users/34455/.dsh/attachments/v1/objects/c6/c688496621ca66b977104b5c158966704914fcf208c0d8f6270d69d0835164fa"
ROOT = r"D:/123/4"
RES = os.path.join(ROOT, "android", "res")

src = Image.open(SRC).convert("RGB")
os.makedirs(os.path.join(ROOT, ".tmp"), exist_ok=True)
src.save(os.path.join(ROOT, ".tmp", "icon_src.jpg"), quality=95)
src.save(os.path.join(ROOT, ".tmp", "icon_src.png"))

# icon canvas: tighten framing on the character (900x900 from the 1024 art, face slightly above center)
S, CX, CY = 900, 512, 470
x0 = max(0, min(src.width - S, CX - S // 2))
y0 = max(0, min(src.height - S, CY - S // 2))
sq = src.crop((x0, y0, x0 + S, y0 + S))

# background color sampled from corners (adaptive-icon background layer)
px = sq.resize((8, 8))
cols = [px.getpixel((x, y)) for x in range(8) for y in range(8) if x in (0, 1, 6, 7) and y in (0, 1, 6, 7)]
bg = tuple(sum(c[i] for c in cols) // len(cols) for i in range(3))

LEG = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
ADP = {"mdpi": 108, "hdpi": 162, "xhdpi": 216, "xxhdpi": 324, "xxxhdpi": 432}

for d, s in LEG.items():
    dd = os.path.join(RES, "mipmap-" + d); os.makedirs(dd, exist_ok=True)
    sq.resize((s, s), Image.LANCZOS).save(os.path.join(dd, "ic_launcher.png"))
for d, s in ADP.items():
    dd = os.path.join(RES, "mipmap-" + d); os.makedirs(dd, exist_ok=True)
    # foreground bleeds to the full 108dp canvas; the launcher mask shows the centre 72dp
    sq.resize((s, s), Image.LANCZOS).save(os.path.join(dd, "ic_launcher_foreground.jpg"), quality=90)

dd = os.path.join(RES, "values"); os.makedirs(dd, exist_ok=True)
with io.open(os.path.join(dd, "colors.xml"), "w", encoding="utf-8") as f:
    f.write('<?xml version="1.0" encoding="utf-8"?>\n<resources>\n')
    f.write('    <color name="ic_launcher_bg">#%02X%02X%02X</color>\n' % bg)
    f.write('</resources>\n')

dd = os.path.join(RES, "mipmap-anydpi-v26"); os.makedirs(dd, exist_ok=True)
with io.open(os.path.join(dd, "ic_launcher.xml"), "w", encoding="utf-8") as f:
    f.write('<?xml version="1.0" encoding="utf-8"?>\n')
    f.write('<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n')
    f.write('    <background android:drawable="@color/ic_launcher_bg" />\n')
    f.write('    <foreground android:drawable="@mipmap/ic_launcher_foreground" />\n')
    f.write('</adaptive-icon>\n')

sq.resize((512, 512), Image.LANCZOS).save(os.path.join(ROOT, "docs", "icon.png")) if os.path.isdir(os.path.join(ROOT, "docs")) else None
sq.resize((512, 512), Image.LANCZOS).save(os.path.join(ROOT, ".tmp", "icon512.png"))
print("bg", bg, "canvas", sq.size)
