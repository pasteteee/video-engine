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

from .details import build as build_details, warn, with_ribbing

AMIKIT = os.environ.get('AMIKIT', '/home/user')       # folder that holds the amikit package


def _toy(spec):
    sys.path.insert(0, AMIKIT)
    from amikit.toy import Toy
    from amikit.piece import LEAN
    return Toy(spec), LEAN


# a single crochet as points (dv rounds below the top of its round, du in half-widths from its centre, n in yarn
# diameters out of the surface).  'L'/'R': into the left / right base stitch; 'C': at the stitch itself.
SC = [                            # a sc seen from the front: a short plump V, wider than tall (as on a real toy)
    ('C', 0.04, -1.00, 0.20),     # where the previous stitch's top ended
    ('C', 0.12, -0.92, 0.40),     # left front leg, upper: starts wide, at the corner of the stitch
    ('C', 0.44, -0.56, 0.46),     # left front leg, middle: leans in at about 45 degrees
    ('L', 0.80, 0.00, 0.30),      # left front leg, lower: into the base stitch
    ('B', 1.00, 0.00, -0.05),     # through the fabric under the base V
    ('C', 0.55, 0.00, -0.42),     # the bar on the wrong side
    ('R', 0.82, 0.00, 0.24),      # back to the front, at the base
    ('C', 0.44, 0.56, 0.46),      # right front leg, middle
    ('C', 0.12, 0.92, 0.40),      # right front leg, upper
    ('C', 0.02, 1.00, 0.26),      # top: front loop along the edge, tucked under the next round's legs
    ('C', -0.03, 1.06, 0.06),     # round the end of the top loop
    ('C', 0.00, 0.80, -0.30),     # back loop
    ('C', 0.04, 1.00, -0.10),
]


# rounds 1-2 of a piece begun in a magic ring: the ring is pulled tight, so the stitches are short radial spokes into
# the centre and their tops make a smooth closed circle (a plain V there opens into a star or a flower)
SC_RING = [
    ('C', 0.02, -1.00, 0.20),
    ('C', 0.16, -0.42, 0.26),     # left leg: nearly radial, close to the right one
    ('L', 0.85, 0.00, 0.14),
    ('B', 1.00, 0.00, -0.05),
    ('C', 0.55, 0.00, -0.36),
    ('R', 0.85, 0.00, 0.14),
    ('C', 0.16, 0.42, 0.26),
    ('C', 0.02, 0.62, 0.26),      # the top runs on round the circle: one even edge, no scallops
    ('C', -0.02, 1.00, 0.16),
    ('C', 0.00, 0.80, -0.30),
    ('C', 0.04, 1.00, -0.10),
]
RING_ROUNDS = 2


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
    ring = counts[0] <= 8                                    # begun in a magic ring (not a chain ring of 48)
    for i, rd in enumerate(rounds, 1):
        # a round that (nearly) doubles the last one is all increases: its stitches fan out short and radial, as in the
        # rounds by the ring, instead of pinched V's that read as a flower on a flat disc (a cookie, an ear)
        steep = prev_n is not None and counts[i - 1] >= 1.45 * prev_n
        tmpl = SC_RING if (ring and i <= RING_ROUNDS) or steep else SC
        n_i = counts[i - 1]
        hw = math.pi / n_i                                  # half a stitch, in angle
        k = 0; j = 0
        ops = [o for o in rd.ops if o in ('sc', 'inc', 'dec')]
        for op in ops:
            outs = 2 if op == 'inc' else 1
            for q in range(outs):
                thc = 2 * math.pi * (k + 0.5 - lean * (i - 0.5)) / n_i
                if prev_n is None:                          # round 1: into the ring
                    bl = br = thc; tb = 0.04
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
                for kind, dv, du, nn in tmpl:
                    # the tip of the V sits between the base stitch and the stitch's own centre: the column still
                    # leans (amikit LEAN), but the two legs stay the same length instead of one long and one steep
                    if kind == 'L':
                        t, th = max(tb, i - dv), 0.6 * bl + 0.4 * thc - 0.12 * hb
                    elif kind == 'R':
                        t, th = max(tb, i - dv), 0.6 * br + 0.4 * thc + 0.12 * hb
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
    app = getattr(inst, 'app', None)
    if app is not None:                                     # sewn on flat: outward is away from the piece under it
        par = app[0]
        g = par.base(np.linspace(0.5, par.p.M - 0.5, 9)[:, None].repeat(8, 1).ravel(),
                     np.tile(np.linspace(0, 2 * np.pi, 8, endpoint=False), 9)).mean(0)
        if np.mean(np.sum((B - g) * Nm, 1)) < 0:
            Nm = -Nm
    elif np.mean(np.sum((B - c) * Nm, 1)) < 0:
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


def yarn_width(yarn):
    """The yarn as it looks in the fabric: a soft cotton yarn is squashed flat by its neighbours, so its visible width
    is about 0.58 of the stitch (2.3 mm at a 4 mm stitch), more than its nominal round thickness."""
    t = float(yarn.get('thickness_mm', 1.9))
    return max(t, 0.58 * float(yarn.get('stitch_mm', 4.0)))


def _yarn_applique(inst):
    """A piece sewn on flat that is big enough to show its stitches (a face, a snout, a hood trim, a pocket) is laid
    as real yarn, round by round, like every other piece; a tiny one (a cheek of one or two rounds) stays a smooth
    detail (details.py), where yarn would only make a knot."""
    try:
        return hasattr(inst.p, 'rounds') and max(inst.p.counts) >= 22
    except Exception:
        return False


def toy_yarn(spec, rmax=None, parts=None):
    """All pieces as one chain with gaps between them.  Returns X, D, colour index per node, palette, gap."""
    toy, lean = _toy(spec)
    d = yarn_width(toy.yarn)
    cols = {}
    Xs, Cs = [], []
    pieces = []
    applique = []                                          # flat pieces sewn on (cheeks, motifs): details.py
    for name, inst in toy.inst.items():
        if parts and name.split('_')[0] not in parts:
            continue
        if getattr(inst.p, 'motif', None) is not None or (getattr(inst, 'app', None) is not None and
                                                           not _yarn_applique(inst)):
            applique.append(inst); continue
        if not hasattr(inst.p, 'rounds') or not hasattr(inst.p, 'counts'):
            warn(f'piece {name!r} has no rounds: not drawn'); continue
        try:
            Xp, sid = piece_yarn(inst, lean, d, rmax, with_stitch=True)
            Xp, sid = with_ribbing(inst, lean, d, Xp, sid)  # ribbed rounds: posts in vertical ribs
        except Exception as e:
            warn(f'piece {name!r} not drawn: {e}'); continue
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
    X = np.concatenate(Xs); C = np.concatenate(Cs)
    # the face, felt, embroidery and the pieces sewn on flat, over the finished yarn (details.py)
    det, spheres, blush = build_details(spec, toy, X, cols, d, applique)
    for P0, rad, cname, strength, host in blush:           # a blush dyes the yarn of its piece under it, fading out
        w = strength * np.exp(-(np.linalg.norm(X - P0, axis=1) / rad) ** 2 * 1.6)
        mine = np.zeros(len(X), bool)
        for q in pieces:
            if q['name'] == host:
                mine[q['start']:q['end']] = True
        w = np.where(mine, w, 0.0)
        lv = np.floor(w / max(strength, 1e-6) * 3.0 + 0.5).astype(int)   # three steps of strength
        for k in (1, 2, 3):
            m = lv == k
            if not m.any():
                continue
            for base in np.unique(C[m]):
                bname = next(nm for nm, ii in cols.items() if ii == base)
                key = f'{bname}+{cname}@{k}'
                if key not in toy.colours:
                    a = strength * k / 3.0
                    toy.colours[key] = (1 - a) * np.asarray(toy.colours.get(bname, (0.8, 0.8, 0.8)), float) + \
                        a * np.asarray(toy.colours.get(cname, (0.95, 0.6, 0.65)), float)
                C[m & (C == base)] = cols.setdefault(key, len(cols))
    pal = [list(toy.colours.get(k, (0.8, 0.8, 0.8))) for k in cols]
    toy.spheres = spheres
    toy.details = det
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
        ims.append(rn.render(X, D, cam, colnode=C, spheres=toy.spheres, details=toy.details))
    Image.fromarray(np.concatenate(ims, 1)).save(out)
    return out
