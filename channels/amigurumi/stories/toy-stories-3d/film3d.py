"""SNACK ATTACK in full 3D: the story engine's acting (snack.py) drives site-style amikit toys in the Blender living
room.  Toys are rendered on twos (12 unique frames per second, the stop-motion cadence); captions and post are added
at 24 fps afterwards by post3d.py.
Usage: python film3d.py OUT [--frames A B] [--still T ...] [--pct 67] [--samples 24]"""
import sys, math, os, argparse
sys.path.insert(0, '/home/user/work/b3d')
sys.path.insert(0, '/home/user/work/story')
import numpy as np
import bpy
from mathutils import Vector

ap = argparse.ArgumentParser()
ap.add_argument('out')
ap.add_argument('--frames', type=int, nargs=2)
ap.add_argument('--still', type=float, nargs='*')
ap.add_argument('--pct', type=int, default=67)
ap.add_argument('--samples', type=int, default=24)
a = ap.parse_args(sys.argv[1:])
os.makedirs(a.out, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
import set3d  # noqa: E402
from toys3d import bmat, K, MM  # noqa: E402
from ami3d import AmiToy, ami_materials  # noqa: E402
import acting  # noqa: E402
import snack as S  # noqa: E402
from engine import ease, clamp, wob  # noqa: E402

RATE = 12                                   # unique frames per second
_blink = acting.blink
S.blink = lambda t, seed=1, every=2.6: 1.0  # lids do the blinking now

sc = bpy.context.scene
M = set3d.materials()
H = set3d.build_room()
M2 = ami_materials()
tc = set3d.coll('toys')
B3 = '/home/user/work/b3d/'
A = S.build()
TID = {'shark': 'shark-in-a-hoodie', 'frog': 'frog-crying-tears', 'goose': 'goose-knife-meme', 'remote': 'tv-remote',
       'sock': 'striped-sock', 'cookie': 'easy-cookie', 'knife': 'knife'}
toys = []
for act in A:
    tid = TID.get(act.key, 'popcorn')
    toys.append(AmiToy(B3 + f'{tid}.ami.pkl', act.key, M2, tc, home=act.home, absolute=True))
T = {t.key: t for t in toys}
T['shark'].add_mouth(M2, tc, ('mouth', 'tooth_0', 'tooth_1', 'tooth_2', 'tooth_3'))
T['shark'].add_swaps(B3 + 'shark-in-a-hoodie.mouths.pkl', M2, tc)
T['frog'].add_mouth(M2, tc, ('mouth',))
T['frog'].add_swaps(B3 + 'frog-crying-tears.mouths.pkl', M2, tc)
# the empty popcorn bucket, story evidence, behind between the shark and the frog
H['bucket'].matrix_world = bmat(np.eye(3), np.array([-44.0, 0.0, -92.0]))
SEED = {'shark': 1, 'frog': 2, 'goose': 3, 'cookie': 4}


def env(t, t0, t1, a=0.08, b=0.1):
    """0 -> 1 -> 0 over [t0, t1] with ramps."""
    return clamp((t - t0) / a) * (1 - clamp((t - (t1 - b)) / b))


def shark_mouth(t):
    m = 0.0
    for (Tp, *_r) in S.PULLS:
        m = max(m, env(t, Tp - 0.32, Tp + 0.42))
    m = max(m, 0.45 * env(t, S.T_HIC - 0.05, S.T_HIC + 0.3))
    m = max(m, env(t, S.T_GULP - 0.5, S.T_GULP + 0.1))
    m = max(m, env(t, S.T_DROP - 0.05, S.T_DROP + 0.4))
    for tb in (S.T_BACK1, S.T_BACK2):
        m = max(m, env(t, tb - 0.05, tb + 0.45))
    if t > S.T_DROP + 0.4:                       # sings along on the beat
        u = ((t - S.T_DROP) / S.BEAT) % 2.0
        m = max(m, 0.45 * (u < 0.55))
    return m


def frog_mouth(t):
    m = 0.0
    for (Tp, *_r) in S.PULLS:
        m = max(m, env(t, Tp + 0.1, Tp + 1.0))
    m = max(m, env(t, S.T_GULP - 0.1, S.T_DROP))
    if t > S.T_DROP:
        u = ((t - S.T_DROP) / S.BEAT + 0.5) % 2.0
        m = max(m, 0.45 * (u < 0.5))
    return m


def soften_eye(p):
    e = p['eye']
    p['eye'] = 1 + (e - 1) * 0.5 if e > 1 else max(e, 0.6)
    return p


# ------------------------------------------------------------------ light events
bulb = bpy.data.materials['bulb'].node_tree.nodes['Emission']
PARTY = [(1.0, 0.35, 0.7), (0.35, 0.75, 1.0), (1.0, 0.8, 0.3), (0.5, 1.0, 0.55)]


def lights(t):
    f = 0.75 + 0.25 * math.sin(t * 23) * math.sin(t * 7.3)
    if t < S.T_DROP:
        H['tv'].data.color = (0.45, 0.6, 1.0)
        H['tv'].data.energy = 14 * f
        bulb.inputs[1].default_value = 40.0
    else:
        bb = (t - S.T_DROP) / S.BEAT
        u = bb % 1.0
        H['tv'].data.color = PARTY[int(bb) % 4]
        H['tv'].data.energy = 18 + 40 * math.exp(-u / 0.15)
        bulb.inputs[1].default_value = 40 + 110 * math.exp(-u / 0.2)
    H['candle_light'].data.energy = 1.5 + 0.25 * math.sin(t * 31) + 0.15 * math.sin(t * 13)
    H['flame'].scale = (1, 1, 2.2 + 0.25 * math.sin(t * 27))


# ------------------------------------------------------------------ camera (the story's shots, in 3D)
cd = bpy.data.cameras.new('cam')
cam = bpy.data.objects.new('cam', cd)
sc.collection.objects.link(cam)
sc.camera = cam
cd.sensor_fit = 'HORIZONTAL'
cd.sensor_width = 36
cd.dof.use_dof = True


def B(p):
    return K @ np.asarray(p, float) * MM


def pose_camera(t):
    tg, fov, shk = S.camera(t)
    tg = np.asarray(tg, float) + np.array([0, S.AIM_UP * 0.9, 0])
    pos = np.asarray(S.CAM0['pos'], float) + np.array([3 * math.sin(0.31 * t), 2 * math.sin(0.23 * t + 1), 0])
    tg = tg + np.array([1.2 * math.sin(0.41 * t + 2), 0.8 * math.sin(0.37 * t), 0])
    dist = np.linalg.norm(tg - pos)
    if shk:
        k = dist * math.tan(math.radians(fov) * shk / 1080)
        tg = tg + k * np.array([math.sin(t * 61.0), math.sin(t * 47.0 + 1), 0])
    fov = fov * 0.9                               # a little tighter: the toys fill the frame
    P0, T0 = B(pos), B(tg)
    cam.location = P0.tolist()
    cam.rotation_euler = Vector((T0 - P0).tolist()).to_track_quat('-Z', 'Y').to_euler()
    cd.lens = 18.0 / math.tan(math.radians(fov) / 2)
    F0 = B(tg + np.array([0, 0, 35.0]))          # focus on the toys' faces, not their middles
    cd.dof.focus_distance = float(np.linalg.norm(F0 - P0))
    cd.dof.aperture_fstop = max(4.0, cd.lens / 12.0)   # long close-up lenses need a smaller aperture


# ------------------------------------------------------------------ render setup
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = a.samples
sc.cycles.use_adaptive_sampling = True
sc.cycles.adaptive_threshold = 0.035
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
    ps = S.pose(t, A)
    for toy, p in zip(toys, ps):
        p = soften_eye(p)
        p['blink'] = _blink(t, SEED.get(toy.key, 9))
        if toy.key == 'shark':
            toy.pose(p, mouth=shark_mouth(t))
        elif toy.key == 'frog':
            toy.pose(p, mouth=frog_mouth(t))
        else:
            toy.pose(p)
    lights(t)
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
        do(f / RATE)
        sc.render.filepath = fp
        bpy.ops.render.render(write_still=True)
        print('frame', f, flush=True)
