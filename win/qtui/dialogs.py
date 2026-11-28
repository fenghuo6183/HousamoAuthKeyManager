# -*- coding: utf-8 -*-
"""App-styled dialogs.

Windows' native message boxes look nothing like the glass UI, so every modal
in the Qt client is drawn here: rounded card, the same fonts and colours, a
draggable header and a single accent button.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QWidget,
)

from . import base
from .widgets import PillButton


class GlassDialog(QDialog):
    """Frameless rounded dialog that matches the rest of the client."""

    def __init__(self, parent, pal, title, width=420, subtitle=""):
        super().__init__(parent)
        self.pal = pal
        self.setWindowTitle(title)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self._scrim = None
        self.finished.connect(self._drop_scrim)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)

        self.panel = QWidget(self)
        self.panel.setObjectName("glassPanel")
        self.panel.setStyleSheet(
            "#glassPanel { background: %s; border: 1px solid %s; border-radius: 18px; }"
            % (pal["card"], pal["border_soft"])
        )
        shadow = QGraphicsDropShadowEffect(self.panel)
        shadow.setBlurRadius(34)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(12, 22, 40, 70))
        self.panel.setGraphicsEffect(shadow)
        outer.addWidget(self.panel)

        box = QVBoxLayout(self.panel)
        box.setContentsMargins(24, 20, 20, 20)
        box.setSpacing(14)

        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(8)
        title_label = QLabel(title)
        title_label.setFont(base.font(13, bold=True))
        title_label.setStyleSheet("background: transparent; color: %s;" % pal["text"])
        head.addWidget(title_label)
        head.addStretch(1)
        close = QPushButton("✕")
        close.setCursor(Qt.PointingHandCursor)
        close.setFixedSize(28, 28)
        close.setStyleSheet(
            "QPushButton { background: transparent; border: none; border-radius: 14px;"
            " color: %s; font-size: 13px; }"
            "QPushButton:hover { background: %s; color: %s; }"
            % (pal["text_muted"], pal["btn_hover"], pal["text"])
        )
        close.clicked.connect(self.reject)
        head.addWidget(close)
        box.addLayout(head)

        if subtitle:
            sub = QLabel(subtitle)
            sub.setWordWrap(True)
            sub.setFont(base.font(9.5))
            sub.setStyleSheet("background: transparent; color: %s;" % pal["text_muted"])
            box.addWidget(sub)

        self.body = QVBoxLayout()
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(12)
        box.addLayout(self.body)

        self.setMinimumWidth(width)
        self.setMaximumWidth(width + 36)

    # -- draggable header ------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.position().y() < 78:
            handle = self.windowHandle()
            if handle is not None:
                handle.startSystemMove()
                return
        super().mousePressEvent(event)

    # -- helpers ---------------------------------------------------------
    def label(self, text, faint=False):
        widget = QLabel(text)
        widget.setWordWrap(True)
        widget.setFont(base.font(9.5))
        widget.setStyleSheet(
            "background: transparent; color: %s;" % self.pal["text_faint" if faint else "text_muted"]
        )
        return widget

    def _drop_scrim(self, *_):
        if self._scrim is not None:
            self._scrim.hide()
            self._scrim.deleteLater()
            self._scrim = None

    def showEvent(self, event):
        super().showEvent(event)
        self._drop_scrim()
        host = self.parentWidget()
        host = host.window() if host is not None else None
        if host is not None:
            scrim = QWidget(host)
            scrim.setObjectName("dialogScrim")
            scrim.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            scrim.setStyleSheet("#dialogScrim { background: rgba(10, 18, 32, 72); }")
            scrim.setGeometry(host.rect())
            scrim.show()
            scrim.raise_()
            self._scrim = scrim

    def buttons(self, cancel_text="取消", ok_text="确定", danger=False, on_ok=None):
        row = QWidget()
        box = QHBoxLayout(row)
        box.setContentsMargins(0, 4, 0, 0)
        box.setSpacing(10)
        box.addStretch(1)
        cancel = PillButton(self.pal, cancel_text, "ghost", height=34, min_width=88)
        cancel.clicked.connect(self.reject)
        box.addWidget(cancel)
        ok = PillButton(self.pal, ok_text, "danger" if danger else "primary",
                        height=34, min_width=96)
        if on_ok is not None:
            ok.clicked.connect(on_ok)
        ok.clicked.connect(self.accept)
        box.addWidget(ok)
        return row, ok


def _field(pal, text="", password=False):
    edit = QLineEdit(text)
    edit.setFont(base.font(10.5))
    if password:
        edit.setEchoMode(QLineEdit.Password)
    edit.setMinimumHeight(38)
    edit.setStyleSheet(
        "QLineEdit { background: %s; border: 1px solid %s; border-radius: 10px;"
        " padding: 6px 10px; color: %s; selection-background-color: %s; }"
        "QLineEdit:focus { border-color: %s; }"
        % (pal["card_soft"], pal["border_soft"], pal["text"], pal["accent"], pal["accent"])
    )
    return edit


def ask_text(parent, pal, title, label, default="", password=False,
             ok_text="确定", cancel_text="取消"):
    """Return the entered text, or "" when cancelled."""
    dialog = GlassDialog(parent, pal, title, width=430)
    dialog.body.addWidget(dialog.label(label))
    edit = _field(pal, default, password=password)
    dialog.body.addWidget(edit)
    result = {"text": ""}

    def submit():
        result["text"] = edit.text().strip()
        dialog.accept()

    row, _ok = dialog.buttons(cancel_text, ok_text, on_ok=submit)
    dialog.body.addWidget(row)
    edit.returnPressed.connect(submit)
    edit.selectAll()
    edit.setFocus()
    dialog.exec()
    return result["text"]


def confirm(parent, pal, title, text, ok_text="确定", danger=False):
    dialog = GlassDialog(parent, pal, title, width=430)
    dialog.body.addWidget(dialog.label(text))
    row, _ = dialog.buttons("取消", ok_text, danger=danger)
    dialog.body.addWidget(row)
    return dialog.exec() == QDialog.Accepted


def show_qr(parent, pal, name, pixmap, hint=""):
    dialog = GlassDialog(parent, pal, name or "账号二维码", width=340)
    pic = QLabel()
    pic.setPixmap(pixmap)
    pic.setAlignment(Qt.AlignCenter)
    dialog.body.addWidget(pic)
    if hint:
        text = dialog.label(hint, faint=True)
        text.setAlignment(Qt.AlignCenter)
        dialog.body.addWidget(text)
    close = PillButton(pal, "关闭", "ghost", height=32, min_width=88)
    close.clicked.connect(dialog.accept)
    row = QWidget()
    box = QHBoxLayout(row)
    box.setContentsMargins(0, 0, 0, 0)
    box.addStretch(1)
    box.addWidget(close)
    dialog.body.addWidget(row)
    dialog.exec()


def show_lan(parent, pal, url, code, hint=""):
    dialog = GlassDialog(parent, pal, "局域网分享", width=460)
    if hint:
        dialog.body.addWidget(dialog.label(hint))
    link = QLabel(url)
    link.setFont(base.mono(12))
    link.setTextInteractionFlags(Qt.TextSelectableByMouse)
    link.setStyleSheet(
        "background: %s; border-radius: 10px; padding: 10px 12px; color: %s;"
        % (pal["card_soft"], pal["accent"])
    )
    dialog.body.addWidget(link)
    dialog.body.addWidget(dialog.label("配对码 %s  ·  关掉这个窗口就停止分享" % code, faint=True))
    close = PillButton(pal, "停止分享", "ghost", height=32, min_width=96)
    close.clicked.connect(dialog.accept)
    row = QWidget()
    box = QHBoxLayout(row)
    box.setContentsMargins(0, 0, 0, 0)
    box.addStretch(1)
    box.addWidget(close)
    dialog.body.addWidget(row)
    dialog.exec()
