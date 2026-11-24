"""Yarn toys as Blender meshes: every piece's yarn swept into a tube (cotton with plies), the core, felt and satin
details, glossy eyes.  Posed per frame from Python with the story engine's rig (rigid pieces, elbow bends, eye pops
and blinks), plus a real opening mouth: the front of the head parts like an iris around a dark throat with a tongue,
so a prop can slide out from inside."""
import json, math, sys
import numpy as np
import bpy
from mathutils import Matrix

sys.path.insert(0, '/home/user/work/story')
from engine import rig as _rig, _rod, clamp  # noqa: E402

YARN_SIDES = 6
MM = 0.001
K = np.array([[1.0, 0, 0], [0, 0, -1.0], [0, 1.0, 0]])     # toy (x, y up, z front) -> Blender (x, -z, y)


def bmat(R, t, off=np.zeros(3)):
    """Blender matrix_world from a toy-space (R, t) in mm."""
    M = np.eye(4)
    M[:3, :3] = K @ R * MM
    M[:3, 3] = K @ t * MM + off
    return Matrix(M.tolist())


def tube(P, r, sides=YARN_SIDES, centre=None):
    n = len(P)
    T = np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-9
    ref = P - (centre if centre is not None else P.mean(0))
    N = ref - (ref * T).sum(1, keepdims=True) * T
    bad = np.linalg.norm(N, axis=1) < 1e-6
    N[bad] = np.cross(T[bad], [0, 1, 0])
    N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-9
    B = np.cross(T, N)
    ang = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    V = P[:, None, :] + r * (np.cos(ang)[None, :, None] * N[:, None, :] + np.sin(ang)[None, :, None] * B[:, None, :])
    V = V.reshape(-1, 3)
    i = np.arange(n - 1)[:, None]
    j = np.arange(sides)[None, :]
    a = i * sides + j
    F = np.stack([a, i * sides + (j + 1) % sides, (i + 1) * sides + (j + 1) % sides, (i + 1) * sides + j], -1).reshape(-1, 4)
    seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    return V, F, np.repeat(seg, sides), np.tile(ang / (2 * np.pi), n)


def mesh_obj(name, V, F, cols=None, uv=None, coll=None, mat=None, smooth=True):
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(V))
    me.vertices.foreach_set('co', np.asarray(V, np.float32).ravel())
    nl = F.shape[1]
    me.loops.add(len(F) * nl)
    me.loops.foreach_set('vertex_index', F.astype(np.int32).ravel())
    me.polygons.add(len(F))
    me.polygons.foreach_set('loop_start', (np.arange(len(F)) * nl).astype(np.int32))
    me.polygons.foreach_set('loop_total', np.full(len(F), nl, np.int32))
    me.update(calc_edges=True)
    if cols is not None:
        at = me.color_attributes.new('col', 'FLOAT_COLOR', 'POINT')
        at.data.foreach_set('color', np.hstack([cols, np.ones((len(cols), 1))]).astype(np.float32).ravel())
    if uv is not None:
        uvl = me.uv_layers.new(name='UVMap')
        uvl.data.foreach_set('uv', uv[F.ravel()].astype(np.float32).ravel())
    me.polygons.foreach_set('use_smooth', np.full(len(F), smooth))
    ob = bpy.data.objects.new(name, me)
    (coll or bpy.context.scene.collection).objects.link(ob)
    if mat:
        me.materials.append(mat)
    return ob


def set_co(ob, V):
    ob.data.vertices.foreach_set('co', np.asarray(V, np.float32).ravel())
    ob.data.update()


def srgb2lin(c):
    c = np.asarray(c, float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


class _DN:
    """The bits of a Dancer the engine's rig needs, rebuilt from the npz."""

    def __init__(self, pieces):
        self.pieces = pieces
        for p in pieces:
            p['joint'] = np.array(p['joint'])
            p['dir'] = np.array(p['dir'])
            p['pid'] = p['name']
            p['parent'] = None if p['parent'] < 0 else p['parent']
        self.order, seen = [], set()
        while len(self.order) < len(pieces):
            for k, p in enumerate(pieces):
                if k not in seen and (p['parent'] is None or p['parent'] in seen):
                    self.order.append(k); seen.add(k)

    def transforms(self, local, root):
        out = [None] * len(self.pieces)
        for k in self.order:
            p = self.pieces[k]
            Rl = local.get(k, np.eye(3))
            if p['parent'] is None:
                out[k] = (root[0] @ Rl, root[1])
            else:
                Rp, tp = out[p['parent']]
                J = p['joint']
                out[k] = (Rp @ Rl, Rp @ (J - Rl @ J) + tp)
        return out


def ramp(V, p, L):
    u = np.clip(((V - p['joint']) @ p['dir']) / L, 0, 1)
    w = np.clip((u - 0.3) / 0.6, 0, 1)
    return w * w * (3 - 2 * w)


class Toy3D:
    def __init__(self, npz, key, mats, coll, home=(0.0, 0.0), off=np.zeros(3)):
        z = np.load(npz, allow_pickle=True)
        self.key, self.home, self.off = key, home, off
        self.X, self.C, self.pal, self.d = z['X'], z['C'], srgb2lin(z['pal']), float(z['d'])
        self.dn = _DN(json.loads(str(z['pieces'])))
        self.pieces = self.dn.pieces
        self.height, self.width = float(z['height']), float(z['width'])
        self.arm = {}
        for k, v in json.loads(str(z['arm'])).items():
            k = int(k)
            self.arm[k] = dict(E=np.array(v['E']), ax=np.array(v['ax']), L=v['L'], tip=np.array(v['tip']),
                               side=self.pieces[k]['side'])
        r = self.d * 0.5 * 0.95
        self.objs, self.rest, self.armw = [], [], {}
        core_X, core_k, core_len = z['core_X'], list(z['core_k']), z['core_len']
        cstart = np.r_[0, np.cumsum(core_len)]
        for k, p in enumerate(self.pieces):
            P = self.X[p['start']:p['end']]
            cen = P.mean(0)
            V, F, u, v = tube(P, r, centre=cen)
            cols = np.repeat(self.pal[self.C[p['start']:p['end']]], YARN_SIDES, axis=0)
            uv = np.stack([u / self.d, v], 1)
            if k in core_k:
                j = core_k.index(k)
                Pc = core_X[cstart[j]:cstart[j + 1]]
                Vc, Fc, uc, vc = tube(Pc, r * 1.2, 4, centre=cen)
                cc = self.pal[self.C[p['start']:p['end']]]
                idx = np.minimum(np.arange(len(Pc)) * len(cc) // max(1, len(Pc)), len(cc) - 1)
                F = np.vstack([F, Fc + len(V)])
                uv = np.vstack([uv, np.stack([uc / self.d, vc], 1)])
                cols = np.vstack([cols, np.repeat(cc[idx] * 0.55, 4, axis=0)])
                V = np.vstack([V, Vc])
            ob = mesh_obj(f'{key}.{p["name"]}', V, F, cols, uv, coll, mats['yarn'])
            self.objs.append(ob)
            self.rest.append(V)
            if k in self.arm:
                self.armw[k] = ramp(V, p, self.arm[k]['L'])
        dV, dF, info = z['det_V'], z['det_F'], z['det_info']
        self.dets = []
        vo = fo = 0
        for row in info:
            k, ci, matk, nv, nf = int(row[0]), int(row[1]), int(row[2]), int(row[4]), int(row[5])
            V = dV[vo:vo + nv].copy()
            F = (dF[fo:fo + nf] - vo).reshape(-1, 3)
            vo += nv; fo += nf
            col = self.pal[ci % len(self.pal)]
            m = mats['satin'] if matk == 1 else mats['felt']
            ob = mesh_obj(f'{key}.det{len(self.dets)}', V, F, np.tile(col, (len(V), 1)), None, coll, m)
            w = ramp(V, self.pieces[k], self.arm[k]['L']) if k in self.arm else None
            self.dets.append(dict(k=k, ob=ob, V=V, w=w, ci=ci, mat=matk))
        self.eyes = []
        for s in z['spheres']:
            k, c, rr = int(s[0]), np.array(s[1:4]), float(s[4])
            me = bpy.data.meshes.get('eye_sphere')
            if me is None:
                bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=20, radius=1.0)
                tmp = bpy.context.active_object
                bpy.ops.object.shade_smooth()
                me = tmp.data
                me.name = 'eye_sphere'
                bpy.data.objects.remove(tmp)
            ob = bpy.data.objects.new(f'{key}.eye', me)
            coll.objects.link(ob)
            if not me.materials:
                me.materials.append(mats['eye'])
            P = self.X[self.pieces[k]['start']:self.pieces[k]['end']]
            nrm = c - P.mean(0)
            nrm /= np.linalg.norm(nrm)
            self.eyes.append((k, ob, c, rr, nrm))
        self.mouth = None
        self.TR = None

    # ---------------------------------------------------------------- mouth
    def add_mouth(self, mats, coll, det_index, pieces, depth=40.0, amax=17.0, bmax=13.0):
        """Opening mouth centred on a face detail (the stitched mouth).  pieces: names of the head shell pieces that
        part around the hole.  Builds the throat (dark tube, cap) and a tongue in the head's frame."""
        dm = self.dets[det_index]
        k = dm['k']
        c = dm['V'].mean(0)
        P = self.X[self.pieces[k]['start']:self.pieces[k]['end']]
        n = np.array([0, 0, 1.0])
        ex = np.array([1.0, 0, 0])
        ey = np.cross(n, ex)
        ks = [i for i, p in enumerate(self.pieces) if p['name'] in pieces]
        # throat: elliptical tube going back into the head, closed at the end
        m, s = 28, 10
        th = np.linspace(0, 2 * np.pi, m, endpoint=False)
        al = np.linspace(1.5, -depth, s)
        ring = np.stack([np.cos(th), np.sin(th)], 1)
        V, F = [], []
        for i, a in enumerate(al):
            g = 1.0 - 0.25 * (i / (s - 1)) ** 2
            for x, y in ring:
                V.append([x * g, y * g, a])
        for i in range(s - 1):
            for j in range(m):
                F.append([i * m + j, i * m + (j + 1) % m, (i + 1) * m + (j + 1) % m, (i + 1) * m + j][::-1])
        V.append([0, 0, -depth - 4]); ci = len(V) - 1
        Fl = [[(s - 1) * m + (j + 1) % m, (s - 1) * m + j, ci] for j in range(m)]
        V = np.array(V)
        throat = mesh_obj(f'{self.key}.throat', V, np.array(F), None, None, coll, mats['throat'])
        cap = mesh_obj(f'{self.key}.throatcap', V, np.array(Fl), None, None, coll, mats['throat'])
        # tongue: a squashed blob lying in the bottom of the throat, sticking forward a little
        u, v = np.meshgrid(np.linspace(0, np.pi, 14), np.linspace(0, 2 * np.pi, 24, endpoint=False), indexing='ij')
        TV = np.stack([np.sin(u) * np.cos(v) * 0.62, np.sin(u) * np.sin(v) * 0.22 - 0.62, np.cos(u) * 0.75 * depth / bmax * 0.45], -1).reshape(-1, 3)
        TV[:, 2] -= depth * 0.32 / 1.0
        Ft = []
        for i in range(13):
            for j in range(24):
                Ft.append([i * 24 + j, i * 24 + (j + 1) % 24, (i + 1) * 24 + (j + 1) % 24, (i + 1) * 24 + j])
        tongue = mesh_obj(f'{self.key}.tongue', TV, np.array(Ft), None, None, coll, mats['tongue'])
        self.mouth = dict(c=c, n=n, ex=ex, ey=ey, k=k, ks=ks, throat=throat, cap=cap, tongue=tongue, amax=amax,
                          bmax=bmax, depth=depth, det=det_index, TV=TV)
        # which details part with the mouth (all on the mouth's pieces)
        self.mouth['dets'] = [i for i, d in enumerate(self.dets) if d['k'] in ks]

    def _iris(self, V, op, smile=0.0):
        """Part the front shell around the open mouth.  V: rest verts in the head frame."""
        M = self.mouth
        a = M['amax'] * (0.55 + 0.45 * op) * (1 + 0.25 * smile)
        b = max(0.4, M['bmax'] * op)
        d = V - M['c']
        al = d @ M['n']
        qx, qy = d @ M['ex'], d @ M['ey']
        cy = -0.25 * b                                   # the jaw drops: the hole sits a little low
        qy2 = qy - cy
        r = np.hypot(qx, qy2) + 1e-9
        cs, sn = qx / r, qy2 / r
        rh = a * b / np.sqrt((b * cs) ** 2 + (a * sn) ** 2)
        w = 16.0 + 6 * op
        ro = rh + w
        front = np.clip((al + 14.0) / 8.0, 0, 1)        # only the front shell
        sel = (r < ro) & (front > 0)
        rn = np.where(sel, rh + (r / ro) * (ro - rh), r)
        rn = r + (rn - r) * front
        lip = np.where(sel, np.clip(1 - (rn - rh) / w, 0, 1), 0.0) * front
        # smile: corners up
        V2 = (M['c'] + np.outer(cs * rn, M['ex']) + np.outer(sn * rn + cy + smile * 3.0 * (cs ** 2) * lip, M['ey'])
              + np.outer(al - lip ** 2 * 3.5 * op, M['n']))
        return np.where(sel[:, None], V2, V)

    # ---------------------------------------------------------------- posing
    def pose(self, p, mouth=0.0, smile=0.0, blush=0.0):
        hide = p['show'] < 0.5
        p = dict(p)
        p['x'] += self.home[0]
        p['z'] += self.home[1]
        local, (R0, t0) = _rig(self, p)
        TR = self.dn.transforms(local, (R0, t0 + np.array([self.home[0], 0.0, self.home[1]])))
        self.TR, self.p = TR, p
        mk = self.mouth['ks'] if self.mouth else []
        for k, ob in enumerate(self.objs):
            ob.hide_render = hide
            if hide:
                continue
            R, t = TR[k]
            V = self.rest[k]
            if k in self.armw:
                ang = p['bendL'] if self.pieces[k]['side'] >= 0 else p['bendR']
                A = self.arm[k]
                V = A['E'] + _rod(V - A['E'], A['ax'], np.radians(ang) * self.armw[k])
                set_co(ob, V)
            elif k in mk:
                set_co(ob, self._iris(V, mouth, smile) if mouth > 0.01 else V)
            ob.matrix_world = bmat(R, t, self.off)
        for i, dd in enumerate(self.dets):
            ob = dd['ob']
            ob.hide_render = hide
            if hide:
                continue
            k = dd['k']
            R, t = TR[k]
            V = dd['V']
            if dd['w'] is not None:
                ang = p['bendL'] if self.pieces[k]['side'] >= 0 else p['bendR']
                A = self.arm[k]
                V = A['E'] + _rod(V - A['E'], A['ax'], np.radians(ang) * dd['w'])
                set_co(ob, V)
            elif k in mk:
                set_co(ob, self._iris(V, mouth, smile) if mouth > 0.01 else V)
            ob.matrix_world = bmat(R, t, self.off)
        if self.mouth:
            M = self.mouth
            R, t = TR[M['k']]
            op = mouth
            a = M['amax'] * (0.55 + 0.45 * op) * (1 + 0.25 * smile)
            b = max(0.4, M['bmax'] * op)
            B = np.stack([M['ex'], M['ey'], M['n']], 1)
            Rm = B @ np.diag([a * 1.05, b * 1.05, 1.0])
            cm = M['c'] + M['ey'] * (-0.25 * b)
            for ob in (M['throat'], M['cap'], M['tongue']):
                ob.hide_render = hide or op < 0.03
                ob.matrix_world = bmat(R @ Rm, R @ cm + t, self.off)
            # tongue keeps its own width, follows the opening's height
            M['tongue'].matrix_world = bmat(R @ B @ np.diag([a, max(b, 4.0), 1.0]), R @ cm + t, self.off)
        e = p['eye']
        bl = p.get('blink', 1.0)
        sq = p.get('squint', 0.0)
        for k, ob, c, rr, nrm in self.eyes:
            ob.hide_render = hide or e * bl < 0.03
            if hide:
                continue
            R, t = TR[k]
            sc = rr * max(e, 0.05)
            c2 = c + nrm * rr * (e - 1) * 0.55
            up = np.array([0, 1.0, 0]) - nrm * nrm[1]
            up /= np.linalg.norm(up) + 1e-9
            x = np.cross(up, nrm)
            Rl = np.stack([x, up, nrm], 1)
            S = np.diag([sc, sc * bl * (1 - 0.55 * sq), sc * 0.8])
            ob.matrix_world = bmat(R @ Rl @ S, R @ c2 + t, self.off)
        return TR

    def world(self, k, Pl, bent=True):
        """Toy-space world point (mm) of a rest point on piece k after the last pose."""
        R, t = self.TR[k]
        Pl = np.asarray(Pl, float)
        if bent and k in self.arm:
            ang = self.p['bendL'] if self.pieces[k]['side'] >= 0 else self.p['bendR']
            A = self.arm[k]
            Pl = A['E'] + _rod((Pl - A['E'])[None], A['ax'], np.array([math.radians(ang)]))[0]
        return R @ Pl + t

    def piece(self, name):
        for k, pc in enumerate(self.pieces):
            if pc['name'] == name:
                return k
        raise KeyError(name)

    def frame(self, k):
        return self.TR[k]
