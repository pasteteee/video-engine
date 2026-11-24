"""SNACK ATTACK: movie night.  Who ate the popcorn?  The shark pulls everything out of its mouth: the remote, a sock,
a live cookie, the goose's own knife...  The goose charges, the shark swallows it, silence, gulp, DROP: the goose
bursts back out in a popcorn explosion and everybody dances."""
import math
import numpy as np
from engine import P, Actor, load_spec, subspec, ease, eout, ein, back_out, wob, keys, clamp, lerp, rot
from acting import life, blink, hop, shake, pop_eyes, dance, jump_squash

NAME = 'snack-attack'
AUDIO = '/home/user/work/music/snack2a.mp3'
AUDIO_CUT = [(0.0, 38.6)]
DUR = 38.6
BG = '/home/user/work/bg/movie.png'
BEAT = 0.39893
LIGHT = (-0.6, 1.0, 0.32)
LOOK = dict(mul=(0.86, 0.80, 0.80), lift=0.0, shadow=0.95, shadow_tint=(0.45, 0.33, 0.25), wrap=0.22, shadow_blur=2.5,
            bloom=0.18, grain=0.035, vignette=0.25)
CAM0 = dict(pos=(0, 118, 640), target=(0, 90, 0), fov=26.0)
AIM_UP = 60.0
CENTER, EXTENT = (0, 60, 0), 420

T_WHO, T_NOTME, T_HIC = 0.3, 3.0, 5.4
T_REMOTE, T_SOCK, T_COOKIE, T_KNIFE = 7.31, 10.52, 13.3, 16.55
T_GRAB, T_GULP, T_DROP, T_BACK1, T_BACK2, T_END = 18.1, 20.6, 21.5, 24.8, 30.9, 37.8

SX, FX, GX = 0.0, -88.0, 92.0             # shark, frog, goose
MOUTH = (0.0, 55.0, 44.0)                 # shark head-piece rest point
NPOP = 7


def build():
    A = [Actor('shark', 'shark-in-a-hoodie', height=115, home=(SX, 0)),
         Actor('frog', 'frog-crying-tears', height=88, home=(FX, -6)),
         Actor('goose', 'goose-knife-meme', height=118, home=(GX, -4)),
         Actor('remote', 'tv-remote', height=62, home=(-700, -500)),
         Actor('sock', 'striped-sock', height=40, home=(-500, -700)),
         Actor('cookie', 'easy-cookie', height=48, home=(700, -500)),
         Actor('knife', 'knife', height=52, home=(500, -700), spec=subspec(load_spec('goose-knife-meme'), ['dagger']))]
    for j in range(NPOP):
        A.append(Actor(f'pop{j}', 'popcorn', height=13, home=(-900 + 60 * j, -900)))
    return A


def item_hold(stage, A, p, side, actor_key='shark'):
    """World point at the shark's hand tip."""
    i = [a.key for a in A].index(actor_key)
    act = A[i]
    k = next(k for k, pc in enumerate(act.dn.pieces) if pc['role'] == 'arm' and (pc.get('side', 0) >= 0) == (side > 0))
    return world_point(act, p, k, act.arm[k]['tip'], arm=True)


def world_point(act, p, k, Pl, arm=False):
    from engine import rig, _rod
    local, (R0, t0) = rig(act, p)
    hx, hz = act.home
    TR = act.dn.transforms(local, (R0, t0 + np.array([hx, 0.0, hz])))
    R, t = TR[k]
    Pl = np.asarray(Pl, float)
    if arm and k in act.arm:
        A = act.arm[k]
        ang = p['bendL'] if A['side'] >= 0 else p['bendR']
        Pl = A['E'] + _rod((Pl - A['E'])[None], A['ax'], np.array([math.radians(ang)]))[0]
    return R @ Pl + t


def held_point(A, p_shark, side):
    m = mouth_world(A, p_shark)
    return m + np.array([side * 34.0, 22.0, 14.0])


def mouth_world(A, p_shark):
    act = A[0]
    return world_point(act, p_shark, act.heads[0], MOUTH)


def ballistic(t, t0, t1, a, b, height):
    u = clamp((t - t0) / (t1 - t0))
    pos = np.array(a) * (1 - u) + np.array(b) * u
    pos[1] += height * 4 * u * (1 - u)
    return pos, u


def beat(t):
    return t / BEAT


PULLS = [  # (time, item key, arm side, landing x, z, spin)
    (T_REMOTE, 'remote', -1, -40, 48, 1),
    (T_SOCK, 'sock', 1, 42, 52, -1),
    (T_COOKIE, 'cookie', -1, -38, 70, 0),
    (T_KNIFE, 'knife', -1, None, None, 0),
]


def pose(t, A):
    names = [a.key for a in A]
    ps = {k: P(x=a.home[0], z=a.home[1], show=0.0 if names.index(k) >= 3 else 1.0) for k, a in zip(names, A)}
    sh, fr, go = ps['shark'], ps['frog'], ps['goose']
    drop = t >= T_DROP
    b = beat(t)
    # ---------------------------------------------------------------- life everywhere
    life(sh, t, 1, 0.8 if not drop else 0.3)
    life(fr, t, 2, 0.9 if not drop else 0.3)
    life(go, t, 3, 0.6 if not drop else 0.3)
    for k, s in (('shark', 1), ('frog', 2), ('goose', 3), ('cookie', 4)):
        ps[k]['eye'] *= blink(t, s)
    # ---------------------------------------------------------------- 0-7 s: accusation, innocence
    if t < T_REMOTE - 1.0:
        u = ease((t - 0.4) / 0.6)
        fr['turn'] += 28 * u
        go['turn'] += -32 * u
        go['tilt'] += 8 * u
        fr['aimL'] = (1.0, 0.35, 0.5) if 0.6 < t < 3.0 else None
        fr['bendL'] += 0
        go['yaw'] += -15 * u
        fr['pitch'] += -4 * u
        if t > T_NOTME:                                   # "not me..." whistling, looking away, arms behind
            v = t - T_NOTME
            sh['turn'] += 30 * math.sin(2 * math.pi * 0.5 * v)
            sh['tilt'] += 10 * math.sin(2 * math.pi * 0.25 * v)
            sh['nod'] += -10 * ease(v / 0.4)
            sh['armL'] += -20
            sh['armR'] += -20
            sh['fwdL'] = sh['fwdR'] = -35 * ease(v / 0.4)
            sh['roll'] += 5 * math.sin(2 * math.pi * 0.5 * v)
        # hiccup: one kernel jumps out of the mouth
        if T_HIC - 0.1 < t < T_HIC + 1.5:
            d = t - T_HIC
            sh['sq'] += 0.25 * wob(d, 3, 6)
            sh['nod'] += 12 * wob(d, 2, 5)
            sh['eye'] *= pop_eyes(t, T_HIC, 1.5, 0.4)
            fr['eye'] *= pop_eyes(t, T_HIC + 0.15, 1.6, 0.6)
            go['eye'] *= pop_eyes(t, T_HIC + 0.2, 1.5, 0.6)
    # ---------------------------------------------------------------- pulls
    landed = {}
    for n, (T, key, side, lx, lz, spin) in enumerate(PULLS):
        it = ps[key]
        sidek = 'L' if side > 0 else 'R'
        if t < T - 1.0:
            continue
        d = t - T
        # the arm goes to the mouth, pulls, then holds the thing up
        reach = ease((d + 1.0) / 0.5) * (1 - ease((d - 0.0) / 0.2) * 0.0)
        if d < 0.35:
            aim = np.array([-side * 0.65, 0.55, 0.75])
            sh['aim' + sidek] = tuple(aim)
            sh['bend' + sidek] += 40 * reach
            sh['nod'] += -14 * reach
            sh['pitch'] += -5 * reach
        elif d < 1.6 or key == 'knife':
            up = eout((d - 0.35) / 0.25)
            show_up = (0.2 + 0.9 * up)
            sh['aim' + sidek] = (side * 0.75, 0.9, 0.55)
            sh['bend' + sidek] += 35 * show_up
            sh['nod'] += 8 * wob(d - 0.35, 2, 5)
            sh['sq'] += 0.2 * wob(d - 0.35, 2.5, 6)
        # the item: in the mouth -> pulled out growing -> held -> tossed -> lands
        m = mouth_world(A, sh)
        if d < -0.25:
            pass
        elif d < 0.35:
            u = clamp((d + 0.25) / 0.6)
            out = m + np.array([side * 6 * u, 10 * u, 34 * eout(u)])
            sc = 0.25 + 0.75 * back_out(u, 2.5)
            it.update(show=1.0, scale=sc, x=out[0], y=out[1] - A[names.index(key)].height * sc * 0.5, z=out[2])
            it['pitch'] = -60 * (1 - u) if key != 'cookie' else 0
            ps['shark']['sq'] += 0.18 * math.sin(math.pi * u)
            sh['eye'] *= 1 + 0.4 * math.sin(math.pi * u)
        elif d < 1.3 or (key == 'knife' and t < T_GRAB):
            hp = held_point(A, sh, side)
            hh = A[names.index(key)].height
            it.update(show=1.0, x=hp[0], y=hp[1] - hh * 0.5, z=hp[2])
            if key == 'sock':
                it['yaw'] = 90
            it['roll'] = side * 10 * wob(d - 0.35, 1.5, 3)
            if key == 'sock':
                it['roll'] += 20 * math.sin(2 * math.pi * 1.2 * d)
            if key == 'cookie':
                it['eye'] *= pop_eyes(t, T + 0.3, 1.4, 0.4)
        elif lx is not None:
            hp0 = held_point(A, sh, side)
            hh = A[names.index(key)].height
            start = np.array([hp0[0], hp0[1] - hh * 0.5, hp0[2]])
            pos, u = ballistic(t, T + 1.3, T + 1.85, start, (lx, 0.0, lz), 35)
            it.update(show=1.0, x=pos[0], y=max(0.0, pos[1]), z=pos[2])
            if u < 1:
                it['roll'] = spin * 360 * u if key != 'cookie' else 0
                it['pitch'] = 0
            else:
                landed[key] = t - (T + 1.85)
                it['sq'] += 0.3 * wob(t - (T + 1.85), 2.5, 6)
                if key == 'remote':
                    it.update(pitch=-90, nolift=True, y=6, roll=0, yaw=25)
                if key == 'sock':
                    it.update(roll=90, nolift=True, y=10, yaw=-30)
            if key == 'remote' and u >= 1:
                it['pitch'] = -90
        # reactions
        fr['eye'] *= pop_eyes(t, T + 0.1, 1.8, 0.9)
        go['eye'] *= pop_eyes(t, T + 0.15, 1.7, 0.9) if key != 'knife' else 1.0
        if 0 < d < 1.2:
            w = ease(d / 0.2) * (1 - ease((d - 0.8) / 0.4))
            fr['pitch'] += -10 * w
            go['pitch'] += -8 * w
            fr['armL'] += 120 * w
            fr['armR'] += 120 * w
            go['armL'] += 60 * w
            go['armR'] += 60 * w
    # the cookie, after landing: alive, happy hops, looks around
    if 'cookie' in landed or t >= T_COOKIE + 1.85:
        ck = ps['cookie']
        ck.update(show=1.0)
        dl = t - (T_COOKIE + 1.85)
        if not drop:
            ck['y'] += hop((dl % 0.8) / 0.4, 8) if (dl % 0.8) < 0.4 else 0
            ck['turn'] += 25 * math.sin(2 * math.pi * 0.4 * dl)
            ck['yaw'] += 20 * math.sin(2 * math.pi * 0.3 * dl)
            ck.update(x=-38, z=70)
    # remote and sock stay on the table
    for key, lx, lz in (('remote', -40, 48), ('sock', 42, 52)):
        T = dict((p[1], p[0]) for p in PULLS)[key]
        if t >= T + 1.85:
            it = ps[key]
            it.update(show=1.0, x=lx, z=lz, y=6 if key == 'remote' else 10, nolift=True)
            it['pitch'] = -90 if key == 'remote' else 0
            it['roll'] = 0 if key == 'remote' else 90
            it['yaw'] = 25 if key == 'remote' else -30
            if key == 'sock':
                it['y'] = 9
            if drop:
                it['y'] += hop((beat(t) % 1.0), 6)
    # ---------------------------------------------------------------- the knife: gone from the goose's wing
    if T_KNIFE - 0.3 < t < T_GRAB + 0.1:
        go['pieces'] = {'dagger': np.eye(3) * 1e-3}
        d = t - T_KNIFE
        if d > 0.2:                                        # the goose looks at its empty wing, then glares
            w = ease((d - 0.2) / 0.3) * (1 - ease((d - 1.0) / 0.3))
            go['turn'] += -40 * w
            go['nod'] += 25 * w
            go['eye'] *= pop_eyes(t, T_KNIFE + 0.5, 2.0, 0.9)
            go['armR'] += 80 * w
    if T_KNIFE + 1.3 < t < T_GRAB + 0.2:                  # furious: shakes, steps toward the shark
        d = t - (T_KNIFE + 1.3)
        go['roll'] += shake(t, 4 * ease(d / 0.3))
        go['x'] += -14 * ease(d / 1.2)
        go['tilt'] += 10
        go['eye'] *= 0.75
    if t >= T_GRAB - 0.15 and t < T_GULP:                 # snatches it back and charges
        d = t - T_GRAB
        go['x'] += -14 - 26 * ease(d / 1.4)
        go['armR'] += 120 * back_out(clamp(d / 0.3))
        go['bendR'] += 30
        go['roll'] += shake(t, 3)
        go['pitch'] += 6
        go['y'] += hop((d % 0.4) / 0.4, 5)
        sh['roll'] += shake(t, 3.5 * ease(d / 0.5), 21)
        sh['eye'] *= 1.35
        sh['pitch'] += -6 * ease(d / 0.5)
    # ---------------------------------------------------------------- gulp: the shark swallows the goose
    if T_GULP - 0.35 <= t < T_DROP:
        d = t - (T_GULP - 0.35)
        m = mouth_world(A, sh)
        u = ein(clamp(d / 0.4))
        gx0 = GX - 40
        go['x'] = lerp(gx0, m[0], u)
        go['y'] = lerp(0, m[1] - 10, u)
        go['z'] = lerp(go['z'], m[2] - 5, u)
        go['scale'] = 1 - 0.95 * u
        go['roll'] += -40 * u
        go['sq'] += -0.3 * u
        if d > 0.42:
            go['show'] = 0.0
        sh['sq'] += 0.25 * wob(d - 0.4, 2, 3) + 0.12 * ease((d - 0.4) / 0.1)
        sh['eye'] *= 1.0 + 0.5 * ease((d - 0.4) / 0.1)
        fr['eye'] *= 2.0 if d > 0.5 else 1.0
        fr['pitch'] += -12 * ease((d - 0.4) / 0.2)
        ps['cookie']['eye'] *= 1.9 if d > 0.6 else 1.0
    # ---------------------------------------------------------------- DROP
    if drop:
        d = t - T_DROP
        if d < 0.9:                                        # the goose bursts out of the shark
            m = mouth_world(A, sh)
            u = clamp(d / 0.55)
            pos, _ = ballistic(t, T_DROP, T_DROP + 0.55, (m[0], m[1] - 20, m[2]), (GX - 10, 0, 6), 70)
            go.update(x=pos[0], y=max(0.0, pos[1]), z=pos[2], scale=0.3 + 0.7 * back_out(clamp(d / 0.25)))
            go['yaw'] += -360 * eout(u)
            go['sq'] += 0.3 * wob(d - 0.55, 2.5, 5)
            sh['sq'] += -0.25 * wob(d, 2, 4)
            sh['nod'] += -20 * wob(d, 1.5, 4)
        else:
            go['x'] = GX - 10
            go['z'] = 6
        # popcorn explosion
        moves = ['bounce', 'bounce', 'pump', 'pump', 'sway', 'sway', 'headbang', 'headbang', 'twist', 'twist', 'spin', 'bounce']
        bar = int((t - T_DROP) / (4 * BEAT))
        mv = moves[bar % len(moves)]
        e = 1.0
        bb = (t - T_DROP) / BEAT
        dance(sh, t, bb, mv, 0, e)
        dance(fr, t, bb - 0.12, {'sway': 'bounce', 'twist': 'pump'}.get(mv, mv), 1, 0.9)
        if d > 0.9:
            dance(go, t, bb - 0.06, {'spin': 'twist'}.get(mv, mv), 2, 0.9)
        ck = ps['cookie']
        ck['y'] += hop(bb % 1.0, 14)
        ck['sq'] += 0.25 * math.exp(-((min(bb % 1, 1 - bb % 1)) / 0.08) ** 2)
        ck['yaw'] += 360 * ease(bb % 4 / 1.0) if int(bb) % 8 == 6 else 0
        ck.update(x=-40, z=72)
        fr['eye'] *= 1.15
    # popcorn: hiccup kernel, the explosion at the drop, fountains on "eat it back"
    bursts = [(T_HIC, 1, 0.0), (T_DROP, NPOP, 0.0), (T_BACK1, NPOP, 0.0), (T_BACK2, NPOP, 0.0)]
    for j in range(NPOP):
        for (T0, n, _) in bursts:
            if j >= n:
                continue
            d = t - T0 - 0.04 * j
            if 0 <= d < 1.6:
                m = mouth_world(A, sh)
                ang = (j / max(1, n - 1) - 0.5) * 2.6 if n > 1 else 0.6
                land = (m[0] + 120 * math.sin(ang) * (0.5 + 0.5 * ((j * 7) % 5) / 4), 0.0, 40 + 50 * ((j * 3) % 4) / 3)
                tl = 0.55 + 0.08 * (j % 3)
                pos, u = ballistic(t, T0 + 0.04 * j, T0 + 0.04 * j + tl, m, land, 70 + 25 * (j % 3))
                q = ps[f'pop{j}']
                q.update(show=1.0, x=pos[0], y=max(0.0, pos[1]), z=pos[2])
                q['roll'] = 540 * u * (1 if j % 2 else -1)
                q['pitch'] = 300 * u
                if u >= 1:
                    q['sq'] += 0.3 * wob(d - tl, 3, 6)
                    q['y'] += hop(clamp((d - tl) / 0.35), 10)
    return [ps[k] for k in names]


# ------------------------------------------------------------------------------------------------ camera
def camera(t):
    """target (x, y, z), fov, shake px"""
    W = ((0, 52, 0), 26.0)
    shots = [
        (0.0, lambda t: (keys(t, [(0, (0, 52, 0)), (3, (0, 54, 0))]), keys(t, [(0, 27.0), (3.0, 23.5)]))),
        (T_NOTME, lambda t: ((SX, 62, 0), keys(t, [(T_NOTME, 15.5), (T_HIC, 14.0), (T_HIC + 0.15, 16.5)]))),
        (T_REMOTE - 1.0, lambda t: ((-8, 56, 0), keys(t, [(T_REMOTE - 1.0, 20.0), (T_REMOTE + 0.3, 21.5)]))),
        (T_REMOTE + 0.8, lambda t: ((0, 54, 0), 25.0)),
        (T_SOCK - 1.0, lambda t: ((8, 56, 0), keys(t, [(T_SOCK - 1.0, 20.0), (T_SOCK + 0.3, 21.5)]))),
        (T_SOCK + 0.8, lambda t: ((0, 54, 0), 25.0)),
        (T_COOKIE - 1.0, lambda t: ((-10, 56, 10), keys(t, [(T_COOKIE - 1.0, 19.5), (T_COOKIE + 0.3, 21.0)]))),
        (T_COOKIE + 1.6, lambda t: ((-20, 45, 30), keys(t, [(T_COOKIE + 1.6, 22.0), (T_KNIFE - 1.0, 24.0)]))),
        (T_KNIFE - 1.0, lambda t: ((10, 56, 0), 20.0)),
        (T_KNIFE + 0.4, lambda t: ((GX - 5, 70, 0), keys(t, [(T_KNIFE + 0.4, 14.0), (T_KNIFE + 1.3, 13.0)]))),
        (T_KNIFE + 1.3, lambda t: ((20, 56, 0), keys(t, [(T_KNIFE + 1.3, 24.0), (T_GRAB, 21.0)]))),
        (T_GRAB, lambda t: ((5, 62, 0), keys(t, [(T_GRAB, 18.0), (T_GULP - 0.4, 12.5)]))),
        (T_GULP - 0.4, lambda t: ((0, 54, 0), 24.0)),
        (T_DROP, None),
    ]
    sel = None
    for t0, f in shots:
        if t >= t0:
            sel = (t0, f)
    t0, f = sel
    sh = 0.0
    if f is not None:
        tg, fov = f(t)
        if T_GRAB <= t < T_GULP - 0.4:
            sh = 3.0 * ease((t - T_GRAB) / 1.5)
        return tg, fov, sh
    # drop: cuts every 2 bars between wide and close-ups, beat zoom pulses
    d = t - T_DROP
    bar2 = int(d / (8 * BEAT))
    u = (d / BEAT) % 1.0
    pulse = 1 - 0.035 * math.exp(-u / 0.12)
    plan = [((0, 54, 0), 26.0), ((SX, 60, 0), 15.0), ((0, 54, 0), 25.0), ((FX + 20, 50, 0), 17.0),
            ((GX - 20, 62, 0), 16.0), ((0, 54, 0), 26.5), ((-20, 45, 40), 17.0), ((0, 54, 0), 25.0)]
    tg, fov = plan[bar2 % len(plan)]
    if t >= T_END:
        tg, fov = (SX, 62, 0), 14.0
    sh = 2.5 * math.exp(-d / 0.4)
    return tg, fov * pulse, sh


CAPS = [
    (0.25, 2.9, ['WHO ATE', 'THE POPCORN?'], 'top'),
    (3.0, 6.9, ['not me...'], 'top'),
    (T_REMOTE - 0.05, T_SOCK - 0.6, ['THE REMOTE!'], 'top'),
    (T_SOCK - 0.05, T_COOKIE - 0.6, ['A SOCK?!'], 'top'),
    (T_COOKIE - 0.05, T_KNIFE - 0.6, ['A COOKIE?!'], 'top'),
    (T_KNIFE - 0.05, T_GRAB - 0.1, ['...AND', 'THE KNIFE?!'], 'top'),
    (T_GULP + 0.05, T_DROP - 0.05, ['*gulp*'], 'mid'),
    (T_DROP, T_DROP + 3.2, ['SNACK', 'ATTACK!'], 'top'),
    (T_BACK1 - 0.1, T_BACK1 + 2.9, ['EAT IT ALL,', 'THEN EAT IT BACK!'], 'top'),
    (27.9, 30.8, ['SNACK', 'ATTACK!'], 'top'),
    (T_BACK2 - 0.1, T_BACK2 + 3.0, ['EAT IT ALL,', 'THEN EAT IT BACK!'], 'top'),
    (34.0, T_END - 0.05, ['SNACK', 'ATTACK!'], 'top'),
    (T_END, DUR, ['who\'s next?'], 'top'),
]
