# -*- coding: utf-8 -*-
"""Qt system tray: QSystemTrayIcon with a small painted app glyph."""

from __future__ import annotations

import os

from PySide6.QtCore import QObject, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from app import theme

from . import base


def app_icon(pal=None):
    """Use the packaged .ico when present, otherwise paint a rounded monogram."""
    icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "assets", "app.ico")
    if os.path.exists(icon_path):
        icon = QIcon(icon_path)
        if not icon.isNull():
            return icon
    pal = pal or theme.palette("light")
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(pal["accent"]))
    painter.drawRoundedRect(QRectF(2, 2, 60, 60), 16, 16)
    painter.setPen(QColor("#FFFFFF"))
    painter.setFont(base.font(30, bold=True))
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "A")
    painter.end()
    return QIcon(pixmap)


class Tray(QObject):
    """Tray icon whose menu mirrors the old Tk tray (show / quit)."""

    def __init__(self, shell, pal=None):
        super().__init__(shell)
        self.shell = shell
        self.icon = QSystemTrayIcon(app_icon(pal), self)
        self.icon.setToolTip(theme.APP_NAME)
        self.menu = QMenu()
        self.menu.addAction("显示窗口", shell.bring_to_front)
        self.backup_action = self.menu.addAction("立即备份", self._backup)
        self.menu.addSeparator()
        self.menu.addAction("退出", shell.quit_app)
        self.icon.setContextMenu(self.menu)
        self.icon.activated.connect(self._on_activated)
        self.ok = False

    def start(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.ok = False
            return False
        self.icon.show()
        self.ok = True
        return True

    def stop(self):
        self.icon.hide()
        self.ok = False

    def notify(self, title, text):
        if not self.ok:
            return
        self.icon.showMessage(title, text, QSystemTrayIcon.Information, 4000)

    def _backup(self):
        controller = getattr(self.shell, "controller", None)
        if controller is not None:
            controller.backup()

    def _on_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.shell.bring_to_front()
