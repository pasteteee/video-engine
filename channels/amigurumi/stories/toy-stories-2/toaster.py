"""THE TOASTER: breakfast in a sunny kitchen.  Ding! a toast.  Ding! ...a blueberry?  Ding! ...a hamster?!
Something's coming... something hot!  Silence.  DROP: the sun in sunglasses blasts out and the kitchen parties."""
import math
import numpy as np
from engine import P, Actor, ease, eout, ein, back_out, wob, keys, clamp, lerp, rot
from acting import life, blink, hop, shake, pop_eyes, dance

NAME = 'the-toaster'
AUDIO = '/mnt/project-files/channel-video/toy-stories-2/music/toaster.mp3'
DUR = 37.7
BG = '/home/user/work/bg/kitchen.png'
BEAT = 0.5
B0 = 0.2204
LIGHT = (-0.85, 0.95, 0.3)
LOOK = dict(mul=(1.03, 0.98, 0.9), lift=0.0, shadow=0.9, shadow_tint=(0.55, 0.40, 0.28), wrap=0.18, shadow_blur=2.0,
            bloom=0.22, grain=0.025, vignette=0.18, contact=0.5)
CAM0 = dict(pos=(0, 118, 640), target=(0, 90, 0), fov=26.0)
AIM_UP = 60.0
CENTER, EXTENT = (0, 60, 0), 420

T_PUSH1, T_D1, T_PUSH2, T_D2, T_PUSH3, T_D3 = 6.0, 8.22, 10.6, 12.21, 14.6, 16.21
T_COMING, T_HOT, T_FREEZE, T_DROP, T_END = 20.2, 22.2, 24.21, 25.71, 37.0
TX, TZ = 0.0, -12.0
PX, DX = -98.0, 102.0
TOP = 82.0


def build():
    return [Actor('toaster', 'retro-toaster', height=84, home=(TX, TZ)),
            Actor('pig', 'easy-pig-ball', height=60, home=(PX, 4)),
            Actor('dog', 'dog-side-eye-suspicious', height=84, home=(DX, -4)),
            Actor('toast', 'toast', height=50, home=(-700, -500)),
            Actor('berry', 'easy-blueberry', height=42, home=(-500, -700)),
            Actor('hamster', 'easy-hamster-ball', height=44, home=(700, -500)),
            Actor('sun', 'sun-sunglasses', height=92, home=(500, -700))]


def beat(t):
    return (t - B0) / BEAT


def ballistic(t, t0, t1, a, b, height):
    u = clamp((t - t0) / (t1 - t0))
    pos = np.array(a, float) * (1 - u) + np.array(b, float) * u
    pos[1] += height * 4 * u * (1 - u)
    return pos, u


POPS = [(T_D1, 'toast', (-52, 0, 58), 1), (T_D2, 'berry', (-18, 0, 72), -1), (T_D3, 'hamster', (40, 0, 62), 1)]


def pose(t, A):
    names = [a.key for a in A]
    ps = {k: P(x=a.home[0], z=a.home[1], show=0.0 if names.index(k) >= 3 else 1.0) for k, a in zip(names, A)}
    to, pg, dg = ps['toaster'], ps['pig'], ps['dog']
    drop = t >= T_DROP
    b = beat(t)
    life(to, t, 5, 0.5)
    life(pg, t, 6, 1.0)
    life(dg, t, 7, 0.7)
    for k, s in (('toaster', 5), ('pig', 6), ('dog', 7), ('berry', 8), ('hamster', 9), ('toast', 10)):
        ps[k]['eye'] *= blink(t, s, 2.3)
    # the dog's side eye toward the toaster, always suspicious
    dg['turn'] += -22
    dg['yaw'] += -12
    pg['yaw'] += 14
    # ---------------------------------------------------------------- intro: the pig is hungry, groove bounce
    if t < T_PUSH1 - 1.2:
        pg['y'] += hop((b % 1.0), 6) if t > 1.0 else 0
        pg['sq'] += 0.12 * math.exp(-((min(b % 1, 1 - b % 1)) / 0.08) ** 2) if t > 1.0 else 0
        to['sq'] += 0.04 * math.sin(math.pi * 2 * b / 2)
    # lever pushes: the pig (twice) and the dog (once) butt the lever down
    lever = 0.0
    for tp, who, sx in ((T_PUSH1, pg, 1), (T_PUSH2, pg, 1), (T_PUSH3, dg, -1)):
        d = t - tp
        if -1.2 < d < 1.0:
            home = PX if who is pg else DX
            close = (TX - 50) if who is pg else (TX + 58)
            w = ease((d + 1.2) / 0.7) * (1 - ease((d - 0.3) / 0.6))
            who['x'] = lerp(home, close, w)
            who['y'] += hop(((d + 1.2) % 0.35) / 0.35, 5) * (w > 0.05 and w < 0.95)
            # the butt: anticipation back, then a quick lean in
            who['pitch'] += -10 * math.exp(-((d + 0.15) / 0.1) ** 2) + 22 * math.exp(-((d - 0.05) / 0.08) ** 2)
            who['roll'] += sx * 12 * math.exp(-((d - 0.05) / 0.08) ** 2)
            who['sq'] += 0.2 * wob(d - 0.05, 3, 6)
        if d >= 0:
            lever = max(lever, ease(d / 0.12))
    for td in (T_D1, T_D2, T_D3):
        if t >= td:
            lever = lever * (1 - ease((t - td) / 0.08)) if t - td < 0.5 else (lever if t >= td + 0.5 else lever)
    # lever state: down between a push and its ding
    down = 0.0
    for tp, td in ((T_PUSH1, T_D1), (T_PUSH2, T_D2), (T_PUSH3, T_D3)):
        if tp <= t < td:
            down = ease((t - tp) / 0.12)
        elif td <= t < td + 0.3:
            down = max(down, 1 - back_out(clamp((t - td) / 0.12), 3))
    if T_COMING - 0.5 <= t < T_DROP:
        down = 1.0
    to['pieces'] = {'lever': rot([0, 0, 1], -40 * down)}
    # heating: the toaster hums, squints a little
    heating = any(tp <= t < td for tp, td in ((T_PUSH1, T_D1), (T_PUSH2, T_D2), (T_PUSH3, T_D3)))
    if heating:
        to['roll'] += shake(t, 0.8, 23)
        to['eye'] *= 0.85
    # the dings: the toaster jumps, the thing flies out, lands
    for n, (td, key, land, spin) in enumerate(POPS):
        d = t - td
        if d >= -0.02:
            to['sq'] += 0.35 * wob(d, 2.5, 5) if d < 1.5 else 0
            to['y'] += hop(clamp(d / 0.25), 10)
            to['eye'] *= pop_eyes(t, td, 1.5, 0.3)
        it = ps[key]
        if d < 0:
            continue
        top = np.array([TX, TOP - 30, TZ])
        tl = 0.95
        pos, u = ballistic(t, td, td + tl, top, land, 150)
        it.update(show=1.0, x=pos[0], y=max(0.0, pos[1]), z=pos[2])
        if u < 1:
            it['roll'] = spin * 360 * eout(u) if key != 'hamster' else 0
            it['yaw'] = 720 * u if key == 'hamster' else 0
            it['sq'] = -0.15 * math.sin(math.pi * u)
        else:
            dl = t - (td + tl)
            it['sq'] += 0.35 * wob(dl, 2.5, 5)
            it['y'] += hop(clamp(dl / 0.3), 14) * (dl < 0.3)
            if key == 'hamster' and not drop:                # dizzy
                it['yaw'] += 50 * math.sin(2 * math.pi * 1.3 * dl) * math.exp(-0.3 * dl)
                it['roll'] += 12 * math.sin(2 * math.pi * 0.9 * dl)
                it['eye'] *= 0.6 + 0.4 * abs(math.sin(4 * dl))
            if key == 'berry' and not drop:
                it['turn'] += 20 * math.sin(2 * math.pi * 0.5 * dl)
                it['tilt'] += 15
            if key == 'toast' and not drop:
                it['yaw'] += 15 * math.sin(2 * math.pi * 0.4 * dl)
        # reactions
        if 0 < d < 2.0:
            w = ease(d / 0.15) * (1 - ease((d - 1.2) / 0.5))
            pg['eye'] *= pop_eyes(t, td + 0.2, 1.7 if key != 'toast' else 1.4, 0.8)
            dg['eye'] *= pop_eyes(t, td + 0.25, 1.6, 0.8)
            if key == 'toast':
                pg['y'] += hop(clamp((d - 1.0) / 0.3), 16) + hop(clamp((d - 1.35) / 0.3), 12)
                pg['earL'] += 30 * w
                pg['earR'] += 30 * w
            else:
                pg['tilt'] += 18 * w
                pg['pitch'] += -8 * w
                dg['tilt'] += -14 * w
                dg['turn'] += 10 * w
    # ---------------------------------------------------------------- something's coming
    if T_COMING <= t < T_DROP:
        d = t - T_COMING
        k = ease(d / 4.0)
        if t < T_FREEZE:
            to['roll'] += shake(t, 2 + 7 * k, 19)
            to['yaw'] += shake(t, 3 * k, 13, 5)
            to['y'] += hop((b * 2 % 1.0), 3 + 9 * k) if t > T_HOT else 0
            to['sq'] += 0.08 * k * math.sin(2 * math.pi * 6 * t)
            to['eye'] *= 1 + 0.6 * k
            for who, home, away in ((pg, PX, PX - 18), (dg, DX, DX + 20)):
                who['x'] = lerp(home, away, ease(d / 1.5))
                who['pitch'] += -8 * ease(d / 1.0)
                who['eye'] *= 1.3 + 0.3 * k
                who['roll'] += shake(t, 1.5 * k, 11)
            for key in ('toast', 'berry', 'hamster'):
                ps[key]['pitch'] += -8 * ease(d / 1.0)
                ps[key]['eye'] *= 1.3 + 0.4 * k
                ps[key]['roll'] += shake(t, 1.2 * k, 13)
        else:                                               # silence: everything frozen, eyes huge
            to['eye'] *= 2.0
            to['sq'] += -0.08
            to['y'] += 4
            to['roll'] += shake(t, 0.6, 31)
            for who, away in ((pg, PX - 18), (dg, DX + 20)):
                who['x'] = away
                who['eye'] *= 1.9
                who['pitch'] += -8
            for key in ('toast', 'berry', 'hamster'):
                ps[key]['eye'] *= 1.8
                ps[key]['pitch'] += -8
    # ---------------------------------------------------------------- DROP
    if drop:
        d = t - T_DROP
        su = ps['sun']
        ty = to['y']
        pos, u = ballistic(t, T_DROP, T_DROP + 0.7, (TX, TOP - 40, TZ), (TX, TOP - 4 + ty, TZ - 2), 140)
        if u >= 1:
            pos[1] = TOP - 4 + ty
        su.update(show=1.0, x=pos[0], y=pos[1], z=pos[2], scale=0.3 + 0.7 * back_out(clamp(d / 0.35), 2), nolift=True)
        su['yaw'] = 360 * eout(u)
        if u >= 1:
            su['sq'] += 0.3 * wob(d - 0.7, 2.5, 5)
        to['x'] = TX + 8 * wob(d, 1.2, 3)
        to['sq'] += -0.3 * wob(d, 2, 4)
        to['y'] += hop(clamp(d / 0.35), 25)
        moves = ['bounce', 'bounce', 'pump', 'twist', 'sway', 'bounce', 'headbang', 'spin']
        bb = (t - T_DROP) / BEAT
        mv = moves[int(bb / 4) % len(moves)]
        if d > 0.5:
            dance(to, t, bb, mv, 0, 0.8)
            dance(pg, t, bb - 0.1, mv, 1, 1.0)
            dance(dg, t, bb - 0.05, mv, 2, 0.9)
        pg['x'], dg['x'] = PX - 6, DX + 8
        if d > 0.75:
            to['y'] = min(to['y'], 10.0)
            su['y'] = TOP - 4 + to['y']
            dance(su, t, bb, {'spin': 'spin', 'headbang': 'bounce'}.get(mv, 'twist'), 3, 1.0)
            su['scale'] = 1.0
            su['roll'] += 6 * math.sin(math.pi * bb)
        for j, key in enumerate(('toast', 'berry', 'hamster')):
            it = ps[key]
            u2 = (bb - 0.15 * j) % 1.0
            it['y'] += hop(u2, 12 + 4 * j)
            it['sq'] += 0.25 * math.exp(-((min(u2, 1 - u2)) / 0.08) ** 2)
            it['yaw'] += 20 * math.sin(math.pi * (bb - 0.15 * j))
        if t >= T_END:
            for k in names:
                ps[k]['eye'] *= 1.0
    return [ps[k] for k in names]


def camera(t):
    if t < T_PUSH1 - 1.4:
        return (keys(t, [(0, (0, 50, 0)), (4.5, (-10, 48, 0))]), keys(t, [(0, 26.0), (4.5, 23.0)]), 0.0)
    if t < T_D1 - 0.3:
        return ((-30, 50, 0), keys(t, [(T_PUSH1 - 1.4, 18.0), (T_D1 - 0.3, 16.5)]), 0.0)
    if t < T_D1 + 1.6:
        return (keys(t, [(T_D1 - 0.3, (-10, 60, 0)), (T_D1 + 1.0, (-25, 48, 20))]), keys(t, [(T_D1 - 0.3, 24.0), (T_D1 + 1.0, 21.0)]), 2.0 * math.exp(-max(0, t - T_D1) / 0.25))
    if t < T_D2 - 0.3:
        return ((-30, 48, 10), keys(t, [(T_D1 + 1.6, 19.0), (T_D2 - 0.3, 17.0)]), 0.0)
    if t < T_D2 + 1.8:
        return (keys(t, [(T_D2 - 0.3, (-5, 60, 0)), (T_D2 + 1.0, (-15, 46, 30))]), keys(t, [(T_D2 - 0.3, 24.0), (T_D2 + 1.0, 20.0)]), 2.0 * math.exp(-max(0, t - T_D2) / 0.25))
    if t < T_D3 - 0.3:
        return ((40, 52, 0), keys(t, [(T_D2 + 1.8, 19.0), (T_D3 - 0.3, 17.5)]), 0.0)
    if t < T_COMING:
        return (keys(t, [(T_D3 - 0.3, (0, 60, 0)), (T_D3 + 1.2, (15, 48, 25)), (T_COMING, (0, 52, 10))]), keys(t, [(T_D3 - 0.3, 25.0), (T_D3 + 1.2, 21.0), (T_COMING, 26.0)]), 2.0 * math.exp(-max(0, t - T_D3) / 0.25))
    if t < T_FREEZE:
        k = ease((t - T_COMING) / 4.0)
        return ((TX, 52, TZ), lerp(24.0, 13.0, k), 1.0 + 4 * k)
    if t < T_DROP:
        return ((TX, 52, TZ), 11.5, 0.3)
    d = t - T_DROP
    u = (d / BEAT) % 1.0
    pulse = 1 - 0.035 * math.exp(-u / 0.12)
    if d < 2.0:
        return ((0, 85, -10), lerp(27.0, 26.0, ease(d / 2.0)) * pulse, 8 * math.exp(-d / 0.3))
    plan = [((0, 58, -10), 26.0), ((TX, 118, TZ), 17.0), ((PX + 20, 45, 0), 16.0), ((0, 55, 0), 26.0),
            ((DX - 15, 52, 0), 16.5), ((0, 45, 40), 18.0), ((0, 58, -10), 26.0)]
    tg, fov = plan[int((d - 2.0) / (8 * BEAT)) % len(plan)]
    if t >= T_END:
        tg, fov = (0, 58, -10), 26.0
    return tg, fov * pulse, 0.0


CAPS = [
    (0.6, 5.0, ['good morning,', 'toast...'], 'top'),
    (T_D1, T_D1 + 0.9, ['DING!'], 'top'),
    (T_D1 + 0.9, T_D2 - 0.6, ['...TOAST!'], 'top'),
    (T_D2, T_D2 + 0.9, ['DING!'], 'top'),
    (T_D2 + 0.9, T_D3 - 0.6, ['...A BERRY?'], 'top'),
    (T_D3, T_D3 + 0.9, ['DING!'], 'top'),
    (T_D3 + 0.9, T_COMING - 0.1, ['...A HAMSTER?!'], 'top'),
    (T_COMING, T_HOT - 0.05, ["something's", 'coming...'], 'top'),
    (T_HOT, T_FREEZE, ['...something', 'HOT!'], 'top'),
    (T_DROP, T_DROP + 3.0, ['BREAKFAST', 'IS SERVED!'], 'top'),
    (T_END - 0.2, DUR, ['POP! POP!', 'TOAST!'], 'top'),
]


def fx(im, t, cam, params, A, project):
    """Glow from the toaster slots while heating and on the drop; a white flash at the drop."""
    from PIL import Image, ImageDraw, ImageFilter
    import numpy as np
    g = 0.0
    for tp, td in ((T_PUSH1, T_D1), (T_PUSH2, T_D2), (T_PUSH3, T_D3)):
        if tp <= t < td + 0.3:
            g = max(g, 0.35 * ease((t - tp) / 1.0) * (1 - ease((t - td) / 0.3)))
    if T_COMING <= t < T_DROP:
        g = max(g, 0.4 + 0.6 * ease((t - T_COMING) / 4.0))
    if T_DROP <= t < T_DROP + 1.2:
        g = max(g, 1.0 - ease((t - T_DROP) / 1.2))
    a = np.asarray(im, np.float32) / 255
    if g > 0.01:
        p = params[0]
        x, y, _ = project(cam, (p['x'], TOP + p['y'] + 2, p['z']))
        lay = Image.new('L', (270, 480), 0)
        d = ImageDraw.Draw(lay)
        r = 40 + 30 * g
        d.ellipse((x / 4 - r, y / 4 - r * 0.6, x / 4 + r, y / 4 + r * 0.6), fill=int(255 * min(1, g)))
        lay = lay.filter(ImageFilter.GaussianBlur(14)).resize((1080, 1920), Image.BILINEAR)
        m = np.asarray(lay, np.float32)[..., None] / 255
        a = 1 - (1 - a) * (1 - m * np.array([1.0, 0.62, 0.25]) * 0.9)
    if T_DROP <= t < T_DROP + 0.4:
        f = 1 - ease((t - T_DROP) / 0.4)
        a = a + (1 - a) * 0.85 * f
    return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8))
