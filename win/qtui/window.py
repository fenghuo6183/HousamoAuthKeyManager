# -*- coding: utf-8 -*-
"""Main window shell: wallpaper backdrop, left rail, page stack."""

from __future__ import annotations

import os

from PySide6.QtCore import QEvent, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QScrollArea,
                               QStackedWidget, QVBoxLayout, QWidget)

from app import config, theme

from . import base
from .widgets import NavButton


def cover_pixmap(path, width, height):
    """Wallpaper scaled to cover the window, centre-cropped."""
    pm = QPixmap(path) if path and os.path.isfile(path) else QPixmap()
    if pm.isNull():
        return None
    pm = pm.scaled(int(width), int(height), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    x = max(0, (pm.width() - int(width)) // 2)
    y = max(0, (pm.height() - int(height)) // 2)
    return pm.copy(x, y, int(width), int(height))


def blurred(pixmap, radius, width, height):
    """Blur through PIL when available (Qt's blur effect is far slower here)."""
    if radius <= 0 or pixmap is None:
        return pixmap
    try:
        from PIL import Image, ImageFilter
    except Exception:
        return pixmap
    img = pixmap.toImage().convertToFormat(QImage.Format_RGBA8888)
    data = bytes(img.bits())
    pil = Image.frombytes("RGBA", (img.width(), img.height()), data, "raw", "RGBA",
                          img.bytesPerLine(), 1)
    pil = pil.filter(ImageFilter.GaussianBlur(float(radius)))
    raw = pil.tobytes("raw", "RGBA")
    qimg = QImage(raw, pil.width, pil.height, QImage.Format_RGBA8888).copy()
    return QPixmap.fromImage(qimg)


class Backdrop(QWidget):
    """Paints the wallpaper once per size change; everything else floats above."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pal = theme.PALETTE
        self._pm = None
        self._key = None
        self.path = ""
        self.blur = 12
        self.veil = 0

    def configure(self, path="", blur=12, veil=0, pal=None):
        self.path = path or ""
        self.blur = blur
        self.veil = veil
        if pal is not None:
            self.pal = pal
        self._key = None
        self.update()

    def _ensure(self):
        size = (max(1, self.width()), max(1, self.height()))
        key = (self.path, self.blur, self.veil, size, id(self.pal))
        if key == self._key and self._pm is not None:
            return
        self._key = key
        pm = cover_pixmap(self.path, size[0], size[1])
        if pm is not None:
            pm = blurred(pm, self.blur, size[0], size[1])
        if pm is None:
            pm = QPixmap(size[0], size[1])
            pm.fill(QColor(self.pal["wall_top"]))
        p = QPainter(pm)
        if self.veil:
            p.fillRect(pm.rect(), base.qc(self.pal["window"], self.veil))
        p.end()
        self._pm = pm

    def pixmap(self):
        """The finished wallpaper (already blurred + veiled) for glass compositing."""
        self._ensure()
        return self._pm

    def paintEvent(self, event):
        self._ensure()
        if self._pm is not None:
            QPainter(self).drawPixmap(0, 0, self._pm)


class Rail(QWidget):
    """Left navigation rail; translucent so the wallpaper shows through."""

    page_requested = Signal(str)

    def __init__(self, pal, parent=None, alpha=0.92):
        super().__init__(parent)
        self.pal = pal
        self.alpha = alpha
        self.setFixedWidth(258)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 30, 16, 18)
        layout.setSpacing(6)

        title = QLabel(theme.APP_NAME)
        title.setFont(base.font(15, bold=True))
        title.setStyleSheet("background: transparent; color: %s;" % pal["text"])
        subtitle = QLabel("Housamo AuthKey Manager")
        subtitle.setFont(base.font(9))
        subtitle.setStyleSheet("background: transparent; color: %s;" % pal["text_muted"])
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(28)

        self.buttons = {}
        for key, text in (("tasks", "任务"), ("vault", "账号库"), ("settings", "设置")):
            button = NavButton(pal, text, self)
            button.clicked.connect(lambda _=False, k=key: self.page_requested.emit(k))
            layout.addWidget(button)
            self.buttons[key] = button
        layout.addStretch(1)

        version = QLabel("v" + theme.APP_VERSION)
        version.setFont(base.font(9))
        version.setStyleSheet("background: transparent; color: %s;" % pal["text_faint"])
        layout.addWidget(version)

    def select(self, key):
        for name, button in self.buttons.items():
            button.setChecked(name == key)
            button.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)
        base.paint_glass(p, self, self.pal, QRectF(self.rect()), 0, self.alpha,
                         base_key="rail", soft_key=None)
        p.setPen(base.qc(self.pal["border"], 120))
        p.drawLine(self.width() - 1, 0, self.width() - 1, self.height())





class Page(QScrollArea):
    """Scrollable page: a column of glass cards inside a fixed content width."""

    def __init__(self, pal, title, subtitle="", parent=None, head_in_card=False):
        super().__init__(parent)
        self.pal = pal
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.viewport().setAutoFillBackground(False)
        self.setStyleSheet("QScrollArea{background: transparent;}")

        body = QWidget()
        body.setStyleSheet("background: transparent;")
        self.column = QVBoxLayout(body)
        self.column.setContentsMargins(34, 26, 34, 26)
        self.column.setSpacing(16)

        head_widget = QWidget()
        head_widget.setStyleSheet("background: transparent;")
        head = QVBoxLayout(head_widget)
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(4)
        self.title = QLabel(title)
        self.title.setFont(base.font(19, bold=True))
        self.title.setStyleSheet("background: transparent; color: %s;" % pal["text"])
        head.addWidget(self.title)
        if subtitle:
            self.subtitle = QLabel(subtitle)
            self.subtitle.setFont(base.font(10))
            self.subtitle.setStyleSheet("background: transparent; color: %s;" % pal["text_muted"])
            head.addWidget(self.subtitle)
        self.head = head_widget
        if not head_in_card:
            self.column.addWidget(head_widget)
            self.column.addSpacing(6)
        self.setWidget(body)

    def add(self, widget, stretch=0):
        self.column.addWidget(widget, stretch)
        return widget


class Shell(QWidget):
    """Window chrome: backdrop + rail + page stack."""

    def __init__(self, settings=None, live=True):
        super().__init__()
        self.settings = settings or config.Settings()
        self.pal = theme.palette(self.settings.get("theme"))
        self.controller = None
        self.hotkey = None
        self._quitting = False
        base.set_low_mode(bool(self.settings.get("low_mode")))
        if live:
            from .controller import Controller
            self.controller = Controller(self.settings, self)
        self.setWindowTitle(theme.APP_NAME)
        self.resize(1100, 900)
        self.setMinimumSize(980, 700)
        self.setAcceptDrops(True)

        self.backdrop = Backdrop(self)
        self.backdrop.setGeometry(self.rect())
        self.backdrop.configure(path=self.settings.get("bg_image"),
                                blur=0 if self.settings.get("low_mode")
                                else self.settings.get("bg_blur"),
                                veil=110, pal=self.pal)
        self.backdrop.lower()

        self.rail = Rail(self.pal, self,
                         alpha=base.card_alpha(self.settings.get("glass")))
        self.pages = QStackedWidget(self)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        row.addWidget(self.rail)
        row.addWidget(self.pages, 1)

        self._cards = [self.rail]
        self.rail.page_requested.connect(self.show_page)
        self.page = "tasks"

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.backdrop.setGeometry(self.rect())
        self.backdrop.lower()

    # -- window lifecycle ---------------------------------------------
    def bring_to_front(self):
        self.showNormal()
        self.show()
        self.raise_()
        self.activateWindow()

    def quit_app(self):
        self._quitting = True
        tray = getattr(self, "tray", None)
        if tray is not None:
            try:
                tray.stop()
            except Exception:
                pass
        QApplication.quit()

    def closeEvent(self, event):
        tray = getattr(self, "tray", None)
        if (tray is not None and getattr(tray, "ok", False)
                and self.settings.get("close_to_tray")
                and not getattr(self, "_quitting", False)):
            event.ignore()
            self.hide()
            tray.notify(theme.APP_NAME, "已缩到托盘，右键图标可以退出")
            return
        self._quitting = True
        super().closeEvent(event)
        QApplication.quit()

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange and self.isMinimized():
            tray = getattr(self, "tray", None)
            if (tray is not None and getattr(tray, "ok", False)
                    and self.settings.get("minimize_to_tray")
                    and not getattr(self, "_quitting", False)):
                QTimer.singleShot(0, self.hide)
                if self.settings.get("notify_balloon"):
                    tray.notify(theme.APP_NAME, "已缩到托盘，双击图标可以打开")
        super().changeEvent(event)

    # -- appearance / hotkey ------------------------------------------
    def apply_low_mode(self, flag):
        """Live switch for low-end machines: no glass blur, no card shadows."""
        flag = bool(flag)
        self.settings.set("low_mode", flag)
        base.set_low_mode(flag)
        self.backdrop.configure(path=self.settings.get("bg_image"),
                                blur=0 if flag else self.settings.get("bg_blur"),
                                veil=110, pal=self.pal)
        self.backdrop.update()
        self.update()
        for card in self._cards:
            card.update()

    def set_hotkey(self, flag):
        """Register/unregister Ctrl+Alt+A; returns whether it is active now."""
        if flag:
            if self.hotkey is None:
                from .hotkey import Hotkey
                self.hotkey = Hotkey(self)
                self.hotkey.triggered.connect(self.bring_to_front)
            ok = self.hotkey.register()
            self.settings.set("hotkey", bool(ok))
            return ok
        if self.hotkey is not None:
            self.hotkey.unregister()
        self.settings.set("hotkey", False)
        return False

    def hotkey_active(self):
        return bool(self.hotkey is not None and self.hotkey.active())

    # -- drag & drop .hak files ---------------------------------------
    def dragEnterEvent(self, event):
        for url in event.mimeData().urls():
            if url.isLocalFile() and url.toLocalFile().lower().endswith(".hak"):
                event.acceptProposedAction()
                return
        super().dragEnterEvent(event)

    def dropEvent(self, event):
        from app.dnd import HAK_SUFFIXES

        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        paths = [p for p in paths if p.lower().endswith(HAK_SUFFIXES)]
        if not paths:
            super().dropEvent(event)
            return
        event.acceptProposedAction()
        if self.controller is not None:
            self.bring_to_front()
            for path in paths:
                self.controller.import_file(path)

    def add_page(self, key, page):
        self.pages.addWidget(page)
        page._key = key
        return page

    def show_page(self, key):
        for i in range(self.pages.count()):
            page = self.pages.widget(i)
            if getattr(page, "_key", None) == key:
                self.pages.setCurrentIndex(i)
                self.page = key
                self.rail.select(key)
                return

    def set_backdrop(self, path=None, blur=None, save=True):
        """Swap the wallpaper and/or its blur without rebuilding the window."""
        if path is not None:
            self.settings.set("bg_image", path, save=save)
        if blur is not None:
            self.settings.set("bg_blur", int(blur), save=save)
        self.backdrop.configure(path=self.settings.get("bg_image"),
                                blur=self.settings.get("bg_blur"),
                                veil=110, pal=self.pal)
        self.backdrop.update()
        for card in self._cards:
            card.update()

    def register_card(self, card):
        self._cards.append(card)
        return card

    def set_glass(self, glass):
        """Live slider update: every registered card follows."""
        alpha = base.card_alpha(glass)
        for card in self._cards:
            card.alpha = alpha
            card.update()
