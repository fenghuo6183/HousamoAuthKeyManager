import os, sys
os.environ.setdefault("HOUSAMO_DATA_DIR", "D:/123/4/.tmp/dlgdata")
os.environ.setdefault("HOUSAMO_NO_ADB", "1")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QLineEdit
from app import config
from qtui import dialogs, base
from qtui.widgets import PillButton
from qt_main import build_shell

app = QApplication(sys.argv)
shell = build_shell(config.Settings(), live=False)
pal = shell.pal

def click_ok(text=None):
    dlg = QApplication.activeModalWidget()
    print("modal:", type(dlg).__name__ if dlg else None)
    if not dlg:
        return
    if text is not None:
        edit = dlg.findChild(QLineEdit)
        if edit is not None:
            edit.setText(text)
    for btn in dlg.findChildren(PillButton):
        if btn.text() in ("确定", "删除"):
            btn.click()
            return

QTimer.singleShot(400, lambda: click_ok("测试名字"))
print("ask_text ->", repr(dialogs.ask_text(shell, pal, "重命名", "新的名字：", default="旧名字")))

QTimer.singleShot(400, lambda: click_ok())
print("confirm ->", dialogs.confirm(shell, pal, "删除记录", "确定删除吗？", ok_text="删除", danger=True))

QTimer.singleShot(400, lambda: click_ok("1234"))
print("pin ->", repr(dialogs.ask_text(shell, pal, "应用锁", "输入 PIN 解锁：", password=True)))
shell.close()
