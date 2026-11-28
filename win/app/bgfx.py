# -*- coding: utf-8 -*-
"""Wallpaper rendering: cover-crop, blur, opacity and rounded glass cards.

Pillow is optional: everything degrades to flat colours when it is missing.
"""

from __future__ import annotations

import os

from . import theme as theme_mod

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageTk
    PIL_OK = True
except Exception:  # pragma: no cover - only when Pillow is missing
    Image = ImageDraw = ImageFilter = ImageTk = None
    PIL_OK = False


def _rgb(color):
    return theme_mod.hex_to_rgb(color)


def cover(img, width, height):
    width = max(1, int(width))
    height = max(1, int(height))
    iw, ih = img.size
    scale = max(width / float(iw), height / float(ih))
    nw = max(1, int(round(iw * scale)))
    nh = max(1, int(round(ih * scale)))
    img = img.resize((nw, nh), Image.LANCZOS)
    left = max(0, (nw - width) // 2)
    top = max(0, (nh - height) // 2)
    return img.crop((left, top, left + width, top + height))


def crop_clamped(img, box, pad_color):
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    width = max(1, x1 - x0)
    height = max(1, y1 - y0)
    iw, ih = img.size
    sx0, sy0 = max(0, x0), max(0, y0)
    sx1, sy1 = min(iw, x1), min(ih, y1)
    if sx1 <= sx0 or sy1 <= sy0:
        return Image.new("RGB", (width, height), pad_color)
    piece = img.crop((sx0, sy0, sx1, sy1))
    if (sx0 - x0, sy0 - y0, sx1 - x0, sy1 - y0) == (0, 0, width, height):
        return piece
    canvas = Image.new("RGB", (width, height), pad_color)
    canvas.paste(piece, (sx0 - x0, sy0 - y0))
    return canvas


def shrink(img, size, scale):
    """Downscale a supersampled image by exact area averaging.

    LANCZOS leaves a light halo on the edges of 1px lines, which reads as
    "blurry" on a UI; averaging keeps corners smooth without the halo.
    """
    if scale > 1 and img.size == (size[0] * scale, size[1] * scale):
        try:
            return img.reduce(scale)
        except Exception:
            pass
    return img.resize(size, Image.BOX) if scale != 1 else img


def rounded_rgba(width, height, radius, fill, outline=None, width_px=1, scale=2):
    width = max(2, int(width))
    height = max(2, int(height))
    img = Image.new("RGBA", (width * scale, height * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(
        [0, 0, width * scale - 1, height * scale - 1],
        radius=max(0, int(radius * scale)),
        fill=fill,
        outline=outline,
        width=max(1, int(width_px * scale)) if outline else 0,
    )
    return shrink(img, (width, height), scale)


class Backdrop:
    """Owns the processed wallpaper and can composite cards on top of it."""

    def __init__(self, palette):
        self.palette = palette
        self.path = ""
        self.blur = 0
        self.alpha = 100
        self._src = None
        self._src_key = None
        self._full = None
        self._full_key = None
        self._thumb_key = None
        self._thumb = None
        # Bumped whenever the wallpaper changes so cached card bitmaps know
        # they are stale without every caller having to remember to say so.
        self.rev = 0
        self._card_layers = {}
        self._layer_order = []

    # -- configuration -------------------------------------------------
    def configure(self, path=None, blur=None, alpha=None):
        if path is not None:
            self.path = path or ""
        if blur is not None:
            try:
                self.blur = max(0, min(60, int(blur)))
            except (TypeError, ValueError):
                self.blur = 0
        if alpha is not None:
            try:
                self.alpha = max(0, min(100, int(alpha)))
            except (TypeError, ValueError):
                self.alpha = 100
        self.invalidate()

    def invalidate(self):
        self._full = None
        self._full_key = None
        self._thumb = None
        self._thumb_key = None
        self.rev += 1

    # -- sources -------------------------------------------------------
    def _source(self):
        if not self.path or not os.path.isfile(self.path):
            return None
        try:
            stamp = os.path.getmtime(self.path)
        except OSError:
            stamp = 0
        key = (self.path, stamp)
        if self._src is not None and self._src_key == key:
            return self._src
        try:
            img = Image.open(self.path)
            img.load()
            self._src = img.convert("RGB")
            self._src_key = key
        except Exception:
            self._src = None
            self._src_key = None
        return self._src

    def has_image(self):
        return self._source() is not None

    # -- wallpaper -----------------------------------------------------
    def _fallback(self, size):
        width, height = size
        pal = self.palette
        top = _rgb(pal["wall_top"])
        bottom = _rgb(pal["wall_bottom"])
        strip = Image.new("RGB", (1, height))
        pixels = strip.load()
        for y in range(height):
            k = y / float(max(1, height - 1))
            pixels[0, y] = tuple(int(top[i] + (bottom[i] - top[i]) * k) for i in range(3))
        img = strip.resize((width, height), Image.BILINEAR)
        glow = Image.new("L", (width, height), 0)
        draw = ImageDraw.Draw(glow)
        radius = int(max(width, height) * 0.6)
        cx, cy = int(width * 0.74), int(height * 0.12)
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=120)
        radius2 = int(max(width, height) * 0.45)
        draw.ellipse([-radius2 // 2, height - radius2, radius2, height + radius2 // 2], fill=80)
        glow = glow.filter(ImageFilter.GaussianBlur(max(10, int(max(width, height) * 0.09))))
        white = Image.new("RGB", (width, height), _rgb(pal["wall_glow"]))
        return Image.composite(white, img, glow.point(lambda v: int(v * 0.6)))

    def full(self, width, height):
        width = max(1, int(width))
        height = max(1, int(height))
        key = (width, height, self.path, int(self.blur), int(self.alpha))
        if self._full is not None and self._full_key == key:
            return self._full
        src = self._source() if PIL_OK else None
        if src is None:
            img = self._fallback((width, height))
        else:
            blur = float(self.blur)
            if blur <= 0.15:
                # no blur: stay at native resolution, upscaling a half-size
                # copy is what made an unblurred wallpaper look soft
                img = cover(src, width, height)
            else:
                scale = 0.5 if max(width, height) > 620 else 1.0
                sw = max(1, int(width * scale))
                sh = max(1, int(height * scale))
                img = cover(src, sw, sh)
                img = img.filter(ImageFilter.GaussianBlur(blur * scale))
                if scale != 1.0:
                    img = img.resize((width, height), Image.LANCZOS)
        if self.alpha < 100:
            solid = Image.new("RGB", (width, height), _rgb(self.palette["window"]))
            img = Image.blend(solid, img, max(0.0, min(1.0, self.alpha / 100.0)))
        self._full = img.convert("RGB")
        self._full_key = key
        return self._full

    def _card_layer(self, width, height, radius, fill, border, margin, shadow_alpha):
        """Shadow + face + hairline, built once per size and colour set.

        Every scroll notch and page switch repaints each card; the blurred
        shadow and the supersampled rounded face were most of that paint and
        neither depends on the wallpaper underneath, so they are cached.
        """
        key = (width, height, int(radius), fill, border, int(margin),
               int(shadow_alpha), self.palette.get("shadow"))
        layer = self._card_layers.get(key)
        if layer is not None:
            return layer
        layer = self._build_card_layer(width, height, radius, fill, border,
                                       margin, shadow_alpha)
        self._card_layers[key] = layer
        self._layer_order.append(key)
        while len(self._layer_order) > 10:
            self._card_layers.pop(self._layer_order.pop(0), None)
        return layer

    def _build_card_layer(self, width, height, radius, fill, border, margin, shadow_alpha):
        margin = max(0, min(margin, min(width, height) // 3))
        inner_w = max(4, width - margin * 2)
        inner_h = max(4, height - margin * 2)
        layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        if shadow_alpha:
            # A blur is already soft: supersampling it only cost time.
            mask = Image.new("L", (width, height), 0)
            ImageDraw.Draw(mask).rounded_rectangle(
                [margin, margin + 3, width - margin - 1, height - margin + 2],
                radius=max(1, int(radius)), fill=int(shadow_alpha * 2.2))
            mask = mask.filter(ImageFilter.GaussianBlur(4))
            shade = Image.new("RGBA", (width, height),
                              _rgb(self.palette["shadow"]) + (0,))
            shade.putalpha(mask)
            layer = Image.alpha_composite(layer, shade)
        scale = 2
        face = Image.new("RGBA", (inner_w * scale, inner_h * scale), (0, 0, 0, 0))
        ImageDraw.Draw(face).rounded_rectangle(
            [0, 0, inner_w * scale - 1, inner_h * scale - 1],
            radius=max(1, int(radius * scale)),
            fill=_rgb(fill) + (255,),
            outline=_rgb(border) + (255,) if border else None,
            width=max(1, scale) if border else 0,
        )
        layer.alpha_composite(shrink(face, (inner_w, inner_h), scale), (margin, margin))
        if border:
            # hairline drawn at 1:1 so it lands on whole pixels instead of
            # being smeared across two of them by the supersample
            ImageDraw.Draw(layer).rounded_rectangle(
                [margin, margin, width - margin - 1, height - margin - 1],
                radius=max(1, int(round(radius))),
                outline=_rgb(border) + (255,),
                width=1,
            )
        return layer

    def card_image(self, size, box, radius=16, fill="#FFFFFF", border="#E2E8F2",
                   margin=8, shadow_alpha=44):
        """Render one rounded card, composited on the wallpaper under its box."""
        base = self.full(*size)
        x, y, width, height = [int(round(v)) for v in box]
        width = max(8, width)
        height = max(8, height)
        back = crop_clamped(base, (x, y, x + width, y + height), _rgb(self.palette["window"]))
        layer = self._card_layer(width, height, radius, fill, border, margin, shadow_alpha)
        return Image.alpha_composite(back.convert("RGBA"), layer).convert("RGB")

    def thumbnail(self, width=150, height=84, radius=10):
        key = (width, height, self.path, self.blur, self.alpha)
        if self._thumb is not None and self._thumb_key == key:
            return self._thumb
        src = self._source()
        if src is None:
            img = self.full(width, height).copy()
        else:
            img = cover(src, width, height)
            if self.blur > 0:
                img = img.filter(ImageFilter.GaussianBlur(max(0.5, self.blur * 0.2)))
        mask = Image.new("L", (width, height), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, width - 1, height - 1],
                                               radius=max(0, int(radius)), fill=255)
        thumb = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        thumb.paste(img.convert("RGBA").resize((width, height), Image.LANCZOS), (0, 0), mask)
        self._thumb = thumb
        self._thumb_key = key
        return self._thumb

    def tk_wallpaper(self, width, height):
        return ImageTk.PhotoImage(self.full(width, height))

    def tk_thumbnail(self, width=150, height=84):
        return ImageTk.PhotoImage(self.thumbnail(width, height))
