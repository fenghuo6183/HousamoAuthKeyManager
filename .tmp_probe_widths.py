import os, sys, tempfile
os.environ['HOUSAMO_DATA_DIR'] = tempfile.mkdtemp(prefix='hak-probe-')
os.environ['HOUSAMO_NO_ADB'] = '1'
sys.path.insert(0, r'D:\123\4\win')
from PySide6.QtWidgets import QApplication
app = QApplication([])
import qt_main
shell = qt_main.build_shell(qt_main.config.Settings(), live=False)
sp = shell.pages.widget(shell.pages.currentIndex()) if hasattr(shell.pages,'widget') else None
from qtui.pages import _SettingsPage
for w in shell.findChildren(_SettingsPage):
    print('settings page min', w.minimumSizeHint().width(), 'size', w.width())
    stack = w.stack
    print('stack min', stack.minimumSizeHint().width())
    for i in range(stack.count()):
        p = stack.widget(i)
        m = p.minimumSizeHint().width()
        print(i, p.minimumSizeHint().width(), p.sizeHint().width())
        if m > 500:
            for c in p.findChildren(object):
                try:
                    mw = c.minimumSizeHint().width()
                except Exception:
                    continue
                if mw > 300:
                    print('   big', type(c).__name__, getattr(c,'objectName',lambda:'')(), mw)
