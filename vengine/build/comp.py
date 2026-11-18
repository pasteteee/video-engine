"""The compositor of a build short: hook → the knit → Done! → real life → CTA, frame by frame (PIL, 1080x1920).

Ported from the channel's goat-sweater-2027 short (comp.py) and made data-driven: the words come from the
storyboard, colours and fonts from the channel profile, the moments from the knit plan.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ..episode import ROOT
from . import storyboard as SB
from .knit import KnitFrames

DESIGN = (1080, 1920)


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def cl(x):
    return max(0.0, min(1.0, x))


def ease(x):
    x = cl(x); return x * x * (3 - 2 * x)


def eout(x):
    x = cl(x); return 1 - (1 - x) ** 3


def eback(x, s=1.7):
    x = cl(x) - 1; return 1 + (s + 1) * x ** 3 + s * x ** 2


def lerp(a, b, t):
    return a + (b - a) * t


class Brand:
    """Colours and fonts of the channel (style.tokens / style.fonts)."""

    def __init__(self, channel: dict):
        st = channel.get("style", {})
        tk = {k.upper(): v for k, v in st.get("tokens", {}).items()}
        self.ink = hex_rgb(tk.get("NAVY", "#1b2454"))
        self.text = hex_rgb(tk.get("CREAM", "#fffbf4"))
        self.accent = hex_rgb(tk.get("YELLOW", "#ffd23f"))
        self.accent2 = hex_rgb(tk.get("PINK", "#f4a9c0"))
        self.ground = (hex_rgb(tk.get("GROUND_TOP", "#f9f3e8")), hex_rgb(tk.get("GROUND_BOTTOM", "#eee4d4")))
        f = st.get("fonts", {})
        d = Path(f.get("dir", "channels/amigurumi/brand/fonts"))
        self.font_dir = d if d.is_absolute() else ROOT / d
        self.files = {"U": f.get("display", "Unbounded-Bold.ttf"), "O": f.get("bold", "Onest-Bold.ttf"),
                      "Os": f.get("semibold", "Onest-SemiBold.ttf")}
        self._fc = {}

    def font(self, face: str, size: int) -> ImageFont.FreeTypeFont:
        k = (face, size)
        if k not in self._fc:
            try:
                self._fc[k] = ImageFont.truetype(str(self.font_dir / self.files[face]), size)
            except OSError:
                self._fc[k] = ImageFont.load_default(size)
        return self._fc[k]


class Compositor:
    def __init__(self, folder: Path, sb: dict, channel: dict, knit: KnitFrames):
        self.folder = Path(folder)
        self.sb = SB.resolve(sb, channel)
        self.tm = SB.timing(sb, channel)
        b = channel.get("build", {})
        self.fps = int(b.get("fps", 30))
        # every layout number is for a 1080x1920 canvas; another output size is a resize at the end
        self.W, self.H = DESIGN
        self.out_size = tuple(int(v) for v in b.get("size", "1080x1920").split("x"))
        self.brand = Brand(channel)
        self.knit = knit
        self.plan, self.pieces = knit.plan, knit.pieces
        self.total = SB.total_stitches(self.pieces)
        self.caps = SB.captions(knit.data, self.sb, self.tm)
        self.c0 = self.pieces[0]["counts"]
        self.snow_on = bool(self.sb["effects"].get("snow"))
        self._tc = {}
        ph = self.sb.get("photos", {})
        self.final_knit = None
        self.photo_hook = self._photo(ph.get("hook"))
        self.photo_real = self._photo(ph.get("real")) or self.photo_hook
        self.photo_cta = self._photo(ph.get("cta")) or self.photo_real
        self.focus_hook = ph.get("hook_focus", [0.40, 0.34])
        self.focus_real = ph.get("real_focus", [0.5, 0.55])
        g0, g1 = self.brand.ground
        self.cta_bg = Image.new("RGB", (self.W, self.H)); d = ImageDraw.Draw(self.cta_bg)
        for y in range(self.H):
            u = y / self.H
            d.line((0, y, self.W, y), fill=tuple(int(lerp(g0[i], g1[i], u)) for i in range(3)))
        rnd = random.Random
        self.flakes = [(rnd(i).random(), rnd(i + 999).random(), rnd(i + 5).choice([5, 7, 9, 12, 16]), rnd(i + 7).random())
                       for i in range(90)]

    # ------------------------------------------------ inputs
    def _photo(self, rel):
        if not rel:
            return None
        p = Path(rel)
        p = p if p.is_absolute() else self.folder / p
        return Image.open(p).convert("RGB")

    def finished(self) -> Image.Image:
        """The finished knit facing us: stands in for a missing photo."""
        if self.final_knit is None:
            self.final_knit = self.knit.frame(len(self.plan) - 1)
        return self.final_knit

    # ------------------------------------------------ drawing helpers
    def text_img(self, s, size, fill, face="U"):
        ink = self.brand.ink
        f = self.brand.font(face, size); sw = int(size * 0.11)
        l, t, r, b = f.getbbox(s, stroke_width=sw)
        im = Image.new("RGBA", (r - l + 30, b - t + 40), (0, 0, 0, 0))
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        shade = tuple(int(c * 0.4) for c in ink) + (110,)
        ImageDraw.Draw(sh).text((14 - l, 24 - t), s, font=f, fill=shade, stroke_width=sw, stroke_fill=shade)
        im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(6)))
        ImageDraw.Draw(im).text((14 - l, 14 - t), s, font=f, fill=fill + (255,), stroke_width=sw, stroke_fill=ink + (255,))
        return im

    def put(self, cv, s, cx, cy, size, t_in, fill=None, alpha=1.0):
        if t_in < 0 or alpha <= 0:
            return
        fill = fill or self.brand.text
        k = (s, size, fill)
        if k not in self._tc:
            if len(self._tc) > 80:
                self._tc.clear()
            self._tc[k] = self.text_img(s, size, fill)
        im = self._tc[k]; sc = max(0.05, eback(t_in / 0.22))
        if abs(sc - 1) > 0.01:
            im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BILINEAR)
        cv.paste(im, (int(cx - im.width / 2), int(cy - im.height / 2)), im)

    def fit(self, line, size, face="U", margin=100):
        f = self.brand.font(face, size)
        while f.getlength(line) + size * 0.22 > self.W - margin and size > 28:
            size -= 4; f = self.brand.font(face, size)
        return size

    def words(self, cv, line, cy, size, t, stagger=0.09, **kw):
        size = self.fit(line, size)
        ws = line.split(" "); f = self.brand.font("U", size); sp = f.getlength(" ")
        wd = [f.getlength(w) for w in ws]; x = self.W / 2 - (sum(wd) + sp * (len(ws) - 1)) / 2
        for k, (w_, d_) in enumerate(zip(ws, wd)):
            self.put(cv, w_, x + d_ / 2, cy, size, t - k * stagger, **kw); x += d_ + sp

    def chip(self, cv, s, cx, cy, size=40, bg=None, fg=None, t_in=1.0, face="O", pad=(28, 16)):
        if t_in <= 0 or not s:
            return
        bg = bg or self.brand.text; fg = fg or self.brand.ink
        size = self.fit(s, size, face, margin=100 + 2 * pad[0])
        f = self.brand.font(face, size); tw = f.getlength(s); sc = eback(t_in / 0.25)
        lay = Image.new("RGBA", (int(tw + 2 * pad[0]), int(size * 1.3 + 2 * pad[1])), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        d.rounded_rectangle([0, 0, lay.width - 1, lay.height - 1], lay.height // 2, fill=bg + (245,))
        d.text((pad[0], lay.height / 2), s, font=f, fill=fg + (255,), anchor="lm")
        if abs(sc - 1) > 0.01:
            lay = lay.resize((max(1, int(lay.width * sc)), max(1, int(lay.height * sc))), Image.BILINEAR)
        cv.paste(lay, (int(cx - lay.width / 2), int(cy - lay.height / 2)), lay)

    def progress(self, cv, x):
        d = ImageDraw.Draw(cv); W = self.W
        d.rounded_rectangle([60, 236, W - 60, 248], 6, fill=(255, 255, 255))
        d.rounded_rectangle([60, 236, 60 + (W - 120) * cl(x), 248], 6, fill=self.brand.accent)

    @staticmethod
    def punch(im, ts, amt=0.07, dur=0.3):
        z = 1 + amt * (1 - eout(ts / dur))
        if z <= 1.001 or ts < 0:
            return im
        w, h = im.size; cw, ch = w / z, h / z
        return im.crop(((w - cw) / 2, (h - ch) / 2, (w + cw) / 2, (h + ch) / 2)).resize((w, h), Image.BILINEAR)

    @staticmethod
    def flash(im, ts, dur=0.18, amt=0.85):
        a = 1 - cl(ts / dur)
        return Image.blend(im, Image.new("RGB", im.size, (255, 255, 255)), a * amt) if a > 0 and ts >= 0 else im

    def snow(self, cv, t, n=90, speed=1.0):
        if not self.snow_on:
            return
        W, H = self.W, self.H
        lay = Image.new("RGBA", cv.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        for (x0, y0, s, ph) in self.flakes[:n]:
            y = ((y0 * H + t * (60 + s * 9) * speed) % (H + 40)) - 20
            x = x0 * W + 18 * math.sin(t * 1.3 + ph * 6.28)
            d.ellipse((x, y, x + s, y + s), fill=(255, 255, 255, int(150 + 90 * ph)))
        cv.paste(lay, (0, 0), lay.filter(ImageFilter.GaussianBlur(1.2)))

    def cover(self, im, cx, cy, zoom):
        W, H = self.W, self.H
        s = max(W / im.width, H / im.height) * zoom; iw, ih = im.width * s, im.height * s
        x, y = (iw - W) * cx, (ih - H) * cy
        return im.resize((int(iw), int(ih)), Image.BILINEAR).crop((int(x), int(y), int(x) + W, int(y) + H))

    # ------------------------------------------------ sections
    def hook(self, t):
        tm, W = self.tm, self.W
        z = 1.28 - 0.10 * eout(t / max(0.5, tm.hook))
        src = self.photo_hook or self.finished()
        fx, fy = self.focus_hook if self.photo_hook else (0.5, 0.5)
        cv = self.cover(src, fx, fy, z * (1 + 0.06 * (1 - eout(t / 0.35))))
        g = Image.new("RGBA", (W, self.H), (0, 0, 0, 0))
        ImageDraw.Draw(g).rectangle((0, 0, W, 760), fill=self.brand.ink + (50,))
        cv = cv.convert("RGBA"); cv.alpha_composite(g.filter(ImageFilter.GaussianBlur(80))); cv = cv.convert("RGB")
        self.snow(cv, t + 3)
        y = 330
        for i, ln in enumerate(self.sb["hook"]["lines"]):
            size = ln.get("size", 100 if i == 0 else 64)
            self.words(cv, ln["text"], y, size, t - i * tm.beat, stagger=0.09 if size > 80 else 0.07,
                       fill=self.brand.accent if ln.get("accent") else None)
            y += int(self.fit(ln["text"], size) * 1.15) + 26
        return self.flash(cv, t, 0.12, 0.6)

    def grow(self, t):
        tm, W = self.tm, self.W
        tg = t - tm.t_grow
        k = min(len(self.plan) - 1, int(tg * self.fps)); f = self.plan[k]
        cv = self.knit.frame(k)
        if cv.size != (W, self.H):
            cv = cv.resize((W, self.H), Image.LANCZOS)
        cv = self.flash(cv, tg, 0.15); cv = self.punch(cv, tg, 0.06)
        cap = [c for c in self.caps if c[0] <= t]
        if cap and t < tm.t_done:
            cv = self.punch(cv, t - cap[-1][0], 0.035, 0.22)
        if t >= tm.t_done:                                  # DONE
            td = t - tm.t_done
            cv = self.punch(self.flash(cv, td, 0.25), td, 0.12, 0.45)
            self.progress(cv, 1.0); self.snow(cv, td, 60, 0.8)
            self.put(cv, self.sb["done"]["title"], W / 2, 420, 160, td, fill=self.brand.accent)
            sub = self.sb["done"]["sub"].format(pieces=len(self.pieces), stitches=format(self.total, ","))
            self.words(cv, sub, 1380, 50, td - 2 * tm.beat, stagger=0.07)
            return cv
        self.progress(cv, f["s"])
        if t >= tm.breath:                                  # the held breath: no new text
            return cv
        if cap:
            ct, cs = cap[-1]
            self.words(cv, cs, 400, 92 if len(cs) < 12 else 78, t - ct)
        if f["pi"] == 0:
            r = f["round"]
            self.chip(cv, "Rnd %d:  %s  (%d)" % (r, SB.round_text(self.c0, r - 1), self.c0[r - 1]), W / 2, 1430, 40,
                      t_in=tg - 0.2)
        else:
            self.chip(cv, "%s stitches" % format(int(f["s"] * self.total), ","), W / 2, 1430, 42)
        sp = SB.speed(self.knit.data, k, self.fps, self.total)
        if f["s"] < 0.995:
            hot = sp >= 300
            self.chip(cv, "x%d" % sp, W - 150, 530, 52 if hot else 44, bg=self.brand.accent2 if hot else self.brand.accent,
                      face="U")
        return cv

    def real(self, t):
        tm, W = self.tm, self.W
        tr = t - tm.t_real
        src = self.photo_real or self.finished()
        fx, fy = self.focus_real if self.photo_real else (0.5, 0.5)
        cv = self.cover(src, fx, fy, 1.12 - 0.08 * ease(tr / max(0.5, tm.real)))
        self.snow(cv, t); cv = self.flash(cv, tr, 0.35, 0.9)
        lines = self.sb["real"]["lines"]
        if lines:
            self.words(cv, lines[0], 380, 104, tr - 0.15)
        if len(lines) > 1:
            self.words(cv, lines[1], 520, 116, tr - 0.15 - 2 * tm.beat, fill=self.brand.accent)
        self.chip(cv, self.sb["real"].get("chip"), W / 2, 1400, 40, t_in=tr - 1.5)
        return cv

    def cta(self, t):
        tm, W, H = self.tm, self.W, self.H
        te = t - tm.t_cta
        cv = self.cta_bg.copy()
        s = int(lerp(1500, 760, eout(te / 0.6)))
        src = self.photo_cta or self.finished()
        sq = min(src.size); x0, y0 = (src.width - sq) // 2, (src.height - sq) // 2
        toy = src.crop((x0, y0, x0 + sq, y0 + sq)).resize((s, s), Image.LANCZOS)
        m = Image.new("L", (s, s), 0); ImageDraw.Draw(m).ellipse((0, 0, s, s), fill=255)
        y = int(lerp(H / 2, 900, eout(te / 0.6)) - s / 2 + 8 * math.sin(te * 3))
        cv.paste(toy, (W // 2 - s // 2, y), m)
        self.snow(cv, t, 40, 0.6)
        c = self.sb["cta"]
        lines = c.get("lines", [])
        if lines:
            self.words(cv, lines[0], 340, 96, te - 0.3, fill=self.brand.accent)
        if len(lines) > 1:
            self.words(cv, lines[1], 470, 96, te - 0.3 - tm.beat)
        b = eback((te - 2 * tm.beat) / 0.4, 2.0)
        if b > 0 and c.get("button"):
            pulse = 1 + 0.035 * math.sin(max(0, te - 1.5) * math.pi * 4) * (te > 1.5)
            bw, bh = 820 * b * pulse, 170 * b * pulse
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
            d.rounded_rectangle([W / 2 - bw / 2, 1360 - bh / 2 + 10, W / 2 + bw / 2, 1360 + bh / 2 + 10], int(bh / 2),
                                fill=tuple(int(v * 0.4) for v in self.brand.ink) + (80,))
            d.rounded_rectangle([W / 2 - bw / 2, 1360 - bh / 2, W / 2 + bw / 2, 1360 + bh / 2], int(bh / 2),
                                fill=self.brand.ink + (255,))
            if b > 0.5:
                fs = self.fit(c["button"], int(76 * min(1.0, b) * pulse), margin=W - 700)
                d.text((W / 2, 1360), c["button"], font=self.brand.font("U", fs), fill=self.brand.accent + (255,), anchor="mm")
            cv.paste(lay, (0, 0), lay)
        self.chip(cv, c.get("chip"), W / 2, 1530, 42, t_in=te - 4 * tm.beat, face="Os")
        return cv

    def frame(self, i: int) -> Image.Image:
        t = i / self.fps
        tm = self.tm
        if t < tm.t_grow:
            im = self.hook(t)
        elif t < tm.t_real:
            im = self.grow(t)
        elif t < tm.t_cta:
            im = self.real(t)
        else:
            im = self.cta(t)
        return self._out(im)

    def _out(self, im):
        return im if im.size == self.out_size else im.resize(self.out_size, Image.LANCZOS)

    @property
    def nframes(self) -> int:
        return int(round(self.tm.t_end * self.fps))

    # ------------------------------------------------ stills for upload
    def shorts_cover(self) -> Image.Image:
        """The hook with every word in, no flash: the Shorts cover."""
        return self._out(self.hook(min(self.tm.hook - 0.05, len(self.sb["hook"]["lines"]) * self.tm.beat + 0.6)))

    def thumbnail(self, w=1280, h=720) -> Image.Image:
        """YouTube thumbnail: the name left in big type, the toy right, the pill under the name."""
        g0, g1 = self.brand.ground
        cv = Image.new("RGB", (w, h)); d = ImageDraw.Draw(cv)
        for x in range(w):
            u = x / w
            d.line((x, 0, x, h), fill=tuple(int(lerp(g1[i], g0[i], u)) for i in range(3)))
        src = self.photo_real or self.photo_hook or self.finished()
        s = h / src.height * 1.0
        toy = src.resize((max(1, int(src.width * s)), h), Image.LANCZOS)
        if toy.width > int(w * 0.56):
            x0 = (toy.width - int(w * 0.56)) // 2
            toy = toy.crop((x0, 0, x0 + int(w * 0.56), h))
        mask = Image.new("L", toy.size, 255)
        md = ImageDraw.Draw(mask)
        for x in range(60):
            md.line((x, 0, x, h), fill=int(255 * x / 60))
        cv.paste(toy, (w - toy.width, 0), mask)
        cv = cv.convert("RGBA")
        lines = [l.upper() for l in self.sb["thumbnail"]["lines"]][:3]
        y = 100 if len(lines) > 2 else 150
        maxw = int(w * 0.5)
        for i, ln in enumerate(lines):
            size = 110
            f = self.brand.font("U", size)
            while f.getlength(ln) > maxw and size > 40:
                size -= 4; f = self.brand.font("U", size)
            im = self.text_img(ln, size, self.brand.accent if i < len(lines) - 1 or len(lines) == 1 else self.brand.text)
            cv.alpha_composite(im, (40, y))
            y += int(size * 1.08)
        pill = self.sb["thumbnail"].get("pill")
        if pill:
            f = self.brand.font("O", 40); tw = f.getlength(pill)
            d = ImageDraw.Draw(cv)
            y = max(y + 20, 520)
            d.rounded_rectangle((56, y, 56 + tw + 80, y + 84), 42, fill=self.brand.ink + (255,))
            d.text((96, y + 42), pill, font=f, fill=self.brand.accent + (255,), anchor="lm")
        return cv.convert("RGB")

    def sheet(self, times: list[float], cols: int = 10, tile=(200, 356)) -> Image.Image:
        """Frame sheet for QA: a tile every few seconds, two rows."""
        ims = [self.frame(int(round(t * self.fps))).resize(tile, Image.LANCZOS) for t in times]
        rows = math.ceil(len(ims) / cols)
        sh = Image.new("RGB", (tile[0] * min(cols, len(ims)), tile[1] * rows), (255, 255, 255))
        for k, im in enumerate(ims):
            sh.paste(im, (tile[0] * (k % cols), tile[1] * (k // cols)))
        return sh
