# -*- coding: utf-8 -*-
"""Shared painting helpers for the Qt shell (colors, fonts, glass shapes)."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainterPath

from app import theme


def qc(value, alpha=255):
    """Palette hex (or QColor) -> QColor with an alpha override."""
    color = QColor(value)
    color.setAlpha(max(0, min(255, int(alpha))))
    return color


def font(size=10.5, bold=False, family=None):
    f = QFont(family or theme.FONT_FAMILY)
    f.setPointSizeF(float(size))
    f.setBold(bool(bold))
    f.setHintingPreference(QFont.PreferFullHinting)
    return f


def mono(size=9.5, bold=False):
    f = QFont(theme.MONO_FAMILY)
    f.setPointSizeF(float(size))
    f.setBold(bool(bold))
    return f


def rounded(rect, radius):
    path = QPainterPath()
    path.addRoundedRect(QRectF(rect), float(radius), float(radius))
    return path


def card_alpha(glass, low=0.30, high=0.94):
    """Slider 0..100 -> card opacity (0 = solid, 100 = most see-through)."""
    try:
        glass = max(0.0, min(100.0, float(glass)))
    except (TypeError, ValueError):
        glass = 0.0
    return high + (low - high) * (glass / 100.0)


def mix(a, b, ratio):
    """Blend two QColors."""
    ratio = max(0.0, min(1.0, float(ratio)))
    return QColor(
        int(a.red() + (b.red() - a.red()) * ratio),
        int(a.green() + (b.green() - a.green()) * ratio),
        int(a.blue() + (b.blue() - a.blue()) * ratio),
        int(a.alpha() + (b.alpha() - a.alpha()) * ratio),
    )


def gradient(color_a, color_b, rect, vertical=True):
    grad = QLinearGradient(QPointF(rect.topLeft()), QPointF(rect.bottomLeft() if vertical else rect.topRight()))
    grad.setColorAt(0.0, color_a)
    grad.setColorAt(1.0, color_b)
    return grad


def draw_shadow(painter, rect, radius, color, spread=18, strength=0.30, layers=9):
    """Soft drop shadow drawn as stacked translucent rounded rects."""
    painter.save()
    painter.setPen(Qt.NoPen)
    for i in range(layers, 0, -1):
        t = i / float(layers)
        alpha = int(255 * strength * (1.0 - t) ** 1.8 / layers * 9)
        if alpha <= 0:
            continue
        painter.setBrush(qc(color, alpha))
        grow = spread * t
        painter.drawRoundedRect(QRectF(rect).adjusted(-grow, -grow * 0.55, grow, grow * 0.85),
                                radius + grow * 0.5, radius + grow * 0.5)
    painter.restore()
