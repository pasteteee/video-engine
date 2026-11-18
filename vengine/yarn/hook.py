"""A crochet hook that works the yarn in the growth shot (the "made with a hook" look).

The hook is drawn as a few capsules (renderer idents 5 metal, 6 matte): a rounded head with a throat, a polished
shaft, a tapered neck and a soft grip.  The working strand runs from the stitch on the hook over the throat, along the
shaft and out of the frame, as a crocheter holds it.

Where the hook is: while the toy grows slowly the hook tip sits on the newest stitch and follows it round the piece.
When the rounds go by faster than the eye can follow (more than ~10 degrees a frame), a hook chasing the tip would
spin; a real crocheter turns the piece instead and keeps the hook still.  So the hook then holds on the rim of the
round being made, on the side facing the camera, and keeps dipping in at a steady stitch rhythm while the yarn grows
round under it (a time-lapse).  Moving to the next piece, it lifts away from the toy and comes down on the new piece.
It slides in at the start and leaves before the face appears.

Everything is precomputed per frame and smoothed with a Gaussian, so the hook never jitters between frames.
"""
from __future__ import annotations

import math

import numpy as np

# hook in millimetres (the yarn spec is in millimetres too); the head and shaft scale with the pattern's hook size
GRIP_R = 4.4
METAL = (0.28, 0.45, 0.86)       # blue anodised aluminium, reads against any yarn and the cream set
GRIP = (0.93, 0.90, 0.84)        # cream soft grip


def _smoothstep(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def _unit(v):
    v = np.asarray(v, float)
    return v / (np.linalg.norm(v, axis=-1, keepdims=True) + 1e-12)


def _gauss(a, sigma):
    if sigma <= 0:
        return np.asarray(a, float)
    from scipy.ndimage import gaussian_filter1d
    return gaussian_filter1d(np.asarray(a, float), sigma, axis=0, mode='nearest')


class HookRig:
    """Per-frame pose of the hook for a `grow.Grow`; `capsules(t, colour_index)` gives the rows for the renderer.

    pal0: the palette index where the two hook colours are (the Grow appends them to its palette)."""

    def __init__(self, g, pal0, hook_mm=4.0, enter=0.35, leave=(0.95, 1.02), follow=(9.0, 16.0), rate=2.2):
        self.g, self.pal0 = g, int(pal0)
        self.sc = float(hook_mm) / 4.0          # the head below is drawn for a 4 mm hook
        X, FPS = g.X, 30
        NF, NB = g.NF, g.NB
        self.fps = FPS
        tip = np.zeros((NF, 3)); front = np.zeros((NF, 3)); otip = np.zeros((NF, 3)); ofr = np.zeros((NF, 3))
        cols = np.zeros(NF, int)
        right = np.zeros((NF, 3)); up = np.zeros((NF, 3)); fwd = np.zeros((NF, 3))
        pis = np.zeros(NF, int)
        for k, f in enumerate(g.plan):
            cam = g.cam_at(k)
            Bm = cam.basis()
            right[k], up[k], fwd[k] = Bm[0], Bm[1], Bm[2]
            pi = f['pi']
            p = g.pieces[pi]
            pis[k] = pi
            n = int(np.clip(f['n'], p['start'] + 2, p['end'] - 1))
            nps = (p['end'] - p['start']) / max(1, sum(p['counts']))           # yarn nodes per stitch
            L = int(max(12, min(n - p['start'], f['count'] * nps)))           # the round being made
            seg = X[n - L:n + 1]
            ctr = seg.mean(0)
            # a round that is still tiny (the magic ring) has no clear centre: use the whole piece made so far
            if np.linalg.norm(seg - ctr, axis=1).mean() < 3.0:
                ctr = X[p['start']:n + 1].mean(0)
            out = _unit(seg - ctr)
            tip[k], otip[k] = seg[-1], out[-1]
            # the front of the rim: facing the camera and a little to its right (the hook comes in from the right)
            to_cam = _unit(cam.pos - seg)
            score = (out * _unit(to_cam + 0.6 * Bm[0])).sum(1)
            j = int(np.argmax(score))
            front[k], ofr[k] = seg[j], out[j]
            cols[k] = int(g.C[n])
        # how fast the tip goes round: the angle between the outward directions of neighbouring frames
        ang = np.degrees(np.arccos(np.clip((otip[1:] * otip[:-1]).sum(1), -1, 1)))
        ang = np.concatenate([[0.0], ang])
        ang[np.concatenate([[False], pis[1:] != pis[:-1]])] = 0.0
        sp = _gauss(ang, 0.6 * FPS)
        w = np.array([_smoothstep((v - follow[0]) / (follow[1] - follow[0])) for v in sp])
        w = _gauss(w, 0.3 * FPS)
        P = tip * (1 - w)[:, None] + front * w[:, None]
        O = _unit(otip * (1 - w)[:, None] + ofr * w[:, None])
        # the hook's own frame: the shaft leans out of the fabric, up and to the right of the frame, a little towards
        # the viewer; the lip lies in the picture plane so its profile (the throat) always reads
        U = _unit(0.50 * O + 0.35 * up + 0.70 * right - 0.25 * fwd)
        # moving to a new piece: lift off along the shaft, then come down on it
        lift = np.zeros(NF)
        for k in np.nonzero(pis[1:] != pis[:-1])[0] + 1:
            kk = np.arange(NF)
            lift = np.maximum(lift, 16.0 * np.exp(-0.5 * ((kk - k) / (0.15 * FPS)) ** 2))
        sig = 0.10 * FPS
        P = _gauss(P, sig)
        U = _unit(_gauss(U, 0.25 * FPS))
        P = P + U * lift[:, None]
        self.P, self.U = P, U
        self.right, self.fwd, self.up = right, fwd, up
        self.cols = cols
        # the stitch rhythm: one dip per stitch while that is slow enough to see, then a steady `rate` per second
        st = np.array([f['st'] + sum(g.pieces[f['pi']]['counts']) * f['pi'] for f in g.plan], float)
        srate = np.clip(np.gradient(st) * FPS, 0, None)
        srate[np.concatenate([[False], pis[1:] != pis[:-1]])] = 0
        freq = np.minimum(_gauss(srate, 0.3 * FPS), rate)
        self.phase = np.cumsum(freq / FPS) * 2 * math.pi
        # in and out: slides in along the shaft at the start, leaves the same way before the face is made
        dur = g.dur
        t = np.arange(NF) / FPS
        self.away = np.array([(1 - _smoothstep(tt / enter)) + _smoothstep((tt / dur - leave[0]) / (leave[1] - leave[0]))
                              for tt in t]) * 220.0
        self.on = self.away < 219.0

    def _at(self, a, k):
        k0 = int(np.clip(math.floor(k), 0, len(a) - 1))
        k1 = min(k0 + 1, len(a) - 1)
        u = float(np.clip(k - k0, 0, 1))
        return a[k0] * (1 - u) + a[k1] * u

    def capsules(self, t):
        """Capsule rows (ax, ay, az, bx, by, bz, r, colour, ident) of the hook and the strand at film time t."""
        k = t * self.fps
        away = float(self._at(self.away, k))
        if away >= 219.0:
            return np.zeros((0, 9))
        U = _unit(self._at(self.U, k))
        fw = _unit(self._at(self.fwd, k))
        V = _unit(np.cross(U, fw))                      # in the picture plane, across the shaft
        if V @ self._at(self.right, k) > 0:             # the lip on the lower-left of the shaft (as it hooks yarn)
            V = -V
        dip = 0.5 - 0.5 * math.cos(float(self._at(self.phase, k)))
        tip = self._at(self.P, k) + U * (away + 1.4 - 2.2 * dip) + V * 0.6 * dip
        rows = []
        metal, grip = self.pal0, self.pal0 + 1

        sc = self.sc

        def cap(s0, o0, s1, o1, r, c, ident, scale=True):
            f = sc if scale else 1.0
            a = tip + U * s0 * f + V * o0 * f
            b = tip + U * s1 * f + V * o1 * f
            rows.append([*a, *b, r * f, c, ident])

        # head: a rounded tip, the throat cut in behind it (a thinner neck pushed to the back), the lip over it
        cap(0.9, 0.15, 2.4, 0.0, 1.45, metal, 5)
        cap(2.6, -0.65, 4.6, -0.55, 1.05, metal, 5)
        cap(1.6, 0.55, 3.4, 0.95, 0.55, metal, 5)
        cap(4.6, -0.3, 7.0, 0.0, 1.45, metal, 5)
        cap(7.0 * sc, 0.0, 58.0, 0.0, 1.8 * sc, metal, 5, False)
        # the neck widens into the grip (a few steps of radius read as a smooth taper at this size)
        for j, rr in enumerate(np.linspace(1.8 * sc + 0.4, GRIP_R - 0.3, 5)):
            cap(58.0 + 2.0 * j, 0.0, 60.0 + 2.0 * j, 0.0, rr, metal, 5, False)
        cap(68.0, 0.0, 160.0, 0.0, GRIP_R, grip, 6, False)
        # the working strand: from the stitch on the hook round the throat, along under the shaft and away
        col = int(self.cols[int(np.clip(round(k), 0, len(self.cols) - 1))])
        ry = 0.5 * self.g.d * 0.9
        # it leaves the shaft after a few millimetres and rises to the left, to the other hand (off the frame)
        W = _unit(0.85 * self._at(self.up, k) - 0.45 * self._at(self.right, k) + 0.25 * U)
        p0, p1 = tip + (U * 3.2 - V * 0.9) * sc, tip + (U * 4.5 - V * 2.6) * sc
        p2 = p1 + U * 6.0 * sc + W * 4.0
        pts = [p0, p1, p2, p2 + W * 30.0 + U * 4.0, p2 + W * 160.0 + U * 10.0]
        for a, b in zip(pts[:-1], pts[1:]):
            rows.append([*a, *b, ry, col, 6])
        return np.asarray(rows, float)
