# -*- coding: utf-8 -*-
"""Color palette and font helpers for the Windows client."""

from __future__ import annotations

APP_NAME = "东放 AuthKey 管家"
APP_SUBTITLE = "Housamo AuthKey Manager"
APP_VERSION = "1.0-win"
REPO_URL = "https://github.com/fenghuo6183/HousamoAuthKeyManager"

FONT_FAMILY = "Microsoft YaHei UI"
MONO_FAMILY = "Consolas"

# Single polished light theme: cards stay opaque and readable on any wallpaper,
# the wallpaper itself shows through the gaps, the rail edge and the page margins.
PALETTE = {
    "window": "#EDF1F9",      # base colour behind cards / blend target for the wallpaper
    "wall_top": "#E8EEFB",    # fallback gradient (no image picked yet)
    "wall_bottom": "#D8E2F5",
    "wall_glow": "#FFFFFF",
    "rail": "#FFFFFF",
    "rail_hover": "#F1F5FD",
    "card": "#FFFFFF",
    "card_soft": "#F5F7FC",
    "card_sunken": "#FAFBFE",
    "border": "#E2E8F2",
    "border_soft": "#EDF1F7",
    "text": "#13203A",
    "text_muted": "#76839B",
    "text_faint": "#9AA6BA",
    "accent": "#2F6BFF",
    "accent_hover": "#2559DB",
    "accent_press": "#1C48BC",
    "accent_soft": "#E9F0FF",
    "on_accent": "#FFFFFF",
    "ok": "#0E9F5B",
    "ok_soft": "#E4F6EC",
    "warn": "#B26A00",
    "warn_soft": "#FDF1DC",
    "err": "#D1453B",
    "err_soft": "#FCEAE8",
    "log_bg": "#121826",
    "log_fg": "#C6D2E6",
    "log_dim": "#7C8AA0",
    "log_err": "#FF9A93",
    "log_ok": "#7FE0A8",
    "log_hint": "#FFD08A",
    "shadow": "#0F172A",
}

LIGHT = PALETTE

# Pixel scale of the running window (1.0 at 96 dpi, 1.5 at 150%, ...).
# The layout is authored in 96-dpi pixels; every measurement goes through
# px() so hi-dpi screens get a proportionally bigger window instead of a
# bitmap-stretched (blurry, ragged) one.
UI_SCALE = 1.0


def set_ui_scale(scale):
    global UI_SCALE
    try:
        scale = float(scale)
    except (TypeError, ValueError):
        scale = 1.0
    UI_SCALE = max(1.0, min(4.0, scale))
    return UI_SCALE


def px(value):
    return int(round(float(value) * UI_SCALE))


def font(size=10, weight="normal", family=None):
    return (family or FONT_FAMILY, size, weight)


def mono(size=9, weight="normal"):
    return (MONO_FAMILY, size, weight)


def hex_to_rgb(value):
    value = str(value).lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(v))) for v in rgb[:3])


def blend(color_a, color_b, ratio):
    """Blend two hex colours; ratio=0 -> color_a, ratio=1 -> color_b."""
    ratio = max(0.0, min(1.0, ratio))
    a = hex_to_rgb(color_a)
    b = hex_to_rgb(color_b)
    return rgb_to_hex(tuple(a[i] + (b[i] - a[i]) * ratio for i in range(3)))
