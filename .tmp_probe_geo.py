import os, sys, tempfile
os.environ['HOUSAMO_DATA_DIR'] = tempfile.mkdtemp(prefix='hak-probe-')
os.environ['HOUSAMO_NO_ADB'] = '1'
sys.path.insert(0, r'D:\123\4\win')
from PySide6.QtWidgets import QApplication, QScrollArea
app = QApplication([])
import qt_main
shell = qt_main.build_shell(qt_main.config.Settings(), live=False)
shell.resize(1100, 900)
shell.show(); app.processEvents()
shell.show_page('settings')
from qtui.pages import _SettingsPage
sp = shell.findChild(_SettingsPage)
sp.select(3); app.processEvents()
page = sp.stack.widget(3)
print('settings', sp.width(), sp.minimumSizeHint().width())
print('page', page.width(), page.minimumSizeHint().width())
sa = page.findChild(QScrollArea)
print('scroll', sa.width() if sa else None, 'viewport', sa.viewport().width() if sa else None, 'hbar max', sa.horizontalScrollBar().maximum() if sa else None)
w = page.widget()
print('inner', w.width(), w.minimumSizeHint().width())
col = page.column
for i in range(col.count()):
    it = col.itemAt(i).widget()
    if it: print(' item', i, type(it).__name__, it.width(), it.minimumSizeHint().width())
