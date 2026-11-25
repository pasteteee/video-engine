"""Toys as on the site's previews: the amikit model (smooth plump crochet pieces, stitch-by-stitch UVs, embroidery,
safety eyes, felt), shaded in Cycles with a tiled single-crochet stitch (plied legs, grooves, fibres) so every loop is
neat and even.  Posed per frame with the story engine's rig.  Faces act: eyes pop, squint and blink as whole groups
(eye + felt backing), an embroidered mouth opens into a soft rounded "D" with a dark lining, a tongue and its teeth,
and a prop can pass out through it."""
import math, pickle, sys
import numpy as np
import bpy

sys.path.insert(0, '/home/user/work/b3d')
from toys3d import bmat, mesh_obj, set_co, srgb2lin, _DN, ramp, _rig, _rod  # noqa: E402
from set3d import new_mat, N, L, setp, bump  # noqa: E402

B3 = '/home/user/work/b3d/'


def ami_materials():
    M = {}
    h_img = bpy.data.images.load(B3 + 'stitch_h.png'); h_img.colorspace_settings.name = 'Non-Color'
    a_img = bpy.data.images.load(B3 + 'stitch_ao.png'); a_img.colorspace_settings.name = 'Non-Color'
    m, nt, bs = new_mat('ami_yarn')
    uv = N(nt, 'ShaderNodeUVMap', uv_map='UVMap')
    th = N(nt, 'ShaderNodeTexImage', image=h_img, interpolation='Cubic')
    ta = N(nt, 'ShaderNodeTexImage', image=a_img, interpolation='Cubic')
    L(nt, uv.outputs[0], th.inputs[0]); L(nt, uv.outputs[0], ta.inputs[0])
    at = N(nt, 'ShaderNodeAttribute', attribute_name='col')
    mx = N(nt, 'ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY')
    import os as _os
    YB = float(_os.environ.get('YARN_BUMP', 1.0)); YD = float(_os.environ.get('YARN_DIST', 0.003))
    YA = float(_os.environ.get('YARN_AO', 1.0)); YS = float(_os.environ.get('YARN_SHEEN', 0.1))
    YT = float(_os.environ.get('YARN_SAT', 1.25))
    mx.inputs['Factor'].default_value = YA
    L(nt, at.outputs['Color'], mx.inputs[6]); L(nt, ta.outputs['Color'], mx.inputs[7])
    hs = N(nt, 'ShaderNodeHueSaturation')
    hs.inputs['Saturation'].default_value = YT
    L(nt, mx.outputs[2], hs.inputs['Color'])
    L(nt, hs.outputs['Color'], bs.inputs['Base Color'])
    setp(bs, Roughness=0.85, Sheen_Weight=YS, Sheen_Roughness=0.5, Subsurface_Weight=0.08, Subsurface_Scale=0.002)
    bump(nt, bs, th.outputs['Color'], YB, YD)
    M[0] = m
    m, nt, bs = new_mat('ami_eye')
    at = N(nt, 'ShaderNodeAttribute', attribute_name='col')
    L(nt, at.outputs['Color'], bs.inputs['Base Color'])
    setp(bs, Roughness=0.06, Coat_Weight=1.0, Coat_Roughness=0.01, Specular_IOR_Level=0.8)
    M[1] = m
    m, nt, bs = new_mat('ami_thread')
    at = N(nt, 'ShaderNodeAttribute', attribute_name='col')
    L(nt, at.outputs['Color'], bs.inputs['Base Color'])
    setp(bs, Roughness=0.5, Sheen_Weight=0.5, Sheen_Roughness=0.3)
    uv = N(nt, 'ShaderNodeUVMap', uv_map='UVMap')
    sx = N(nt, 'ShaderNodeSeparateXYZ'); L(nt, uv.outputs[0], sx.inputs[0])
    a = N(nt, 'ShaderNodeMath', operation='MULTIPLY_ADD', i_Value_001=2.2)
    L(nt, sx.outputs[0], a.inputs[0]); L(nt, sx.outputs[1], a.inputs[2])
    c = N(nt, 'ShaderNodeMath', operation='SINE'); L(nt, a.outputs[0], c.inputs[0])
    bump(nt, bs, c.outputs[0], 0.35, 0.0002)
    M[2] = m
    m, nt, bs = new_mat('ami_felt')
    at = N(nt, 'ShaderNodeAttribute', attribute_name='col')
    L(nt, at.outputs['Color'], bs.inputs['Base Color'])
    setp(bs, Roughness=1.0, Sheen_Weight=1.0, Sheen_Roughness=0.5)
    nz = N(nt, 'ShaderNodeTexNoise', i_Scale=2500.0, i_Detail=4.0)
    bump(nt, bs, nz.outputs[0], 0.25, 0.0002)
    M[3] = m
    m, nt, bs = new_mat('ami_lining')
    at = N(nt, 'ShaderNodeAttribute', attribute_name='col')
    L(nt, at.outputs['Color'], bs.inputs['Base Color'])
    setp(bs, Roughness=0.7, Sheen_Weight=0.6, Sheen_Roughness=0.4)
    m, nt, bs = new_mat('ami_sparkle')
    setp(bs, Base_Color=(1, 1, 1, 1), Roughness=0.2, Emission_Color=(1, 1, 1, 1), Emission_Strength=2.5)
    M['sparkle'] = m
    M['lining'] = bpy.data.materials['ami_lining']
    m, nt, bs = new_mat('ami_tongue')
    setp(bs, Base_Color=(0.9, 0.36, 0.42, 1), Roughness=0.6, Sheen_Weight=0.6)
    M['tongue'] = m
    return M


class AmiToy:
    def __init__(self, pkl, key, M, coll, home=(0.0, 0.0), off=np.zeros(3), absolute=False):
        self.absolute = absolute
        d = pickle.load(open(pkl, 'rb'))
        self.key, self.home, self.off = key, home, off
        rg = d['rig']
        self.dn = _DN(rg['pieces'])
        self.pieces = self.dn.pieces
        self.height, self.width = d['height'], d['width']
        self.arm = {}
        for k, v in rg['arm'].items():
            k = int(k)
            self.arm[k] = dict(E=np.array(v['E']), ax=np.array(v['ax']), L=v['L'], tip=np.array(v['tip']),
                               side=self.pieces[k]['side'])
        self.pidx = {p['name']: k for k, p in enumerate(self.pieces)}
        self.alias = rg.get('alias', {})
        self.pmap = rg.get('pmap', {})
        self.objs = []
        for o in d['parts']:
            k = self.kof(o['piece'])
            col = srgb2lin(o['C'])
            uv = o['UV'] if o['mat'] in (0, 2) else None
            ob = mesh_obj(f"{key}.{o['name']}", o['V'], o['F'], col, uv, coll, M[o['mat']])
            w = ramp(o['V'], self.pieces[k], self.arm[k]['L']) if k in self.arm else None
            self.objs.append(dict(ob=ob, k=k, V=o['V'].astype(float), w=w, fid=o['fid'], mat=o['mat'], name=o['name'], N=o['N']))
        # eye groups: each safety eye with the felt / thread right around it
        self.eyes = []
        for e in [x for x in self.objs if x['mat'] == 1]:
            c = e['V'].mean(0)
            r = np.linalg.norm(e['V'] - c, axis=1).max()
            grp = [e] + [x for x in self.objs if x['mat'] == 3 and x['k'] == e['k']
                         and np.linalg.norm(x['V'].mean(0) - c) < r * 1.6]
            nrm = e['N'].astype(float).mean(0)
            nrm /= np.linalg.norm(nrm)
            nrm = 0.6 * nrm + 0.4 * np.array([0, 0, 1.0]); nrm /= np.linalg.norm(nrm)   # gaze a little forward
            self.eyes.append(dict(c=c, r=r, n=nrm, grp=grp))
        spark = bpy.data.meshes.get('sparkle_dot')
        if spark is None:
            bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=1.0)
            tmp = bpy.context.active_object
            bpy.ops.object.shade_smooth()
            spark = tmp.data; spark.name = 'sparkle_dot'
            bpy.data.objects.remove(tmp)
            spark.materials.append(M['sparkle'])
        sV = np.array([v.co[:] for v in spark.vertices])
        sF = np.array([list(p.vertices) for p in spark.polygons if len(p.vertices) == 4] + [])
        for e in self.eyes:
            n = e['n']
            up = np.array([0, 1.0, 0]) - n * n[1]; up /= np.linalg.norm(up)
            sd = np.cross(up, n)
            # crocheted eyelid: a thin cap of the skin's yarn over the eye, it rolls down to blink or squint
            Ve = e['grp'][0]['V']
            A = np.hstack([2 * Ve, np.ones((len(Ve), 1))])
            sol = np.linalg.lstsq(A, (Ve ** 2).sum(1), rcond=None)[0]
            e['sc'] = sol[:3]; e['sr'] = math.sqrt(max(sol[3] + sol[:3] @ sol[:3], 1e-6))
            skin = [x for x in self.objs if x['k'] == e['grp'][0]['k'] and x['mat'] == 0]
            Vs = np.concatenate([x['V'] for x in skin])
            Cs = np.concatenate([np.array([c.color[:3] for c in x['ob'].data.attributes['col'].data]) for x in skin])
            j0 = np.argsort(np.linalg.norm(Vs - e['c'], axis=1))[:40]
            e['lidcol'] = Cs[j0].mean(0)
            e['up'], e['sd'] = up, sd
            e['lid'] = None
        self.coll, self.Mmat = coll, M
        for e in self.eyes:
            for x in e['grp']:
                x['eye'] = e
        self.mouth = None
        self.TR = None

    def kof(self, name, depth=0):
        """Rig piece that carries a part: itself, its unmirrored id (cheek_L -> cheek), or the part it is sewn on."""
        if name in self.pidx:
            return self.pidx[name]
        if self.pmap.get(name) in self.pidx:
            return self.pidx[self.pmap[name]]
        base = name[:-2] if name[-2:] in ('_L', '_R') else name
        for nm in (base + '_L' if name.endswith('_L') else None, base):
            if nm and nm in self.pidx:
                return self.pidx[nm]
        on = self.alias.get(base)
        if on and depth < 6:
            side = name[-2:] if name[-2:] in ('_L', '_R') else ''
            if on + side in self.pidx:
                return self.pidx[on + side]
            return self.kof(on, depth + 1)
        return 0

    def objs_piece_centre(self, k):
        Vs = [x['V'] for x in self.objs if x['k'] == k and x['mat'] == 0]
        return np.concatenate(Vs).mean(0) if Vs else np.zeros(3)

    def piece(self, name):
        return self.pidx[name]

    # ---------------------------------------------------------------- mouth
    def add_swaps(self, pkl, M, coll):
        """Replacement mouths (stop-motion style): embroidered half-open and open mouths swapped in by state."""
        d = pickle.load(open(pkl, 'rb'))
        self.swaps = {}
        for st, ms in d.items():
            obs = []
            for o in ms:
                k = self.kof(o['piece'])
                uv = o['UV'] if o['mat'] in (0, 2) else None
                ob = mesh_obj(f"{self.key}.{st}.{o['name']}", o['V'], o['F'], srgb2lin(o['C']), uv, coll, M[o['mat']])
                obs.append((ob, k))
            self.swaps[st] = obs

    def add_mouth(self, M, coll, fids, normal=(0, 0, 1.0), lining=True, ky=1.9, tshrink=0.3):
        """fids: face-item ids that make the mouth (the embroidered mouth first, then teeth)."""
        mo = [x for x in self.objs if x['fid'] in fids]
        main = [x for x in mo if x['fid'] == fids[0]]
        Vm = np.concatenate([x['V'] for x in main])
        n = np.asarray(normal, float); n /= np.linalg.norm(n)
        ex = np.array([1.0, 0, 0]); ey = np.cross(n, ex)
        c = Vm.mean(0)
        top = c + ey * ((Vm - c) @ ey).max()
        w = ((Vm - c) @ ex).ptp() / 2
        h = ((Vm - c) @ ey).ptp() / 2
        k = main[0]['k']
        # the face surface under the mouth (to keep the opened mouth on it)
        face = np.concatenate([x['V'] for x in self.objs if x['k'] == k and x['mat'] == 0])
        self.mouth = dict(ky=ky, tshrink=tshrink, c=c, top=top, n=n, ex=ex, ey=ey, w=w, h=h, k=k, objs=mo, face=face, main=fids[0])
        self._fit_face()
        self.mouth['gc'] = {f: np.concatenate([x['V'] for x in mo if x['fid'] == f]).mean(0) for f in set(x['fid'] for x in mo)}
        # lining + tongue: an oval patch just in front of the face, shown as the mouth opens
        m, s = 40, 8
        th = np.linspace(0, 2 * np.pi, m, endpoint=False)
        V = [[0, 0, 0]]
        for i in range(1, s + 1):
            rr = i / s
            for t in th:
                V.append([math.cos(t) * rr, math.sin(t) * rr, 0])
        V = np.array(V)
        F = [[0, 1 + j, 1 + (j + 1) % m] for j in range(m)]
        for i in range(s - 1):
            for j in range(m):
                a0 = 1 + i * m
                F.append([a0 + j, a0 + m + j, a0 + m + (j + 1) % m])
                F.append([a0 + j, a0 + m + (j + 1) % m, a0 + (j + 1) % m])
        F = np.array(F)
        self.mouth['disc'] = V
        rr = np.linalg.norm(V[:, :2], axis=1)
        g = np.clip(rr, 0, 1) ** 1.5
        lc = np.outer(1 - g, [0.03, 0.004, 0.012]) + np.outer(g, [0.42, 0.06, 0.12])
        self.mouth['lining'] = mesh_obj(f'{self.key}.lining', V, F, lc, None, coll, M['lining'])
        self.mouth['tongue'] = mesh_obj(f'{self.key}.tongue', V, F, None, None, coll, M['tongue'])

    def _fit_face(self):
        Mo = self.mouth
        F = Mo['face'] - Mo['top']
        qx, qy, al = F @ Mo['ex'], F @ Mo['ey'], F @ Mo['n']
        near = (np.hypot(qx, qy) < 3.2 * max(Mo['w'], 8)) & (al > -6)
        qx, qy, al = qx[near], qy[near], al[near]
        # keep the outermost (front) sheet only: per small cell the highest point
        A = np.stack([np.ones_like(qx), qx, qy, qx * qx, qy * qy, qx * qy], 1)
        coef = np.linalg.lstsq(A, al, rcond=None)[0]
        for _ in range(3):
            res = al - A @ coef
            keep = res > -1.0
            coef = np.linalg.lstsq(A[keep], al[keep], rcond=None)[0]
        Mo['coef'] = coef

    def _h(self, qx, qy):
        c = self.mouth['coef']
        return c[0] + c[1] * qx + c[2] * qy + c[3] * qx * qx + c[4] * qy * qy + c[5] * qx * qy

    def _place(self, qx, qy, lift):
        Mo = self.mouth
        return Mo['top'] + np.outer(qx, Mo['ex']) + np.outer(qy, Mo['ey']) + np.outer(self._h(qx, qy) + lift, Mo['n'])

    def _mouth_verts(self, x, op, smile):
        Mo = self.mouth
        V = x['V']
        d = V - Mo['top']
        qx, qy, al = d @ Mo['ex'], d @ Mo['ey'], d @ Mo['n']
        lift = al - self._h(qx, qy)
        sx = 1 + 0.55 * op + 0.15 * smile
        sy = 1 + Mo['ky'] * op
        if x['fid'] == self.mouth['main']:
            qx2 = qx * sx
            qy2 = qy * sy + smile * 2.2 * (qx / max(Mo['w'], 1)) ** 2
            return self._place(qx2, qy2, lift)
        # teeth and other bits move with the lip they sit on, without stretching
        G = Mo['gc'][x['fid']]
        cx, cy = (G - Mo['top']) @ Mo['ex'], (G - Mo['top']) @ Mo['ey']
        dx, dy = cx * sx - cx, cy * sy - cy + smile * 2.2 * (cx / max(Mo['w'], 1)) ** 2
        sh = 1 - Mo['tshrink'] * min(op, 1)
        return self._place(cx + dx + (qx - cx) * sh, cy + dy + (qy - cy) * sh, lift * sh)

    # ---------------------------------------------------------------- posing
    def pose(self, p, mouth=0.0, smile=0.0):
        if getattr(self, 'swaps', None):
            return self._pose_swap(p, mouth, smile)
        return self._pose(p, mouth, smile)

    def _pose_swap(self, p, mouth, smile):
        st = 'closed' if mouth < 0.18 else 'half' if mouth < 0.55 else 'open'
        TR = self._pose(p, 0.0, smile)
        hide = p['show'] < 0.5
        for x in self.mouth['objs']:
            x['ob'].hide_render = hide or st != 'closed'
        for name in ('lining', 'tongue'):
            self.mouth[name].hide_render = True
        for s_, obs in self.swaps.items():
            for ob, k in obs:
                ob.hide_render = hide or s_ != st
                R, t = TR[k]
                ob.matrix_world = bmat(R, t, self.off)
        self.mstate = st
        return TR

    def _pose(self, p, mouth=0.0, smile=0.0):
        hide = p['show'] < 0.5
        p = dict(p)
        if not self.absolute:
            p['x'] += self.home[0]
            p['z'] += self.home[1]
        local, (R0, t0) = _rig(self, p)
        TR = self.dn.transforms(local, (R0, t0 + np.array([self.home[0], 0.0, self.home[1]])))
        self.TR, self.p = TR, p
        e_sc = p['eye']
        bl = p.get('blink', 1.0)
        sq = p.get('squint', 0.0)
        mo_ids = set(id(x) for x in self.mouth['objs']) if self.mouth else set()
        for x in self.objs:
            ob = x['ob']
            ob.hide_render = hide
            if hide:
                continue
            k = x['k']
            R, t = TR[k]
            V = x['V']
            changed = False
            if x['w'] is not None:
                ang = p['bendL'] if self.pieces[k]['side'] >= 0 else p['bendR']
                A = self.arm[k]
                if abs(ang) > 0.05:
                    V = A['E'] + _rod(V - A['E'], A['ax'], np.radians(ang) * x['w'])
                changed = True
            if 'eye' in x:
                e = x['eye']
                ey = np.array([0, 1.0, 0]) - e['n'] * e['n'][1]
                ey /= np.linalg.norm(ey)
                d = V - e['c']
                along_y = d @ ey
                s = e_sc
                V = e['c'] + d * s + e['n'] * e['r'] * (s - 1) * 0.35
                changed = True
            if id(x) in mo_ids:
                V = self._mouth_verts(x, mouth, smile) if (mouth > 0.01 or smile > 0.01) else V
                changed = True
            if changed:
                set_co(ob, V)
            ob.matrix_world = bmat(R, t, self.off)
        lid = float(np.clip(max(1 - bl, 0.55 * sq), 0, 1))
        for e in self.eyes:
            self._lid(e, lid, e_sc, TR, hide)
        if self.mouth:
            Mo = self.mouth
            R, t = TR[Mo['k']]
            vis = mouth > 0.04
            W = Mo['w'] * (1 + 0.55 * mouth) * 0.86
            Hh = Mo['h'] * (1 + Mo['ky'] * mouth) * 0.8
            cen = Mo['top'] + Mo['ey'] * (-Mo['h'] * (1 + Mo['ky'] * mouth))
            D = Mo['disc']
            for name, sx, sy, dy, lift in (('lining', W, Hh, 0.0, 0.35), ('tongue', W * 0.55, Hh * 0.38, -Hh * 0.5, 0.5)):
                cq = (cen - Mo['top']) @ Mo['ey']
                P = self._place(D[:, 0] * sx, D[:, 1] * sy + dy + cq, lift)
                ob = Mo[name]
                ob.hide_render = hide or not vis
                set_co(ob, P)
                ob.matrix_world = bmat(R, t, self.off)
        return TR

    def _lid(self, e, lid, s, TR, hide):
        """Eyelid cap covering the eye from the top down to `lid` (0 open .. 1 closed)."""
        nu, nv = 28, 10
        if e['lid'] is None:
            F = []
            for i in range(nu - 1):
                for j in range(nv - 1):
                    a0 = i * nv + j
                    F.append([a0, a0 + 1, a0 + nv + 1, a0 + nv])
            V0 = np.zeros((nu * nv, 3))
            uv = np.stack(np.meshgrid(np.linspace(0, 9, nu), np.linspace(0, 3, nv), indexing='ij'), -1).reshape(-1, 2)
            ob = mesh_obj(f'{self.key}.lid', V0, np.array(F), np.tile(e['lidcol'], (len(V0), 1)), uv, self.coll, self.Mmat[0])
            e['lid'] = ob
        ob = e['lid']
        ob.hide_render = hide or lid < 0.03
        if ob.hide_render:
            return
        R, t = TR[e['grp'][0]['k']]
        rad = e['sr'] * s * 1.12
        cen = e['sc'] + e['n'] * e['r'] * (s - 1) * 0.35 + (e['sc'] - e['c']) * (s - 1)
        n, up, sd = e['n'], e['up'], e['sd']
        ph = np.linspace(-1.75, 1.75, nu)                 # around, across the front of the eye
        th = np.linspace(0.0, 0.08 + lid * (math.pi * 0.62), nv)   # from the top down to the lid edge
        PH, TH = np.meshgrid(ph, th, indexing='ij')
        # direction: start at 'up' tilted to the front, rotate down towards the front/bottom
        d = (np.cos(TH)[..., None] * up + np.sin(TH)[..., None] * (np.cos(PH)[..., None] * n + np.sin(PH)[..., None] * sd))
        V = (cen + rad * d).reshape(-1, 3)
        set_co(ob, V)
        ob.matrix_world = bmat(R, t, self.off)

    def world(self, k, Pl, bent=True):
        R, t = self.TR[k]
        Pl = np.asarray(Pl, float)
        if bent and k in self.arm:
            ang = self.p['bendL'] if self.pieces[k]['side'] >= 0 else self.p['bendR']
            A = self.arm[k]
            Pl = A['E'] + _rod((Pl - A['E'])[None], A['ax'], np.array([math.radians(ang)]))[0]
        return R @ Pl + t


class Prop:
    """A one-piece amikit prop placed by hand (remote, popcorn)."""

    def __init__(self, pkl, key, M, coll):
        d = pickle.load(open(pkl, 'rb'))
        self.objs = []
        self.parts = d['parts']
        for o in d['parts']:
            uv = o['UV'] if o['mat'] in (0, 2) else None
            self.objs.append(mesh_obj(f"{key}.{o['name']}", o['V'], o['F'], srgb2lin(o['C']), uv, coll, M[o['mat']]))
        self.height = d['height']

    def place(self, R, t):
        mw = bmat(R, t)
        for ob in self.objs:
            ob.matrix_world = mw
