"""A whole toy from its pattern, as one yarn per piece, stitch by stitch.

    python -m vengine yarn still SPEC.json OUT.png [--size 900] [--views front,34,back]

The pattern (amikit spec: parts with rounds "mr 6", "inc 6 to 54", ...) is expanded into rounds of stitches by amikit,
and amikit gives the surface each piece takes when stuffed.  Every single crochet of every round is then laid on that
surface as yarn: its two front legs (the V seen on the right side) go down into the stitch of the previous round it is
worked into, the yarn passes through to the back (the bar seen on the wrong side) and its top loop lies along the
edge, where the next round is worked into it.  An increase is two stitches into one, a decrease one stitch into two.

This is the pattern laid out stitch by stitch, not simulated: the yarn path is a template per stitch.  It is the
starting shape a physical relaxation can take, and the thing to compare with a real crocheted toy.
"""
from __future__ import annotations
import argparse, json, math, os, sys
from pathlib import Path
import numpy as np

AMIKIT = os.environ.get('AMIKIT', '/home/user')       # folder that holds the amikit package


def _toy(spec):
    sys.path.insert(0, AMIKIT)
    from amikit.toy import Toy
    from amikit.piece import LEAN
    return Toy(spec), LEAN


# a single crochet as points (dv rounds below the top of its round, du in half-widths from its centre, n in yarn
# diameters out of the surface).  'L'/'R': into the left / right base stitch; 'C': at the stitch itself.
SC = [                            # a sc seen from the front: a plump V (legs stay up, no pointed leaf ends)
    ('C', 0.00, -1.00, 0.24),     # where the previous stitch's top ended
    ('C', 0.24, -0.84, 0.46),     # left front leg, upper
    ('C', 0.55, -0.46, 0.44),     # left front leg, middle
    ('L', 0.85, 0.00, 0.30),      # left front leg, lower: into the base stitch
    ('B', 1.00, 0.00, -0.05),     # through the fabric under the base V
    ('C', 0.55, 0.00, -0.42),     # the bar on the wrong side
    ('R', 0.88, 0.00, 0.24),      # back to the front, at the base
    ('C', 0.55, 0.46, 0.44),      # right front leg, middle
    ('C', 0.24, 0.84, 0.46),      # right front leg, upper
    ('C', 0.02, 0.86, 0.38),      # top: front loop along the edge
    ('C', -0.06, 1.00, 0.14),     # round the end of the top loop
    ('C', 0.00, 0.80, -0.30),     # back loop
    ('C', 0.04, 1.00, -0.10),
]


def _catmull(P, per, tag=None):
    """Catmull-Rom through P, about `per` apart.  With `tag` (one value per point of P) also returns, per output point,
    the tag of the control point its segment starts at."""
    P = np.asarray(P, float)
    P = np.concatenate([P[:1], P, P[-1:]])
    out, tags = [], []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        k = max(2, int(math.ceil(np.linalg.norm(p2 - p1) / per)))
        for u in np.arange(k) / k:
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3))
            tags.append(tag[i - 1] if tag is not None else 0)
    out.append(P[-2])
    tags.append(tag[-1] if tag is not None else 0)
    return (np.array(out), np.array(tags)) if tag is not None else np.array(out)


def _resample(X, h, tag=None):
    s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(X, axis=0), axis=1))])
    q = np.arange(0, s[-1], h)
    Y = np.stack([np.interp(q, s, X[:, c]) for c in range(3)], 1)
    if tag is None:
        return Y
    return Y, np.asarray(tag)[np.clip(np.searchsorted(s, q, side='right') - 1, 0, len(tag) - 1)]


def piece_yarn(inst, lean, d, rmax=None, with_stitch=False):
    """Centreline of the yarn of one piece (rounds 1..N).  Returns points (P, 3); with_stitch: also, per point, the
    (round, stitch) it belongs to, as round * 100000 + stitch (round from 1, stitch from 0)."""
    p = inst.p
    counts = p.counts
    rounds = p.rounds[:rmax] if rmax else p.rounds
    T, TH, NN, SID = [], [], [], []
    prev_n = None
    for i, rd in enumerate(rounds, 1):
        n_i = counts[i - 1]
        hw = math.pi / n_i                                  # half a stitch, in angle
        k = 0; j = 0
        ops = [o for o in rd.ops if o in ('sc', 'inc', 'dec')]
        for op in ops:
            outs = 2 if op == 'inc' else 1
            for q in range(outs):
                thc = 2 * math.pi * (k + 0.5 - lean * (i - 0.5)) / n_i
                if prev_n is None:                          # round 1: into the ring
                    bl = br = thc; tb = 0.18
                    hb = 0.0
                else:
                    hb = math.pi / prev_n
                    thb = 2 * math.pi * (j + 0.5 - lean * (i - 1.5)) / prev_n
                    if op == 'dec':
                        bl, br = thb, thb + 2 * hb
                    elif op == 'inc':                      # two stitches share one: each takes a side of it
                        bl = br = thb + (-0.35 if q == 0 else 0.35) * hb
                    else:
                        bl = br = thb
                    tb = i - 1
                for kind, dv, du, nn in SC:
                    if kind == 'L':
                        t, th = max(tb, i - dv), bl - 0.35 * hb
                    elif kind == 'R':
                        t, th = max(tb, i - dv), br + 0.35 * hb
                    elif kind == 'B':
                        t, th = max(tb - 0.02, i - dv), 0.5 * (bl + br)
                    else:
                        t, th = i - dv, thc + du * hw
                    T.append(t); TH.append(th); NN.append(nn); SID.append(i * 100000 + min(k, n_i - 1))
                k += 1
            j += 2 if op == 'dec' else 1
        prev_n = n_i
    T = np.clip(np.array(T), 0.02, p.M); TH = np.array(TH); NN = np.array(NN)
    B = inst.base(T, TH)
    Nm = inst.base_normal(T, TH)
    # outward: away from the axis of the piece
    c = B.mean(0)
    if np.mean(np.sum((B - c) * Nm, 1)) < 0:
        Nm = -Nm
    P = B + Nm * (NN * d)[:, None]
    if with_stitch:
        X, tg = _catmull(P, 0.3, np.array(SID))
        return _resample(X, 0.5, tg)
    X = _catmull(P, 0.3)
    return _resample(X, 0.5)


class _FlatDisc:
    """A flat circle of sc rounds (6, 12, 18 ...) as an amikit-like instance, for piece_yarn."""
    def __init__(self, P0, n0, e1, e2, rx, ry, n):
        from types import SimpleNamespace as NS
        self.P0, self.n0, self.e1, self.e2, self.rx, self.ry, self.n = P0, n0, e1, e2, rx, ry, n
        rounds = [NS(ops=['inc'] * 6)] + [NS(ops=(['sc'] * i + ['inc']) * 6) for i in range(n - 1)]
        self.p = NS(rounds=rounds, counts=[6 * (i + 1) for i in range(n)], M=float(n))

    def base(self, T, TH):
        T = np.asarray(T, float); TH = np.asarray(TH, float); u = T / self.n
        return (self.P0[None] + np.outer(u * self.rx * np.cos(TH), self.e1) + np.outer(u * self.ry * np.sin(TH), self.e2))

    def base_normal(self, T, TH):
        return np.tile(self.n0, (len(np.atleast_1d(T)), 1))


def flat_circle(P0, n0, e1, e2, rx, ry, d):
    n = max(2, int(round(max(rx, ry) / (0.9 * d))))
    return piece_yarn(_FlatDisc(P0, n0, e1, e2, rx, ry, n), 0.0, d * 0.8)


def directors(X):
    Tn = np.gradient(X, axis=0); Tn /= np.linalg.norm(Tn, axis=1)[:, None] + 1e-30
    D = np.zeros_like(X); d = np.cross(Tn[0], [0.3, 0.5, 0.8]); d /= np.linalg.norm(d)
    for i in range(len(X)):
        d = d - Tn[i] * (d @ Tn[i]); d /= np.linalg.norm(d) + 1e-30; D[i] = d
    return D


def toy_yarn(spec, rmax=None, parts=None):
    """All pieces as one chain with gaps between them.  Returns X, D, colour index per node, palette, gap."""
    toy, lean = _toy(spec)
    d = float(toy.yarn.get('thickness_mm', 1.9))
    cols = {}
    Xs, Cs = [], []
    pieces = []
    for name, inst in toy.inst.items():
        if parts and name.split('_')[0] not in parts:
            continue
        if not hasattr(inst.p, 'rounds') or not hasattr(inst.p, 'counts'):
            continue
        try:
            Xp, sid = piece_yarn(inst, lean, d, rmax, with_stitch=True)
        except Exception as e:                              # flat / motif pieces are not laid yet
            print('skip', name, e); continue
        col = inst.p.colour
        ci = cols.setdefault(col, len(cols))
        cnode = np.full(len(Xp), ci, np.int32)
        try:                                               # colour zones of the pattern (faces, stripes, patches)
            chart = toy.chart(inst)
        except Exception as e:
            print('no colour chart for', name, e); chart = None
        if chart is not None:
            for q in np.unique(sid):
                rq, kq = int(q // 100000), int(q % 100000)
                if 1 <= rq <= len(chart) and chart[rq - 1]:
                    cname = chart[rq - 1][min(kq, len(chart[rq - 1]) - 1)]
                    if cname != col:
                        cnode[sid == q] = cols.setdefault(cname, len(cols))
        n0 = sum(len(x) for x in Xs)
        pieces.append(dict(name=name, part=name.split('_')[0], start=n0, end=n0 + len(Xp), counts=list(inst.p.counts[:rmax] if rmax else inst.p.counts),
                           name_ru=next((q.get('name_ru') for q in spec['parts'] if q['id'] == name.split('_')[0]), name)))
        Xs.append(Xp); Cs.append(cnode)
    # the face: eyes, noses and satin as a tight spiral of yarn (a dome), embroidery as a strand on the surface
    spheres = []

    def dome(P0, n0, wx, wy, hgt, off=(0.0, 0.0), pitch=0.4):
        up = np.array([0.0, 1.0, 0.0])
        e1 = np.cross(up, n0); e1 = e1 / (np.linalg.norm(e1) + 1e-9); e2 = np.cross(n0, e1)
        P0 = P0 + off[0] * e1 + off[1] * e2
        R = 0.5 * max(wx, wy)
        a = np.linspace(0, 2 * np.pi * R / (pitch * d), max(200, int(40 * R)))
        u = a / a[-1]
        x = u * (0.5 * wx - d / 2) * np.cos(a); y = u * (0.5 * wy - d / 2) * np.sin(a)
        z = d * 0.45 + hgt * np.sqrt(np.clip(1 - u ** 2, 0, 1))
        return P0 + np.outer(x, e1) + np.outer(y, e2) + np.outer(z, n0)

    for f in spec.get('face', []):
        hosts = [k for k in toy.inst if k == f['on'] or k.startswith(f['on'] + '_')]
        if not hosts or f['type'] not in ('safety_eye', 'safety_nose', 'satin', 'stitch'):
            continue
        inst = toy.inst[hosts[0]]
        col = f.get('colour', 'black')
        ci = cols.setdefault(col, len(cols))
        if f['type'] == 'stitch':
            pts = [inst.point(rnd, az) for rnd, az in f['points']]
            P = np.array([q + nq * 0.5 * d for q, nq in pts])   # sunk between the stitches: reads as a thin thread
            Xp = _resample(_catmull(P, 0.3), 0.5)
            Xs.append(Xp); Cs.append(np.full(len(Xp), ci, np.int32))
            continue
        if len(hosts) > 1:                                  # on a mirrored pair of pieces: the same place on each
            where = [(toy.inst[hn], f['at']['az']) for hn in hosts]
        elif f.get('mirror'):
            where = [(inst, f['at']['az']), (inst, -f['at']['az'])]
        else:
            where = [(inst, f['at']['az'])]
        for hi, az in where:
            P0, n0 = hi.point(f['at']['round'], az)
            sz = f.get('size_mm', 10)
            wx, wy = (sz if isinstance(sz, list) else [sz, sz]) if f['type'] != 'satin' else (f.get('width_mm', 6), f.get('height_mm', 6))
            hgt = {'safety_eye': 0.3 * max(wx, wy), 'safety_nose': 0.3 * max(wx, wy)}.get(f['type'], f.get('thickness_mm', 1.0) * 0.6)
            off = f.get('offset_mm', [0.0, 0.0])
            off = (off[0] * (1 if az >= 0 or not f.get('mirror') else -1), off[1])
            if f['type'] == 'safety_eye':                   # a glossy plastic half-ball, traced by the renderer
                up_ = np.array([0.0, 1.0, 0.0]); e1 = np.cross(up_, n0); e1 /= np.linalg.norm(e1) + 1e-9
                e2 = np.cross(n0, e1); Rr = 0.5 * max(wx, wy)
                c = P0 + n0 * (f.get('lift_mm', 0.0) + 0.55 * d - 0.35 * Rr) + off[0] * e1 + off[1] * e2
                spheres.append([c[0], c[1], c[2], Rr, ci])
                continue
            if f['type'] == 'satin':                        # a cheek: a small flat crocheted circle sewn on
                up_ = np.array([0.0, 1.0, 0.0]); e1 = np.cross(up_, n0); e1 /= np.linalg.norm(e1) + 1e-9
                e2 = np.cross(n0, e1)
                Xp = flat_circle(P0 + n0 * (f.get('lift_mm', 0.0) + 0.15 * d) + off[0] * e1 + off[1] * e2, n0, e1, e2,
                                 0.5 * wx, 0.5 * wy, d)
                Xs.append(Xp); Cs.append(np.full(len(Xp), ci, np.int32))
                continue
            flat = False
            Xp = _resample(dome(P0 + n0 * f.get('lift_mm', 0.0), n0, wx, wy, hgt * (0.5 if flat else 1.0), off,
                                pitch=0.95 if flat else 0.4), 0.5)
            Xs.append(Xp); Cs.append(np.full(len(Xp), ci, np.int32))
    X = np.concatenate(Xs); C = np.concatenate(Cs)
    pal = [list(toy.colours.get(k, (0.8, 0.8, 0.8))) for k in cols]
    toy.spheres = np.array(spheres, float).reshape(-1, 5)
    toy.yarn_pieces = pieces                                # node ranges of the pieces, for captions and cameras
    return X, directors(X), C, pal, d, toy


def still(spec_path, out, size=900, views='front,34,back', rmax=None, parts=None):
    """A strip of views of the finished toy (a look check)."""
    from PIL import Image
    from .render import Renderer, Camera
    spec = json.loads(Path(spec_path).read_text())
    X, D, C, pal, d, toy = toy_yarn(spec, rmax, parts.split(',') if parts else None)
    soft = 1.2
    rn = Renderer(size, size, ss=2, r=d / 2 / soft, h=0.5, soft=soft, palette=pal)
    rn.set_scene(X)
    lo, hi = X.min(0), X.max(0); g = 0.5 * (lo + hi); ext = float(np.linalg.norm(hi - lo))
    dirs = {'front': [0, 0.15, 1], '34': [0.6, 0.2, 0.8], 'back': [0, 0.15, -1], 'side': [1, 0.1, 0],
            'top': [0, 1, 0.2], 'bottom': [0, -1, 0.2]}
    ims = []
    for v in views.split(','):
        e = np.array(dirs[v], float); e /= np.linalg.norm(e)
        cam = Camera(g + e * ext * 2.2, g, up=(0, 1, 0) if abs(e[1]) < 0.9 else (0, 0, 1), fov=30)
        ims.append(rn.render(X, D, cam, colnode=C, spheres=toy.spheres))
    Image.fromarray(np.concatenate(ims, 1)).save(out)
    return out
