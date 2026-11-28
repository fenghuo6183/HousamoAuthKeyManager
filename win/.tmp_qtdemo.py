
import os, sys
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QImage, QPixmap, QPainter, QPainterPath, QColor, QFont, QPen, QLinearGradient
from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QComboBox,
                               QLineEdit, QVBoxLayout, QHBoxLayout, QFrame)

WALL = os.path.join(os.environ.get("APPDATA",""), "HousamoAuthKeyManager", "background.jpg")
W, H = 1100, 900
SCALE = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
ALPHA = float(sys.argv[2]) if len(sys.argv) > 2 else 0.14
OUT = sys.argv[3] if len(sys.argv) > 3 else "../.tmp/qt_demo.png"

def cover_pixmap(path, w, h):
    pm = QPixmap(path)
    if pm.isNull():
        pm = QPixmap(w, h); pm.fill(QColor("#3a3f52")); return pm
    pm = pm.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    x = (pm.width() - w)//2; y = (pm.height() - h)//2
    return pm.copy(x, y, w, h)

app = QApplication(sys.argv)
root = QWidget()
root.resize(W, H)

class Backdrop(QWidget):
    def __init__(self, pm):
        super().__init__(root)
        self.pm = pm
        self.setGeometry(0, 0, W, H)
    def paintEvent(self, e):
        p = QPainter(self)
        p.drawPixmap(0, 0, self.pm)
        # slight dark veil so white text works
        p.fillRect(self.rect(), QColor(12, 16, 28, 74))

backdrop = Backdrop(cover_pixmap(WALL, W, H))

def card(parent, x, y, w, h, radius=22):
    c = QWidget(parent)
    c.setGeometry(x, y, w, h)
    c._r = radius
    c._alpha = ALPHA
    def paint(self, e, c=c):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        path = QPainterPath(); path.addRoundedRect(QRectF(self.rect()).adjusted(1,1,-1,-1), c._r, c._r)
        # shadow
        for i in range(10, 0, -1):
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, int(3.2*i*(c._alpha+0.2))))
            p.drawRoundedRect(QRectF(self.rect()).adjusted(1-i*0.6, 2-i*0.3, -1+i*0.6, -1+i*0.6), c._r+i*0.5, c._r+i*0.5)
        p.setClipPath(path)
        p.fillPath(path, QColor(255, 255, 255, int(255*c._alpha)))
        p.setClipping(False)
        p.setPen(QPen(QColor(255,255,255,int(90*min(1.0,c._alpha*4))), 1))
        p.drawPath(path)
    c.paintEvent = paint.__get__(c, QWidget)
    return c

def label(parent, text, size=10.5, color="#F2F5FA", bold=False):
    l = QLabel(text, parent)
    f = QFont("Microsoft YaHei UI", size)
    f.setBold(bold)
    l.setFont(f)
    l.setStyleSheet("background: transparent; color: %s;" % color)
    return l

def pill(parent, text, kind="primary", w=170, h=40):
    b = QPushButton(text, parent)
    f = QFont("Microsoft YaHei UI", 10); f.setBold(kind=="primary")
    b.setFont(f); b.setCursor(Qt.PointingHandCursor); b.resize(w, h)
    if kind == "primary":
        b.setStyleSheet("QPushButton{border:none;border-radius:%dpx;color:white;"
                        "background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #4A82FF,stop:1 #2F6BFF);}"
                        "QPushButton:hover{background:#4A82FF;}" % (h//2))
    else:
        b.setStyleSheet("QPushButton{border:1px solid rgba(255,255,255,90);border-radius:%dpx;color:#EAF0FA;"
                        "background:rgba(255,255,255,32);}QPushButton:hover{background:rgba(255,255,255,56);}" % (h//2))
    return b

# rail
rail = QWidget(root); rail.setGeometry(0, 0, 258, H)
def rail_paint(self, e):
    p = QPainter(self); p.fillRect(self.rect(), QColor(255,255,255,26))
    p.setPen(QPen(QColor(255,255,255,40), 1)); p.drawLine(self.width()-1, 0, self.width()-1, self.height())
rail.paintEvent = rail_paint.__get__(rail, QWidget)

t = label(rail, "东放 AuthKey 管家", 15, "#FFFFFF", True); t.move(28, 34)
s = label(rail, "Housamo AuthKey Manager", 9, "#C9D4E6"); s.move(28, 66)
for i, (name, active) in enumerate([("任务", True), ("账号库", False), ("设置", False)]):
    bw = QWidget(rail); bw.setGeometry(16, 130 + i*56, 226, 46)
    def paint(self, e, active=active):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing, True)
        path = QPainterPath(); path.addRoundedRect(QRectF(self.rect()), 12, 12)
        p.fillPath(path, QColor(47,107,255,205) if active else QColor(255,255,255,18))
    bw.paintEvent = paint.__get__(bw, QWidget)
    l = label(bw, name, 10.5, "#FFFFFF" if active else "#DCE4F2", active); l.move(18, 13)

# card 1: tasks
c1 = card(root, 288, 120, 788, 340)
label(c1, "连接", 13, "#FFFFFF", True).move(26, 20)
label(c1, "当前设备：127.0.0.1:16384　·　已连接", 10, "#C9D4E6").move(26, 52)
pill(c1, "连接设置", "ghost", 130, 38).move(26, 88)
pill(c1, "打开游戏", "primary", 150, 40).move(26, 146)
label(c1, "备份 AuthKey 会在游戏启动后读取账号目录。", 10, "#C9D4E6").move(26, 200)

# card 2: settings rows
c2 = card(root, 288, 490, 788, 330)
label(c2, "运行设置", 13, "#FFFFFF", True).move(26, 20)
rows = [("连接配置", "自动检测"), ("扫描端口", "16384, 7555, 62001"), ("只显示模拟器", "开启")]
y = 62
for k, v in rows:
    label(c2, k, 10.5, "#EAF0FA").move(26, y+8)
    box = QLineEdit(c2); box.setText(v); box.setGeometry(300, y, 320, 34)
    box.setStyleSheet("QLineEdit{background:rgba(255,255,255,26);border:1px solid rgba(255,255,255,60);"
                      "border-radius:8px;color:#FFFFFF;padding-left:10px;}")
    y += 52
cb = QComboBox(c2); cb.addItems(["自动检测", "MuMu", "雷电"]); cb.setGeometry(300, y, 200, 34)
cb.setStyleSheet("QComboBox{background:rgba(255,255,255,26);border:1px solid rgba(255,255,255,60);"
                 "border-radius:8px;color:#FFFFFF;padding-left:10px;}"
                 "QComboBox::drop-down{border:none;}QComboBox QAbstractItemView{background:#2b3244;color:#fff;}")
label(c2, "连接配置", 10.5, "#EAF0FA").move(26, y+8)

# log card
c3 = card(root, 288, 845 - 20, 788, 0)  # skipped, keep simple

root.show()
app.processEvents()
pm = root.grab()
pm.save(OUT)
print("saved", OUT, pm.width(), pm.height())
