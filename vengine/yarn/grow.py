"""A toy crocheted stitch by stitch as yarn, on an accelerating clock, with a moving camera (the growth shot).

    python -m vengine yarn grow SPEC.json OUTDIR [--size 1080x1920] [--dur 16] [--reveal 3.5] [--frames a:b | --part i/n]
    python -m vengine yarn grow SPEC.json OUTDIR --still 2,8,15,18     (a strip of frames: OUTDIR/still.jpg)

Writes OUTDIR/%04d.png and OUTDIR/plan.json (per frame: t, n, piece, name, pi, round, rounds, st, count, face, s; and
the pieces), the format the montage reads for captions and sound.  Frames that already exist are skipped, so a killed
render continues where it stopped; several processes may render different --frames ranges into one folder.

What makes it pleasant to watch (and is the difference from the first version, yg4.py):
* the yarn grows continuously: the newest few millimetres taper in from nothing instead of whole nodes popping in;
* the camera target and distance are smoothed with a Gaussian (no lag-and-catch-up), the turn speeds up gently and
  the final reveal continues the same turn and settles facing the viewer, with no jump in speed;
* frames where the picture moves fast are rendered as several sub-frames and averaged (motion blur), so stitches do
  not strobe when the toy spins;
* the renderer itself is temporally stable (see render.py), so the montage needs no frame blending.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

FPS = 30


def _smoothstep(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def _gauss_smooth(a, sigma):
    """Zero-phase Gaussian smoothing of a per-frame series along axis 0 (edges held)."""
    if sigma <= 0:
        return a
    from scipy.ndimage import gaussian_filter1d
    return gaussian_filter1d(np.asarray(a, float), sigma, axis=0, mode='nearest')


def brighten(c, amount):
    import colorsys
    h, l, s = colorsys.rgb_to_hls(*c)
    l2 = l + (1 - l) * (amount - 1) * 0.9 if 0.22 < l < 0.92 else l
    return list(colorsys.hls_to_rgb(h, min(0.95, l2), min(1, s * 1.12)))


class Grow:
    def __init__(self, spec, size=(1080, 1920), dur=16.0, reveal=3.5, ss=3, soft=1.2, core=0.3, core_shade=0.55,
                 bright=1.12, mblur=4, turn=250.0, max_px=6.0):
        from .render import Renderer
        from .toy import toy_yarn
        self.W, self.H = size
        self.turn, self.max_px = float(turn), float(max_px)
        self.dur, self.reveal, self.mblur = float(dur), float(reveal), int(mblur)
        X, D, C, pal, d, toy = toy_yarn(spec)
        self.X, self.D, self.C, self.d, self.toy = X, D, C, d, toy
        self.pieces = toy.yarn_pieces
        self.NY = self.pieces[-1]['end']                       # yarn of the pieces; the nodes after it are the face
        pal2 = [brighten(c, bright) for c in pal]
        self.NP = len(pal2)
        pal2 = pal2 + [[v * core_shade for v in p] for p in pal2]
        # a hidden core: the same yarn pushed inwards, a shade darker, so the backdrop does not shine through between
        # stitches (bright specks there are the worst flicker of all: they are the highest-contrast edges)
        self.core = []
        if core > 0:
            for p in self.pieces:
                if p['part'] in ('cheek',):
                    continue
                seg = X[p['start']:p['end']]
                c = seg.mean(0)
                nrm = seg - c
                nrm /= np.linalg.norm(nrm, axis=1)[:, None] + 1e-9
                self.core.append((p['start'], p['end'], seg - nrm * core * d))
        r = d / 2 / soft
        self.taper = max(4, int(round(2.0 * d / 0.5)))         # nodes over which the growing tip swells to full size
        self.rn = Renderer(self.W, self.H, ss=ss, r=r, h=0.5, soft=soft, palette=pal2)
        scene = [X] + [Xc for _, _, Xc in self.core]
        self.core_off = np.cumsum([len(X)] + [len(Xc) for _, _, Xc in self.core])[:-1]
        self.rn.set_scene(np.concatenate(scene))
        self.spheres = np.asarray(getattr(toy, 'spheres', np.zeros((0, 5))), float).reshape(-1, 5)
        self.NB = int(round(self.dur * FPS))
        self.NF = int(round((self.dur + self.reveal) * FPS))
        self._plan()
        self._camera()

    # --------------------------------------------------------------------------------------------- the clock
    def prog(self, t):
        """Fraction of all yarn made at film time t: slow first (after round 3 of the first piece), then faster."""
        x = t / self.dur
        p0 = self.pieces[0]
        s0 = (sum(p0['counts'][:3]) / sum(p0['counts'])) * (p0['end'] - p0['start']) / self.NY
        return s0 + (1 - s0) * (min(1.0, 0.06 * x + 0.94 * x ** 2.2) if x < 0.94 else 1.0)

    def face_at(self, t):
        return _smoothstep((t / self.dur - 0.88) / 0.1)

    def _plan(self):
        plan = []
        for i in range(self.NF):
            t = i / FPS
            s = self.prog(t)
            n = int(s * self.NY)
            pi = next((k for k, p in enumerate(self.pieces) if n < p['end']), len(self.pieces) - 1)
            p = self.pieces[pi]
            fr = (n - p['start']) / max(1, p['end'] - p['start'])
            cnt = p['counts']
            q = fr * sum(cnt)
            cum = np.concatenate([[0], np.cumsum(cnt)])
            rnd = int(np.clip(np.searchsorted(cum, q, side='right'), 1, len(cnt)))
            plan.append(dict(t=t, n=n, piece=p['part'], name=p['name'], pi=pi, round=rnd, rounds=len(cnt), st=float(q),
                             count=int(cnt[rnd - 1]), face=self.face_at(t), s=s))
        self.plan = plan

    # --------------------------------------------------------------------------------------------- the camera
    def _camera(self):
        X = self.X
        lo_all, hi_all = X.min(0), X.max(0)
        gall = (lo_all + hi_all) / 2
        Rall = float(np.linalg.norm(hi_all - lo_all) / 2)
        tg, rad = [], []
        for f in self.plan:
            # frame the yarn being worked, but never much tighter than all that is made so far: a new small piece
            # (an ear) must not make the camera swoop in on it and back out
            p = self.pieces[f['pi']]
            Xi = X[max(p['start'], f['n'] - 4000):max(p['start'] + 50, f['n'])]
            lo, hi = Xi.min(0), Xi.max(0)
            Xm = X[:max(50, f['n']):7]
            lom, him = Xm.min(0), Xm.max(0)
            rr, rm = float(np.linalg.norm(hi - lo) / 2), float(np.linalg.norm(him - lom) / 2)
            w = 0.0 if f['pi'] == 0 else 0.45
            tg.append((lo + hi) / 2 * (1 - w) + (lom + him) / 2 * w)
            rad.append(max(16.0, rr, 0.8 * rm))
        tg = _gauss_smooth(np.array(tg), 0.8 * FPS)
        rad = _gauss_smooth(np.array(rad), 0.8 * FPS)
        for k, f in enumerate(self.plan):                   # the last part of the build pulls back to the whole toy
            w = _smoothstep((f['t'] / self.dur - 0.7) / 0.25)
            tg[k] = tg[k] * (1 - w) + gall * w
            rad[k] = rad[k] * (1 - w) + Rall * w
        self.tg, self.rad = tg, rad
        self.el = np.array([48.0 - 36.0 * _smoothstep(min(1.0, f['t'] / self.dur) / 0.65) for f in self.plan])
        # the turn.  The wanted speed rises gently from v0 to v1 deg/s during the build, but it is capped so that the
        # yarn never slides more than `max_px` pixels a frame on screen (a close-up of a big piece turning at the same
        # angular speed as a small one slides much faster); the cap is smoothed so the speed has no corners.
        # The reveal then keeps turning at the speed it has and settles, at rest, facing the viewer.
        v0, v1 = 6.0, 2.0 * self.turn / self.dur - 6.0
        want = np.array([(v0 + (v1 - v0) * _smoothstep(min(k / FPS, self.dur) / self.dur)) / FPS for k in range(self.NF)])
        cap = np.empty(self.NF)
        a = 25.0
        for k in range(self.NF):
            if k > self.NB:
                cap[k] = want[k]
                continue
            pts = self._pts(k)
            c0 = self._cam(a, self.el[k], self.tg[k], self.rad[k])
            c1 = self._cam(a + 1.0, self.el[k], self.tg[k], self.rad[k])
            k1 = min(k + 1, self.NF - 1)
            c2 = self._cam(a, self.el[k1], self.tg[k1], self.rad[k1])
            p0 = self._project(c0, pts)
            per_deg = np.percentile(np.linalg.norm(self._project(c1, pts) - p0, axis=1), 90)
            trans = np.percentile(np.linalg.norm(self._project(c2, pts) - p0, axis=1), 90)
            cap[k] = max(0.15 * want[k], (self.max_px - trans) / max(per_deg, 1e-6))
            a += min(want[k], cap[k])
        step = _gauss_smooth(np.minimum(want, cap), 0.5 * FPS)
        self.az = np.zeros(self.NF)
        self.az[0] = 25.0
        for k in range(1, self.NB + 1):
            self.az[k] = self.az[k - 1] + step[k - 1]
        a_end, v_end, L = self.az[self.NB], step[self.NB - 1] * FPS, max(1, self.NF - 1 - self.NB) / FPS
        target = 360.0 * math.ceil((a_end + v_end * L / 3.0) / 360.0)   # the nearest front that needs no reversing
        for k in range(self.NB + 1, self.NF):                # cubic Hermite: starts at speed v_end, ends at rest
            u = min(1.0, (k - self.NB) / max(1, self.NF - 1 - self.NB))
            h10 = u ** 3 - 2 * u ** 2 + u
            h01 = -2 * u ** 3 + 3 * u ** 2
            self.az[k] = a_end + h10 * v_end * L + h01 * (target - a_end)

    def _pts(self, k, m=1500):
        """A fixed sample of the yarn made by frame k (for screen-motion estimates)."""
        n = max(30, min(self.NY, self.plan[k]['n']))
        return self.X[np.linspace(0, n - 1, min(m, n)).astype(int)]

    def _cam(self, az, el, tg, rad):
        from .render import Camera
        az, el = math.radians(az), math.radians(el)
        e = np.array([math.sin(az) * math.cos(el), math.sin(el), math.cos(az) * math.cos(el)])
        dist = rad * (3.1 if self.H > self.W else 2.6)
        return Camera(tg + e * dist, tg, up=(0, 1, 0), fov=30)

    def _project(self, cam, pts):
        B = cam.basis()
        v = (pts - cam.pos) @ B.T
        fpx = 0.5 * self.W / math.tan(math.radians(cam.fov) / 2)
        z = np.maximum(v[:, 2], 1e-3)
        return np.stack([fpx * v[:, 0] / z, fpx * v[:, 1] / z], 1)

    def cam_at(self, k):
        """Camera at a (fractional) frame position k."""
        k0 = int(np.clip(math.floor(k), 0, self.NF - 1))
        k1 = min(k0 + 1, self.NF - 1)
        u = float(np.clip(k - k0, 0.0, 1.0))
        lerp = lambda a: a[k0] * (1 - u) + a[k1] * u
        return self._cam(lerp(self.az), lerp(self.el), lerp(self.tg), lerp(self.rad))

    # --------------------------------------------------------------------------------------------- one frame
    def _draw(self, t):
        """Render the toy as it is at film time t (seconds, may fall between frames)."""
        X, D, C, NY = self.X, self.D, self.C, self.NY
        nf = self.prog(t) * NY
        face = self.face_at(t)
        n = min(NY, int(math.ceil(nf)) + 1)
        n = max(n, 30)
        idx = [np.arange(n)]
        rs = [np.clip((nf - np.arange(n)) / self.taper, 0.0, 1.0) ** 0.5]
        nface = len(X) - NY
        if face > 0 and nface > 0:
            ff = face * nface
            m = min(nface, int(math.ceil(ff)) + 1)
            idx.append(NY + np.arange(m))
            rs.append(np.clip((ff - np.arange(m)) / self.taper, 0.0, 1.0) ** 0.5)
        Xs = [X[i] for i in idx]
        Ds = [D[i] for i in idx]
        Cs = [C[i] for i in idx]
        sh = list(idx)
        for (s0, s1, Xc), off in zip(self.core, self.core_off):
            m = min(n, s1) - s0
            if m > 20:
                Xs.append(Xc[:m]); Ds.append(D[s0:s0 + m]); Cs.append(C[s0:s0 + m] + self.NP)
                rs.append(np.clip((nf - (s0 + np.arange(m))) / self.taper, 0.0, 1.0) ** 0.5)
                sh.append(off + np.arange(m))
        # pieces are separate chains: a gap between them is longer than `gap` and is not drawn
        sp = self.spheres.copy()
        if len(sp):
            sp[:, 3] *= _smoothstep((face - 0.35) / 0.4)
        k = t * FPS
        return self.rn.render(np.concatenate(Xs), np.concatenate(Ds), self.cam_at(k), colnode=np.concatenate(Cs),
                              radius=np.concatenate(rs), spheres=sp, gap=2.0, shape_idx=np.concatenate(sh))

    def motion_px(self, k):
        """How far the yarn slides on screen over one frame (90th percentile, pixels)."""
        k = int(np.clip(k, 0, self.NF - 2))
        pts = self._pts(k, 800)
        return float(np.percentile(np.linalg.norm(self._project(self.cam_at(k + 1), pts)
                                                  - self._project(self.cam_at(k), pts), axis=1), 90))

    def frame(self, k):
        """Frame k, with motion blur: sub-frames over half a frame (a 180 degree shutter) when the picture moves."""
        nsub = 1
        if self.mblur > 1:
            nsub = int(np.clip(math.ceil(self.motion_px(k) / 2.0), 1, self.mblur))
        if nsub == 1:
            return self._draw(k / FPS)
        acc = None
        for j in range(nsub):
            tk = (k + ((j + 0.5) / nsub - 0.5) * 0.5) / FPS
            im = self._draw(max(0.0, tk)).astype(np.float32)
            acc = im if acc is None else acc + im
        return np.clip(acc / nsub + 0.5, 0, 255).astype(np.uint8)


def _atomic_json(obj, path):
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, 'w') as fh:
        json.dump(obj, fh)
    os.replace(tmp, path)


def main(argv=None):
    ap = argparse.ArgumentParser(prog='vengine yarn grow', description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('spec'); ap.add_argument('out')
    ap.add_argument('--size', default='1080x1920'); ap.add_argument('--dur', type=float, default=16.0)
    ap.add_argument('--reveal', type=float, default=3.5); ap.add_argument('--ss', type=int, default=3)
    ap.add_argument('--frames', help='a:b, frame range'); ap.add_argument('--part', default='0/1', help='i/n of all frames')
    ap.add_argument('--still', help='comma separated times in seconds: write OUT/still.jpg')
    ap.add_argument('--core', type=float, default=0.3); ap.add_argument('--soft', type=float, default=1.2)
    ap.add_argument('--bright', type=float, default=1.12); ap.add_argument('--mblur', type=int, default=4)
    a = ap.parse_args(argv)
    from PIL import Image
    W, H = [int(v) for v in a.size.split('x')]
    g = Grow(json.loads(Path(a.spec).read_text()), (W, H), a.dur, a.reveal, ss=a.ss, soft=a.soft, core=a.core,
             bright=a.bright, mblur=a.mblur)
    os.makedirs(a.out, exist_ok=True)
    _atomic_json(dict(plan=g.plan, pieces=[dict(p) for p in g.pieces], fps=FPS, size=[W, H], dur=a.dur,
                      reveal=a.reveal, renderer='yarn'), os.path.join(a.out, 'plan.json'))
    if a.still:
        ims = [Image.fromarray(g.frame(int(round(float(t) * FPS)))).resize((W // 3, H // 3), Image.LANCZOS)
               for t in a.still.split(',')]
        sh = Image.new('RGB', (W // 3 * len(ims), H // 3))
        for j, im in enumerate(ims):
            sh.paste(im, (j * W // 3, 0))
        sh.save(os.path.join(a.out, 'still.jpg'), quality=92)
        return 0
    if a.frames:
        f0, f1 = [int(v) for v in a.frames.split(':')]
    else:
        pi, pn = [int(v) for v in a.part.split('/')]
        f0, f1 = g.NF * pi // pn, g.NF * (pi + 1) // pn
    for k in range(max(0, f0), min(g.NF, f1)):
        fn = os.path.join(a.out, '%04d.png' % k)
        if os.path.exists(fn):
            continue
        tmp = fn + '.tmp.png'
        Image.fromarray(g.frame(k)).save(tmp)
        os.replace(tmp, fn)
    return 0


if __name__ == '__main__':
    sys.exit(main())
