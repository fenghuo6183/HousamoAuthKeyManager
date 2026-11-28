# -*- coding: utf-8 -*-
"""Custom painted widgets for the Qt shell: glass cards, pills, switches."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt, Signal, Property
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from . import base


class GlassCard(QWidget):
    """Rounded translucent panel. Children paint on top of the glass."""

    def __init__(self, pal, parent=None, radius=22, alpha=0.86, border=0.5, shadow=True):
        super().__init__(parent)
        self.pal = pal
        self.radius = radius
        self.alpha = alpha
        self.border_strength = border
        self.shadow = shadow
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setAutoFillBackground(False)

    def set_palette(self, pal):
        self.pal = pal
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
        if self.shadow:
            base.draw_shadow(p, rect, self.radius, self.pal["shadow"],
                             spread=16, strength=0.13 + 0.10 * (1.0 - self.alpha))
        path = base.rounded(rect, self.radius)
        top = base.qc(self.pal["card"], 255 * self.alpha)
        bottom = base.qc(base.mix(QColor(self.pal["card"]), QColor(self.pal["card_soft"]), 0.55), 255 * self.alpha)
        p.setPen(Qt.NoPen)
        p.setBrush(base.gradient(top, bottom, rect))
        p.drawPath(path)
        border_alpha = int(255 * self.border_strength * min(1.0, self.alpha + 0.25))
        p.setPen(QPen(base.qc(self.pal["border"], border_alpha), 1))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)


class PillButton(QAbstractButton):
    """Rounded button in the four palette kinds used across the app."""

    KINDS = {
        "primary": ("accent", "on_accent", None, "accent_hover", "accent_press"),
        "ghost": ("card_soft", "text", "border", "btn_hover", "btn_press"),
        "soft": ("accent_soft", "accent", None, "soft_hover", "soft_press"),
        "danger": ("err_soft", "err", None, "danger_hover", "danger_press"),
    }

    def __init__(self, pal, text, kind="primary", parent=None, height=40, min_width=0, glyph=""):
        super().__init__(parent)
        self.pal = pal
        self.kind = kind
        self._height = height
        self._min_width = min_width
        self._glyph = glyph
        self.setText(text)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.TabFocus)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setFont(base.font(10.5, bold=(kind == "primary")))

    def set_palette(self, pal):
        self.pal = pal
        self.update()

    def sizeHint(self):
        fm = QFontMetrics(self.font())
        text = self.text()
        width = fm.horizontalAdvance(text) + 44 + (18 if self._glyph else 0)
        if self.kind == "primary":
            width += 10
        return QSize(max(width, self._min_width, 96), self._height)

    def _colors(self):
        fill, ink, border, hover, press = self.KINDS.get(self.kind, self.KINDS["primary"])
        if not self.isEnabled():
            return (base.qc(self.pal["glyph_off"]), base.qc(self.pal["glyph_off_line"]),
                    base.qc(self.pal["border_soft"]), None)
        if self.isDown():
            fill = press
        elif self.underMouse():
            fill = hover
        return (base.qc(self.pal[fill]), base.qc(self.pal[ink]),
                base.qc(self.pal[border]) if border else QColor(0, 0, 0, 0), None)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = rect.height() / 2.0
        fill, ink, border, _ = self._colors()
        path = base.rounded(rect, radius)
        if self.kind == "primary" and self.isEnabled():
            top = base.mix(fill, QColor("#FFFFFF"), 0.16)
            p.setPen(Qt.NoPen)
            p.setBrush(base.gradient(top, fill, rect))
        else:
            p.setPen(Qt.NoPen)
            p.setBrush(fill)
        p.drawPath(path)
        if border.alpha():
            p.setPen(QPen(border, 1))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), radius - 0.5, radius - 0.5)
        if self.hasFocus():
            p.setPen(QPen(base.qc(self.pal["accent"], 110), 1.2))
            p.setBrush(Qt.NoBrush)
            p.drawPath(base.rounded(rect.adjusted(1.5, 1.5, -1.5, -1.5), radius))
        p.setPen(QPen(ink))
        p.setFont(self.font())
        text = (self._glyph + "  " + self.text()) if self._glyph else self.text()
        p.drawText(self.rect(), Qt.AlignCenter, text)


class NavButton(QAbstractButton):
    """Left rail entry: label, rounded highlight when active."""

    def __init__(self, pal, text, parent=None, height=46):
        super().__init__(parent)
        self.pal = pal
        self._height = height
        self.setText(text)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.TabFocus)
        self.setFont(base.font(10.5))
        self.setCheckable(True)

    def set_palette(self, pal):
        self.pal = pal
        self.update()

    def sizeHint(self):
        return QSize(226, self._height)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(1, 2, -1, -2)
        path = base.rounded(rect, 12)
        if self.isChecked():
            p.setPen(Qt.NoPen)
            p.setBrush(base.gradient(base.qc(self.pal["accent"], 235),
                                     base.qc(self.pal["accent_press"], 235), rect))
            p.drawPath(path)
        elif self.underMouse():
            p.setPen(Qt.NoPen)
            p.setBrush(base.qc(self.pal["accent_soft"], 140))
            p.drawPath(path)
        ink = base.qc(self.pal["on_accent"]) if self.isChecked() else base.qc(self.pal["text"])
        if not self.isChecked() and not self.underMouse():
            ink = base.qc(self.pal["text"])
        p.setPen(QPen(ink))
        p.setFont(base.font(10.5, bold=self.isChecked()))
        p.drawText(rect.adjusted(20, 0, -14, 0), Qt.AlignVCenter | Qt.AlignLeft, self.text())


class SubNavButton(QAbstractButton):
    """Sub-section entry inside a page (MAA-style settings list)."""

    def __init__(self, pal, text, parent=None, height=38):
        super().__init__(parent)
        self.pal = pal
        self._height = height
        self.setText(text)
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(True)
        self.setFont(base.font(10.5))

    def set_palette(self, pal):
        self.pal = pal
        self.update()

    def sizeHint(self):
        return QSize(166, self._height)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        if self.isChecked():
            p.setPen(Qt.NoPen)
            p.setBrush(base.qc(self.pal["accent_soft"], 210))
            p.drawRoundedRect(rect, 10, 10)
            bar = QRectF(rect.left() + 9, rect.center().y() - 8, 3, 16)
            p.setBrush(base.qc(self.pal["accent"]))
            p.drawRoundedRect(bar, 1.5, 1.5)
        elif self.underMouse():
            p.setPen(Qt.NoPen)
            p.setBrush(base.qc(self.pal["soft_hover"], 150))
            p.drawRoundedRect(rect, 10, 10)
        if self.isChecked():
            ink = base.qc(self.pal["accent"])
        else:
            ink = base.qc(self.pal["text_muted"] if not self.underMouse() else self.pal["text"])
        p.setPen(QPen(ink))
        p.setFont(base.font(10.5, bold=self.isChecked()))
        p.drawText(rect.adjusted(24, 0, -12, 0), Qt.AlignVCenter | Qt.AlignLeft, self.text())


class Toggle(QAbstractButton):
    """iOS-style switch used for the on/off settings rows."""

    def __init__(self, pal, checked=False, parent=None):
        super().__init__(parent)
        self.pal = pal
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.TabFocus)
        self.setFixedSize(46, 26)

    def set_palette(self, pal):
        self.pal = pal
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        on = self.isChecked()
        track = base.qc(self.pal["accent"]) if on else base.qc(self.pal["check_border"], 170)
        p.setPen(Qt.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
        knob = 20.0
        x = rect.right() - knob - 2 if on else rect.left() + 2
        p.setBrush(base.qc("#FFFFFF"))
        p.drawEllipse(QRectF(x, rect.center().y() - knob / 2, knob, knob))


class Segmented(QWidget):
    """Two/three-way segmented control (MAA style connection picker)."""

    changed = Signal(int)

    def __init__(self, pal, options, index=0, parent=None, width=None, height=36):
        super().__init__(parent)
        self.pal = pal
        self.options = list(options)
        self.index = int(index) if 0 <= int(index) < len(self.options) else 0
        self._height = height
        self.setFixedHeight(height)
        if width:
            self.setFixedWidth(width)
        else:
            self.setMinimumWidth(60 * len(self.options))
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.TabFocus)

    def set_palette(self, pal):
        self.pal = pal
        self.update()

    def set_index(self, index):
        index = max(0, min(len(self.options) - 1, int(index)))
        if index != self.index:
            self.index = index
            self.update()
            self.changed.emit(index)

    def mousePressEvent(self, event):
        if self.options:
            seg = self.width() / float(len(self.options))
            self.set_index(int(event.position().x() // seg))
        super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setPen(Qt.NoPen)
        p.setBrush(base.qc(self.pal["card_soft"], 220))
        p.drawRoundedRect(rect, 10, 10)
        if not self.options:
            return
        seg = rect.width() / len(self.options)
        active = QRectF(rect.left() + seg * self.index + 3, rect.top() + 3, seg - 6, rect.height() - 6)
        p.setBrush(base.qc(self.pal["accent"]))
        p.drawRoundedRect(active, 8, 8)
        p.setFont(base.font(10))
        for i, text in enumerate(self.options):
            cell = QRectF(rect.left() + seg * i, rect.top(), seg, rect.height())
            ink = base.qc(self.pal["on_accent"]) if i == self.index else base.qc(self.pal["text_muted"])
            p.setPen(QPen(ink))
            p.drawText(cell, Qt.AlignCenter, text)


class Field(QWidget):
    """Label + control row used inside cards."""

    def __init__(self, pal, label, control, hint="", parent=None, label_width=150, expand=False):
        super().__init__(parent)
        self.pal = pal
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(14)
        box = QVBoxLayout()
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(3)
        self.label = QLabel(label)
        self.label.setFont(base.font(10.5))
        self.label.setStyleSheet("background: transparent; color: %s;" % pal["text"])
        box.addWidget(self.label)
        if hint:
            small = QLabel(hint)
            small.setFont(base.font(9))
            small.setWordWrap(True)
            small.setFixedWidth(label_width)
            small.setStyleSheet("background: transparent; color: %s;" % pal["text_faint"])
            box.addWidget(small)
        holder = QWidget()
        holder.setLayout(box)
        holder.setFixedWidth(label_width)
        row.addWidget(holder)
        if expand:
            row.addWidget(control, 1)
        else:
            row.addStretch(1)
            row.addWidget(control)
