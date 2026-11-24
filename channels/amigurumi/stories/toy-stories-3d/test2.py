"""3.5 s 3D test: the shark opens its mouth, a TV remote slides out of its throat, it grabs it and switches the
channel; the frog gasps, recoils into the popcorn bucket, popcorn spills and rolls on the table.
Usage: python test1.py OUT_DIR [--still T] [--frames A B] [--pct 100] [--samples 48]"""
import sys, math, os, argparse
sys.path.insert(0, '/home/user/work/b3d')
import numpy as np
import bpy
from mathutils import Matrix, Quaternion, Vector

ap = argparse.ArgumentParser()
ap.add_argument('out')
ap.add_argument('--still', type=float, nargs='*')
ap.add_argument('--frames', type=int, nargs=2)
ap.add_argument('--pct', type=int, default=100)
ap.add_argument('--samples', type=int, default=48)
ap.add_argument('--cam', type=str, default=None)
a = ap.parse_args(sys.argv[1:])
os.makedirs(a.out, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
import set3d, toys3d  # noqa: E402
from toys3d import Toy3D, bmat, K, MM  # noqa: E402
from engine import P, ease, eout, back_out, spring, wob, keys, clamp, lerp  # noqa: E402
from acting import life, blink, pop_eyes, shake, hop  # noqa: E402
from vengine.yarn.dance import rot  # noqa: E402

FPS, DUR = 24, 3.5
sc = bpy.context.scene
M = set3d.materials()
H = set3d.build_room()
tc = set3d.coll('toys')
B3 = '/home/user/work/b3d/'
from ami3d import AmiToy, Prop, ami_materials  # noqa: E402
M2 = ami_materials()
shark = AmiToy(B3 + 'shark-in-a-hoodie.ami.pkl', 'shark', M2, tc, home=(-54.0, 0.0))
shark.add_mouth(M2, tc, ('mouth', 'tooth_0', 'tooth_1', 'tooth_2', 'tooth_3'), ky=2.3, tshrink=0.35)
frog = AmiToy(B3 + 'frog-crying-tears.ami.pkl', 'frog', M2, tc, home=(56.0, 4.0))
frog.add_mouth(M2, tc, ('mouth',))
shark.add_swaps(B3 + 'shark-in-a-hoodie.mouths.pkl', M2, tc)
frog.add_swaps(B3 + 'frog-crying-tears.mouths.pkl', M2, tc)
remote = Prop(B3 + 'tv-remote.ami.pkl', 'remote', M2, tc)
pop = Prop(B3 + 'popcorn.ami.pkl', 'pop', M2, tc)
# the remote's LED: a small bead on its top end
led = set3d.sphere(tc, 'led', 1.6, (0, 0, 0), M['led'], seg=12)
LED_AT = np.array([0.0, 57.0, 3.2])

# ------------------------------------------------------------------ popcorn: heap in the bucket + spilled kernels
BUCKET = np.array([92.0, 0.0, -62.0])            # toy space (mm): x, y (table), z (front +)
rng = np.random.default_rng(3)
kernels = []
for i in range(26):
    ob = pop.objs[0] if i == 0 else pop.objs[0].copy()
    if i:
        tc.objects.link(ob)
    ang = rng.uniform(0, 2 * np.pi); rr = rng.uniform(0, 22) if i > 6 else rng.uniform(0, 14)
    lp = np.array([math.cos(ang) * rr, 60 + rng.uniform(0, 14) - rr * 0.3, math.sin(ang) * rr])
    R0 = rot(rng.normal(size=3), rng.uniform(0, 360))
    kernels.append(dict(ob=ob, lp=lp, R0=R0, spill=i < 9, w=rng.normal(size=3)))
T_HIT = 1.62
# simulate the spilled ones: thrown from the rim when the bucket tips, gravity, bounces on the table, roll + friction
G = -9810.0


def simulate(k):
    lp = k['lp']
    p = BUCKET + np.array([lp[0] * 1.1 - 6, 66 + lp[1] * 0.1, lp[2] * 1.1])
    v = np.array([rng.uniform(-260, 120), rng.uniform(300, 520), rng.uniform(140, 420)])
    om = rng.normal(size=3) * 14
    path, R = [], k['R0'].copy()
    t, dt = T_HIT, 1 / 480
    while t < DUR + 0.1:
        v[1] += G * dt
        p = p + v * dt
        if p[1] < 6.5:
            p[1] = 6.5
            if v[1] < -60:
                v[1] = -v[1] * 0.32
                v[[0, 2]] *= 0.75
            else:
                v[1] = 0
                v[[0, 2]] *= (1 - 3.0 * dt)
            om = np.array([v[2], 0, -v[0]]) / 6.5
        n = np.linalg.norm(om)
        if n > 1e-6:
            R = rot(om / n, math.degrees(n * dt)) @ R
        path.append((t, p.copy(), R.copy()))
        t += dt
    k['path'] = path


for k in kernels:
    if k['spill']:
        simulate(k)


def bucket_tilt(t):
    """Tip away from the frog when hit, rock back and settle (degrees)."""
    d = t - T_HIT
    if d < 0:
        return 0.0
    return 24 * math.exp(-4.5 * d) * math.sin(2 * math.pi * 1.9 * d + 0.35) + 6 * math.exp(-2.0 * d) * (d < 0.15) * d / 0.15


def pose_bucket(t):
    th = bucket_tilt(t)
    # pivot on the rim edge away from the frog (towards -x, back)
    edge = BUCKET + np.array([-26.0, 0, -6.0])
    ax = np.array([0, 0, 1.0]) * -1
    Rb = rot([0.25, 0, 1.0], th)
    tb = edge + Rb @ (BUCKET - edge)
    H['bucket'].matrix_world = bmat(Rb, tb)
    return Rb, tb


def pose_popcorn(t, Rb, tb):
    for k in kernels:
        if k['spill'] and t >= T_HIT:
            i = min(len(k['path']) - 1, int((t - T_HIT) * 480))
            _, p, R = k['path'][i]
            k['ob'].matrix_world = bmat(R, p)
        else:
            k['ob'].matrix_world = bmat(Rb @ k['R0'], Rb @ k['lp'] + tb)


# ------------------------------------------------------------------ acting
def blinkv(t, seed):
    return blink(t, seed, every=2.3)


def shark_act(t):
    p = P(yaw=14.0, armL=-22.0, armR=-22.0)
    life(p, t, seed=2, amt=0.8)
    p['blink'] = blinkv(t, 5) if t > 2.2 or t < 0.4 else 1.0
    # anticipation: lean back, squash, squeeze the eyes
    ant = ease((t - 0.42) / 0.4) * (1 - ease((t - 0.95) / 0.25))
    p['pitch'] += -7 * ant
    p['sq'] += 0.14 * ant
    p['squint'] = 0.85 * ant + 0.35 * clamp((t - 2.5) / 0.3) * (1 - 0.0)
    # mouth: pops open, pulses as it pushes the remote out, snaps shut with a wobble, then a smug grin
    op = back_out((t - 0.85) / 0.28, 2.2) if t < 1.95 else 1 - spring((t - 1.95) / 0.9, 2.0, 5.0)
    if 1.15 < t < 1.9:
        op *= 0.93 + 0.07 * math.cos(2 * math.pi * 5.0 * (t - 1.15))
    op = clamp(op, 0, 1.12)
    mouth = op if t > 0.85 else 0.0
    smile = clamp((t - 2.1) / 0.3) * 0.8
    p['nod'] += -16 * clamp(op) * (1 if t < 2.1 else 0.6) + 6 * ant
    p['sq'] += -0.08 * clamp(op)
    p['eye'] = 1.0 + 0.12 * clamp((t - 2.2) / 0.2)
    # the right fin reaches the mouth, grabs the remote, swings it at the TV, clicks
    reach = ease((t - 1.25) / 0.45)
    swing = ease((t - 1.98) / 0.35)
    mouthp = np.array([-12.0, 62.0, 68.0])
    J = shark.pieces[shark.piece('arm_R')]['joint']
    d_mouth = mouthp - J
    d_tv = np.array([-0.15, 0.55, 1.0])
    d_rest = np.array([-0.8, -0.6, 0.2])
    d = d_rest * (1 - reach) + d_mouth / np.linalg.norm(d_mouth) * reach
    d = d * (1 - swing) + d_tv * swing
    p['aimR'] = d
    click = math.exp(-((t - 2.45) / 0.05) ** 2)
    p['bendR'] = 35 * reach * (1 - swing) + 25 * swing + 25 * click
    p['nod'] += 4 * click
    if t > 2.6:                                        # satisfied little bob
        p['y'] += hop(((t - 2.6) * 2.2) % 1, 4)
        p['roll'] += 4 * math.sin(2 * math.pi * 1.1 * (t - 2.6))
    return p, mouth, smile, reach, swing, click


def frog_act(t):
    p = P(yaw=-18.0, z=0.0, armL=-15.0, armR=-15.0)
    life(p, t, seed=7, amt=1.0)
    p['blink'] = blinkv(t, 9)
    look = ease((t - 1.05) / 0.2)
    back = ease((t - 2.4) / 0.3)
    p['turn'] += -38 * look * (1 - back)
    p['yaw'] += -10 * look * (1 - back)
    # gasp: eyes pop, body stretches, recoils back into the bucket, arms fly up
    sh = clamp((t - 1.22) / 0.12)
    p['eye'] = pop_eyes(t, 1.22, peak=1.4, hold=1.0)
    rec = eout((t - 1.22) / 0.4) * (1 - ease((t - 2.0) / 0.5) * 0.7)
    p['z'] += -26 * rec
    p['x'] += 10 * rec
    p['pitch'] += -20 * rec + 12 * wob(t - T_HIT, 3.0, 6.0)
    p['sq'] += -0.2 * sh * (1 - ease((t - 1.5) / 0.3)) + 0.2 * wob(t - T_HIT, 3.5, 7.0)
    p['y'] += hop((t - 1.22) / 0.3, 9) if 1.22 < t < 1.52 else 0
    p['armL'] += 150 * rec
    p['armR'] += 150 * rec
    p['bendL'] += 40 * rec
    p['bendR'] += 40 * rec
    p['roll'] += shake(t, 3.0, 19) * clamp((t - T_HIT) / 0.05) * (1 - clamp((t - 2.1) / 0.3))
    gasp = clamp(back_out((t - 1.22) / 0.18) * 0.9) * (1 - ease((t - 2.0) / 0.4)) + 0.35 * clamp((t - 2.55) / 0.2)
    # double blink in disbelief
    if 2.05 < t < 2.4:
        p['blink'] = 0.1 + 0.9 * abs(math.cos(math.pi * (t - 2.05) / 0.175))
    if t > 2.6:                                        # the new channel: a happy bounce
        u = (t - 2.6) * 2.2
        p['y'] += hop(u % 1, 10)
        p['sq'] += 0.15 * math.exp(-((min(u % 1, 1 - u % 1)) / 0.1) ** 2)
        p['armL'] += 60 + 40 * math.sin(2 * math.pi * u)
        p['armR'] += 60 - 40 * math.sin(2 * math.pi * u)
    return p, clamp(gasp)


# remote: inside the throat -> slides out along the mouth axis -> into the fin
RSC = 0.6                                              # a toy-sized remote, cute and it fits the mouth
_a = math.radians(42)                                  # comes out leaning towards the fin, buttons to camera
_L = np.array([-math.sin(_a), 0, math.cos(_a)]); _B = np.array([math.cos(_a), 0, math.sin(_a)])
R_OUT = np.stack([np.cross(_L, _B), _L, _B], 1)


def pose_remote(t, reach, swing, click):
    M_ = shark.mouth
    Rh, th = shark.TR[M_['k']]
    out = -3 + 70 * ease((t - 1.05) / 0.85)
    out += 3 * math.sin(2 * math.pi * 5 * (t - 1.15)) * (1.05 < t < 1.9)
    base = M_['top'] - M_['ey'] * 12.0 + M_['n'] * 1.0 + (Rh_n := R_OUT @ np.array([0, 1.0, 0])) * (out - 62) * RSC
    Rm, tm = Rh @ R_OUT, Rh @ base + th
    k = shark.piece('arm_R')
    A = shark.arm[k]
    tip = shark.world(k, A['tip'])
    Rb0, _ = shark.TR[0]
    dl = np.array([-0.35, 0.55, 0.9]); dl /= np.linalg.norm(dl)
    up = np.array([0, 1.0, 0]) - dl * dl[1]; up /= np.linalg.norm(up)
    ex = np.cross(dl, up)
    Rhold = (Rb0 / np.cbrt(np.linalg.det(Rb0))) @ np.stack([ex, dl, -up], 1) @ rot([0, 1, 0], 180) * np.cbrt(np.linalg.det(Rb0))
    hold_t = tip - Rhold @ np.array([0, 10.0, 0]) + (Rb0 @ np.array([12.0, 8.0, 26.0]))
    g = ease((t - 1.88) / 0.22)
    q0 = Matrix(Rm.tolist()).to_quaternion()
    q1 = Matrix((Rhold / np.cbrt(np.linalg.det(Rhold))).tolist()).to_quaternion()
    R = np.array(q0.slerp(q1, g).to_matrix())
    tt = tm * (1 - g) + hold_t * g
    remote.place(R * RSC, tt)
    for ob in remote.objs + [led]:
        ob.hide_render = t < 1.02
    led.matrix_world = bmat(R * RSC, tt + R @ LED_AT * RSC)
    M['led'].node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 40.0 * click


def tv_light(t):
    """Old channel: cool blue flicker; after the click a warm, fast-cut colourful one."""
    f = 0.75 + 0.25 * math.sin(t * 23) * math.sin(t * 7.3)
    if t < 2.47:
        col, pw = (0.45, 0.6, 1.0), 14 * f
    else:
        u = (t - 2.47)
        flash = math.exp(-u / 0.08)
        hues = [(1.0, 0.45, 0.75), (1.0, 0.75, 0.35), (0.5, 1.0, 0.6)]
        col = hues[int(u * 4) % 3]
        pw = 20 * f + 60 * flash
    H['tv'].data.color = col
    H['tv'].data.energy = pw
    fl = 1.5 + 0.25 * math.sin(t * 31) + 0.15 * math.sin(t * 13)
    H['candle_light'].data.energy = fl
    H['flame'].scale = (1, 1, 2.2 + 0.25 * math.sin(t * 27))


# ------------------------------------------------------------------ camera
cd = bpy.data.cameras.new('cam')
cam = bpy.data.objects.new('cam', cd)
sc.collection.objects.link(cam)
sc.camera = cam
cd.lens = 42
cd.sensor_fit = 'VERTICAL'
cd.sensor_height = 36
cd.dof.use_dof = True
cd.dof.aperture_fstop = 2.4


def pose_camera(t):
    push = ease(t / DUR)
    tgt = np.array([0.0, 0.01, 0.052])
    dist = 0.56 - 0.05 * push
    el = math.radians(7.5)
    az = math.radians(-4 + 5 * push)
    pos = tgt + dist * np.array([math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)])
    pos += 0.0012 * np.array([math.sin(t * 1.7), math.sin(t * 1.3 + 1), math.sin(t * 2.1 + 2)])
    if a.cam:
        cx, cd_ = (float(v) for v in a.cam.split(','))
        tgt = np.array([cx, 0.0, 0.05]); pos = tgt + cd_ * np.array([0, -math.cos(el), math.sin(el)])
    cam.location = pos.tolist()
    cam.rotation_euler = Vector((tgt - pos).tolist()).to_track_quat('-Z', 'Y').to_euler()
    cd.dof.focus_distance = float(np.linalg.norm(tgt - pos))
    cd.shift_y = 0.12


# ------------------------------------------------------------------ render setup
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = a.samples
sc.cycles.use_adaptive_sampling = True
sc.cycles.adaptive_threshold = 0.035
sc.render.use_persistent_data = True
sc.cycles.use_denoising = True
sc.cycles.denoiser = 'OPENIMAGEDENOISE'
sc.cycles.max_bounces = 6
sc.cycles.diffuse_bounces = 2
sc.cycles.glossy_bounces = 3
sc.cycles.transmission_bounces = 6
sc.cycles.sample_clamp_indirect = 4.0
sc.render.resolution_x, sc.render.resolution_y = 1080, 1920
sc.render.resolution_percentage = a.pct
sc.render.image_settings.file_format = 'PNG'
sc.view_settings.view_transform = 'AgX'
try:
    sc.view_settings.look = 'AgX - Medium High Contrast'
except Exception:
    pass
sc.render.film_transparent = False


def do(t):
    ps, mouth, smile, reach, swing, click = shark_act(t)
    shark.pose(ps, mouth=mouth, smile=smile)
    pf, gasp = frog_act(t)
    frog.pose(pf, mouth=gasp * 0.6)
    pose_remote(t, reach, swing, click)
    Rb, tb = pose_bucket(t)
    pose_popcorn(t, Rb, tb)
    tv_light(t)
    pose_camera(t)


if a.still is not None:
    for t in a.still:
        do(t)
        sc.render.filepath = os.path.join(a.out, f'still_{t:05.2f}.png')
        bpy.ops.render.render(write_still=True)
        print('wrote', sc.render.filepath, flush=True)
else:
    f0, f1 = a.frames
    for f in range(f0, f1):
        fp = os.path.join(a.out, f'f{f:04d}.png')
        if os.path.exists(fp):
            continue
        do(f / FPS)
        sc.render.filepath = fp
        bpy.ops.render.render(write_still=True)
        print('frame', f, flush=True)
