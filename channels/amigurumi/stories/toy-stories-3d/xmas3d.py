"""SANTA'S STUCK: Christmas Eve on the coffee table.  Santa gets stuck head-first in a crocheted chimney, only his legs
kick in the air.  An elf pops out of a gift box and pulls, a reindeer joins, a fox ornament drops off the tree to
help: still stuck.  Then a pug in an ugly sweater crunches a cookie... the legs sniff... silence... and Santa bursts
out in a soot cloud on the drop.  Party.  End card: crochet them all on amigurumi.ai.
Rendered on twos (12 poses a second) in Cycles; captions and the end card come in post (xpost.py).
Usage: python xmas3d.py OUT [--frames A B] [--still T ...] [--pct 60] [--samples 20]"""
import sys, math, os, argparse
sys.path.insert(0, '/home/user/work/b3d')
sys.path.insert(0, '/home/user/work/story')
import numpy as np
import bpy
from mathutils import Vector, Euler

ap = argparse.ArgumentParser()
ap.add_argument('out')
ap.add_argument('--frames', type=int, nargs=2)
ap.add_argument('--still', type=float, nargs='*')
ap.add_argument('--step', type=int, default=1)
ap.add_argument('--pct', type=int, default=60)
ap.add_argument('--samples', type=int, default=20)
a = ap.parse_args(sys.argv[1:])
os.makedirs(a.out, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
import xmas_set  # noqa: E402
from xmas_set import T, MM  # noqa: E402
from ami3d import AmiToy, ami_materials  # noqa: E402
from engine import P, ease, eout, ein, back_out, wob, clamp, lerp, keys  # noqa: E402
from acting import life, blink, hop, shake, pop_eyes, dance, jump_squash  # noqa: E402

RATE = 12
DUR = 59.3
BEAT = 0.48775
T_DROP = 39.73
T_EVE, T_UHOH, T_THUD, T_STUCK = 2.2, 4.0, 8.22, 8.6
T_GRUNT, T_PULL, T_POP, T_OOPS = 11.8, 12.9, 14.0, 14.9
T_PH1, T_PH2, T_STILL = 16.3, 18.1, 21.8
T_CRUNCH, T_WAIT, T_SNIFF1, T_SNIFF2 = 24.0, 25.8, 27.3, 29.0
T_SIL, T_BUILD, T_BACK, T_HOHO, T_END = 30.3, 31.0, 35.5, 46.5, 54.4

CH = (20.0, -30.0)                 # chimney
GIFT = (-150.0, -80.0)
TREE = (130.0, -70.0)
FOX_HANG = (78.0, 104.0, -20.0)
PLATE = (100.0, 62.0)

sc = bpy.context.scene
H = xmas_set.build()
M2 = ami_materials()
tc = bpy.data.collections.new('toys'); sc.collection.children.link(tc)
B3 = '/home/user/work/b3d/'
CAST = [('legs', 'hanging-santa-legs'), ('elf', 'christmas-elf-doll'), ('deer', 'reindeer-sweater'),
        ('fox', 'fox-ornament-earmuffs'), ('dog', 'dog-ugly-sweater'), ('santa', 'santa-claus')]
TOY = {k: AmiToy(B3 + f'{tid}.ami.pkl', k, M2, tc, absolute=True) for k, tid in CAST}
# the fox ornament's ribbon up to its branch
import set3d as _s3  # noqa: E402
STRING = _s3.cyl(H['tree'][0].users_collection[0], 'fox_string', 0.0006, 1.0, (0, 0, 0), _s3.plain('ribbon2', (0.8, 0.1, 0.1), 0.4)[0], verts=8)
SEED = {'legs': 1, 'elf': 2, 'deer': 3, 'fox': 4, 'dog': 5, 'santa': 6}


def piece_centre(toy, name):
    Vs = [x['V'] for x in toy.objs if x['mat'] == 0 and x['name'].split('@')[-1].split('#')[0] == name]
    return np.concatenate(Vs).mean(0) if Vs else None


DOG_HEAD = TOY['dog'].kof('head')
DOG_MOUTH = piece_centre(TOY['dog'], 'muzzle') + np.array([0.0, -15.0, 6.0])
SANTA_ARM = [k for k, pc in enumerate(TOY['santa'].pieces) if pc['role'] == 'arm']


def env(t, t0, t1, a=0.12, b=0.15):
    return clamp((t - t0) / a) * (1 - clamp((t - (t1 - b)) / b))


def walk(p, t, amt=1.0, f=2.4):
    ph = 2 * math.pi * f * t
    p['legL'] += 28 * amt * math.sin(ph)
    p['legR'] += -28 * amt * math.sin(ph)
    p['y'] += 5 * amt * abs(math.sin(ph))
    p['roll'] += 6 * amt * math.sin(ph)
    p['armL'] += 25 * amt * math.sin(ph)
    p['armR'] += -25 * amt * math.sin(ph)
    p['sq'] += 0.05 * amt * abs(math.cos(ph))


def path(t, pts):
    """Piecewise eased motion through (time, x, z) keys."""
    if t <= pts[0][0]:
        return pts[0][1], pts[0][2], 0.0
    for (t0, x0, z0), (t1, x1, z1) in zip(pts, pts[1:]):
        if t < t1:
            u = ease((t - t0) / (t1 - t0))
            moving = 1.0 if (x0, z0) != (x1, z1) else 0.0
            return lerp(x0, x1, u), lerp(z0, z1, u), moving * math.sin(math.pi * clamp((t - t0) / (t1 - t0)))
    return pts[-1][1], pts[-1][2], 0.0


def face_yaw(x, z, tx, tz, k=0.8):
    """Yaw that turns a toy toward a point, a little less than fully (faces stay to the camera)."""
    return max(-55.0, min(55.0, k * math.degrees(math.atan2(tx - x, tz - z))))


def ballistic(t, t0, t1, a, b, height):
    u = clamp((t - t0) / (t1 - t0))
    pos = np.array(a, float) * (1 - u) + np.array(b, float) * u
    pos[1] += height * 4 * u * (1 - u)
    return pos, u


# ------------------------------------------------------------------ the acting
def act(t):
    ps = {k: P() for k in TOY}
    lg, el, de, fx, dg, sa = (ps[k] for k in ('legs', 'elf', 'deer', 'fox', 'dog', 'santa'))
    drop = t >= T_DROP
    frozen = T_SIL <= t < T_BUILD
    for k, s in SEED.items():
        if not frozen:
            life(ps[k], t, s, 0.6 if not drop else 0.25)
        ps[k]['blink'] = blink(t, s) if not frozen else 1.0
    bb = (t - T_DROP) / BEAT
    # ---------------------------------------------------------------- the chimney and Santa's legs
    lg.update(x=CH[0], z=CH[1])
    legs_out = clamp((t - (T_THUD - 0.08)) / 0.12)            # legs shoot out on the thud
    legs_in = 1 - clamp((t - T_BACK) / 0.22)                  # ...and zip back in
    s_leg = max(1e-3, back_out(legs_out, 2.5) * legs_in)
    kick = 0.0
    if T_THUD < t < T_SIL:
        kick = 1.0
        if T_PH1 <= t < T_STILL:
            kick = 0.6
        if T_CRUNCH - 0.3 <= t < T_SIL:
            kick = 0.25
    if T_BUILD <= t < T_BACK:
        kick = 0.6 + 2.0 * ease((t - T_BUILD) / (T_BACK - T_BUILD))
    f = 3.0 + 3.0 * (t > T_BUILD) * clamp((t - T_BUILD) / 4)
    ka = 26 * kick * math.sin(2 * math.pi * f * t)
    kb = 26 * kick * math.sin(2 * math.pi * f * t + 2.2)
    lean = 0.0
    if T_SNIFF1 - 0.6 < t < T_SIL + 0.4:                    # the legs lean toward the cookie, sniffing
        lean = -28 * ease((t - (T_SNIFF1 - 0.6)) / 0.5)
        for ts in (T_SNIFF1, T_SNIFF1 + 0.35, T_SNIFF2, T_SNIFF2 + 0.3):
            lean += -8 * math.exp(-((t - ts) / 0.07) ** 2)
    pull = 0.0
    if T_GRUNT - 0.3 < t < T_POP:
        pull = 22 * ease((t - (T_GRUNT - 0.3)) / 0.6)
    if T_PH1 < t < T_STILL:
        pull = 26 + 10 * max(0.0, math.sin(2 * math.pi * (t - T_PH1) / (2 * BEAT)))
    from engine import rot
    lg['pieces'] = {'leg_a': rot([0, 0, 1], -ka * 0.6 + pull * 0.7 + lean) @ rot([1, 0, 0], ka) * s_leg,
                    'leg_b': rot([0, 0, 1], kb * 0.6 + pull + lean) @ rot([1, 0, 0], -kb) * s_leg}
    if T_THUD - 3.6 < t < T_THUD:                             # rumble before the thud
        r = ease((t - (T_THUD - 3.6)) / 3.6)
        lg['roll'] += shake(t, 3 * r, 13)
        lg['sq'] += 0.04 * r * math.sin(2 * math.pi * 9 * t)
    if T_THUD <= t < T_THUD + 0.6:
        lg['sq'] += 0.3 * wob(t - T_THUD, 2.5, 6)
    lg['roll'] += pull * 0.35
    lg['eye'] *= pop_eyes(t, T_THUD, 1.5, 0.8) * pop_eyes(t, T_POP, 1.3, 0.3)
    if t < T_THUD:
        lg['blink'] = 0.0                                     # asleep until the thud
    if T_BUILD <= t < T_DROP:                                 # the chimney swells and rumbles
        r = ease((t - T_BUILD) / (T_DROP - T_BUILD))
        lg['roll'] += shake(t, 5 * r, 15)
        lg['sq'] += -0.12 * r + 0.08 * r * math.sin(2 * math.pi * t / BEAT)
        lg['eye'] *= 1 + 0.5 * r
    if drop:
        dance(lg, t, bb, 'bounce', 0, 0.6)
        lg['sq'] += 0.3 * wob(t - T_DROP, 2.5, 5) if t < T_DROP + 0.8 else 0
    # ---------------------------------------------------------------- the elf: out of the gift
    gx, gz = GIFT
    if t < T_STUCK - 0.05:
        el.update(show=0.0)
    elif t < T_STUCK + 0.8:
        pos, u = ballistic(t, T_STUCK - 0.05, T_STUCK + 0.8, (gx, -60, gz), (-80, 0, 30), 170)
        el.update(x=pos[0], y=max(0.0, pos[1]), z=pos[2])
        el['yaw'] += -360 * eout(u)
        el['armL'] += 150; el['armR'] += 150
        el['sq'] += -0.15 * math.sin(math.pi * u)
    else:
        x, z, mv = path(t, [(T_STUCK + 0.8, -80, 30), (10.6, -80, 30), (11.3, -26, -22), (T_POP, -26, -22), (T_POP + 0.55, -80, 10),
                            (15.9, -80, 10), (16.2, -26, -22), (T_STILL, -26, -22), (T_STILL + 0.5, -60, 20), (23.4, -60, 20),
                            (T_WAIT, -60, 20), (T_BACK, -80, 30), (T_DROP + 0.5, -78, 34)])
        el.update(x=x, z=z)
        walk(el, t, mv)
        if t < T_STUCK + 1.4:
            el['sq'] += 0.28 * wob(t - (T_STUCK + 0.8), 2.5, 6)
        el['eye'] *= pop_eyes(t, T_STUCK + 0.95, 1.7, 0.9)
        el['yaw'] += face_yaw(x, z, CH[0], CH[1], 0.35)
        if 11.3 <= t < T_POP:                                   # grab and pull the boot
            u = ease((t - 11.3) / 0.3)
            el['aimL'] = (0.55, 0.85, -0.2); el['aimR'] = (0.75, 0.75, -0.2)
            el['roll'] += 18 * ease((t - T_GRUNT) / 0.4) + shake(t, 2.5 * (t > T_GRUNT))
            el['eye'] *= 0.8 if t > T_GRUNT else 1.0
            el['squint'] = 0.6 if t > T_GRUNT else 0.0
            el['y'] += 4 * u
        if T_POP <= t < 15.9:                                   # slips, flies back, lands on its bum
            d = t - T_POP
            el['y'] += hop(d / 0.55, 30) if d < 0.55 else 0
            el['pitch'] += -35 * ease(d / 0.3) * (1 - ease((d - 1.4) / 0.4))
            el['sq'] += 0.3 * wob(d - 0.55, 2.5, 6) if d > 0.55 else 0
            el['eye'] *= pop_eyes(t, T_POP + 0.05, 1.6, 0.6)
            el['armL'] += 120 * (1 - ease((d - 0.6) / 0.5)); el['armR'] += 120 * (1 - ease((d - 0.6) / 0.5))
        if T_PH1 <= t < T_STILL:                                # pulls again, with the reindeer
            el['aimL'] = (0.55, 0.85, -0.2); el['aimR'] = (0.75, 0.75, -0.2)
            tug = max(0.0, math.sin(2 * math.pi * (t - T_PH1) / (2 * BEAT)))
            el['roll'] += 20 + 8 * tug
            el['squint'] = 0.7
            el['x'] += -4 * tug
        if T_STILL <= t < 23.4:                                 # the chain collapses
            d = t - T_STILL
            el['pitch'] += -40 * ease(d / 0.25) * (1 - ease((d - 1.2) / 0.4))
            el['roll'] += -15 * wob(d, 1.5, 4)
            el['eye'] *= pop_eyes(t, T_STILL, 1.5, 0.6)
        if t >= T_CRUNCH - 0.1 and t < T_BACK:                  # looks at the pug, then has the idea
            el['turn'] += 35 * ease((t - (T_CRUNCH - 0.1)) / 0.25)
            el['yaw'] += 20 * ease((t - (T_CRUNCH - 0.1)) / 0.4)
        if T_WAIT <= t < T_WAIT + 1.6:
            d = t - T_WAIT
            el['y'] += hop(d / 0.35, 22) if d < 0.35 else 0
            el['aimR'] = (0.3, 1.0, 0.25)                       # finger up: idea!
            el['eye'] *= pop_eyes(t, T_WAIT, 1.8, 1.0)
            el['sq'] += 0.25 * wob(d - 0.35, 2.5, 6) if d > 0.35 else 0
        if T_BUILD <= t < T_DROP:                               # backs off, covers its eyes
            r = ease((t - T_BACK) / 0.6)
            el['aimL'] = (0.3, 0.9, 0.9) if r > 0.5 else el.get('aimL')
            el['aimR'] = (-0.3, 0.9, 0.9) if r > 0.5 else el.get('aimR')
            el['roll'] += shake(t, 3 * r)
            el['eye'] *= 1.2
    # ---------------------------------------------------------------- the reindeer: walks in from the left
    if t < 14.4:
        de.update(show=0.0)
    else:
        x, z, mv = path(t, [(14.4, -270, 4), (15.6, -110, 0), (16.0, -70, -18), (T_STILL, -70, -18), (T_STILL + 0.5, -110, 10), (23.4, -110, 10),
                            (T_BACK, -134, 20), (T_DROP + 0.5, -134, 20)])
        de.update(x=x, z=z)
        walk(de, t, mv, 2.0)
        de['yaw'] += 55 if t < 16.3 else face_yaw(x, z, CH[0], CH[1], 0.5)
        de['eye'] *= pop_eyes(t, 15.7, 1.5, 0.5)
        if T_PH1 <= t < T_STILL:
            de['aimL'] = (0.6, 0.35, 0.2); de['aimR'] = (0.7, 0.3, 0.3)
            tug = max(0.0, math.sin(2 * math.pi * (t - T_PH1 - 0.08) / (2 * BEAT)))
            de['roll'] += 16 + 8 * tug
            de['x'] += -4 * tug
            de['squint'] = 0.6
        if T_STILL <= t < 23.4:
            d = t - T_STILL
            de['pitch'] += -35 * ease((d - 0.08) / 0.25) * (1 - ease((d - 1.2) / 0.4))
            de['roll'] += -20 * wob(d, 1.5, 4)
            de['eye'] *= pop_eyes(t, T_STILL + 0.1, 1.5, 0.6)
        if t >= T_CRUNCH and t < T_BACK:
            de['turn'] += 40 * ease((t - T_CRUNCH) / 0.25)
            de['eye'] *= pop_eyes(t, T_CRUNCH + 0.1, 1.5, 0.6)
        if T_BUILD <= t < T_DROP:
            de['roll'] += shake(t, 2.5 * ease((t - T_BUILD) / 3))
            de['eye'] *= 1.25
    # ---------------------------------------------------------------- the fox ornament: wakes on the tree, drops
    hx, hy, hz = FOX_HANG
    if t < T_PH2:
        fx.update(x=hx, y=hy, z=hz, nolift=True)
        fx['roll'] += 6 * math.sin(2 * math.pi * 0.4 * t)
        if t < 16.8:
            fx['blink'] = 0.0
        fx['eye'] *= pop_eyes(t, 16.9, 1.6, 0.8)
        if t > 17.3:
            fx['roll'] += 25 * math.sin(2 * math.pi * 2.2 * (t - 17.3)) * ease((t - 17.3) / 0.3)
            fx['turn'] += -30
    elif t < T_PH2 + 0.5:
        pos, u = ballistic(t, T_PH2, T_PH2 + 0.5, (hx, hy, hz), (60, 0, 24), 20)
        fx.update(x=pos[0], y=max(0.0, pos[1]), z=pos[2])
        fx['roll'] += 200 * u
        fx['eye'] *= 1.5
    else:
        x, z, mv = path(t, [(T_PH2 + 0.5, 60, 24), (19.6, -110, -6), (T_STILL, -110, -6), (T_STILL + 0.5, -135, 40),
                            (T_BACK, -78, 62), (T_DROP + 0.5, -78, 62)])
        fx.update(x=x, z=z)
        if t < 19.6:
            fx['roll'] += 360 * 3 * ease((t - (T_PH2 + 0.5)) / (19.6 - T_PH2 - 0.5))   # rolls across the table
            fx['y'] += hop(((t - T_PH2 - 0.5) % 0.3) / 0.3, 6)
        if 19.6 <= t < T_STILL:
            tug = max(0.0, math.sin(2 * math.pi * (t - T_PH1 - 0.16) / (2 * BEAT)))
            fx['roll'] += 14 + 6 * tug
            fx['yaw'] += 50
            fx['squint'] = 0.7
        if T_STILL <= t < 23.4:
            d = t - T_STILL
            fx['y'] += hop(d / 0.5, 25) if d < 0.5 else 0
            fx['roll'] += -360 * ease(d / 0.5)
            fx['eye'] *= pop_eyes(t, T_STILL + 0.15, 1.5, 0.6)
        if t >= T_CRUNCH and t < T_BUILD:
            fx['turn'] += 40 * ease((t - T_CRUNCH) / 0.25)
        if T_BUILD <= t < T_DROP:
            fx['roll'] += shake(t, 3 * ease((t - T_BUILD) / 3))
            fx['eye'] *= 1.3
    # tree shakes when the fox drops (and on the beat after the drop)
    tw = 0.0
    if T_PH2 - 0.1 < t < T_PH2 + 1.5:
        tw = 6 * wob(t - T_PH2, 2.5, 4)
    if drop:
        tw = 2.5 * math.sin(2 * math.pi * bb / 2)
    H['tree_root'].rotation_euler = (math.radians(tw), math.radians(tw * 0.5), 0)
    if t < T_PH2:                                              # the ribbon from the fox's loop to the branch
        top = np.array([fx['x'], FOX_HANG[1] + 60, fx['z']]) + np.array([-0.9 * fx['roll'], 0, 0])
        br = np.array([87.0, 178.0, -50.0])
        mid = (top + br) / 2
        d = Vector(T(*br)) - Vector(T(*top))
        STRING.location = T(*mid)
        STRING.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
        STRING.scale = (1, 1, d.length)
        STRING.hide_render = False
    else:
        STRING.hide_render = True
    # ---------------------------------------------------------------- the pug: cookie thief, then the solution
    hold_cookie = False
    if t < 22.6:
        dg.update(show=0.0)
    else:
        x, z, mv = path(t, [(22.6, 250, -40), (23.6, 142, 12), (26.4, 142, 12), (28.6, 84, -30), (T_BACK, 84, -30),
                            (T_DROP, 80, 30), (T_DROP + 0.6, 92, 40)])
        dg.update(x=x, z=z)
        walk(dg, t, mv, 2.6)
        dg['yaw'] += -40 * mv
        hold_cookie = t >= T_CRUNCH - 0.25 and t < T_DROP + 0.1
        if T_CRUNCH - 0.2 <= t < T_WAIT:                          # munch munch
            d = t - T_CRUNCH
            dg['nod'] += 8 * math.sin(2 * math.pi * 3.5 * d) * (d > 0)
            dg['sq'] += 0.06 * math.sin(2 * math.pi * 3.5 * d) * (d > 0)
            dg['squint'] = 0.6 * (0 < d < 1.2)
        if T_WAIT <= t < 26.4:                                   # caught! freezes
            dg['eye'] *= pop_eyes(t, T_WAIT + 0.1, 1.9, 0.6)
            dg['sq'] += 0.2 * wob(t - T_WAIT, 2, 5)
        if 28.6 <= t < T_BACK:                                   # offers the cookie up to the legs
            dg['nod'] += -18 * ease((t - 28.6) / 0.4)
            dg['yaw'] += face_yaw(x, z, CH[0], CH[1], 0.6)
            dg['y'] += 6 * ease((t - 28.6) / 0.4)
        if T_BUILD <= t < T_DROP:
            dg['roll'] += shake(t, 2.5 * ease((t - T_BUILD) / 3))
            dg['eye'] *= 1.25
    # ---------------------------------------------------------------- Santa: bursts out on the drop
    if t < T_DROP:
        sa.update(show=0.0)
    elif t < T_DROP + 0.75:
        pos, u = ballistic(t, T_DROP, T_DROP + 0.75, (CH[0], 30, CH[1]), (10, 0, 50), 150)
        sa.update(x=pos[0], y=max(0.0, pos[1]), z=pos[2], scale=0.35 + 0.65 * back_out(clamp((t - T_DROP) / 0.3)))
        sa['yaw'] += 360 * eout(u)
        sa['armL'] += 150; sa['armR'] += 150
        sa['eye'] *= 1.4
    else:
        sa.update(x=10, z=50)
        if t < T_DROP + 1.3:
            sa['sq'] += 0.3 * wob(t - (T_DROP + 0.75), 2.5, 6)
    # ---------------------------------------------------------------- everyone's reactions to the big moments
    for k, p in ps.items():
        if k in ('legs', 'santa'):
            continue
        p['eye'] *= pop_eyes(t, T_THUD + 0.05, 1.5, 0.6) if k == 'fox' and False else 1.0
        if T_DROP <= t < T_DROP + 0.5:
            p['eye'] *= 1.6
            p['pitch'] += -12 * wob(t - T_DROP, 2, 5)
    # ---------------------------------------------------------------- party
    if drop and t > T_DROP + 0.6:
        moves = ['bounce', 'pump', 'sway', 'twist', 'bounce', 'headbang', 'pump', 'spin']
        bar = int((t - T_DROP) / (4 * BEAT))
        mv = moves[bar % len(moves)]
        party = [('santa', 0.0, 1.0), ('elf', -0.1, 0.9), ('deer', -0.15, 0.8), ('fox', 0.05, 0.9), ('dog', -0.05, 0.85)]
        for i, (k, off, e) in enumerate(party):
            dance(ps[k], t, bb + off, mv if k != 'fox' else 'bounce', i, e)
        if T_HOHO <= t < T_HOHO + 1.6:                           # ho ho ho: belly laughs
            d = t - T_HOHO
            sa['sq'] += 0.18 * abs(math.sin(2 * math.pi * 1.9 * d))
            sa['squint'] = 0.7
            sa['nod'] += -10
    if t >= T_END:                                               # the line-up for the end card
        u = ease((t - T_END) / 0.6)
        for k, (x, z) in {'elf': (-75, 40), 'deer': (-130, 14), 'fox': (-40, 84), 'santa': (25, 50), 'dog': (100, 40)}.items():
            ps[k]['x'] = lerp(ps[k]['x'], x, u)
            ps[k]['z'] = lerp(ps[k]['z'], z, u)
    return ps, hold_cookie


# ------------------------------------------------------------------ set events (lid, puffs, cookie, lights, snow)
def puffs(t, events):
    """events: (t0, origin, n, spread, rise).  Cartoon soot balls bloom and drift up."""
    obs = H['puffs']
    used = 0
    for (t0, org, n, spread, rise) in events:
        d = t - t0
        if not (0 <= d < 1.4):
            continue
        for j in range(n):
            if used >= len(obs):
                break
            ob = obs[used]; used += 1
            a = j * 2.39996
            r = spread * (0.4 + 0.6 * ((j * 7) % 5) / 4)
            u = eout(d / 1.4)
            x = org[0] + r * math.cos(a) * u
            z = org[2] + r * math.sin(a) * 0.5 * u
            y = org[1] + rise * u + 10 * (j % 3)
            s = (6 + 9 * ((j * 3) % 4) / 3) * math.sin(math.pi * clamp(d / 1.4)) ** 0.6
            ob.location = T(x, y, z)
            ob.scale = (s * MM,) * 3
            ob.hide_render = False
    for ob in obs[used:]:
        ob.hide_render = True


def sparks(t, t0, org, n=16):
    for j, ob in enumerate(H['sparks']):
        d = t - t0
        if 0 <= d < 1.2 and j < n:
            a = j * 2.39996
            pos, u = ballistic(t, t0, t0 + 1.2, org, (org[0] + 140 * math.cos(a), 0, org[2] + 70 * math.sin(a)), 120 + 40 * (j % 3))
            ob.location = T(*pos)
            s = 2.2 * (1 - u)
            ob.scale = (s * MM,) * 3
            ob.hide_render = s < 0.1
        else:
            ob.hide_render = True


def set_events(t, ps, hold_cookie):
    # the gift lid pops off when the elf jumps out
    gx, gz, gs = H['gift']
    lid = H['lid']
    if t < T_STUCK - 0.1:
        lid.location = T(gx, gs + shake(t, 1.2 * (t > T_STUCK - 0.9)), gz)
        lid.rotation_euler = (0, math.radians(shake(t, 3 * (t > T_STUCK - 0.9))), 0)
    else:
        pos, u = ballistic(t, T_STUCK - 0.1, T_STUCK + 0.6, (gx, gs, gz), (gx - 75, 9, gz + 40), 110)
        lid.location = T(*pos)
        lid.rotation_euler = (math.radians(-160 * eout(u)), math.radians(70 * u), math.radians(30 * u))
    # soot: thud puff, sniff puffs, build puffs, the drop cloud
    top = (CH[0], 52, CH[1])
    ev = [(T_THUD, top, 5, 30, 40)]
    for k in range(int(max(0, (min(t, T_DROP) - T_BUILD) / BEAT)) + 1):
        tb = T_BUILD + k * BEAT
        if tb < T_DROP and t >= T_BUILD:
            ev.append((tb, top, 2, 12, 25))
    ev.append((T_DROP, (CH[0], 45, CH[1]), 12, 110, 70))
    puffs(t, ev[-3:] if len(ev) > 3 else ev)
    sparks(t, T_DROP, (CH[0], 60, CH[1]))
    # the cookie in the pug's mouth (then Santa's hand)
    ck = H['cookies'][3]
    if hold_cookie:
        dog = TOY['dog']
        w = dog.world(DOG_HEAD, DOG_MOUTH, bent=False)
        ck.location = T(*w)
        ck.rotation_euler = (math.radians(15), 0, math.radians(10))
        if T_CRUNCH <= t < T_WAIT:                          # bites out of it
            ck.scale = (1, 1 - 0.25 * clamp((t - T_CRUNCH) / 1.2), 1)
    elif t >= T_DROP + 0.1:
        sa = TOY['santa']
        if t < T_DROP + 0.75:
            ck.location = T(*ballistic(t, T_DROP + 0.1, T_DROP + 0.75, (70, 20, 30), (25, 40, 60), 60)[0])
        else:
            k = SANTA_ARM[0]
            w = sa.world(k, sa.arm[k]['tip']) if k in sa.arm else np.array([25, 40, 60])
            ck.location = T(*w)
            if t > T_HOHO - 1.0:                               # eaten bit by bit
                ck.scale = (1, max(0.05, 0.75 - 0.15 * int((t - (T_HOHO - 1.0)) / 0.9)), 1)
    # lights: twinkle, fire flicker, the party flashes on the beat
    cols = H['cols']
    fl = 0.8 + 0.2 * math.sin(t * 23) * math.sin(t * 7.3)
    H['fire'].data.energy = 120 * fl
    H['fire_m'].inputs[1].default_value = 25 * fl
    drop = t >= T_DROP
    bb = (t - T_DROP) / BEAT
    build = ease((t - T_BUILD) / (T_DROP - T_BUILD)) if T_BUILD <= t < T_DROP else 0.0
    for lst, base in ((H['tbulbs'], 6.0), (H['garland'], 18.0), (H['bigbulbs'], 12.0)):
        for i, (node, ci) in enumerate(lst):
            if drop:
                on = (int(bb) + ci) % 4 < 2
                node.inputs[0].default_value = (*cols[(ci + int(bb)) % 4], 1)
                node.inputs[1].default_value = base * (0.4 + 2.2 * on * math.exp(-(bb % 1) / 0.35))
            else:
                tw = 0.7 + 0.3 * math.sin(t * (1.3 + 0.37 * i) + i)
                if build:
                    tw *= 1 + build * 1.5 * (math.sin(t * 40 + i) > 0)
                if T_SIL <= t < T_BUILD:
                    tw *= 0.25
                node.inputs[0].default_value = (*cols[ci], 1)
                node.inputs[1].default_value = base * tw
    party = H['party'].data
    if drop:
        party.color = cols[int(bb) % 4]
        party.energy = 10 + 30 * math.exp(-(bb % 1) / 0.2)
    else:
        party.energy = 0.0
    H['key'].data.energy = 22 * (0.35 if T_SIL <= t < T_BUILD else 1.0)
    # snow outside
    for (s, z0, sp, ph) in H['snow']:
        z = z0 - (sp * t) % 1.08
        if z < 0.36:
            z += 1.08
        s.location.z = z
        s.location.y += 0.0
    # sweet star pulse
    st = 1 + 0.15 * math.sin(t * 3) + (0.6 * math.exp(-(bb % 1) / 0.25) if drop else 0)
    H['star'].scale = (st, st, st)


# ------------------------------------------------------------------ camera
cd = bpy.data.cameras.new('cam')
cam = bpy.data.objects.new('cam', cd)
sc.collection.objects.link(cam)
sc.camera = cam
cd.sensor_fit = 'HORIZONTAL'
cd.sensor_width = 36
cd.dof.use_dof = True

WIDE = ((0, 70, 0), 470, 34.0)


def shot(t):
    """(target, distance, horizontal fov) per moment, cutting with the story."""
    S = [
        (0.0, lambda t: ((0, keys(t, [(0, 90), (T_THUD, 62)]), 0), keys(t, [(0, 560), (T_THUD - 0.3, 330)]), 30.0)),
        (T_THUD - 0.02, lambda t: ((CH[0], 62, CH[1]), 260, 30.0)),
        (T_STUCK - 0.1, lambda t: ((-70, 60, 10), 360, 34.0)),
        (T_STUCK + 1.0, lambda t: ((-30, 62, 0), 300, 32.0)),
        (11.2, lambda t: ((-22, 66, 0), keys(t, [(11.2, 300), (T_POP, 250)]), 30.0)),
        (T_POP, lambda t: ((-60, 55, 10), 360, 34.0)),
        (14.4, lambda t: ((-120, 60, 10), 380, 36.0)),
        (T_PH1 - 0.1, lambda t: ((-60, 62, 5), 330, 34.0)),
        (16.6, lambda t: ((FOX_HANG[0], FOX_HANG[1] - 10, FOX_HANG[2]), 200, 30.0)),
        (T_PH2 + 0.4, lambda t: ((-40, 60, 15), keys(t, [(T_PH2 + 0.4, 470), (T_STILL, 420)]), 36.0)),
        (T_STILL, lambda t: ((-90, 45, 20), 340, 34.0)),
        (23.0, lambda t: ((125, 55, 20), keys(t, [(23.0, 320), (T_WAIT, 260)]), 30.0)),
        (T_WAIT - 0.05, lambda t: ((-70, 60, 30), 230, 30.0)),
        (26.5, lambda t: ((40, 62, 0), 420, 34.0)),
        (T_SNIFF1 - 0.4, lambda t: ((50, 85, -25), keys(t, [(T_SNIFF1 - 0.4, 330), (T_SIL, 260)]), 30.0)),
        (T_BUILD, lambda t: ((0, 65, 0), keys(t, [(T_BUILD, 480), (T_BACK, 380)]), 34.0)),
        (T_BACK, lambda t: ((CH[0], 55, CH[1]), keys(t, [(T_BACK, 330), (T_DROP - 0.05, 200)]), 30.0)),
        (T_DROP, None),
    ]
    sel = [s for s in S if t >= s[0]][-1]
    if sel[1] is not None:
        return sel[1](t)
    d = t - T_DROP
    bar2 = int(d / (8 * BEAT))
    plan = [((0, 70, 20), 520, 36.0), ((0, 75, 48), 240, 30.0), ((-110, 60, 20), 300, 32.0), ((0, 70, 20), 500, 36.0),
            ((0, 78, 48), 200, 28.0), ((90, 55, 40), 280, 32.0), ((-40, 60, 60), 300, 32.0), ((0, 70, 20), 520, 36.0)]
    if T_HOHO <= t < T_HOHO + 2.0:
        return (0, 80, 48), 200, 28.0
    if t >= T_END:
        return (-15, 62, 40), 470, 38.0
    return plan[bar2 % len(plan)]


def pose_camera(t):
    tg, dist, fov = shot(t)
    tg = np.array(tg, float)
    elev = math.radians(21)
    az = math.radians(4 * math.sin(0.21 * t))
    pos = tg + dist * np.array([math.sin(az) * math.cos(elev), math.sin(elev), math.cos(az) * math.cos(elev)])
    pos += np.array([2 * math.sin(0.31 * t), 1.5 * math.sin(0.23 * t + 1), 0])
    sh = 0.0
    if T_THUD <= t < T_THUD + 0.5:
        sh = 4 * (1 - (t - T_THUD) / 0.5)
    if T_BUILD <= t < T_DROP:
        sh = 2.5 * ease((t - T_BUILD) / (T_DROP - T_BUILD))
    if T_DROP <= t < T_DROP + 0.6:
        sh = 6 * (1 - (t - T_DROP) / 0.6)
    if t >= T_DROP:
        u = ((t - T_DROP) / BEAT) % 1.0
        dist *= 1 - 0.03 * math.exp(-u / 0.12)
    tg = tg + sh * np.array([math.sin(t * 61.0), math.sin(t * 47.0 + 1), 0])
    P0, T0 = Vector(T(*pos)), Vector(T(*tg))
    cam.location = P0
    cam.rotation_euler = (T0 - P0).to_track_quat('-Z', 'Y').to_euler()
    cd.lens = 18.0 / math.tan(math.radians(fov) / 2)
    cd.dof.focus_distance = (T0 - P0).length
    cd.dof.aperture_fstop = max(4.0, cd.lens / 12.0)


# ------------------------------------------------------------------ render setup
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = a.samples
sc.cycles.use_adaptive_sampling = True
sc.cycles.adaptive_threshold = 0.04
sc.cycles.use_denoising = True
sc.cycles.denoiser = 'OPENIMAGEDENOISE'
sc.cycles.max_bounces = 6
sc.cycles.diffuse_bounces = 2
sc.cycles.glossy_bounces = 3
sc.cycles.transmission_bounces = 6
sc.cycles.sample_clamp_indirect = 4.0
sc.render.use_persistent_data = True
sc.render.resolution_x, sc.render.resolution_y = 1080, 1920
sc.render.resolution_percentage = a.pct
sc.render.image_settings.file_format = 'PNG'
sc.view_settings.view_transform = 'AgX'
try:
    sc.view_settings.look = 'AgX - Medium High Contrast'
except Exception:
    pass


def do(t):
    ps, hold = act(t)
    for k, toy in TOY.items():
        toy.pose(ps[k])
    set_events(t, ps, hold)
    pose_camera(t)


if a.still is not None:
    for t in a.still:
        do(t)
        sc.render.filepath = os.path.join(os.path.abspath(a.out), f'still_{t:05.2f}.png')
        bpy.ops.render.render(write_still=True)
        print('wrote', sc.render.filepath, flush=True)
else:
    f0, f1 = a.frames
    for f in range(f0, f1, a.step):
        fp = os.path.join(os.path.abspath(a.out), f'f{f:04d}.png')
        if os.path.exists(fp):
            continue
        do(f / RATE)
        sc.render.filepath = fp
        bpy.ops.render.render(write_still=True)
        print('frame', f, flush=True)
