"""Story Shorts engine: yarn toys and crocheted props acting in a photographed set.

* Actors are Dancers (vengine.yarn.dance) posed every frame from a script: walk, hop, squash and stretch, head turns,
  arms that aim at a point and bend at the elbow (a smooth curl, not a rigid stick), legs, ears, eyes that pop or
  blink, props held in a hand or coming out of a mouth.
* One 3D camera per moment (wide, close-up, push-in, shake); the background photo is cropped to match it.
* The renderer's own floor gives the cast shadows: the toys are rendered over a white floor plane, that floor is read
  back as a shadow mask (light direction matched to the photo) and multiplied into the photo, so arms, hops and props
  throw real shadows on the table.
* Grade, light wrap from the set, bloom and grain sit the yarn in the photo.
"""
from __future__ import annotations

import json
import math
import os
import sys

sys.path.insert(0, '/home/user/video-engine')
os.environ.setdefault('AMIKIT', '/home/user')
import numpy as np  # noqa: E402
from PIL import Image, ImageFilter  # noqa: E402

from vengine.yarn.dance import Dancer, Stage, rot  # noqa: E402
from vengine.yarn.render import Camera, look_at  # noqa: E402

ROOT = '/home/user/video-engine/channels/amigurumi'
OUTW, OUTH = 1080, 1920
KEYS = dict(x=0.0, y=0.0, z=0.0, yaw=0.0, roll=0.0, pitch=0.0, sq=0.0, scale=1.0, turn=0.0, tilt=0.0, nod=0.0,
            armL=0.0, armR=0.0, fwdL=0.0, fwdR=0.0, bendL=0.0, bendR=0.0, legL=0.0, legR=0.0, earL=0.0, earR=0.0,
            tail=0.0, hat=0.0, eye=1.0, show=1.0)


def P(**kw):
    p = dict(KEYS)
    p.update(kw)
    return p


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def eout(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ein(x):
    x = clamp(x)
    return x ** 3


def back_out(x, k=1.9):
    x = clamp(x) - 1
    return 1 + x * x * ((k + 1) * x + k)


def spring(x, f=2.2, damp=4.0):
    """0 -> 1 with an overshoot and a settle (x in seconds-ish units)."""
    if x <= 0:
        return 0.0
    return 1 - math.exp(-damp * x) * math.cos(2 * math.pi * f * x)


def wob(x, f=3.0, damp=5.0):
    """A decaying wobble starting at 0 (for jiggle after an impact)."""
    if x <= 0:
        return 0.0
    return math.exp(-damp * x) * math.sin(2 * math.pi * f * x)


def lerp(a, b, u):
    return a + (b - a) * u


def keys(t, kf, fn=ease):
    """Piecewise interpolation through [(t, value), ...] with easing between keys."""
    if t <= kf[0][0]:
        return kf[0][1]
    for (t0, v0), (t1, v1) in zip(kf, kf[1:]):
        if t <= t1:
            u = fn((t - t0) / max(1e-9, t1 - t0))
            if isinstance(v0, (tuple, list)):
                return tuple(lerp(a, b, u) for a, b in zip(v0, v1))
            return lerp(v0, v1, u)
    return kf[-1][1]


def load_spec(tid):
    for base in ('toys', 'props'):
        f = f'{ROOT}/{base}/{tid}/spec.json'
        if os.path.exists(f):
            return json.load(open(f))
    raise FileNotFoundError(tid)


def subspec(sp, keep):
    s = json.loads(json.dumps(sp))
    s['parts'] = [p for p in s['parts'] if p['id'] in keep]
    s['assembly'] = [a for a in s.get('assembly', []) if a.get('part') in keep]
    s['assembly'] = s['assembly'][:1] + [a for a in s['assembly'][1:] if a.get('on') in keep]
    if s['assembly'] and 'on' in s['assembly'][0]:
        a0 = s['assembly'][0]
        s['assembly'][0] = {'part': a0['part'], 'axis': a0.get('dir', [0, 1, 0])}
    s['face'] = [f for f in s.get('face', []) if f.get('on') in keep]
    return s


def _rod(V, k, ang):
    """Rotate rows of V about unit axis k by per-row angles (radians)."""
    c = np.cos(ang)[:, None]
    s = np.sin(ang)[:, None]
    kv = V @ k
    return V * c + np.cross(k, V) * s + np.outer(kv, k) * (1 - c)


class Actor:
    def __init__(self, key, tid, height=None, home=(0.0, 0.0), spec=None, eyes=True):
        sp = spec or load_spec(tid)
        dn = Dancer(sp, scale=1.0)
        if height:
            dn = Dancer(sp, scale=height / dn.height)
        self.key, self.dn, self.home = key, dn, home
        self.height, self.width = dn.height, dn.width
        # arms: elbow, bend axis, per-point ramp, tip
        self.arm = {}
        for k, pc in enumerate(dn.pieces):
            if pc['role'] != 'arm' or pc['parent'] is None:
                continue
            Xp = dn.X[pc['start']:pc['end']]
            J, d = pc['joint'], pc['dir']
            s = (Xp - J) @ d
            L = max(1e-6, float(s.max()))
            u = np.clip(s / L, 0, 1)
            ax = np.cross(d, [0.0, 0.0, 1.0])
            if np.linalg.norm(ax) < 1e-3:
                ax = np.array([1.0, 0, 0])
            ax /= np.linalg.norm(ax)
            if pc.get('side', 0) < 0:
                ax = -ax
            w = np.clip((u - 0.3) / 0.6, 0, 1)
            w = w * w * (3 - 2 * w)
            tip = Xp[np.argmax(s)] * 0.0 + (J + d * L * 0.92)
            self.arm[k] = dict(E=J + d * L * 0.38, ax=ax, w=w, tip=tip, L=L, side=pc.get('side', 0.0))
        # eyes: outward normals from their piece's centre
        self.eyes = []
        for i, (k, s) in enumerate(dn.spheres):
            pc = dn.pieces[k]
            c = dn.X[pc['start']:pc['end']].mean(0)
            n = s[:3] - c
            n /= np.linalg.norm(n) + 1e-9
            self.eyes.append(n)
        self.heads = [k for k, pc in enumerate(dn.pieces) if pc['role'] == 'head']

    def piece(self, name):
        for k, pc in enumerate(self.dn.pieces):
            if pc['name'] == name or pc['pid'] == name:
                return k
        raise KeyError(name)


def rig(actor, p):
    dn = actor.dn
    local = {}
    for k, pc in enumerate(dn.pieces):
        r, sd = pc['role'], pc.get('side', 0.0)
        L = sd >= 0
        if r == 'head':
            local[k] = rot([0, 1, 0], p['turn']) @ rot([0, 0, 1], p['tilt']) @ rot([1, 0, 0], p['nod'])
        elif r == 'arm' and k in actor.arm:
            a = p['armL'] if L else p['armR']
            f = p['fwdL'] if L else p['fwdR']
            aim = p.get('aimL' if L else 'aimR')
            d = np.array(pc.get('dir', [0, -1, 0]), float)
            if aim is not None:                       # aim the arm along a direction in the body's frame
                tg = np.asarray(aim, float)
                tg = tg / (np.linalg.norm(tg) + 1e-9)
                ax = np.cross(d, tg)
                na = np.linalg.norm(ax)
                ang = math.degrees(math.atan2(na, float(d @ tg)))
                local[k] = rot(ax / na, ang) if na > 1e-6 else np.eye(3)
            else:
                tg = np.array([0.8 if L else -0.8, 1.0, 0.45])
                tg /= np.linalg.norm(tg)
                ax = np.cross(d, tg)
                if np.linalg.norm(ax) < 1e-6:
                    ax = np.array([0, 0, 1.0])
                full = math.degrees(math.acos(float(np.clip(d @ tg, -1, 1))))
                local[k] = rot(ax, full * a / 150.0) @ rot([1, 0, 0], -f)
        elif r == 'leg':
            local[k] = rot([1, 0, 0], -(p['legL'] if L else p['legR']))
        elif r == 'ear':
            e = p['earL'] if L else p['earR']
            local[k] = rot([0, 0, 1], e if L else -e)
        elif r == 'tail':
            local[k] = rot([0, 1, 0], p['tail']) @ rot([1, 0, 0], 0.3 * p['tail'])
        elif r == 'hat':
            local[k] = rot([0, 0, 1], p['hat'])
    for name, R in (p.get('pieces') or {}).items():
        local[actor.piece(name)] = R
    sq = clamp(p['sq'], -0.35, 0.4)
    s = p['scale']
    S = np.diag([1 + 0.5 * sq, 1 - sq, 1 + 0.5 * sq]) * s
    R0 = rot([0, 1, 0], p['yaw']) @ rot([0, 0, 1], p['roll']) @ rot([1, 0, 0], p['pitch']) @ S
    half = 0.5 * actor.width * 0.5 * s
    lift = half * math.sin(math.radians(min(70, abs(p['roll'])))) + 0.8 * half * math.sin(math.radians(min(70, abs(p['pitch']))))
    if p.get('nolift'):
        lift = 0.0
    hx, hz = actor.home
    return local, (R0, np.array([p['x'] - hx, p['y'] + lift, p['z'] - hz]))


class LiveStage(Stage):
    """Stage with elbow bends, eye scaling, hidden actors and attachment points."""

    def __init__(self, actors, W, H, ss=2, light=(-0.5, 1.0, 0.5), extent=None, center=None, floor_y=None):
        self.actors = actors
        places = [(a.home[0], a.home[1], 0.0) for a in actors]
        super().__init__([a.dn for a in actors], places, W=W, H=H, ss=ss, floor=1.0, bg=((1, 1, 1), (1, 1, 1)))
        l = np.asarray(light, float)
        self.rn.ldir = l / np.linalg.norm(l)
        self.rn.halo = 0.0
        if extent:
            self.rn.extent = extent
        if center is not None:
            self.rn.center = np.asarray(center, float)
        # map piece slices for bends
        self.yslice = {}
        for kind, i, k, a, b in self.slices:
            if kind == 'yarn':
                self.yslice[i] = a
        self.coreslice = {(i, k): (a, b) for kind, i, k, a, b in self.slices if kind == 'core'}

    def pose_actors(self, params):
        """params: per actor a P dict.  Returns X, D, Q, details, spheres and per-actor transforms."""
        from vengine.yarn.details import Details
        X = np.empty_like(self.Xrest)
        D = np.empty_like(self.Drest)
        Q = np.empty_like(self.Q0)
        TR = []
        for i, act in enumerate(self.actors):
            local, (R0, t0) = rig(act, params[i])
            x, z, face = self.places[i]
            root = (R0, t0 + np.array([x, 0.0, z]))
            if params[i]['show'] < 0.5:
                root = (R0 * 1e-3, np.array([0.0, -5e4, -5e4]))
            TR.append(act.dn.transforms(local, root))
        self.TR = TR

        def bent(i, k, V, dirs=False):
            act = self.actors[i]
            if k not in act.arm:
                return V
            p = params[i]
            ang = p['bendL'] if act.arm[k]['side'] >= 0 else p['bendR']
            if abs(ang) < 1e-3:
                return V
            A = act.arm[k]
            pc = act.dn.pieces[k]
            one = V.ndim == 1
            if one:
                V = V[None]
            if len(V) == pc['end'] - pc['start'] and not dirs:
                w = A['w']
            elif len(V) == pc['end'] - pc['start']:
                w = A['w']
            else:
                u = np.clip(((V - pc['joint']) @ pc['dir']) / A['L'], 0, 1)
                w = np.clip((u - 0.3) / 0.6, 0, 1)
                w = w * w * (3 - 2 * w)
            th = np.radians(ang) * w
            if dirs:
                out = _rod(V, A['ax'], th)
            else:
                out = A['E'] + _rod(V - A['E'], A['ax'], th)
            return out[0] if one else out

        for kind, i, k, a, b in self.slices:
            dn = self.dancers[i]
            if kind == 'yarn':
                for kk, pc in enumerate(dn.pieces):
                    R, t = TR[i][kk]
                    s, e = a + pc['start'], a + pc['end']
                    Xl = bent(i, kk, self.Xrest[s:e] - [self.places[i][0], 0, self.places[i][1]] + [self.places[i][0], 0, self.places[i][1]] if False else dn.X[pc['start']:pc['end']])
                    X[s:e] = Xl @ R.T + t
                    D[s:e] = bent(i, kk, self.Drest[s:e], True) @ R.T
                    Q[s:e] = bent(i, kk, self.Q0[s:e], True) @ R.T
            else:
                R, t = TR[i][k]
                pc = dn.pieces[k]
                Xl = self.Xrest[a:b]
                if k in self.actors[i].arm:
                    Xl = bent(i, k, Xl)
                X[a:b] = Xl @ R.T + t
                D[a:b] = self.Drest[a:b] @ R.T
                Q[a:b] = self.Q0[a:b] @ R.T
        # renormalise directors (scaled actors)
        nD = np.linalg.norm(D, axis=1, keepdims=True)
        D = D / np.maximum(nD, 1e-9)
        det = Details(None, None, 1.0)
        for i, act in enumerate(self.actors):
            if params[i]['show'] < 0.5:
                continue
            sc = params[i]['scale']
            for k, it in act.dn.items:
                R, t = TR[i][k]
                V, C = it['V'], it['C']
                if k in act.arm:
                    V = bent(i, k, V); C = bent(i, k, C)
                it2 = dict(it)
                it2['V'] = V @ R.T + t
                Rn = R / max(1e-6, sc)
                it2['N'] = it['N'] @ Rn.T
                it2['C'] = C @ R.T + t
                row = it['row'].copy()
                row[0] += self.off[i]
                for s0 in (6, 9, 12):
                    row[s0:s0 + 3] = Rn @ row[s0:s0 + 3]
                it2['row'] = row
                det.items.append(it2)
        sp = []
        for i, act in enumerate(self.actors):
            if params[i]['show'] < 0.5:
                continue
            e = params[i]['eye']
            sc = params[i]['scale']
            for j, (k, s) in enumerate(act.dn.spheres):
                R, t = TR[i][k]
                s2 = s.copy()
                n = act.eyes[j]
                c = s[:3] + n * s[3] * (e - 1) * 0.55
                s2[:3] = R @ c + t
                s2[3] = s[3] * e * sc
                s2[4] += self.off[i]
                if s2[3] > 0.05:
                    sp.append(s2)
        sp = np.array(sp).reshape(-1, 5)
        return X, D, Q, det, sp

    def world(self, i, k, Pl, params=None):
        """World position of a point given in actor i's piece-k rest frame (after the last pose)."""
        R, t = self.TR[i][k]
        act = self.actors[i]
        Pl = np.asarray(Pl, float)
        if k in act.arm and params is not None:
            ang = params[i]['bendL'] if act.arm[k]['side'] >= 0 else params[i]['bendR']
            A = act.arm[k]
            Pl = A['E'] + _rod((Pl - A['E'])[None], A['ax'], np.array([math.radians(ang)]))[0]
        return R @ Pl + t

    def render_frame(self, params, cam):
        X, D, Q, det, sp = self.pose_actors(params)
        self.rn._shape = (Q, self.c0)
        img = self.rn.render(X, D, cam, colnode=self.Crest, spheres=sp, gap=2.0, details=det, details_t=1.0)
        rn = self.rn
        m = (rn.idb > 0).astype(np.float32)
        ss = rn.ss
        h, w = m.shape[0] // ss, m.shape[1] // ss
        a = m[:h * ss, :w * ss].reshape(h, ss, w, ss).mean(axis=(1, 3))
        return img[:h, :w], a


# ------------------------------------------------------------------------------------------------ camera & set
class Set:
    """The photographed set and the master camera that lines world space up with it."""

    def __init__(self, photo, cam0, ground_y, px_per_mm, cx=None):
        self.photo = Image.open(photo).convert('RGB')
        self.cam0 = cam0                       # dict: pos, target, fov  (world mm)
        self.k = self.photo.width / OUTW       # photo px per canvas px
        self.ground_y = ground_y
        self.px_per_mm = px_per_mm


def make_cam(pos, target, fov):
    return Camera(np.asarray(pos, float), np.asarray(target, float), up=(0, 1, 0), fov=fov)


def project(cam, Pw, W=OUTW, H=OUTH):
    Bm = look_at(cam.pos, cam.target, cam.up)
    pc = Bm @ (np.asarray(Pw, float) - cam.pos)
    fpx = 0.5 * W / math.tan(math.radians(cam.fov) / 2)
    return W / 2 + fpx * pc[0] / pc[2], H / 2 - fpx * pc[1] / pc[2], pc[2]


def lin(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def composite(bg, rgb, alpha, look):
    """bg: canvas photo crop (float 0..1 sRGB, HxWx3).  rgb/alpha: yarn render over white floor + coverage."""
    rl = lin(rgb.astype(np.float32) / 255.0)
    # the floor (no yarn): its brightness is the shadow factor
    fl = rl.mean(axis=2)
    sh = np.where(alpha < 0.999, np.clip(fl / max(1e-3, look.get('white', 1.0)), 0, 1), 1.0)
    # soften: shadows in photos are not razor sharp
    shi = Image.fromarray((sh * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(look.get('shadow_blur', 2.0)))
    sh = np.asarray(shi, np.float32) / 255.0
    blobs = look.get('_blobs')
    if blobs:
        from PIL import ImageDraw
        m = Image.new('L', (sh.shape[1] // 4, sh.shape[0] // 4), 0)
        d = ImageDraw.Draw(m)
        for (bx, by, rx, ry, s_) in blobs:
            bx, by, rx, ry = bx / 4, by / 4, rx / 4, ry / 4
            d.ellipse((bx - rx, by - ry, bx + rx, by + ry), fill=int(255 * min(1.0, max(0.0, float(s_)))))
        m = m.filter(ImageFilter.GaussianBlur(float(max(2.0, blobs[0][3] / 4 * 0.6)))).resize((sh.shape[1], sh.shape[0]), Image.BILINEAR)
        mb = np.asarray(m, np.float32) / 255
        sh = sh * (1 - look.get('contact', 0.55) * mb * (alpha < 0.999))
    st = look.get('shadow', 0.85)
    tint = np.array(look.get('shadow_tint', (0.55, 0.42, 0.32)), np.float32)
    bl = lin(bg)
    f = 1 - st * (1 - sh)
    shade = f[..., None] * (1 - (1 - tint) * (1 - f[..., None]) * 0.6)
    bl = bl * shade
    # toys: grade in linear light, wrap the set's light round the edges
    yl = rl * np.array(look.get('mul', (1, 1, 1)), np.float32) + look.get('lift', 0.0)
    wrap_src = look.get('_wrap')
    al = alpha.astype(np.float32)
    if wrap_src is not None and look.get('wrap', 0) > 0:
        ab = np.asarray(Image.fromarray((al * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6)), np.float32) / 255
        wr = np.clip((1 - ab) * 2.5, 0, 1) * look['wrap'] * al
        yl = yl * (1 - wr[..., None]) + lin(wrap_src) * wr[..., None] * 1.1
    out = bl * (1 - al[..., None]) + yl * al[..., None]
    return srgb(out)


def bg_crop(photo, cx, cy, zoom, blur=0.0):
    """Canvas-space centre (cx, cy) and zoom -> OUTW x OUTH crop of the photo (photo covers the canvas at zoom 1)."""
    zoom = max(1.0, zoom)
    k = photo.width / OUTW
    w, h = OUTW / zoom * k, OUTH / zoom * k
    x0 = min(max(0, cx * k - w / 2), photo.width - w)
    y0 = min(max(0, cy * k - h / 2), photo.height - h)
    im = photo.resize((OUTW, OUTH), Image.LANCZOS, box=(x0, y0, x0 + w, y0 + h))
    if blur > 0:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    return im, (x0 / k, y0 / k, w / k, h / k)
