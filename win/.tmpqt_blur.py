
import os, sys
sys.path.insert(0, ".")
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap, QImage
from PIL import Image, ImageFilter
app = QApplication(sys.argv)
WALL = os.path.join(os.environ.get("APPDATA",""), "HousamoAuthKeyManager", "background.jpg")
print("wall exists", os.path.isfile(WALL))
pm = QPixmap(WALL).scaled(1100, 900)
img = QImage(pm).convertToFormat(QImage.Format_RGBA8888)
print("img", img.width(), img.height(), img.bytesPerLine())
data = bytes(img.bits())
pil = Image.frombytes("RGBA", (img.width(), img.height()), data, "raw", "RGBA", img.bytesPerLine(), 1)
print("pil", pil.size)
pil = pil.filter(ImageFilter.GaussianBlur(8))
raw = pil.tobytes("raw", "RGBA")
qimg = QImage(raw, pil.width, pil.height, QImage.Format_RGBA8888).copy()
print("qimg", qimg.width(), qimg.height(), qimg.isNull())
out = QPixmap.fromImage(qimg)
print("pm", out.width(), out.height(), out.isNull())
out.save("../.tmp/qt_blurtest.png")
print("ok")
