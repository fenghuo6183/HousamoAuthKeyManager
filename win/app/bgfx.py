# -*- coding: utf-8 -*-
"""Wallpaper rendering: cover-crop, blur, opacity and rounded glass cards.

Pillow is optional: everything degrades to flat colours when it is missing.
"""

from __future__ import annotations

import os

from . import theme as theme_mod

try:
    from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageTk
    PIL_OK = True
except Exception:  # pragma: no cover - only when Pillow is missing
    Image = ImageChops = ImageDraw = ImageFilter = ImageTk = None
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


def frost_extra(amount):
    """Blur radius used behind a see-through card, shared by tint and patch."""
    return 0.0 if amount <= 0 else 1.0 + 2.0 * amount


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


def feather_scrim(img, scrim):
    """Darken the left of a wallpaper crop, fading out at every edge.

    Where the darkening reaches zero the pixels are identical to the
    wallpaper underneath, so the header has no visible border and reads as
    part of the picture instead of as another panel.
    """
    width, height = img.size
    gw, gh = 48, 24
    values = []
    for gy in range(gh):
        fy = (gy + 0.5) / gh
        vy = min(1.0, fy / 0.38, (1.0 - fy) / 0.38)
        vy = vy * vy * (3.0 - 2.0 * vy)
        for gx in range(gw):
            fx = max(0.0, 1.0 - (gx + 0.5) / gw / 0.72)
            amount = scrim * fx * fx * vy
            values.append(255 - int(215 * amount))
    mult = Image.new("L", (gw, gh))
    mult.putdata(values)
    mult = mult.resize((width, height), Image.BILINEAR)
    return ImageChops.multiply(img, Image.merge("RGB", (mult, mult, mult)))


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
        self._tone = None
        self._tone_key = None
        # Bumped whenever the wallpaper changes so cached card bitmaps know
        # they are stale without every caller having to remember to say so.
        self.rev = 0
        self._card_layers = {}
        self._layer_order = []
        self._frost = {}
        self._frost_key = None

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

    def tone(self):
        """Average colour of the wallpaper as #rrggbb (None without an image).

        The UI copies its panels' colours a little towards this tone, which is
        what makes an opaque Tk frame read as frosted glass over the picture.
        """
        src = self._source()
        if src is None:
            return None
        key = ("tone", self.path)
        if self._tone is not None and self._tone_key == key:
            return self._tone
        try:
            tiny = src.resize((1, 1), Image.BOX)
            self._tone = theme_mod.rgb_to_hex(tiny.getpixel((0, 0)))
        except Exception:
            self._tone = None
        self._tone_key = key

    def frost(self, size, extra=0.0, flat=False):
        """A blurrier copy of the wallpaper, used behind see-through cards.

        Tile-by-tile colour sampling flattens a picture; the smoother the
        source, the less the seams between neighbouring widgets show.

        flat=True also collapses the horizontal detail: every widget row is
        one flat rectangle, so if the picture behind it keeps its side-to-side
        texture the row's single colour can never match it and the card turns
        into a stack of bands. Keeping only the vertical wash means a row's
        average colour *is* the picture at that row, on every column.
        """
        if extra <= 0.2:
            return self.full(*size)
        key = (tuple(size), round(float(extra), 1), bool(flat))
        if self._frost_key != (key, self.rev):
            self._frost = {}
            self._frost_key = (key, self.rev)
        img = self._frost.get(key)
        if img is None:
            img = self.full(*size).filter(ImageFilter.GaussianBlur(float(extra)))
            if flat:
                # 压成一列再铺回去：结果只有上下变化，同一行上从左到右完全
                # 一样。行底全是纯色块，只有这样才能和行色严丝合缝。
                width, height = img.size
                img = img.resize((1, height), Image.BOX).resize(
                    (width, height), Image.BILINEAR)
            self._frost[key] = img
            while len(self._frost) > 6:
                self._frost.pop(next(iter(self._frost)))
        return img

    def sample(self, size, box, extra=0.0, patch=11):
        """Colour of the wallpaper right behind a widget, as #rrggbb.

        Averaging the whole rectangle turns every widget into a flat band and
        neighbouring bands no longer line up; a small patch at its centre
        follows the picture instead, so the rectangles read as one surface.
        """
        x, y, width, height = [int(round(v)) for v in box]
        if width < 2 or height < 2:
            return None
        try:
            img = self.frost(size, extra)
            cx, cy = x + width // 2, y + height // 2
            half = max(1, int(patch) // 2)
            iw, ih = img.size
            x0 = max(0, min(iw - 1, cx - half))
            y0 = max(0, min(ih - 1, cy - half))
            x1 = max(x0 + 1, min(iw, cx + half))
            y1 = max(y0 + 1, min(ih, cy + half))
            tiny = img.crop((x0, y0, x1, y1)).resize((1, 1), Image.BOX)
            return theme_mod.rgb_to_hex(tiny.getpixel((0, 0)))
        except Exception:
            return None

    def mean(self, size, box, extra=0.0, flat=False):
        """Average wallpaper colour over one whole rectangle, as #rrggbb.

        Sampling a small patch made neighbouring rows land on unrelated
        colours and the panel read as a stack of zebra bands. Averaging the
        whole rectangle instead follows the picture's vertical gradient: rows
        next to each other differ by very little, so the card looks like one
        sheet of frosted glass.
        """
        x, y, width, height = [int(round(v)) for v in box]
        if width < 2 or height < 2:
            return None
        try:
            img = self.frost(size, extra, flat)
            iw, ih = img.size
            x0 = max(0, min(iw - 1, x))
            y0 = max(0, min(ih - 1, y))
            x1 = max(x0 + 1, min(iw, x + width))
            y1 = max(y0 + 1, min(ih, y + height))
            tiny = img.crop((x0, y0, x1, y1)).resize((1, 1), Image.BOX)
            return theme_mod.rgb_to_hex(tiny.getpixel((0, 0)))
        except Exception:
            return None

    def patch(self, size, box, extra=0.0, flat=False):
        """The wallpaper crop behind one rectangle, for use inside a card."""
        src = self.frost(size, extra, flat)
        if src is None:
            return None
        iw, ih = src.size
        x0, y0, x1, y1 = [int(round(v)) for v in box]
        x0, y0 = max(0, min(iw - 1, x0)), max(0, min(ih - 1, y0))
        x1, y1 = max(x0 + 1, min(iw, x1)), max(y0 + 1, min(ih, y1))
        return src.crop((x0, y0, x1, y1))

    def tone_at(self, size, box):
        """Average colour of the wallpaper under one card, as #rrggbb.

        A card borrows the colour right behind it, not the whole picture's
        average, so a card on a dark corner stays dark and one on a bright
        sky stays bright.
        """
        src = self._source()
        if src is None:
            return None
        try:
            x, y, width, height = [int(round(v)) for v in box]
            if width < 4 or height < 4:
                return None
            crop = crop_clamped(self.full(*size), (x, y, x + width, y + height),
                                _rgb(self.palette["window"]))
            tiny = crop.resize((1, 1), Image.BOX)
            return theme_mod.rgb_to_hex(tiny.getpixel((0, 0)))
        except Exception:
            return None
        return self._tone

    def _accent_band(self, width, height):
        """Branded header used when no wallpaper is picked."""
        pal = self.palette
        top = _rgb(pal["accent"])
        bottom = _rgb(pal["accent_press"])
        strip = Image.new("RGB", (1, height))
        pixels = strip.load()
        for y in range(height):
            k = y / float(max(1, height - 1))
            pixels[0, y] = tuple(int(top[i] + (bottom[i] - top[i]) * k) for i in range(3))
        band = strip.resize((width, height), Image.BILINEAR)
        glow = Image.new("L", (width, height), 0)
        radius = max(width, height)
        ImageDraw.Draw(glow).ellipse(
            [int(width * 0.55) - radius, int(height * 0.6) - radius,
             int(width * 0.55) + radius, int(height * 0.6) + radius], fill=90)
        glow = glow.filter(ImageFilter.GaussianBlur(max(8, height // 3)))
        light = Image.new("RGB", (width, height), _rgb(pal["accent_hover"]))
        return Image.composite(light, band, glow.point(lambda v: int(v * 0.5)))

    def hero_image(self, size, box, radius=18, scrim=0.62):
        """The wallpaper itself, darkened behind the page title.

        The scrim fades out before the edges, so no border shows and the
        header melts into the window wallpaper.
        """
        x, y, width, height = [int(round(v)) for v in box]
        width = max(8, width)
        height = max(8, height)
        if self.has_image():
            base = crop_clamped(self.full(*size), (x, y, x + width, y + height),
                                _rgb(self.palette["window"])).convert("RGB")
            return feather_scrim(base, scrim) if scrim > 0 else base
        base = self._accent_band(width, height)
        mask = Image.new("L", (width, height), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            [0, 0, width - 1, height - 1], radius=max(0, int(radius)), fill=255)
        band = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        band.paste(base.convert("RGB"), (0, 0), mask)
        return band.convert("RGB")

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

    def _card_layer(self, width, height, radius, fill, border, margin,
                    shadow_alpha, alpha=255, face=None):
        """Shadow + face + hairline, built once per size and colour set.

        Every scroll notch and page switch repaints each card; the blurred
        shadow and the supersampled rounded face were most of that paint and
        neither depends on the wallpaper underneath, so they are cached.
        """
        key = (width, height, int(radius), fill, border, int(margin),
               int(shadow_alpha), int(alpha), self.palette.get("shadow"),
               face is not None)
        layer = self._card_layers.get(key)
        if layer is not None and face is None:
            return layer
        layer = self._build_card_layer(width, height, radius, fill, border,
                                       margin, shadow_alpha, alpha,
                                       face is not None)
        self._card_layers[key] = layer
        self._layer_order.append(key)
        while len(self._layer_order) > 10:
            self._card_layers.pop(self._layer_order.pop(0), None)
        return layer

    def _build_card_layer(self, width, height, radius, fill, border, margin,
                          shadow_alpha, alpha=255, face=False):
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
        if face:
            # 透明卡片：面板由 card_image 贴壁纸，这里只负责阴影
            return layer
        face = Image.new("RGBA", (inner_w * scale, inner_h * scale), (0, 0, 0, 0))
        ImageDraw.Draw(face).rounded_rectangle(
            [0, 0, inner_w * scale - 1, inner_h * scale - 1],
            radius=max(1, int(radius * scale)),
            fill=_rgb(fill) + (max(0, min(255, int(alpha))),),
            outline=_rgb(border) + (max(0, min(255, int(alpha))),) if border else None,
            width=max(1, scale) if border else 0,
        )
        face_img = shrink(face, (inner_w, inner_h), scale)
        if alpha < 250:
            # 半透明的卡片不要一条硬边：把面板自己的 alpha 从边上羽化掉，
            # 看起来像玻璃边缘融进壁纸，而不是描了一圈灰线
            feather = Image.new("L", (inner_w, inner_h), 0)
            ImageDraw.Draw(feather).rounded_rectangle(
                [0, 0, inner_w - 1, inner_h - 1],
                radius=max(1, int(round(radius))), fill=255)
            feather = feather.filter(ImageFilter.GaussianBlur(6))
            face_img.putalpha(ImageChops.multiply(
                face_img.getchannel("A"), feather))
        layer.alpha_composite(face_img, (margin, margin))
        if border and alpha >= 250:
            # hairline drawn at 1:1 so it lands on whole pixels instead of
            # being smeared across two of them by the supersample
            ImageDraw.Draw(layer).rounded_rectangle(
                [margin, margin, width - margin - 1, height - margin - 1],
                radius=max(1, int(round(radius))),
                outline=_rgb(border) + (max(0, min(255, int(alpha) + 60)),),
                width=1,
            )
        return layer

    def card_image(self, size, box, radius=16, fill="#FFFFFF", border="#E2E8F2",
                   margin=8, shadow_alpha=44, alpha=255, face_mix=0.0,
                   face_extra=None, flat=False):
        """Render one rounded card over the wallpaper under its box.

        face_mix > 0 lets the wallpaper itself become the panel: the crop
        under the card is blended towards fill by (1 - face_mix), so at 1.0
        the card is a rounded window with only a hairline. The same frosted
        crop is what App samples for the widgets inside, which keeps their
        rectangles from standing out of the picture.
        """
        alpha = max(0, min(255, int(alpha)))
        face_mix = max(0.0, min(1.0, float(face_mix or 0.0)))
        x, y, width, height = [int(round(v)) for v in box]
        width = max(8, width)
        height = max(8, height)
        if face_extra is None:
            face_extra = 1.5 + 2.5 * face_mix
        back = crop_clamped(self.frost(size, face_extra, flat),
                            (x, y, x + width, y + height),
                            _rgb(self.palette["window"]))
        if face_mix <= 0.02:
            layer = self._card_layer(width, height, radius, fill, border, margin,
                                     shadow_alpha, alpha)
            return Image.alpha_composite(back.convert("RGBA"), layer).convert("RGB")
        layer = self._card_layer(width, height, radius, fill, border, margin,
                                 shadow_alpha, alpha, face=True)
        inner_w = max(4, width - margin * 2)
        inner_h = max(4, height - margin * 2)
        panel = back.crop((margin, margin, margin + inner_w, margin + inner_h))
        solid = Image.new("RGB", (inner_w, inner_h), _rgb(fill))
        panel = Image.blend(solid, panel, face_mix).convert("RGBA")
        mask = Image.new("L", (inner_w, inner_h), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            [0, 0, inner_w - 1, inner_h - 1], radius=max(1, int(round(radius))),
            fill=255)
        panel.putalpha(mask)
        img = back.convert("RGBA")
        img.alpha_composite(layer)
        img.alpha_composite(panel, (margin, margin))
        if border:
            ImageDraw.Draw(img).rounded_rectangle(
                [margin, margin, width - margin - 1, height - margin - 1],
                radius=max(1, int(round(radius))),
                # 越透，描边越要让位：一块玻璃不该有实心边框
                outline=_rgb(border) + (int(round(120 * (1.0 - 0.6 * face_mix))),),
                width=1)
        return img.convert("RGB")

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
