"""Frame-to-frame stability probe: how much a picture changes that should not.

    python -m vengine yarn probe SPEC.json OUTDIR [--size 540x960]

Three checks on a toy:
  grow   the camera stands still, the yarn grows: away from the new yarn nothing may change;
  orbit  the camera turns by 0.05 deg per frame (a fifth of a pixel): the picture must change smoothly, so the second
         difference of three frames, |b - (a + c) / 2|, measures noise, popping edges and crawling texture;
  far    the same with the whole toy small in frame (texture finer than a pixel: moire).
Numbers are mean absolute levels (0..255) and are written to OUTDIR/stable.json with heat maps of the orbit check.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path

import numpy as np


def second_diff(frames):
    A = [np.asarray(f, np.float32) for f in frames]
    return float(np.mean([np.abs(A[i] - (A[i - 1] + A[i + 1]) / 2).mean() for i in range(1, len(A) - 1)]))


def probe(spec, out, size=(540, 960), step=0.05, n=20000):
    from PIL import Image
    from .render import Camera, Renderer
    from .toy import toy_yarn
    X, D, C, pal, d, toy = toy_yarn(spec)
    W, H = size
    rn = Renderer(W, H, ss=2, r=d / 2 / 1.2, h=0.5, soft=1.2, palette=pal)
    rn.set_scene(X)
    p = toy.yarn_pieces[0]
    Xi = X[:p['end']]
    lo, hi = Xi.min(0), Xi.max(0)
    g = (lo + hi) / 2
    R = np.linalg.norm(hi - lo) / 2

    def cam(az, zoom=1.0, tg=g):
        az, el = math.radians(az), math.radians(20)
        e = np.array([math.sin(az) * math.cos(el), math.sin(el), math.cos(az) * math.cos(el)])
        return Camera(tg + e * R * 3.1 * zoom, tg, up=(0, 1, 0), fov=30)

    def shot(m, c):
        return rn.render(X[:m], D[:m], c, colnode=C[:m])

    os.makedirs(out, exist_ok=True)
    n = min(n, p['end'] - 600)
    grow = [shot(n + 150 * k, cam(30)) for k in range(3)]
    orbit = [shot(n, cam(30 + step * k, tg=g + np.array([0.08, 0.06, 0.0]) * step * k)) for k in range(6)]
    gall = (X.min(0) + X.max(0)) / 2
    far = [shot(p['end'], cam(30 + step * k, zoom=2.2, tg=gall)) for k in range(4)]
    res = dict(grow=second_diff(grow), orbit=second_diff(orbit), far=second_diff(far),
               orbit_motion=float(np.mean([np.abs(orbit[i + 1].astype(np.float32) - orbit[i]).mean() for i in range(5)])))
    for name, fr in (('orbit', orbit), ('far', far)):
        A = [f.astype(np.float32) for f in fr]
        hmap = np.abs(A[2] - (A[1] + A[3]) / 2).mean(2)
        Image.fromarray(np.clip(hmap * 10, 0, 255).astype(np.uint8)).save(os.path.join(out, f'{name}_heat.png'))
        Image.fromarray(fr[2]).save(os.path.join(out, f'{name}.png'))
    Path(out, 'stable.json').write_text(json.dumps(res, indent=2))
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(prog='vengine yarn probe', description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('spec'); ap.add_argument('out'); ap.add_argument('--size', default='540x960')
    ap.add_argument('--step', type=float, default=0.05)
    a = ap.parse_args(argv)
    W, H = [int(v) for v in a.size.split('x')]
    print(json.dumps(probe(json.loads(Path(a.spec).read_text()), a.out, (W, H), a.step), indent=2))
    return 0
