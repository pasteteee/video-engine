"""Remove folded (flipped) triangles from an amikit mesh: where an applique's outer rounds crowd onto a curved
piece, the stitch relief folds over itself and renders as dark specks.  Relax just those spots."""
import numpy as np


def flips(V, F, N):
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    return (fn * N[F].mean(1)).sum(1) < 0


def unfold(V, F, N, iters=60, grow=1):
    V = V.astype(float).copy()
    N = N.astype(float)
    nb = [[] for _ in range(len(V))]
    for a, b, c in F:
        nb[a] += [b, c]; nb[b] += [a, c]; nb[c] += [a, b]
    nb = [np.unique(x) if x else np.zeros(0, int) for x in nb]
    # band edges (each round is its own strip) stay put, or the rounds would part and show gaps
    E = np.sort(np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), 1)
    u, cnt = np.unique(E, axis=0, return_counts=True)
    edge = np.zeros(len(V), bool); edge[u[cnt == 1].ravel()] = True
    for it in range(iters):
        bad = flips(V, F, N)
        if not bad.any():
            break
        sel = np.zeros(len(V), bool); sel[F[bad].ravel()] = True
        for _ in range(grow):
            s2 = sel.copy()
            for i in np.where(sel)[0]:
                s2[nb[i]] = True
            sel = s2
        idx = np.where(sel & ~edge)[0]
        avg = np.array([V[nb[i]].mean(0) if len(nb[i]) else V[i] for i in idx])
        # move toward the neighbours' average, keeping the height along the normal (no shrinking into the toy)
        d = avg - V[idx]
        n = N[idx]
        d_t = d - n * (d * n).sum(1, keepdims=True)
        V[idx] += 0.6 * d_t + 0.3 * n * (d * n).sum(1, keepdims=True)
    return V.astype(np.float32), int(flips(V, F, N).sum())


def tuck(parts, spec):
    """Appliques stacked on one piece (a hood trim under a face patch): wherever an under-layer comes within a
    yarn's thickness of the layer on top, tuck it back so it never pokes through as specks."""
    from scipy.spatial import cKDTree
    app = {a['part']: (a['on'], a.get('lift', 0.0)) for a in spec.get('assembly', []) if a.get('applique')}
    by = {}
    for p in parts:
        if p['mat'] == 0:
            by.setdefault(p['piece'].rsplit('_', 1)[0] if p['piece'] not in app else p['piece'], []).append(p)
    names = list(app)
    for a in names:
        for b in names:
            if a == b or app[a][0] != app[b][0] or app[a][1] >= app[b][1]:
                continue
            top = np.concatenate([p['V'] for p in by.get(b, [])]) if by.get(b) else None
            if top is None:
                continue
            tr = cKDTree(top)
            for p in by.get(a, []):
                V = p['V'].astype(float)
                d, _ = tr.query(V)
                w = np.clip((3.0 - d) / 1.5, 0, 1)
                p['V'] = (V - p['N'].astype(float) * (1.4 * w)[:, None]).astype(np.float32)


def backing(parts, spec, depth=0.3):
    """Each applique gets a lining of its own yarn a little beneath it: the gaps between its rounds then read as
    grooves in the same colour, never as specks of the piece underneath."""
    app = {a['part'] for a in spec.get('assembly', []) if a.get('applique')}
    for p in parts:
        base = p['piece'][:-2] if p['piece'][-2:] in ('_L', '_R') else p['piece']
        if p['mat'] != 0 or base not in app:
            continue
        V, F, N = p['V'].astype(float), p['F'], p['N'].astype(float)
        n = len(V)
        p['V'] = np.concatenate([V, V - N * depth]).astype(np.float32)
        p['F'] = np.concatenate([F, F + n]).astype(np.int32)
        for k in ('C', 'N', 'UV', 'H'):
            p[k] = np.concatenate([p[k], p[k] * (0.92 if k == 'C' else 1)]).astype(np.float32)


def overlap_rounds(parts, spec, kv, ext=0.6):
    """Each round of an applique is its own strip; where the patch wraps a curved piece the strips part a little.
    Stretch every strip's two edge rows outward so neighbouring rounds overlap like real stitches do."""
    app = {a['part'] for a in spec.get('assembly', []) if a.get('applique')}
    nv = kv + 1
    for p in parts:
        base = p['piece'][:-2] if p['piece'][-2:] in ('_L', '_R') else p['piece']
        if p['mat'] != 0 or base not in app:
            continue
        V = p['V'].astype(float)
        T = p['UV'][:, 1]
        # strips are consecutive blocks of nu rows of nv vertices; a new block starts where the row's T changes
        if len(V) % nv:
            continue
        R = len(V) // nv
        T0 = T.reshape(R, nv)[:, 0]
        starts = [0] + [r for r in range(1, R) if abs(T0[r] - T0[r - 1]) > 1e-4] + [R]
        G = V.reshape(R, nv, 3)
        for r0, r1 in zip(starts[:-1], starts[1:]):
            if r1 - r0 < 2:
                continue
            g = G[r0:r1]
            g[:, 0] += (g[:, 0] - g[:, 1]) * ext * kv / 3
            g[:, -1] += (g[:, -1] - g[:, -2]) * ext * kv / 3
        p['V'] = G.reshape(-1, 3).astype(np.float32)


def reorient(parts):
    """A triangle still folded after relaxing is turned to face out with its neighbours (else it renders black)."""
    for p in parts:
        if p['mat'] != 0:
            continue
        bad = flips(p['V'].astype(float), p['F'], p['N'].astype(float))
        if bad.any():
            F = p['F'].copy(); F[bad] = F[bad][:, ::-1]; p['F'] = F
