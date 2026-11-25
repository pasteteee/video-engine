"""Finished yarn toys dancing to a beat: every piece of a toy is a rigid part of a small rig (body, head, arms, legs,
ears, tail, hat), posed per frame and drawn by the yarn renderer.

The rig comes from the spec's assembly: a piece hangs on the piece it is sewn `on`, and turns about its joint, the
middle of its yarn that touches the parent.  The role of a piece (arm, leg, ear, ...) comes from its part id.  The
choreography is a function of film time and the beat (`Moves`), so the same score drives the music and the dance.
"""
from __future__ import annotations

import math

import numpy as np

ROLES = (('head', 'head'), ('arm', 'arm'), ('hand', 'arm'), ('wing', 'arm'), ('paw', 'leg'), ('leg', 'leg'),
         ('foot', 'leg'), ('boot', 'leg'), ('ear', 'ear'), ('tail', 'tail'), ('hat', 'hat'), ('pompom', 'hat'),
         ('horn', 'stiff'))


def rot(axis, deg):
    a = np.asarray(axis, float)
    a = a / (np.linalg.norm(a) + 1e-12)
    t = math.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + math.sin(t) * K + (1 - math.cos(t)) * (K @ K)


class Dancer:
    """One toy: its yarn (rest pose, standing on y = 0, centred), core, details and spheres, and its rig."""

    def __init__(self, spec, name=None, core=0.3, scale=1.0):
        from .toy import toy_yarn
        X, D, C, pal, d, toy = toy_yarn(spec)
        self.name = name or spec.get('name', 'toy')
        self.d = d
        lo, hi = X.min(0), X.max(0)
        shift = np.array([-(lo[0] + hi[0]) / 2, -lo[1], -(lo[2] + hi[2]) / 2])
        X = (X + shift) * scale
        self.X, self.D, self.C, self.pal, self.toy = X, D, C, pal, toy
        self.height = float(X[:, 1].max())
        self.width = float(X[:, 0].max() - X[:, 0].min())
        self.pieces = [dict(p) for p in toy.yarn_pieces]
        ids = sorted((p['id'] for p in spec['parts']), key=len, reverse=True)
        on = {}
        for e in spec.get('assembly', []):
            on.setdefault(e.get('part'), e.get('on'))
        names = [p['name'] for p in self.pieces]
        for p in self.pieces:
            pid = next((i for i in ids if p['name'] == i or p['name'].startswith(i + '_')), p['part'])
            p['pid'] = pid
            toks = pid.lower().split('_')
            p['role'] = next((r for k, r in ROLES if any(t == k or t == k + 's' for t in toks)), 'stiff')
        for k, p in enumerate(self.pieces):
            par = on.get(p['pid'])
            p['parent'] = None
            if par is not None and k > 0:
                side = p['name'][len(p['pid']):]                  # '_L', '_R' or ''
                cand = [par + side, par, par + '_L']
                pk = next((j for j, n in enumerate(names) if n in cand and j != k), None)
                p['parent'] = pk if pk is not None else 0
            elif k > 0:
                p['parent'] = 0
        # the root is the body: the first piece; a piece hung on nothing hangs on it
        self.order = self._topo()
        # joints: the middle of the child's yarn nearest its parent
        from scipy.spatial import cKDTree
        for p in self.pieces:
            if p['parent'] is None:
                p['joint'] = np.array([0.0, 0.0, 0.0])
                continue
            q = self.pieces[p['parent']]
            tree = cKDTree(X[q['start']:q['end']:3])
            Xc = X[p['start']:p['end']]
            dist, _ = tree.query(Xc[::2])
            k = max(8, len(dist) // 25)
            near = np.argsort(dist)[:k]
            p['joint'] = Xc[::2][near].mean(0)
            p['side'] = float(np.sign(p['joint'][0])) if abs(p['joint'][0]) > 2 else 0.0
            p['dir'] = Xc.mean(0) - p['joint']
            p['dir'] /= np.linalg.norm(p['dir']) + 1e-9
        self.pieces[0]['side'] = 0.0
        # a prop sewn on the body but held in a paw (a candy cane) goes with the paw
        for k, p in enumerate(self.pieces):
            if p['role'] != 'stiff' or p['parent'] != 0:
                continue
            Xc = X[p['start']:p['end']:3]
            d0, _ = cKDTree(X[self.pieces[0]['start']:self.pieces[0]['end']:3]).query(Xc)
            for j, q in enumerate(self.pieces):
                if q['role'] == 'arm':
                    dj, _ = cKDTree(X[q['start']:q['end']:3]).query(Xc)
                    if (dj < 2 * d).mean() > (d0 < 2 * d).mean():
                        p['parent'] = j
                        self.order = None
                        break
        if self.order is None:
            self.order = self._topo()
        # node -> piece
        self.piece_of = np.zeros(len(X), np.int32)
        for k, p in enumerate(self.pieces):
            self.piece_of[p['start']:p['end']] = k
        # hidden core (as in grow.py): the same yarn pushed inwards, a little darker
        self.core = []
        if core > 0:
            for k, p in enumerate(self.pieces):
                seg = X[p['start']:p['end']]
                c = seg.mean(0)
                nrm = seg - c
                nrm /= np.linalg.norm(nrm, axis=1)[:, None] + 1e-9
                self.core.append((k, seg - nrm * core * d))
        # details and spheres hang on the piece nearest them
        tree = cKDTree(X)
        self.items = []
        if toy.details is not None:
            for it in toy.details.items:
                it = dict(it)
                it['V'] = (it['V'] + shift) * scale
                it['C'] = (it['C'] + shift) * scale
                _, j = tree.query(it['V'].mean(0))
                self.items.append((int(self.piece_of[j]), it))
        self.spheres = []
        for s in np.asarray(getattr(toy, 'spheres', np.zeros((0, 5))), float).reshape(-1, 5):
            s = s.copy()
            s[:3] = (s[:3] + shift) * scale
            s[3] *= scale
            _, j = tree.query(s[:3])
            self.spheres.append((int(self.piece_of[j]), s))

    def _topo(self):
        out, seen = [], set()

        def visit(k):
            if k in seen:
                return
            par = self.pieces[k]['parent']
            if par is not None:
                visit(par)
            seen.add(k)
            out.append(k)
        for k in range(len(self.pieces)):
            visit(k)
        return out

    def transforms(self, local, root):
        """local: piece index -> 3x3 rotation about its joint (in the parent's frame).  root: (R, t) of the body.
        Returns (R, t) per piece in world space."""
        out = [None] * len(self.pieces)
        for k in self.order:
            p = self.pieces[k]
            Rl = local.get(k, np.eye(3))
            if p['parent'] is None:
                R0, t0 = root
                out[k] = (R0 @ Rl, t0)
            else:
                Rp, tp = out[p['parent']]
                J = p['joint']
                out[k] = (Rp @ Rl, Rp @ (J - Rl @ J) + tp)
        return out


class Stage:
    """Several dancers in one yarn scene, posed per frame."""

    def __init__(self, dancers, places, W=1080, H=1920, ss=2, soft=1.35, core_shade=0.85, ao=0.6, floor=0.42,
                 bg=None):
        from .render import Renderer
        self.dancers = dancers
        self.places = places                      # per dancer: (x, z, facing degrees)
        pal, off = [], []
        for dn in dancers:
            off.append(len(pal))
            pal += [list(c) for c in dn.pal]
        self.NP = len(pal)
        pal2 = pal + [[v * core_shade for v in c] for c in pal]
        Xs, Cs, self.slices = [], [], []
        n = 0
        for i, dn in enumerate(dancers):
            Xs.append(dn.X); Cs.append(dn.C + off[i])
            self.slices.append(('yarn', i, None, n, n + len(dn.X)))
            n += len(dn.X)
        for i, dn in enumerate(dancers):
            for k, Xc in dn.core:
                p = dn.pieces[k]
                Xs.append(Xc); Cs.append(dn.C[p['start']:p['end']] + off[i] + self.NP)
                self.slices.append(('core', i, k, n, n + len(Xc)))
                n += len(Xc)
        self.Xrest = np.concatenate(Xs)
        self.Crest = np.concatenate(Cs).astype(np.int32)
        self.off = off
        d = dancers[0].d
        r = d / 2 / soft
        self.r = r
        kw = dict(shadow_floor=float(floor), backdrop_y=-0.5 * r)
        if bg is not None:
            kw.update(bg_top=tuple(bg[0]), bg_bot=tuple(bg[1]))
        self.rn = Renderer(W, H, ss=ss, r=r, h=0.5, soft=soft, palette=pal2, ao=ao, **kw)
        # the rest pose, placed, gives the soft section shapes; they are turned with their piece every frame
        Xp = self.Xrest.copy()
        for i, (x, z, face) in enumerate(places):
            R = rot([0, 1, 0], face)
            for kind, di, k, a, b in self.slices:
                if di == i:
                    Xp[a:b] = Xp[a:b] @ R.T + [x, 0.0, z]
        self.rn.set_scene(Xp)
        self.rn.extent *= 1.35                    # room in the shadow map for jumps and arms in the air
        self.Q0, self.c0 = self.rn._shape
        # Q was computed in placed space: take it back to each dancer's rest frame
        self.Q0 = self.Q0.copy()
        for i, (x, z, face) in enumerate(places):
            R = rot([0, 1, 0], face)
            for kind, di, k, a, b in self.slices:
                if di == i:
                    self.Q0[a:b] = self.Q0[a:b] @ R
        self.Drest = np.concatenate([dn.D for dn in dancers] +
                                    [dancers[i].D[dancers[i].pieces[k]['start']:dancers[i].pieces[k]['end']]
                                     for kind, i, k, a, b in self.slices if kind == 'core'])

    def pose(self, poses):
        """poses: per dancer (local rotations dict, (R, t) root in the dancer's own frame).  Returns world X, D, Q,
        details, spheres."""
        from .details import Details
        X = np.empty_like(self.Xrest)
        D = np.empty_like(self.Drest)
        Q = np.empty_like(self.Q0)
        TR = []
        for i, dn in enumerate(self.dancers):
            local, (R0, t0) = poses[i]
            x, z, face = self.places[i]
            Rf = rot([0, 1, 0], face)
            root = (Rf @ R0, Rf @ t0 + np.array([x, 0.0, z]))
            TR.append(dn.transforms(local, root))
        for kind, i, k, a, b in self.slices:
            dn = self.dancers[i]
            if kind == 'yarn':
                for kk, p in enumerate(dn.pieces):
                    R, t = TR[i][kk]
                    s, e = a + p['start'], a + p['end']
                    X[s:e] = self.Xrest[s:e] @ R.T + t
                    D[s:e] = self.Drest[s:e] @ R.T
                    Q[s:e] = self.Q0[s:e] @ R.T
            else:
                R, t = TR[i][k]
                X[a:b] = self.Xrest[a:b] @ R.T + t
                D[a:b] = self.Drest[a:b] @ R.T
                Q[a:b] = self.Q0[a:b] @ R.T
        det = Details(None, None, 1.0)
        for i, dn in enumerate(self.dancers):
            for k, it in dn.items:
                R, t = TR[i][k]
                it2 = dict(it)
                it2['V'] = it['V'] @ R.T + t
                it2['N'] = it['N'] @ R.T
                it2['C'] = it['C'] @ R.T + t
                row = it['row'].copy()
                row[0] += self.off[i]
                for s0 in (6, 9, 12):
                    row[s0:s0 + 3] = R @ row[s0:s0 + 3]
                it2['row'] = row
                det.items.append(it2)
        sp = []
        for i, dn in enumerate(self.dancers):
            for k, s in dn.spheres:
                R, t = TR[i][k]
                s2 = s.copy()
                s2[:3] = R @ s[:3] + t
                s2[4] += self.off[i]
                sp.append(s2)
        sp = np.array(sp).reshape(-1, 5)
        return X, D, Q, det, sp

    def render(self, poses, cam):
        X, D, Q, det, sp = self.pose(poses)
        self.rn._shape = (Q, self.c0)
        return self.rn.render(X, D, cam, colnode=self.Crest, spheres=sp, gap=2.0, details=det, details_t=1.0)
