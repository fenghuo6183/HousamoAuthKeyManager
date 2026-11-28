# -*- coding: utf-8 -*-
"""Color palette and font helpers for the Windows client."""

from __future__ import annotations

APP_NAME = "东放 AuthKey 管家"
APP_SUBTITLE = "Housamo AuthKey"
APP_VERSION = "1.0.29"
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
    "check_border": "#B8C6DC",
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
    "btn_hover": "#DCE7FF",      # ghost button hover / press
    "btn_press": "#C9D9FF",
    "soft_hover": "#D8E4FF",     # soft (tinted) button hover / press
    "soft_press": "#C9D9FF",
    "danger_hover": "#F8DBD8",
    "danger_press": "#F1C8C4",
    "head_hover": "#EAEFF9",     # tree heading hover
    "scroll_hover": "#AEBBD2",
    "glyph_off": "#E8EDF6",      # disabled button fill
    "glyph_off_line": "#ACB7C9",
}

LIGHT = PALETTE

# Dark counterpart of PALETTE. Same keys, so every widget can be rebuilt from
# either palette without special cases.
DARK = {
    "window": "#0F1420",
    "wall_top": "#131B2C",
    "wall_bottom": "#0A0E17",
    "wall_glow": "#22304F",
    "rail": "#151B28",
    "rail_hover": "#1E2637",
    "card": "#1A2130",
    "card_soft": "#222B3C",
    "card_sunken": "#1F2634",
    "border": "#2E3850",
    "check_border": "#4A5C7E",
    "border_soft": "#252D3E",
    "text": "#E9F0FB",
    "text_muted": "#9AA7BE",
    "text_faint": "#77849A",
    "accent": "#4C86FF",
    "accent_hover": "#6A9BFF",
    "accent_press": "#3B70D8",
    "accent_soft": "#243453",
    "on_accent": "#FFFFFF",
    "ok": "#3FD08A",
    "ok_soft": "#173627",
    "warn": "#E5AC4E",
    "warn_soft": "#3A2C12",
    "err": "#FF7A70",
    "err_soft": "#3B1F1C",
    "log_bg": "#0B0F18",
    "log_fg": "#C6D2E6",
    "log_dim": "#7C8AA0",
    "log_err": "#FF9A93",
    "log_ok": "#7FE0A8",
    "log_hint": "#FFD08A",
    "shadow": "#000000",
    "btn_hover": "#2A3A55",
    "btn_press": "#31405C",
    "soft_hover": "#2C3D5E",
    "soft_press": "#34496E",
    "danger_hover": "#4A2621",
    "danger_press": "#552D27",
    "head_hover": "#28334A",
    "scroll_hover": "#3A4763",
    "glyph_off": "#2A3345",
    "glyph_off_line": "#4A5673",
}


def palette(name=None):
    """Palette by name ("dark"/"light"); unknown names fall back to light."""
    return DARK if name == "dark" else LIGHT

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
