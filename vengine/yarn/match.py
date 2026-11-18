"""Find the angle of the toy's studio photo, so the growth shot can end exactly on it.

    python -m vengine yarn match SPEC.json PHOTO [--out match.json] [--fov 18] [--az 32 --el 12] [--sheet look.jpg]

The studio photo on the site is an AI edit of the site's 3D render: shape, pose and angle are the model's, only the
material, light and backdrop change.  So the yarn toy, seen from the right azimuth and elevation through a long lens,
has the photo's silhouette.  This module:

* cuts the toy out of a photo on a seamless backdrop (`toy_mask`): the backdrop is a smooth gradient fitted from the
  border, the toy is what differs from it in colour or texture, the soft contact shadow is recognised and left out;
* aligns two silhouettes with a similarity (scale + shift, `align`) and scores them by IoU;
* searches azimuth and elevation (`fit_view`) for the best IoU, coarse grid then finer steps around the best.

The result (az, el, fov, iou and the photo's backdrop colours) goes to match.json; `vengine yarn grow --view
match.json` ends its final turn in that view and records it in plan.json, and the build compositor dissolves the
last knit frame into the photo aligned by the same `align` (vengine/build/comp.py).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

WORK = 360                                   # working size of the silhouettes (pixels, longer side)


# --------------------------------------------------------------------------------------------- silhouettes
def _backdrop(im: np.ndarray, border: int) -> np.ndarray:
    """The smooth backdrop under the whole image, fitted (cubic in x, y) to a border strip."""
    H, W = im.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    u, v = xx / W, yy / H
    b = np.zeros((H, W), bool)
    b[:border] = b[-border:] = True
    b[:, :border] = b[:, -border:] = True
    A = np.stack([np.ones_like(u), u, v, u * u, u * v, v * v, v ** 3, u * v * v, u * u * v], -1)
    coef, *_ = np.linalg.lstsq(A[b], im[b], rcond=None)
    return A @ coef


def toy_mask(img, work: int = WORK) -> np.ndarray:
    """Boolean silhouette of the toy in an RGB image on a seamless backdrop, at `work` px on the longer side.

    A pixel is toy when it is brighter than the backdrop, has a different hue (the backdrop's colour scaled, as a
    shadow is, does not count), or has texture.  The largest blob is kept and its holes are filled."""
    from PIL import Image
    from scipy import ndimage as nd
    im = img if isinstance(img, Image.Image) else Image.fromarray(np.asarray(img, np.uint8))
    im = im.convert('RGB')
    s = work / max(im.size)
    im = np.asarray(im.resize((max(8, round(im.width * s)), max(8, round(im.height * s))), Image.LANCZOS), float)
    bg = _backdrop(im, max(3, work // 30))
    r = im / np.maximum(bg, 1.0)
    rl = r.mean(-1, keepdims=True)
    chrom = np.abs(r / np.maximum(rl, 1e-3) - 1).max(-1) * 255
    bright = (rl[..., 0] - 1) * 255
    lum = im @ [0.3, 0.59, 0.11]
    k = 5
    m1 = nd.uniform_filter(lum, k)
    sd = np.sqrt(np.maximum(nd.uniform_filter(lum * lum, k) - m1 * m1, 0))
    # a shadow on the backdrop: darker, the backdrop's own warm hue a little deepened (r >= g >= b ratios), smooth
    shadow = (bright < 0) & (bright > -100) & (r[..., 0] >= r[..., 1] - 0.01) & (r[..., 1] >= r[..., 2] - 0.01) \
        & (chrom < 60)
    mask = (bright > 8) | (((chrom > 10) | (sd > 4)) & ~shadow) | (sd > 12)
    mask = nd.binary_opening(mask, iterations=1)
    lab, n = nd.label(mask)
    if n == 0:
        return mask
    mask = lab == (1 + int(np.argmax(nd.sum(mask, lab, range(1, n + 1)))))
    mask = nd.binary_closing(mask, iterations=3)
    return nd.binary_fill_holes(mask)


def _moments(m):
    ys, xs = np.nonzero(m)
    return float(xs.mean()), float(ys.mean()), float(len(xs))


def iou(a, b) -> float:
    u = np.logical_or(a, b).sum()
    return float(np.logical_and(a, b).sum() / u) if u else 0.0


def warp(m, s, tx, ty, shape):
    """Mask m moved into an image of `shape` so that a point p of m lands on s * p + (tx, ty) (x, y pixels)."""
    from scipy import ndimage as nd
    # output (y, x) samples input at ((y - ty) / s, (x - tx) / s)
    return nd.affine_transform(m.astype(np.float32), [1 / s, 1 / s], offset=[-ty / s, -tx / s], output_shape=shape,
                               order=1) > 0.5


def align(src, dst, steps=(0.04, 0.02, 0.01)) -> dict:
    """Similarity (scale s, shift tx, ty in dst pixels) that lays silhouette `src` over `dst`, best IoU.

    Starts from the centroids and the area ratio, then a small coordinate search on s, tx, ty."""
    cx0, cy0, a0 = _moments(src)
    cx1, cy1, a1 = _moments(dst)
    s = math.sqrt(a1 / max(a0, 1.0))
    p = [s, cx1 - s * cx0, cy1 - s * cy0]
    best = iou(warp(src, *p, dst.shape), dst)
    span = max(dst.shape)
    for st in steps:
        moved = True
        while moved:
            moved = False
            for i, d in ((0, st), (0, -st), (1, st * span), (1, -st * span), (2, st * span), (2, -st * span)):
                q = list(p)
                if i == 0:                                  # scale about the dst centroid of the current fit
                    k = (p[0] + d) / p[0]
                    q = [p[0] + d, cx1 + (p[1] - cx1) * k, cy1 + (p[2] - cy1) * k]
                else:
                    q[i] += d
                v = iou(warp(src, *q, dst.shape), dst)
                if v > best + 1e-5:
                    best, p, moved = v, q, True
    return dict(s=p[0], tx=p[1], ty=p[2], iou=best)


def backdrop_colours(img) -> tuple[list[float], list[float]]:
    """Mean colour (sRGB 0..1) of the top and the bottom 6% rows of a photo: the backdrop and the surface."""
    a = np.asarray(img.convert('RGB'), float) / 255
    n = max(1, a.shape[0] * 6 // 100)
    return a[:n].reshape(-1, 3).mean(0).round(4).tolist(), a[-n:].reshape(-1, 3).mean(0).round(4).tolist()


# --------------------------------------------------------------------------------------------- the view search
class Viewer:
    """Silhouettes of the finished yarn toy from any view (a small Grow, no motion blur, one sample per pixel)."""

    def __init__(self, spec, size: int = WORK):
        from .grow import Grow
        self.g = Grow(spec, (size, size), ss=1, mblur=1, floor=0.0)
        X = self.g.X
        lo, hi = X.min(0), X.max(0)
        self.c, self.R = (lo + hi) / 2, float(np.linalg.norm(hi - lo) / 2)
        self.size = size

    def camera(self, az, el, fov):
        from .render import Camera
        a, e = math.radians(az), math.radians(el)
        d = np.array([math.sin(a) * math.cos(e), math.sin(e), math.cos(a) * math.cos(e)])
        dist = self.R / math.tan(math.radians(fov) / 2) / 0.8
        return Camera(self.c + d * dist, self.c, fov=fov)

    def image(self, az, el, fov):
        g = self.g
        cam = self.camera(az, el, fov)
        g.cam_at = lambda k: cam
        return g._draw(g.NF / 30.0)

    def mask(self, az, el, fov):
        self.image(az, el, fov)
        return self.g.rn.idb > 0


def fit_view(spec, photo, az0=32.0, el0=12.0, fov=18.0, size=WORK, log=None) -> dict:
    """Azimuth and elevation whose silhouette best matches the photo's (IoU after a similarity fit)."""
    from PIL import Image
    ph = Image.open(photo).convert('RGB') if not hasattr(photo, 'convert') else photo
    target = toy_mask(ph, size)
    v = Viewer(spec, size)
    seen = {}

    def score(az, el):
        k = (round(az, 2), round(el, 2))
        if k not in seen:
            seen[k] = align(v.mask(az, el, fov), target, steps=(0.03, 0.01))['iou']
            if log:
                log(f'az {az:6.1f} el {el:5.1f}  iou {seen[k]:.4f}')
        return seen[k]

    grid = [(az0 + da, el0 + de) for da in range(-24, 25, 8) for de in (-8, 0, 8)]
    az, el = max(grid, key=lambda p: score(*p))
    for st in (4.0, 2.0, 1.0):
        moved = True
        while moved:
            moved = False
            for da, de in ((st, 0), (-st, 0), (0, st), (0, -st)):
                if score(az + da, el + de) > score(az, el) + 1e-5:
                    az, el, moved = az + da, el + de, True
    m = v.mask(az, el, fov)
    fit = align(m, target)
    top, bot = backdrop_colours(ph)
    return dict(az=float(az), el=float(el), fov=float(fov), iou=round(fit['iou'], 4), bg_top=top, bg_bot=bot,
                tried=len(seen), _render=v.image(az, el, fov), _mask=m, _target=target, _fit=fit)


def overlay(render_mask, target, fit) -> 'Image.Image':
    """Look check: photo silhouette in blue, the fitted render silhouette in red, overlap in purple."""
    from PIL import Image
    w = warp(render_mask, fit['s'], fit['tx'], fit['ty'], target.shape)
    im = np.full(target.shape + (3,), 255, np.uint8)
    im[target] = (120, 150, 255)
    im[w] = (255, 120, 120)
    im[w & target] = (150, 90, 170)
    return Image.fromarray(im)


def main(argv=None):
    ap = argparse.ArgumentParser(prog='vengine yarn match', description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('spec'); ap.add_argument('photo')
    ap.add_argument('--out', help='match.json (default: next to the photo)')
    ap.add_argument('--fov', type=float, default=18.0); ap.add_argument('--az', type=float, default=32.0)
    ap.add_argument('--el', type=float, default=12.0); ap.add_argument('--size', type=int, default=WORK)
    ap.add_argument('--sheet', help='write a look-check image: photo | render | silhouettes')
    a = ap.parse_args(argv)
    from PIL import Image
    ph = Image.open(a.photo).convert('RGB')
    r = fit_view(json.loads(Path(a.spec).read_text()), ph, a.az, a.el, a.fov, a.size,
                 log=lambda s: print(s, file=sys.stderr))
    out = Path(a.out) if a.out else Path(a.photo).with_name('match.json')
    res = {k: v for k, v in r.items() if not k.startswith('_')}
    res['photo'] = str(a.photo)
    out.write_text(json.dumps(res, indent=1))
    if a.sheet:
        n = a.size
        p = ph.resize((round(ph.width * n / max(ph.size)), round(ph.height * n / max(ph.size))), Image.LANCZOS)
        sh = Image.new('RGB', (3 * n + 20, n), (255, 255, 255))
        sh.paste(p, (0, 0)); sh.paste(Image.fromarray(r['_render']), (n + 10, 0))
        sh.paste(overlay(r['_mask'], r['_target'], r['_fit']), (2 * n + 20, 0))
        sh.save(a.sheet, quality=90)
    print(json.dumps(res))
    return 0


if __name__ == '__main__':
    sys.exit(main())
