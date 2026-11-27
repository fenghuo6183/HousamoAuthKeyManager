# -*- coding: utf-8 -*-
"""Render an AuthKey as a QR code (for the Windows "生成二维码" dialog).

Kept dependency free: the encoder is the vendored MIT `qrcodegen` module, and
the bitmap is built with Pillow (already used for the wallpaper).
"""

from __future__ import annotations

from . import bgfx

DARK = (16, 20, 24)
LIGHT = (255, 255, 255)
BORDER = 4          # quiet zone in modules, the QR spec asks for 4
MIN_MODULE = 2      # never render a 1px module: it stops scanning on zoom


def modules(key_text):
    """Boolean grid of the encoded key (True = dark module)."""
    from .qrcodegen import QrCode
    try:
        code = QrCode.encode_text(key_text, QrCode.Ecc.MEDIUM)
    except ValueError:
        # Very long keys stay scannable at the lowest error-correction level.
        code = QrCode.encode_text(key_text, QrCode.Ecc.LOW)
    size = code.get_size()
    return [[code.get_module(x, y) for x in range(size)] for y in range(size)]


def render(key_text, pixels=520):
    """Return a Pillow image holding the QR, or None when Pillow is missing."""
    if not bgfx.PIL_OK:
        return None
    from PIL import Image
    grid = modules(key_text)
    count = len(grid) + BORDER * 2
    scale = max(MIN_MODULE, int(pixels) // max(1, count))
    small = Image.new("L", (len(grid), len(grid)), 255)
    for y, row in enumerate(grid):
        for x, on in enumerate(row):
            if on:
                small.putpixel((x, y), 0)
    body = small.resize((len(grid) * scale, len(grid) * scale), Image.NEAREST)
    plate = Image.new("L", (count * scale, count * scale), 255)
    plate.paste(body, (BORDER * scale, BORDER * scale))
    return plate


def save_png(key_text, path, pixels=520):
    """Write the QR as PNG; returns the path, or None when Pillow is missing."""
    image = render(key_text, pixels)
    if image is None:
        return None
    image.save(path, "PNG")
    return path
