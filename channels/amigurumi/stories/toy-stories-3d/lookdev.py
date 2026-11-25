"""Look-dev stills of one toy in a soft studio, to compare with its AI preview before animating.
Usage: python lookdev.py PKL OUT_PREFIX [--views front,q34,face] [--px 700] [--samples 48]"""
import sys, os, math, argparse
sys.path.insert(0, '/home/user/work/b3d')
sys.path.insert(0, '/home/user/work/story')
import numpy as np
import bpy
from mathutils import Vector

ap = argparse.ArgumentParser()
ap.add_argument('pkl')
ap.add_argument('out')
ap.add_argument('--views', default='front,q34,face')
ap.add_argument('--px', type=int, default=700)
ap.add_argument('--samples', type=int, default=48)
ap.add_argument('--hide', default='')
a = ap.parse_args(sys.argv[1:])

bpy.ops.wm.read_factory_settings(use_empty=True)
import set3d  # noqa: E402
from set3d import plain, area  # noqa: E402
from toys3d import K, MM  # noqa: E402
from ami3d import AmiToy, ami_materials  # noqa: E402

sc = bpy.context.scene
c = set3d.coll('studio')
M2 = ami_materials()
toy = AmiToy(a.pkl, 'toy', M2, c, absolute=True)
from toys3d import bmat  # noqa: E402
for x in toy.objs:
    x['ob'].matrix_world = bmat(np.eye(3), np.zeros(3))
    if x['name'] in a.hide.split(','):
        x['ob'].hide_render = True
h = toy.height
# backdrop: a big soft cove
bpy.ops.mesh.primitive_plane_add(size=4, location=(0, 0, 0))
fl = bpy.context.active_object
fl.data.materials.append(plain('backdrop', (0.78, 0.74, 0.70), rough=0.9)[0])
bpy.ops.mesh.primitive_plane_add(size=4, location=(0, 0.6, 1.0), rotation=(math.radians(90), 0, 0))
bpy.context.active_object.data.materials.append(bpy.data.materials['backdrop'])
w = sc.world or bpy.data.worlds.new('w'); sc.world = w
w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (0.5, 0.48, 0.46, 1)
w.node_tree.nodes['Background'].inputs[1].default_value = 0.3
H = h * MM
area('key', (0.25, -0.35, H * 1.8), (0, 0, H * 0.55), 0.35, (1.0, 0.95, 0.88), 6)
area('fill', (-0.35, -0.25, H * 1.0), (0, 0, H * 0.5), 0.5, (0.85, 0.9, 1.0), 2)
area('rim', (0.05, 0.35, H * 1.6), (0, 0, H * 0.6), 0.3, (1.0, 0.95, 0.9), 4)

cd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cd)
sc.collection.objects.link(cam); sc.camera = cam
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = a.samples
sc.cycles.use_denoising = True
sc.render.resolution_x = sc.render.resolution_y = a.px
sc.view_settings.view_transform = 'AgX'
try:
    sc.view_settings.look = 'AgX - Medium High Contrast'
except Exception:
    pass
VIEWS = {'front': (0, H * 0.5, 2.6 * H, 40), 'q34': (35, H * 0.5, 2.6 * H, 40), 'face': (12, H * 0.72, 1.25 * H, 40),
         'side': (80, H * 0.5, 2.6 * H, 40)}
for v in a.views.split(','):
    az, tz, d, lens = VIEWS[v]
    tg = Vector((0, 0, tz))
    p = tg + Vector((d * math.sin(math.radians(az)), -d * math.cos(math.radians(az)), d * 0.18))
    cam.location = p
    cam.rotation_euler = (tg - p).to_track_quat('-Z', 'Y').to_euler()
    cd.lens = lens
    sc.render.filepath = os.path.abspath(f'{a.out}_{v}.png')
    bpy.ops.render.render(write_still=True)
    print('wrote', sc.render.filepath, flush=True)
