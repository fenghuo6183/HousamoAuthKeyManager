import os, sys
os.environ.setdefault('HOUSAMO_NO_ADB','1')
sys.path.insert(0, r'D:\123\4\win')
from PySide6.QtWidgets import QApplication, QScrollArea
app = QApplication([])
import qt_main
shell = qt_main.build_shell(qt_main.config.Settings(), live=False)
shell.resize(1100, 900)
shell.show_page('settings'); shell.show(); app.processEvents()
from qtui.pages import _SettingsPage, _data_section
sp = shell.findChild(_SettingsPage)
sp.select(3); app.processEvents(); app.processEvents()
page = sp.stack.widget(3)
print('settings', sp.width(), sp.minimumSizeHint().width(), 'page', page.width(), page.minimumSizeHint().width())
w = page.widget(); print('inner', w.width(), w.minimumSizeHint().width())
for i in range(page.column.count()):
    it = page.column.itemAt(i).widget()
    if it:
        print('card', it.width(), it.minimumSizeHint().width())
        lay = it.layout()
        for j in range(lay.count()):
            ch = lay.itemAt(j).widget()
            if ch: print('   child', j, type(ch).__name__, ch.width(), ch.minimumSizeHint().width())
