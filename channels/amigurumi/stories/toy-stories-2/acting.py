"""Acting helpers: life (breathing, sway, blinks), hops, shakes, dance moves.  All pure functions of time."""
import math
from engine import P, ease, eout, back_out, wob, clamp, lerp


def h(seed, k):
    x = math.sin(seed * 127.1 + k * 311.7) * 43758.5453
    return x - math.floor(x)


def life(p, t, seed=1, amt=1.0):
    """Breathing, slow sway, ear/tail flicks.  Adds into p."""
    ph = h(seed, 1) * 6.28
    p['sq'] += 0.025 * amt * math.sin(2 * math.pi * 0.45 * t + ph)
    p['roll'] += 2.0 * amt * math.sin(2 * math.pi * 0.23 * t + ph * 1.3)
    p['turn'] += 5.0 * amt * math.sin(2 * math.pi * 0.17 * t + ph * 0.7)
    p['tilt'] += 3.0 * amt * math.sin(2 * math.pi * 0.21 * t + ph * 1.9)
    p['tail'] += 12 * amt * math.sin(2 * math.pi * 0.9 * t + ph)
    p['earL'] += 5 * amt * math.sin(2 * math.pi * 0.31 * t + ph)
    p['earR'] += 5 * amt * math.sin(2 * math.pi * 0.29 * t + ph + 1)
    p['armL'] += 6 * amt * math.sin(2 * math.pi * 0.4 * t + ph)
    p['armR'] += 6 * amt * math.sin(2 * math.pi * 0.4 * t + ph + 0.8)
    return p


def blink(t, seed=1, every=2.6):
    """Eye scale factor from blinks: a blink every ~every s (seeded jitter), 0.13 s long."""
    k = math.floor(t / every)
    for j in (k - 1, k):
        tb = j * every + h(seed, j) * every * 0.7
        d = t - tb
        if 0 <= d < 0.14:
            return 0.08 + 0.92 * abs(d - 0.07) / 0.07
    return 1.0


def hop(u, height):
    u = clamp(u)
    return height * 4 * u * (1 - u)


def jump_squash(u):
    """Squash before take-off and at landing for a jump over u in [0,1] (u<0: anticipation, u>1: landing)."""
    if u < 0:
        return 0.22 * ease(1 + u / 0.25) if u > -0.25 else 0.0
    if u > 1:
        return 0.25 * wob(u - 1, 2.5, 6) if u < 2 else 0.0
    return -0.14 * math.sin(math.pi * u)


def shake(t, amp, f=17.0, seed=3):
    return amp * (math.sin(2 * math.pi * f * t + seed) * 0.6 + math.sin(2 * math.pi * f * 1.7 * t + seed * 2) * 0.4)


def pop_eyes(t, t0, peak=1.75, hold=0.6):
    """Eyes grow fast with an overshoot at t0, hold, then settle back."""
    d = t - t0
    if d < 0:
        return 1.0
    if d < hold:
        return 1 + (peak - 1) * back_out(d / 0.16, 3.0)
    return 1 + (peak - 1) * (1 - ease((d - hold) / 0.35))


def dance(p, t, b, move, i=0, e=1.0):
    """Beat-synced moves.  b: beat position (float).  Writes into p."""
    u = b % 1.0
    n = int(math.floor(b))
    side = 1 if n % 2 == 0 else -1
    land = math.exp(-((min(u, 1 - u)) / 0.08) ** 2)
    if move == 'bounce':
        p['y'] += hop(u, 16 * e)
        p['sq'] += 0.22 * e * land - 0.1 * e * math.sin(math.pi * u)
        p['armL'] += 110 * e * (0.5 + 0.5 * math.cos(2 * math.pi * u))
        p['armR'] += 110 * e * (0.5 + 0.5 * math.cos(2 * math.pi * u))
        p['bendL'] += 40 * math.sin(math.pi * u)
        p['bendR'] += 40 * math.sin(math.pi * u)
        p['nod'] += -10 * e * land
        p['earL'] += 25 * e * math.sin(math.pi * u)
        p['earR'] += 25 * e * math.sin(math.pi * u)
    elif move == 'sway':
        s = math.sin(math.pi * (b % 2.0))
        p['roll'] += 12 * e * math.sin(math.pi * b)
        p['x'] += 10 * e * math.sin(math.pi * b)
        p['sq'] += 0.12 * e * land
        p['armL'] += 140 if side > 0 else 30
        p['armR'] += 140 if side < 0 else 30
        p['bendL'] += 50 * (1 - u)
        p['bendR'] += 50 * u
        p['tilt'] += -12 * e * math.sin(math.pi * b)
    elif move == 'headbang':
        p['nod'] += 22 * e * (land - 0.3)
        p['pitch'] += 8 * e * land
        p['sq'] += 0.18 * e * land
        p['armL'] += 150 * (0.6 + 0.4 * math.cos(2 * math.pi * u))
        p['armR'] += 150 * (0.6 + 0.4 * math.cos(2 * math.pi * u))
        p['bendL'] += 70 * land
        p['bendR'] += 70 * land
    elif move == 'spin':
        p['yaw'] += 360 * ease(u) if n % 4 == 0 else 0
        p['y'] += hop(u, 22 * e) if n % 4 == 0 else hop(u, 8 * e)
        p['sq'] += 0.2 * e * land
        p['armL'] += 150
        p['armR'] += 150
    elif move == 'twist':
        p['yaw'] += 28 * e * math.sin(math.pi * b)
        p['turn'] += -20 * e * math.sin(math.pi * b)
        p['sq'] += 0.15 * e * land
        p['y'] += hop(u, 6 * e)
        p['armL'] += 90 + 50 * math.sin(math.pi * b)
        p['armR'] += 90 - 50 * math.sin(math.pi * b)
        p['bendL'] += 60
        p['bendR'] += 60
    elif move == 'pump':                       # fist pump, alternating arm
        up = 0.5 + 0.5 * math.cos(2 * math.pi * u)
        p['armL'] += 160 * up if side > 0 else 40
        p['armR'] += 160 * up if side < 0 else 40
        p['bendL'] += 80 * (1 - up)
        p['bendR'] += 80 * (1 - up)
        p['y'] += hop(u, 10 * e)
        p['sq'] += 0.18 * e * land
        p['nod'] += -14 * land
    return p
