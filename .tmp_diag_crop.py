
from PIL import Image
im = Image.open(r"D:/123/4/.tmp/diag100.png").convert("RGB")
im.crop((150, 230, 1150, 470)).save(r"D:/123/4/.tmp/d100crop.png")
im2 = Image.open(r"D:/123/4/.tmp/diag25.png").convert("RGB")
im2.crop((150, 230, 1150, 470)).save(r"D:/123/4/.tmp/d25crop.png")
