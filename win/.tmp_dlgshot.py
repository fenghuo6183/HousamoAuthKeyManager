import os, sys, time
os.environ.setdefault("HOUSAMO_DATA_DIR", "D:/123/4/.tmp/dlgdata")
os.environ.setdefault("HOUSAMO_NO_ADB", "1")
os.environ.setdefault("HOUSAMO_NO_TRAY", "1")
os.environ.setdefault("QT_SCALE_FACTOR", "1.5")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PySide6.QtCore import QPoint
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication
from app import config
from qtui import dialogs, pages
from qt_main import build_shell

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".tmp")

def pump(ms=420):
    end = time.time() + ms / 1000.0
    while time.time() < end:
        QApplication.processEvents()
        time.sleep(0.01)

app = QApplication(sys.argv)
settings = config.Settings()
if os.environ.get("SNAP_THEME"):
    settings.set("theme", os.environ["SNAP_THEME"], save=False)
shell = build_shell(settings, live=False)
shell.resize(1100, 900)
shell.show_page("tasks")
shell.show()
pump(900)

shots = []
def fake_exec(self):
    self.show()
    self.adjustSize()
    pump(450)
    shots.append((self, self.grab()))
    self.close()
    pump(120)
    return 0
dialogs.GlassDialog.exec = fake_exec

pal = shell.pal
dialogs.ask_text(shell, pal, "重命名", "新的名字：", default="Housamo 主号")
dialogs.ask_text(shell, pal, "应用锁", "输入 PIN 解锁：", password=True)
dialogs.confirm(shell, pal, "删除记录", "确定删除「Housamo 主号」吗？密钥会从本机账号库里移除。", ok_text="删除", danger=True)
dialogs.show_qr(shell, pal, "Housamo 主号", pages._qr_pixmap("housamo-demo-key-0123456789"),
                "手机版「任务 · 扫码导入」可以直接扫这张图")
dialogs.show_lan(shell, pal, "http://192.168.1.23:8765", "4821",
                 "手机和电脑连同一个 Wi-Fi，然后在手机版输入这个地址")

base = shell.grab()
shell_pos = shell.mapToGlobal(QPoint(0, 0))
from PIL import Image
for i, (dlg, pm) in enumerate(shots):
    dlg_pos = dlg.mapToGlobal(QPoint(0, 0))
    dx = dlg_pos.x() - shell_pos.x()
    dy = dlg_pos.y() - shell_pos.y()
    base.save(os.path.join(OUT, "dlg_base.png"))
    shell_img = Image.open(os.path.join(OUT, "dlg_base.png")).convert("RGBA")
    dlg_path = os.path.join(OUT, "dlg_raw_%d.png" % i)
    pm.save(dlg_path)
    dlg_img = Image.open(dlg_path).convert("RGBA")
    shell_img.alpha_composite(dlg_img, (max(0, dx), max(0, dy)))
    shell_img.convert("RGB").save(os.path.join(OUT, "dlg_%d.png" % i))
    print("shot", i, dlg.windowTitle(), dx, dy, dlg_img.size)
print("done")
