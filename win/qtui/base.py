# -*- coding: utf-8 -*-
"""Shared painting helpers for the Qt shell (colors, fonts, glass shapes)."""

from __future__ import annotations

import os

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath

from app import theme

# Glass tuning (env override is only for side-by-side screenshots).
GLASS_TINT = float(os.environ.get("QT_GLASS_TINT", "0.45"))
GLASS_RELIEF = float(os.environ.get("QT_GLASS_RELIEF", "0.45"))
GLASS_FLOOR = float(os.environ.get("QT_GLASS_FLOOR", "0.80"))


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


def card_alpha(glass, low=0.52, high=0.98):
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


def wallpaper_of(widget):
    """The finished wallpaper pixmap the window paints behind everything."""
    backdrop = getattr(widget.window(), "backdrop", None)
    if backdrop is None:
        return None
    try:
        return backdrop.pixmap()
    except AttributeError:
        return None


def wallpaper_under(widget):
    """Average wallpaper colour behind a widget (cached per pixmap + geometry)."""
    pixmap = wallpaper_of(widget)
    if pixmap is None or pixmap.isNull():
        return None
    origin = widget.mapTo(widget.window(), QPoint(0, 0))
    key = (pixmap.cacheKey(), origin.x(), origin.y(), widget.width(), widget.height())
    if getattr(widget, "_glass_key", None) == key:
        return getattr(widget, "_glass_avg", None)
    piece = pixmap.copy(QRect(origin, widget.size()).intersected(pixmap.rect()))
    image = piece.scaled(1, 1, Qt.IgnoreAspectRatio, Qt.SmoothTransformation).toImage()
    widget._glass_key = key
    widget._glass_avg = None if image.isNull() else QColor(image.pixel(0, 0))
    return widget._glass_avg


def glass_face(widget, pal, alpha, base_key="card", soft_key="card_soft", soft_mix=0.55):
    """Work out the two fill colours (and effective alpha) for a glass panel.

    The tint keeps the wallpaper's hue from turning grey, and the luminance
    floor keeps a light panel light when the wallpaper under it is dark.
    """
    alpha = float(alpha)
    top = QColor(pal[base_key])
    bottom = mix(top, QColor(pal[soft_key]), soft_mix) if soft_key else QColor(top)
    average = wallpaper_under(widget)
    if average is None:
        return top, bottom, alpha
    lum = 0.299 * average.redF() + 0.587 * average.greenF() + 0.114 * average.blueF()
    if lum < GLASS_FLOOR:
        alpha = max(alpha, min(0.97, (GLASS_FLOOR - lum) / (1.0 - lum)))
    tint = max(0.0, min(1.0, GLASS_TINT * (1.0 - alpha)))
    if tint > 0.01:
        pale = average
        if average.hsvHueF() >= 0:
            pale = QColor.fromHsvF(average.hsvHueF(),
                                   min(0.36, average.hsvSaturationF() * 1.4), 0.95)
        top = mix(top, pale, tint)
        bottom = mix(bottom, pale, tint)
    return top, bottom, alpha


def paint_glass(painter, widget, pal, rect, radius, alpha,
                base_key="card", soft_key="card_soft", border_strength=0.0):
    """Fill a translucent panel that keeps the wallpaper's colour and hue."""
    top, bottom, alpha = glass_face(widget, pal, alpha, base_key, soft_key)
    if radius:
        path = rounded(rect, radius)
    else:
        path = QPainterPath()
        path.addRect(QRectF(rect))
    painter.save()
    painter.setPen(Qt.NoPen)
    painter.setBrush(gradient(qc(top, 255 * alpha), qc(bottom, 255 * alpha), rect))
    painter.drawPath(path)
    if alpha < 0.985:
        wallpaper = wallpaper_of(widget)
        if wallpaper is not None and not wallpaper.isNull():
            origin = widget.mapTo(widget.window(), QPoint(0, 0))
            painter.save()
            painter.setClipPath(path)
            painter.setCompositionMode(QPainter.CompositionMode_Overlay)
            painter.setOpacity(max(0.0, min(0.8, (1.0 - alpha) * GLASS_RELIEF)))
            painter.drawPixmap(QRect(0, 0, widget.width(), widget.height()), wallpaper,
                               QRect(origin, widget.size()))
            painter.restore()
    if border_strength > 0.0:
        border_alpha = int(255 * border_strength * min(1.0, alpha + 0.25))
        painter.setPen(qc(pal["border"], border_alpha))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)
    painter.restore()
    return alpha


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
