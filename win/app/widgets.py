# -*- coding: utf-8 -*-
"""Small widget kit used to build the modern look without external themes."""

from __future__ import annotations

import tkinter as tk

from . import bgfx
from . import theme as theme_mod

try:
    from PIL import Image, ImageDraw, ImageTk
except Exception:  # pragma: no cover
    Image, ImageDraw, ImageTk = None, None, None


# -- tiny builders -----------------------------------------------------
def label(master, app, text="", size=10, weight="normal", color="text", bg="card",
          family=None, anchor="w", justify="left", wraplength=0, width=0):
    return tk.Label(
        master, text=text, font=theme_mod.font(size, weight, family), width=width,
        fg=app.pal[color], bg=app.pal[bg], anchor=anchor, justify=justify,
        bd=0, highlightthickness=0, wrap=wraplength,
    )


def mono_label(master, app, text="", size=9, color="text", bg="card"):
    return tk.Label(master, text=text, font=theme_mod.mono(size), fg=app.pal[color],
                    bg=app.pal[bg], bd=0, highlightthickness=0)


def entry(master, app, textvariable=None, width=24, bg="card_soft", show=None):
    return tk.Entry(
        master, textvariable=textvariable, width=width, font=theme_mod.font(10),
        bg=app.pal[bg], fg=app.pal["text"], insertbackground=app.pal["text"],
        relief="flat", bd=0, highlightthickness=1,
        highlightbackground=app.pal["border"], highlightcolor=app.pal["accent"],
        show=show,
    )


def chip(master, app, text, tone="accent"):
    tones = {
        "accent": ("accent_soft", "accent"),
        "ok": ("ok_soft", "ok"),
        "warn": ("warn_soft", "warn"),
        "err": ("err_soft", "err"),
        "muted": ("card_soft", "text_muted"),
    }
    bg, fg = tones.get(tone, tones["muted"])
    return tk.Label(master, text=text, font=theme_mod.font(9), fg=app.pal[fg],
                    bg=app.pal[bg], padx=theme_mod.px(9), pady=theme_mod.px(3),
                    bd=0, highlightthickness=0)


def separator(master, app, bg="card"):
    holder = tk.Frame(master, bg=app.pal[bg], height=1)
    holder.pack_propagate(False)
    line = tk.Frame(holder, bg=app.pal["border_soft"], height=1)
    line.pack(fill="x", pady=theme_mod.px(0))
    return holder


def rounded_photo(app, width, height, radius, fill, border=None, scale=2):
    if not bgfx.PIL_OK or ImageTk is None:
        return None
    img = bgfx.rounded_rgba(width, height, radius, fill, border, 1, scale)
    return ImageTk.PhotoImage(img)


def icon_photo(app, size=38, radius=12, fill=None, text="东", fg="#FFFFFF", size_pt=16):
    """Round square app icon rendered with Pillow (falls back to a plain frame)."""
    if not bgfx.PIL_OK or ImageTk is None:
        return None
    size = theme_mod.px(size)
    radius = theme_mod.px(radius)
    img = bgfx.rounded_rgba(size, size, radius, theme_mod.hex_to_rgb(fill or app.pal["accent"]) + (255,))
    holder = tk.Canvas(app.root, width=size, height=size, bg=app.pal["rail"],
                       highlightthickness=0, bd=0)
    photo = ImageTk.PhotoImage(img)
    holder.create_image(0, 0, anchor="nw", image=photo)
    holder.image = photo
    holder.create_text(size // 2, size // 2 - 1, text=text,
                       font=theme_mod.font(size_pt, "bold"), fill=fg)
    return holder


# -- rounded card ------------------------------------------------------
class RoundCard(tk.Canvas):
    """A rounded, softly shadowed panel composited on the wallpaper."""

    def __init__(self, app, master=None, radius=16, pad=18, margin=8,
                 fill="card", shadow=44, border="border"):
        master = master or app.canvas
        super().__init__(master, bg=app.pal["window"], highlightthickness=0, bd=0, takefocus=0)
        self.app = app
        self.radius = theme_mod.px(radius)
        self.pad = theme_mod.px(pad)
        self.margin = theme_mod.px(margin)
        self.fill = fill
        self.shadow = shadow
        self.border = border
        self._photo = None
        self._img_id = None
        self._box = (0, 0, 1, 1)
        self.body = tk.Frame(self, bg=app.pal[fill], bd=0, highlightthickness=0)
        inset = self.margin + self.pad
        self._win = self.create_window(inset, inset, window=self.body, anchor="nw")
        app.cards.append(self)

    def required_height(self):
        """Outer height the card needs so no packed row gets clipped.

        Fixed page heights are authored at 96 dpi; this keeps them honest
        after the window scale changes (fonts grow with the DPI, paddings
        with it, and rounding adds a pixel here and there).
        """
        self.body.update_idletasks()
        return int(self.body.winfo_reqheight() + 2 * (self.margin + self.pad))

    # geometry is always driven by the app layout, never by <Configure>,
    # so the wallpaper crop under the card is exact.
    def layout(self, x, y, width, height):
        self._box = (x, y, width, height)
        self.place(x=x, y=y, width=width, height=height)
        self.render()

    def render(self):
        x, y, width, height = self._box
        if width < 20 or height < 20:
            return
        inset = self.margin + self.pad
        self.itemconfigure(self._win, width=max(1, width - 2 * inset),
                           height=max(1, height - 2 * inset))
        if not bgfx.PIL_OK or ImageTk is None:
            self.configure(bg=self.app.pal[self.fill])
            return
        try:
            img = self.app.backdrop.card_image(
                (self.app.canvas.winfo_width(), self.app.canvas.winfo_height()),
                self._box, self.radius, self.app.pal[self.fill],
                self.app.pal[self.border], self.margin, self.shadow)
            self._photo = ImageTk.PhotoImage(img)
            if self._img_id is None:
                self._img_id = self.create_image(0, 0, anchor="nw", image=self._photo,
                                                 tags=("cardbg",))
            else:
                self.itemconfigure(self._img_id, image=self._photo)
            self.tag_lower("cardbg")
        except Exception:
            self.configure(bg=self.app.pal[self.fill])


# -- buttons -----------------------------------------------------------
class PillButton(tk.Canvas):
    KINDS = {
        "primary": dict(fill="accent", hover="accent_hover", press="accent_press",
                        text="on_accent", border=None, emph=True),
        "ghost": dict(fill="card_soft", hover="accent_soft", press="btn_hover",
                      text="text", border="border", emph=False),
        "soft": dict(fill="accent_soft", hover="soft_hover", press="soft_press",
                     text="accent", border=None, emph=False),
        "danger": dict(fill="err_soft", hover="danger_hover", press="danger_press",
                       text="err", border=None, emph=False),
    }

    def __init__(self, app, master, text, command=None, kind="primary",
                 width=170, height=40, radius=None, glyph="", bg="card"):
        width = theme_mod.px(width)
        height = theme_mod.px(height)
        radius = theme_mod.px(radius) if radius is not None else None
        super().__init__(master, width=width, height=height, bg=app.pal[bg],
                         highlightthickness=0, bd=0, takefocus=0)
        self.app = app
        self._bg = bg
        self._photo = None
        self.text = text
        self.glyph = glyph
        self.command = command
        self.kind = kind
        self._width = width
        self._height = height
        self._radius = radius if radius is not None else min(theme_mod.px(14), height // 2)
        self._enabled = True
        self._state = "normal"
        self._photos = {}
        self._bg_id = None
        self._text_id = None
        self._base_bg = bg
        self.bind("<Enter>", lambda e: self._set_state("hover"))
        self.bind("<Leave>", lambda e: self._set_state("normal"))
        self.bind("<ButtonPress-1>", lambda e: self._set_state("press"))
        self.bind("<ButtonRelease-1>", self._on_release)
        self._render()

    # -- api ---------------------------------------------------------
    def set_text(self, text):
        self.text = text
        self._render()

    def set_enabled(self, enabled):
        self._enabled = bool(enabled)
        self._state = "normal" if enabled else "disabled"
        self._render()

    # keep the old ttk-ish call site working
    def configure(self, cnf=None, **kwargs):  # noqa: D401 - ttk compatibility shim
        state = kwargs.pop("state", None)
        if state is not None:
            self.set_enabled(str(state) != "disabled")
        return super().configure(cnf, **kwargs)

    # -- internals ---------------------------------------------------
    def _palette(self):
        spec = self.KINDS.get(self.kind, self.KINDS["primary"])
        if not self._enabled:
            return self.app.pal["glyph_off"], self.app.pal["glyph_off_line"], None
        key = {"normal": "fill", "hover": "hover", "press": "press"}.get(self._state, "fill")
        fill = self.app.pal[spec[key]]
        fg = self.app.pal[spec["text"]]
        border = self.app.pal[spec["border"]] if spec["border"] else None
        return fill, fg, border

    def _render(self):
        fill, fg, border = self._palette()
        photo = None
        if bgfx.PIL_OK and ImageTk is not None:
            key = (fill, border)
            if key not in self._photos:
                img = bgfx.rounded_rgba(self._width, self._height, self._radius,
                                        theme_mod.hex_to_rgb(fill) + (255,),
                                        theme_mod.hex_to_rgb(border) + (255,) if border else None,
                                        1, 2)
                self._photos[key] = ImageTk.PhotoImage(img)
            photo = self._photos[key]
        self.delete("all")
        self._bg_id = None
        if photo is not None:
            self._bg_id = self.create_image(0, 0, anchor="nw", image=photo)
        else:
            self.configure(bg=fill)
            self.create_rectangle(0, 0, self._width, self._height, fill=fill, outline="")
        caption = ("%s  %s" % (self.glyph, self.text)) if self.glyph else self.text
        weight = "bold" if self.kind in ("primary", "soft") else "normal"
        self._text_id = self.create_text(self._width // 2, self._height // 2 - 1,
                                         text=caption,
                                         font=theme_mod.font(10, weight),
                                         fill=fg)

    def _set_state(self, state):
        if not self._enabled:
            return
        if state != self._state:
            self._state = state
            self._render()

    def _on_release(self, event):
        inside = 0 <= event.x <= self._width and 0 <= event.y <= self._height
        self._set_state("hover" if inside else "normal")
        if inside and self._enabled and self.command:
            self.command()


class NavButton(tk.Canvas):
    def __init__(self, app, master, text, glyph, command, width=176, height=42):
        width = theme_mod.px(width)
        height = theme_mod.px(height)
        super().__init__(master, width=width, height=height, bg=app.pal["rail"],
                         highlightthickness=0, bd=0, takefocus=0)
        self.app = app
        self.text = text
        self.glyph = glyph
        self.command = command
        self._width = width
        self._height = height
        self.active = False
        self._hover = False
        self._photos = {}
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", lambda e: self.command())
        self._render()

    def _on_enter(self, _event):
        self._hover = True
        self._render()
        self.configure(cursor="hand2")

    def _on_leave(self, _event):
        self._hover = False
        self._render()

    def set_active(self, active):
        self.active = bool(active)
        self._render()

    def _render(self):
        if self.active:
            fill = self.app.pal["accent_soft"]
            fg = self.app.pal["accent"]
            weight = "bold"
        elif self._hover:
            fill = self.app.pal["rail_hover"]
            fg = self.app.pal["text"]
            weight = "normal"
        else:
            fill = self.app.pal["rail"]
            fg = self.app.pal["text_muted"]
            weight = "normal"
        self.delete("all")
        photo = None
        if bgfx.PIL_OK and ImageTk is not None:
            if fill not in self._photos:
                img = bgfx.rounded_rgba(self._width, self._height, theme_mod.px(10),
                                        theme_mod.hex_to_rgb(fill) + (255,), scale=2)
                self._photos[fill] = ImageTk.PhotoImage(img)
            photo = self._photos[fill]
        if photo is not None:
            self.create_image(0, 0, anchor="nw", image=photo)
        else:
            self.configure(bg=fill)
            self.create_rectangle(0, 0, self._width, self._height, fill=fill, outline="")
        self.create_text(theme_mod.px(18), self._height // 2, text=self.glyph, anchor="w",
                         font=theme_mod.font(12), fill=fg)
        self.create_text(theme_mod.px(44), self._height // 2, text=self.text, anchor="w",
                         font=theme_mod.font(10, weight), fill=fg)
        if self.active:
            self.create_rectangle(0, theme_mod.px(11), theme_mod.px(3),
                                  self._height - theme_mod.px(11),
                                  fill=self.app.pal["accent"], outline="")
        else:
            self.configure(cursor="hand2")


# -- slider ------------------------------------------------------------
class MiniSlider(tk.Canvas):
    def __init__(self, app, master, value=0, from_=0, to=100, on_change=None,
                 width=260, height=26, bg="card", step=1):
        width = theme_mod.px(width)
        height = theme_mod.px(height)
        super().__init__(master, width=width, height=height, bg=app.pal[bg],
                         highlightthickness=0, bd=0, takefocus=0)
        self.app = app
        self._bg = bg
        self._photo = None
        self.from_ = float(from_)
        self.to = float(to)
        self.step = max(0.0, float(step))
        self.on_change = on_change
        self.value = float(value)
        self._width = width
        self._height = height
        self._dragging = False
        self.bind("<Configure>", self._on_configure)
        self.bind("<Button-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self._draw()

    def _on_configure(self, event):
        self._width = event.width
        self._height = event.height
        self._draw()

    def _pad(self):
        return theme_mod.px(11)

    def _track(self):
        return self._pad(), max(self._pad() + 1, self._width - self._pad())

    def _draw(self):
        self.delete("all")
        y = self._height // 2
        x0, x1 = self._track()
        span = max(1.0, self.to - self.from_)
        ratio = max(0.0, min(1.0, (self.value - self.from_) / span))
        knob_x = x0 + (x1 - x0) * ratio
        photo = self._render(x0, x1, y, knob_x)
        if photo is not None:
            self._photo = photo
            self.create_image(0, 0, anchor="nw", image=photo)
        else:  # Pillow missing: plain, slightly blocky but functional
            self.create_line(x0, y, x1, y, width=6, capstyle="round",
                             fill=self.app.pal["card_soft"])
            self.create_line(x0, y, max(x0, knob_x), y, width=6, capstyle="round",
                             fill=self.app.pal["accent"])
            self.create_oval(knob_x - 9, y - 9, knob_x + 9, y + 9,
                             fill=self.app.pal["card"], outline=self.app.pal["accent"],
                             width=2)
            self.create_oval(knob_x - 4, y - 4, knob_x + 4, y + 4,
                             fill=self.app.pal["accent"], outline="")
        self.configure(cursor="hand2")

    def _render(self, x0, x1, y, knob_x):
        """Draw track + knob supersampled; canvas ovals/lines have no AA and
        showed stair-stepped caps and a jagged ring."""
        if not bgfx.PIL_OK or Image is None or ImageTk is None:
            return None
        width = max(2, int(self._width))
        height = max(2, int(self._height))
        s = 3
        pal = self.app.pal
        img = Image.new("RGBA", (width * s, height * s),
                        theme_mod.hex_to_rgb(pal[self._bg]) + (255,))
        draw = ImageDraw.Draw(img)
        cy = y * s
        thick = max(2, theme_mod.px(6)) * s
        cy0, cy1 = cy - thick // 2, cy + thick // 2
        track = theme_mod.hex_to_rgb(pal["card_soft"]) + (255,)
        accent = theme_mod.hex_to_rgb(pal["accent"]) + (255,)
        white = theme_mod.hex_to_rgb(pal["card"]) + (255,)

        def round_cap(xc, color):
            draw.ellipse([xc - thick // 2, cy0, xc + thick // 2, cy1], fill=color)

        ax0, ax1 = int(round(x0 * s)), int(round(x1 * s))
        draw.rectangle([ax0, cy0, ax1, cy1], fill=track)
        round_cap(ax0, track)
        round_cap(ax1, track)
        kx = int(round(knob_x * s))
        if kx > ax0:
            draw.rectangle([ax0, cy0, kx, cy1], fill=accent)
            round_cap(ax0, accent)
        ring = theme_mod.px(9) * s
        draw.ellipse([kx - ring, cy - ring, kx + ring, cy + ring],
                     fill=white, outline=accent, width=theme_mod.px(2) * s)
        dot = theme_mod.px(4) * s
        draw.ellipse([kx - dot, cy - dot, kx + dot, cy + dot], fill=accent)
        try:
            img = img.reduce(s)
        except Exception:
            img = img.resize((width, height), Image.BOX)
        return ImageTk.PhotoImage(img)

    def _value_from_x(self, x):
        x0, x1 = self._track()
        ratio = (float(x) - x0) / max(1.0, float(x1 - x0))
        ratio = max(0.0, min(1.0, ratio))
        value = self.from_ + ratio * (self.to - self.from_)
        if self.step:
            value = round(value / self.step) * self.step
        return max(self.from_, min(self.to, value))

    def _apply(self, x):
        value = self._value_from_x(x)
        changed = value != self.value
        self.value = value
        self._draw()
        if changed and self.on_change:
            self.on_change(self.value)

    def _on_press(self, event):
        self._dragging = True
        self._apply(event.x)

    def _on_drag(self, event):
        if self._dragging:
            self._apply(event.x)

    def _on_release(self, event):
        self._dragging = False
        self._apply(event.x)

    def get(self):
        return self.value

    def set(self, value):
        try:
            value = float(value)
        except (TypeError, ValueError):
            return
        self.value = max(self.from_, min(self.to, value))
        self._draw()


class Segmented(tk.Frame):
    """Pill switcher: 东京放课后 / LiveAHero，或 账号 / 备份。"""

    def __init__(self, app, master, options, active=None, command=None, pad_x=12):
        border = theme_mod.px(1)
        tk.Frame.__init__(self, master, bg=app.pal["card_soft"], bd=0,
                          highlightthickness=border,
                          highlightbackground=app.pal["border"],
                          highlightcolor=app.pal["border"])
        self.app = app
        self.pal = app.pal
        self.options = list(options)
        self.active = active or (self.options[0][0] if self.options else None)
        self.command = command
        self.labels = {}
        for key, text in self.options:
            lab = tk.Label(self, text=text, font=theme_mod.font(9), bd=0,
                           highlightthickness=0, cursor="hand2",
                           padx=theme_mod.px(pad_x), pady=theme_mod.px(4))
            lab.pack(side="left", padx=theme_mod.px(2), pady=theme_mod.px(2))
            lab.bind("<Button-1>", lambda _e, k=key: self.select(k))
            self.labels[key] = lab
        self._paint()

    def _paint(self):
        for key, lab in self.labels.items():
            active = key == self.active
            lab.configure(bg=self.pal["accent"] if active else self.pal["card_soft"],
                          fg=self.pal["on_accent"] if active else self.pal["text"])

    def set_active(self, key):
        self.active = key
        self._paint()

    def set_text(self, key, text):
        if key in self.labels:
            self.labels[key].configure(text=text)

    def select(self, key):
        if key == self.active:
            return
        self.active = key
        self._paint()
        if self.command:
            self.command(key)


class SectionTitle:
    """Convenience builder for a card header row (title + hint + right slot)."""

    @staticmethod
    def build(app, parent, title, hint="", right=None, bg="card"):
        row = tk.Frame(parent, bg=app.pal[bg])
        left = tk.Frame(row, bg=app.pal[bg])
        left.pack(side="left", anchor="w")
        label(left, app, title, size=12, weight="bold", bg=bg).pack(side="left")
        if hint:
            label(left, app, hint, size=9, color="text_muted", bg=bg).pack(side="left", padx=(theme_mod.px(10), theme_mod.px(0)))
        if right is not None:
            right(row)
        return row
