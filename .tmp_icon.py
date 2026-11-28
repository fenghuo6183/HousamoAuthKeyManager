
import os
from PIL import Image
src = r"D:/123/4/docs/icon.png"
out = r"D:/123/4/win/assets/icon.ico"
os.makedirs(os.path.dirname(out), exist_ok=True)
im = Image.open(src).convert("RGBA")
sizes = [(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)]
im.save(out, format="ICO", sizes=sizes)
print(out, os.path.getsize(out))
