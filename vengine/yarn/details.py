"""The face and the pieces that are not rounds of single crochet: what the yarn path does not lay.

* felt (amber eyes): a flat stiff shape glued on, matte, with a soft rounded cut edge;
* satin (pupils, noses): a low dome of parallel strands of embroidery thread, laid over the stitches;
* stitch / embroidery / line (mouths): a thin thread of its own thickness on top of the stitches;
* safety_nose: a glossy plastic dome; safety_eye stays a glossy half-ball (render.py `_trace_spheres`);
* blush: the yarn under it takes the colour, fading out;
* appliques (cheeks) and motifs (a star): a small flat crocheted piece sewn on, as a smooth shape with stitches
  radiating from its centre and its rounds as faint rings; the outline comes from amikit, so a star has its points;
* ribbing (`rib` rounds: collars, hems, cuffs): front- and back-post columns, a band two rounds tall with vertical ribs.

Everything except ribbing is a small surface mesh (patch or tube) with its own local coordinates in millimetres; the
renderer rasterises it (render.py `_raster_details`) and shades it from those coordinates (`_shade_details`), so the
texture sits on the detail and does not crawl from frame to frame.  The meshes rest on the finished yarn: their base
follows the tops of the stitches under them.  A face item or piece of a kind that is not drawn is reported, not
silently dropped.
"""
from __future__ import annotations

import math
import sys

import numpy as np

WORLD_Y = np.array([0.0, 1.0, 0.0])
FELT, SATIN, CROCHET, THREAD, PLASTIC = range(5)
DRAWN = ('safety_eye', 'eye', 'safety_nose', 'satin', 'felt', 'stitch', 'embroidery', 'line', 'blush', 'strap')
NE = 16                                     # floats per element row (see Details.table)


def warn(msg):
    print('yarn: warning:', msg, file=sys.stderr)


def _norm(v):
    return v / (np.linalg.norm(v, axis=-1, keepdims=True) + 1e-12)


def _frame(n0, rot_deg=0.0):
    """e1 (right as seen looking at the surface), e2 (up, toward the toy's up), n0."""
    up = WORLD_Y - (WORLD_Y @ n0) * n0
    if np.linalg.norm(up) < 1e-3:
        up = np.array([0.0, 0.0, -1.0]) - (np.array([0.0, 0.0, -1.0]) @ n0) * n0
    e2 = _norm(up)
    e1 = np.cross(e2, n0)
    if rot_deg:
        a = math.radians(rot_deg)
        e1, e2 = math.cos(a) * e1 + math.sin(a) * e2, -math.sin(a) * e1 + math.cos(a) * e2
    return e1, e2


def _smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


class Details:
    """All detail meshes of a toy.  Elements are revealed in order by `frame(t)` (t 0..1, the face phase)."""

    def __init__(self, yarn_tree, X, rv):
        self.tree, self.X, self.rv = yarn_tree, X, rv
        self.items = []

    # -------------------------------------------------------------------------------------------- the yarn under it
    def envelope(self, pts, n0, reach=7.0):
        """Height along n0 of the top of the yarn under each point (NaN where there is none)."""
        out = np.full(len(pts), np.nan)
        if self.tree is None:
            return out
        rv = self.rv
        for i, nb in enumerate(self.tree.query_ball_point(pts, reach)):
            if not nb:
                continue
            q = self.X[nb] - pts[i]
            z = q @ n0
            lat2 = np.einsum('ij,ij->i', q, q) - z * z
            ok = (lat2 < rv * rv) & (np.abs(z) < reach)
            if ok.any():
                out[i] = float(np.max(z[ok] + np.sqrt(rv * rv - lat2[ok])))
        return out

    def stack(self, it):
        """What is laid next rests on this item's surface too (the envelope then includes its vertices)."""
        V = it['V'][::2]
        self.X = np.concatenate([self.X, V]) if self.X is not None and len(self.X) else V
        from scipy.spatial import cKDTree
        self.tree = cKDTree(self.X)

    # -------------------------------------------------------------------------------------------- builders
    def patch(self, P0, n0, radius, profile, ci, mat, rot=0.0, p1=0.0, p2=0.0, gloss=0.0, thick=1.0, na=120, nr=14,
              lift=0.0, seat=0.8):
        """A shape over the surface at P0: radius(theta) its outline (mm), profile(rho) its height over the yarn."""
        e1, e2 = _frame(n0, rot)
        th = np.linspace(0, 2 * np.pi, na, endpoint=False)
        R = np.asarray(radius(th), float)
        rho = np.sin(np.linspace(0, 1, nr + 1) * np.pi / 2)          # denser at the rim, where it rolls over
        x = rho[:, None] * R[None] * np.cos(th)[None]
        y = rho[:, None] * R[None] * np.sin(th)[None]
        flat = P0 + x[..., None] * e1 + y[..., None] * e2
        env = self.envelope(flat.reshape(-1, 3), n0).reshape(x.shape)
        ok = np.isfinite(env)
        if ok.sum() >= 6:                                           # a smooth seat on the tops of the stitches
            A = np.stack([np.ones_like(x), x, y, x * x, x * y, y * y], -1)
            c, *_ = np.linalg.lstsq(A[ok], env[ok], rcond=None)
            base = A @ c
            base = base + np.quantile(env[ok] - base[ok], seat)
        else:
            base = np.zeros_like(x)
        z = base + np.asarray(profile(rho), float)[:, None] + lift
        V = flat + z[..., None] * n0
        dr = np.gradient(V, axis=0)
        dt = np.roll(V, -1, axis=1) - np.roll(V, 1, axis=1)
        N = _norm(np.cross(dt, dr))
        if np.mean(N[1:] @ n0) < 0:
            N = -N
        N[0] = n0
        UVW = np.stack([x, y, np.broadcast_to(rho[:, None], x.shape)], -1)
        F = []
        for i in range(nr):
            for j in range(na):
                a0, a1 = i * na + j, i * na + (j + 1) % na
                b0, b1 = a0 + na, a1 + na
                F += [[a0, b0, b1], [a0, b1, a1]]
        self.items.append(dict(V=V.reshape(-1, 3), N=N.reshape(-1, 3), U=UVW.reshape(-1, 3), F=np.array(F, np.int32),
                               C=P0 + float(np.median(base)) * n0, fs=None,
                               row=self._row(ci, mat, p1, p2, gloss, thick, e1, e2, n0)))

    def tube(self, P, Nrm, th, ci, gloss=0.08, sides=10, ply=3):
        """A thread of diameter th along P (normals Nrm: the surface it lies on)."""
        P = np.asarray(P, float)
        T = _norm(np.gradient(P, axis=0))
        Bn = _norm(np.cross(T, Nrm))
        Nn = np.cross(Bn, T)
        s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
        ph = np.linspace(0, 2 * np.pi, sides, endpoint=False)
        ring = np.cos(ph)[None, :, None] * Nn[:, None] + np.sin(ph)[None, :, None] * Bn[:, None]
        V = P[:, None] + 0.5 * th * ring
        # round ends: the first and last rings shrink in
        k = np.ones(len(P))
        k[0] = k[-1] = 0.35
        k[1] = k[-2] = 0.8
        V = P[:, None] + 0.5 * th * ring * k[:, None, None]
        U = np.stack([np.broadcast_to(s[:, None], ring.shape[:2]), np.broadcast_to(ph[None], ring.shape[:2]),
                      np.zeros(ring.shape[:2])], -1)
        F = []
        m = len(P)
        for i in range(m - 1):
            for j in range(sides):
                a0, a1 = i * sides + j, i * sides + (j + 1) % sides
                F += [[a0, a0 + sides, a1 + sides], [a0, a1 + sides, a1]]
        F = np.array(F, np.int32)
        fs = s[F[:, 0] // sides] / max(s[-1], 1e-9)                 # where along the thread each triangle is
        self.items.append(dict(V=V.reshape(-1, 3), N=ring.reshape(-1, 3), U=U.reshape(-1, 3), F=F, C=P[0], fs=fs,
                               row=self._row(ci, THREAD, ply * th * 1.1, ply, gloss, th, T[0], Nn[0], Nrm[0])))

    @staticmethod
    def _row(ci, mat, p1, p2, gloss, thick, e1, e2, n0):
        r = np.zeros(NE)
        r[:6] = [ci, mat, p1, p2, gloss, thick]
        r[6:9], r[9:12], r[12:15] = e1, e2, n0
        return r

    # -------------------------------------------------------------------------------------------- per frame
    def frame(self, t=1.0):
        """Meshes as they are at reveal time t (0..1): each detail appears in turn, patches growing out of their
        centre, threads drawn along their length.  Returns V, N, U, F, element per triangle, element table, or None."""
        ne = len(self.items)
        if not ne:
            return None
        Vs, Ns, Us, Fs, Es = [], [], [], [], []
        off = 0
        for k, it in enumerate(self.items):
            a = 0.6 * k / ne
            s = _smooth((t - a) / 0.4)
            if s <= 1e-3:
                continue
            F = it['F']
            if it['fs'] is not None:                                # a thread is drawn along its length
                F = F[it['fs'] <= s]
                V = it['V']
            else:
                V = it['C'] + (it['V'] - it['C']) * s
            if not len(F):
                continue
            Vs.append(V); Ns.append(it['N']); Us.append(it['U']); Fs.append(F + off)
            Es.append(np.full(len(F), k, np.int32))
            off += len(V)
        if not Fs:
            return None
        return (np.ascontiguousarray(np.concatenate(Vs)), np.ascontiguousarray(np.concatenate(Ns)),
                np.ascontiguousarray(np.concatenate(Us)), np.ascontiguousarray(np.concatenate(Fs)),
                np.ascontiguousarray(np.concatenate(Es)), np.ascontiguousarray(np.stack([i['row'] for i in self.items])))


# ------------------------------------------------------------------------------------------------ shapes
def ellipse(a, b):
    """Outline radius of an ellipse with full sizes a x b."""
    return lambda th: (a / 2) * (b / 2) / np.sqrt(((b / 2) * np.cos(th)) ** 2 + ((a / 2) * np.sin(th)) ** 2 + 1e-12)


def shape_outline(shape, w, h):
    if shape in ('triangle', 'heart'):
        def r(th):                                                # rounded downward triangle (a nose)
            e = ellipse(w, h)(th)
            down = np.clip(-np.sin(th), 0, 1)
            return e * (1 - 0.32 * down * np.abs(np.cos(th)) ** 0.6)
        return r
    return ellipse(w, h)


def felt_profile(th):
    return lambda rho: th * np.sqrt(np.clip(1 - (np.clip(rho - 0.78, 0, None) / 0.22) ** 2, 0, 1)) + 0.05


def dome_profile(hgt, edge):
    return lambda rho: edge + (hgt - edge) * np.sqrt(np.clip(1 - rho ** 2, 0, 1))


def pillow_profile(hgt, k=4.0):
    return lambda rho: 0.15 * hgt + 0.85 * hgt * np.clip(1 - rho ** k, 0, 1) ** 0.5


# ------------------------------------------------------------------------------------------------ the face
def face_items(spec, toy):
    """The face list with mirrored items doubled: (item, instance name, az, x-sign)."""
    out = []
    for f in spec.get('face', []):
        hosts = [k for k in toy.inst if k == f['on'] or k.startswith(f['on'] + '_')]
        if not hosts:
            warn(f"face item {f.get('id', f['type'])!r}: no piece {f['on']!r}")
            continue
        at = f.get('at', {})
        az = at.get('az', 0.0)
        if len(hosts) > 1:                                         # on a mirrored pair: the same place on each
            out += [(f, h, az, 1.0 if i == 0 else -1.0, 1.0) for i, h in enumerate(hosts)]
        elif f.get('mirror'):
            out += [(f, hosts[0], az, 1.0, 1.0), (f, hosts[0], -az, -1.0, -1.0)]
        else:
            out.append((f, hosts[0], az, 1.0, 1.0))
    return out


def _thread_path(inst, pts, mirror, step=0.25):
    """Points [round, az] on a piece, densely along the surface: positions and normals."""
    P, N = [], []
    pts = [(float(r), float(a) * mirror) for r, a in pts]
    # azimuths go the short way round: (-155, 180) is 25 degrees through the back, not 335 through the front
    az = np.degrees(np.unwrap(np.radians([a for _, a in pts])))
    pts = [(r, float(a)) for (r, _), a in zip(pts, az)]
    for (r0, a0), (r1, a1) in zip(pts[:-1], pts[1:]):
        p0, _ = inst.point(r0, a0)
        p1, _ = inst.point(r1, a1)
        k = max(2, int(math.ceil(np.linalg.norm(p1 - p0) / step)))
        for u in np.arange(k) / k:
            p, n = inst.point(r0 + (r1 - r0) * u, a0 + (a1 - a0) * u)
            P.append(p); N.append(n)
    p, n = inst.point(*pts[-1])
    P.append(p); N.append(n)
    return np.array(P), _norm(np.array(N))


def build(spec, toy, X, cols, d, applique=()):
    """Details of the toy over its finished yarn X.  cols: colour name -> palette index (extended here).
    applique: amikit instances of flat pieces sewn on (cheeks, motifs).  Returns (Details, spheres rows, blush list)."""
    from scipy.spatial import cKDTree
    rv = d / 2
    det = Details(cKDTree(X) if len(X) else None, X, rv)
    spheres = []
    blush = []

    def ci_of(name):
        return cols.setdefault(name, len(cols))

    # pieces sewn on flat: their outline from amikit, in rounds of stitches; the bigger first, so a smaller piece
    # sewn over a bigger one (a shark face over its hood trim) rests on it instead of cutting through it
    def _area(inst):
        try:
            return float(inst.p.counts[-1]) * len(inst.p.counts)
        except Exception:
            return 0.0
    for inst in sorted(applique, key=_area, reverse=True):
        p = inst.p
        M = float(p.M)
        motif = getattr(p, 'motif', None) is not None
        th = np.linspace(0, 2 * np.pi, 180, endpoint=False)
        P0 = inst.base(np.array([0.0]), np.array([0.0]))[0]
        O = inst.base(np.full(len(th), M), th)
        nrm = inst.base_normal(np.array([0.5 * M]), np.array([0.0]))[0]
        parent = inst.app[0] if getattr(inst, 'app', None) is not None else None
        if parent is not None:
            g = parent.base(np.linspace(0.5, parent.p.M - 0.5, 9)[:, None].repeat(8, 1).ravel(),
                            np.tile(np.linspace(0, 2 * np.pi, 8, endpoint=False), 9))
            if nrm @ (P0 - g.mean(0)) < 0:
                nrm = -nrm
        nrm = _norm(nrm)
        e1, e2 = _frame(nrm)
        q = O - P0
        ang = np.arctan2(q @ e2, q @ e1)
        rad = np.linalg.norm(q - np.outer(q @ nrm, nrm), axis=1)
        order = np.argsort(ang)
        ang, rad = ang[order], rad[order]
        if motif:                                                  # crocheted points are rounded, not cut sharp
            kk = np.exp(-0.5 * (np.arange(-6, 7) / 2.5) ** 2)
            rad = np.convolve(np.concatenate([rad[-6:], rad, rad[:6]]), kk / kk.sum(), 'valid')
        outline = (lambda A, Rr: (lambda t: np.interp(np.mod(t + np.pi, 2 * np.pi) - np.pi, A, Rr, period=2 * np.pi)))(ang, rad)
        # rounds as they read on the toy: about one yarn width and a half each, however the pattern started
        nrd = max(len(p.counts) if hasattr(p, 'counts') else 2, int(round(float(rad.mean()) / (1.35 * d))), 1)
        det.patch(P0, nrm, outline, pillow_profile((0.8 if motif else 0.5) * d, 2.0 if motif else 5.0), ci_of(p.colour), CROCHET,
                  p1=1.45 * d, p2=nrd, gloss=0.0, thick=d,
                  na=240 if motif else 160, nr=20, seat=0.7)
        det.stack(det.items[-1])

    for f, hname, az, sx, _m in face_items(spec, toy):
        kind = f['type']
        if kind not in DRAWN:
            warn(f"face item type {kind!r} ({f.get('id', '')}) is not drawn by the yarn renderer")
            continue
        inst = toy.inst[hname]
        col = f.get('colour', 'black')
        if col not in toy.colours:
            warn(f"face item {f.get('id', kind)!r}: unknown colour {col!r}")
        ci = ci_of(col)
        if kind in ('stitch', 'embroidery', 'line', 'strap'):
            th = float(f.get('thickness_mm', 1.3 if kind != 'strap' else 0.8 * toy.yarn.get('stitch_mm', 4.0)))
            P, Nn = _thread_path(inst, f['points'], _m)
            env = np.array([det.envelope(P[i:i + 1], Nn[i])[0] for i in range(len(P))])
            env = np.where(np.isfinite(env), env, 0.0)
            # a thread pulled over the stitches rests on their tops, sinking a little between them
            k = max(1, int(round(1.6 / 0.25)))
            envs = np.array([env[max(0, i - k):i + k + 1].max() for i in range(len(env))])
            envs = 0.5 * envs + 0.5 * np.convolve(np.pad(envs, k, mode='edge'), np.ones(2 * k + 1) / (2 * k + 1), 'valid')
            P = P + Nn * (envs + 0.3 * th + float(f.get('lift_mm', 0.0)))[:, None]
            det.tube(P, Nn, th, ci, gloss=0.06)
            continue
        if kind == 'blush':
            P0, n0 = inst.point(f['at']['round'], az)
            blush.append((P0, float(f.get('size_mm', 8)) / 2, col, float(f.get('strength', 0.55)), hname))
            continue
        P0, n0 = inst.point(f['at']['round'], az)
        n0 = _norm(n0)
        if kind in ('satin',):
            wx, wy = float(f.get('width_mm', 6)), float(f.get('height_mm', 6))
        else:
            sz = f.get('size_mm', 10)
            wx, wy = (sz if isinstance(sz, list) else [sz, sz])
            wx, wy = float(wx), float(wy)
        off = f.get('offset_mm', [0.0, 0.0])
        e1, e2 = _frame(n0)
        P0 = P0 + sx * float(off[0]) * e1 + float(off[1]) * e2
        rot = sx * float(f.get('rotate', 0.0))
        lift = float(f.get('lift_mm', 0.0))
        if kind in ('safety_eye', 'eye'):                         # a glossy plastic half-ball, traced by the renderer
            Rr = 0.5 * max(wx, wy)
            env = det.envelope(P0[None], n0)[0]
            base = (env if np.isfinite(env) else 0.55 * d) - 0.4 * Rr
            c = P0 + n0 * (f.get('lift_mm', 0.0) + base)
            spheres.append([c[0], c[1], c[2], Rr, ci])
            for k_ in ('iris', 'highlight'):
                if f.get(k_):
                    warn(f"safety eye {f.get('id', '')!r}: {k_!r} is not drawn (one-colour eye)")
            continue
        if kind == 'felt':
            tf = float(f.get('thickness_mm', 1.0))
            det.patch(P0, n0, ellipse(wx, wy), felt_profile(tf), ci, FELT, rot=rot, gloss=0.10, thick=tf, lift=lift,
                      seat=0.75)
        elif kind == 'satin':
            th = float(f.get('thickness_mm', 1.4))
            nstr = max(3, int(f.get('strands', round(wy / (th * 0.55)))))
            hgt = 0.55 * th + 0.12 * min(wx, wy)
            # over felt or other embroidery (lift_mm): sit on what is already there, not on the yarn
            seat = 0.85
            under = [it for it in det.items if it['fs'] is None and np.linalg.norm(it['C'] - P0) < 0.5 * max(wx, wy) + 4]
            base_lift = 0.0
            if lift > 0 and under:
                top = max(float(np.max((it['V'] - P0) @ n0)) for it in under)
                env = det.envelope(P0[None], n0)[0]
                base_lift = max(0.0, top - (env if np.isfinite(env) else 0.0))
            det.patch(P0, n0, shape_outline(f.get('shape', 'oval'), wx, wy), dome_profile(hgt, 0.25 * th), ci, SATIN,
                      rot=rot, p1=wy / nstr, p2=th, gloss=0.08, thick=th, lift=base_lift + 0.4 * lift, seat=seat)
        elif kind == 'safety_nose':
            hgt = 0.45 * min(wx, wy)
            det.patch(P0, n0, shape_outline(f.get('shape', 'triangle'), wx, wy), dome_profile(hgt, 0.15 * hgt), ci,
                      PLASTIC, rot=rot, gloss=1.0, thick=hgt, lift=lift)
    return det, np.array(spheres, float).reshape(-1, 5), blush


# ------------------------------------------------------------------------------------------------ ribbing
def rib_rounds(inst, lean, d):
    """Rounds of the piece worked as ribbing (1-based)."""
    return [i for i, rd in enumerate(inst.p.rounds, 1) if getattr(rd, 'loop', 'both') == 'rib']


def rib_yarn(inst, lean, d, i):
    """Round i worked as ribbing (fpdc, bpdc around): each stitch a post two rounds tall, front posts standing out
    and back posts sunk in between, so the band reads as vertical ribs.  Returns points and stitch ids."""
    from .toy import _catmull, _resample
    p = inst.p
    n = p.counts[i - 1]
    hw = math.pi / n
    t_top = i - 0.04
    t_bot = max(i - 2.0, 0.02) + 0.06
    mid = 0.5 * (t_top + t_bot)
    T, TH, NN, SID = [], [], [], []
    for k in range(n):
        thc = 2 * math.pi * (k + 0.5 - lean * (i - 0.5)) / n
        fp = (k % 2 == 0)
        lf = 0.75 if fp else 0.25                                  # how far the post stands out, yarn diameters
        tw = 0.10 if fp else 0.04
        pts = [
            (t_top, -1.00, 0.30),                                  # the top chain of the round, along the edge
            (t_top - 0.10, -0.60, lf - 0.10),
            (mid + 0.30, -0.45, lf + tw),                          # down one side of the post
            (mid - 0.30, -0.47, lf + tw),
            (t_bot + 0.12, -0.42, lf - 0.05),
            (t_bot - 0.05, 0.00, lf - 0.55),                       # round the post below, hidden behind it
            (t_bot + 0.12, 0.42, lf - 0.05),
            (mid - 0.30, 0.47, lf + tw),                           # and up the other side, close to the first
            (mid + 0.30, 0.45, lf + tw),
            (t_top - 0.10, 0.60, lf - 0.10),
            (t_top, 1.00, 0.30),
        ]
        for tt, du, nn in pts:
            T.append(tt); TH.append(thc + du * hw); NN.append(nn); SID.append(i * 100000 + k)
    T = np.clip(np.array(T), 0.02, p.M)
    TH = np.array(TH); NN = np.array(NN)
    B = inst.base(T, TH)
    Nm = inst.base_normal(T, TH)
    c = B.mean(0)
    if np.mean(np.sum((B - c) * Nm, 1)) < 0:
        Nm = -Nm
    P = B + Nm * (NN * d)[:, None]
    X, tg = _catmull(P, 0.3, np.array(SID))
    return _resample(X, 0.5, tg)


def with_ribbing(inst, lean, d, Xp, sid):
    """Replace the rib rounds of one piece's yarn (and the round each covers) by ribbing posts."""
    ribs = rib_rounds(inst, lean, d)
    if not ribs:
        return Xp, sid
    rnd = sid // 100000
    drop = set(ribs) | {i - 1 for i in ribs if i - 1 >= 1 and i - 1 not in ribs}
    out_X, out_s = [], []
    done = set()
    for i in sorted(set(rnd.tolist()) | set(ribs)):
        if i in ribs:
            if i not in done:
                Xr, sr = rib_yarn(inst, lean, d, i)
                out_X.append(Xr); out_s.append(sr); done.add(i)
            continue
        if i in drop:
            continue
        m = rnd == i
        out_X.append(Xp[m]); out_s.append(sid[m])
    return np.concatenate(out_X), np.concatenate(out_s)
