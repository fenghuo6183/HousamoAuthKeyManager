# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from app import config
from qtui.pages import settings_page
from qtui.window import Shell

app = QApplication(sys.argv)
settings = config.Settings()
shell = Shell(settings, live=True)
shell.add_page("settings", settings_page(shell))
shell.resize(1100, 900)
def probe():
    shell.show_page("settings")
    sw = shell.pages.currentWidget()
    sw.select(3)
    shell.resize(1100, 900)
    app.processEvents(); shell.repaint(); app.processEvents()
    page = sw.stack.widget(3)
    print("settings", sw.width(), "page", page.width(), "inner", page.widget().width())
    card = page.column.itemAt(0).widget()
    print("card", card.geometry().getRect())
    lay = card.layout()
    for j in range(lay.count()):
        ch = lay.itemAt(j).widget()
        if not ch: continue
        print(j, type(ch).__name__, "geom", ch.geometry().getRect(), "min", ch.minimumSizeHint().width())
        if type(ch).__name__ == "Field":
            for k in range(ch.layout().count()):
                it = ch.layout().itemAt(k)
                w = it.widget()
                if w: print("   ", type(w).__name__, w.geometry().getRect(), "min", w.minimumSizeHint().width())
    shell.grab().save("../.tmp/probe_geo.png")
    app.quit()
QTimer.singleShot(3000, probe)
sys.exit(app.exec())
