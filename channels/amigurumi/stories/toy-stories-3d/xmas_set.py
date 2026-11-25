"""Christmas Eve on the coffee table, all 3D: a crocheted mini tree with bulbs and a star, a wrapped gift box with a
lid that pops, a plate of cookies and a glass of milk, candy canes; behind, a cosy room with a big tree, a fireplace
with a real glow and knitted stockings, a garland of lights and a snowy night window.
Metres, z up, the table top at z = 0, the camera looks along +y.  Toy-space helpers: T(x, y, z) in mm."""
import math, random
import numpy as np
import bpy
from mathutils import Matrix, Vector
from set3d import (new_mat, N, L, setp, bump, wood_mat, fabric_mat, plain, emit, coll, link, box, cyl, sphere,
                   area, point)

random.seed(11)
MM = 0.001


def T(x, y, z):
    """toy mm (x right, y up, z to camera) -> Blender metres"""
    return (x * MM, -z * MM, y * MM)


def knit_cone(c, name, r0, r1, h, loc, col, rings=7):
    """A crocheted cone (the mini tree) as stacked, slightly flared skirts with a stitch bump."""
    m = fabric_mat(name + '_m', col, sheen=0.25, knit=True)
    obs = []
    for i in range(rings):
        u = i / rings
        r = r0 + (r1 - r0) * u
        z = loc[2] + h * u
        bpy.ops.mesh.primitive_cone_add(vertices=64, radius1=r, radius2=r * 0.35, depth=h / rings * 1.7,
                                        location=(loc[0], loc[1], z + h / rings * 0.85), end_fill_type='NOTHING')
        ob = bpy.context.active_object
        ob.name = name
        V = np.zeros(len(ob.data.vertices) * 3); ob.data.vertices.foreach_get('co', V); V = V.reshape(-1, 3)
        ang = np.arctan2(V[:, 1], V[:, 0])
        bot = V[:, 2] < 0
        V[bot, 0] *= 1 + 0.06 * np.sin(ang[bot] * 9)          # scalloped rim
        V[bot, 1] *= 1 + 0.06 * np.sin(ang[bot] * 9)
        ob.data.vertices.foreach_set('co', V.ravel()); ob.data.update()
        md = ob.modifiers.new('sol', 'SOLIDIFY'); md.thickness = 0.004
        md = ob.modifiers.new('sub', 'SUBSURF'); md.levels = 1; md.render_levels = 1
        bpy.ops.object.shade_smooth()
        ob.data.materials.append(m)
        link(ob, c)
        obs.append(ob)
    return obs


def build():
    c = coll('xmas')
    H = {}
    wood = wood_mat('wood_table', base=(0.42, 0.22, 0.1), dark=(0.17, 0.075, 0.03), scale=1.4)
    box(c, 'table_top', (1.3, 0.9, 0.036), (0, 0.22, -0.018), wood, bevel=0.008, segs=5)
    for sx in (-0.58, 0.58):
        for sy in (-0.15, 0.6):
            cyl(c, 'leg', 0.022, 0.39, (sx, sy, -0.23), wood, verts=24, r2=0.016)
    # a knitted table runner under the action
    runner = fabric_mat('runner', (0.85, 0.8, 0.7), sheen=0.6, knit=True)
    box(c, 'runner', (1.3, 0.16, 0.003), (0, 0.33, 0.0015), runner, bevel=0.001)
    # ---------------------------------------------------------------- the crocheted mini tree (right, behind)
    tx, tz = 105, -100
    trunk_m = fabric_mat('trunk', (0.35, 0.2, 0.1), knit=True)
    cyl(c, 'trunk', 0.018, 0.04, T(tx, 20, tz), trunk_m, verts=24)
    pot_m = fabric_mat('tree_pot', (0.7, 0.08, 0.1), knit=True)
    cyl(c, 'tree_pot', 0.035, 0.035, T(tx, 17, tz), pot_m, verts=40, r2=0.042)
    H['tree'] = knit_cone(c, 'tree', 0.1, 0.014, 0.27, T(tx, 36, tz), (0.08, 0.36, 0.14))
    tree_root = bpy.data.objects.new('tree_root', None); c.objects.link(tree_root)
    tree_root.location = T(tx, 36, tz)
    for ob in H['tree']:
        ob.parent = tree_root; ob.matrix_parent_inverse = tree_root.matrix_world.inverted()
    H['tree_root'] = tree_root
    star_m = emit('star', (1.0, 0.82, 0.35), 8.0)
    bpy.ops.mesh.primitive_cone_add(vertices=5, radius1=0.013, radius2=0.0, depth=0.008, location=T(tx, 312, tz),
                                    rotation=(math.pi / 2, 0, 0))
    st = bpy.context.active_object; st.data.materials.append(star_m); link(st, c)
    st.parent = tree_root; st.matrix_parent_inverse = tree_root.matrix_world.inverted()
    H['star'] = st
    # tree bulbs (party colours later) and little baubles
    H['tbulbs'] = []
    cols = [(1.0, 0.35, 0.3), (1.0, 0.8, 0.35), (0.4, 0.7, 1.0), (0.5, 1.0, 0.55)]
    for i in range(34):
        u = random.uniform(0.05, 0.92)
        r = (0.1 + (0.014 - 0.1) * u) * 1.02 + 0.004
        a = i * 2.39996
        p = (tx * MM + r * math.cos(a), -tz * MM + r * math.sin(a), (36 + 250 * u) * MM)
        m = emit(f'tb{i}', cols[i % 4], 6.0)
        b = sphere(c, 'tbulb', 0.0045, p, m, seg=12)
        b.parent = tree_root; b.matrix_parent_inverse = tree_root.matrix_world.inverted()
        H['tbulbs'].append((m.node_tree.nodes['Emission'], i % 4))
    # ---------------------------------------------------------------- gift box with a lid (left)
    gx, gz, gs = -168, -36, 0.088
    gift = new_mat('gift')[0]
    nt = gift.node_tree; bs = nt.nodes['Principled BSDF']
    tc = N(nt, 'ShaderNodeTexCoord'); ck = N(nt, 'ShaderNodeTexChecker', i_Scale=14.0)
    ck.inputs['Color1'].default_value = (0.08, 0.32, 0.18, 1); ck.inputs['Color2'].default_value = (0.06, 0.26, 0.14, 1)
    L(nt, tc.outputs['Object'], ck.inputs[0]); L(nt, ck.outputs[0], bs.inputs['Base Color'])
    setp(bs, Roughness=0.45, Sheen_Weight=0.3)
    ribbon, _, _ = plain('ribbon', (0.85, 0.1, 0.12), 0.3, Sheen_Weight=0.6, Coat_Weight=0.3)
    # walls only (open top), so the elf can rise out of it
    for (dx, dz, sx, sz) in ((0, gs / 2, gs, 0.003), (0, -gs / 2, gs, 0.003), (gs / 2, 0, 0.003, gs), (-gs / 2, 0, 0.003, gs)):
        box(c, 'gift_wall', (sx, sz, gs), (gx * MM + dx, -gz * MM + dz, gs / 2), gift, bevel=0.001)
    box(c, 'gift_floor', (gs, gs, 0.003), (gx * MM, -gz * MM, 0.0015), gift, bevel=0)
    box(c, 'gift_rib', (0.012, gs + 0.002, gs + 0.001), (gx * MM, -gz * MM, gs / 2), ribbon, bevel=0.001)
    box(c, 'gift_rib', (gs + 0.002, 0.012, gs + 0.001), (gx * MM, -gz * MM, gs / 2), ribbon, bevel=0.001)
    lid_p = bpy.data.objects.new('lid_pivot', None); c.objects.link(lid_p)
    lid_p.location = (gx * MM, -gz * MM, gs)
    lid = box(c, 'gift_lid', (gs + 0.008, gs + 0.008, 0.016), (gx * MM, -gz * MM, gs + 0.006), gift, bevel=0.002)
    lr1 = box(c, 'lid_rib', (0.013, gs + 0.01, 0.017), (gx * MM, -gz * MM, gs + 0.006), ribbon, bevel=0.001)
    lr2 = box(c, 'lid_rib', (gs + 0.01, 0.013, 0.017), (gx * MM, -gz * MM, gs + 0.006), ribbon, bevel=0.001)
    # a bow on the lid
    for s in (-1, 1):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.012, minor_radius=0.004, location=(gx * MM + s * 0.011, -gz * MM, gs + 0.02),
                                         rotation=(math.pi / 2, 0.4 * s, 0))
        bw = bpy.context.active_object; bw.scale = (1, 0.6, 1); bpy.ops.object.shade_smooth()
        bw.data.materials.append(ribbon); link(bw, c)
        bw.parent = lid_p; bw.matrix_parent_inverse = lid_p.matrix_world.inverted()
    for ob in (lid, lr1, lr2):
        ob.parent = lid_p; ob.matrix_parent_inverse = lid_p.matrix_world.inverted()
    H['lid'] = lid_p
    H['gift'] = (gx, gz, gs / MM)
    # ---------------------------------------------------------------- the little crocheted house; the chimney stands at
    # its front-right corner, rising over the eaves
    hx0, hx1, hz0, hz1, hw, hr = -112, 42, -140, -45, 40, 70
    wall_k = fabric_mat('house_wall', (0.92, 0.66, 0.32), sheen=0.05, knit=True)
    roof_k = fabric_mat('house_roof', (0.55, 0.04, 0.05), sheen=0.05, knit=True)
    snow_k = fabric_mat('house_snow', (0.97, 0.97, 1.0), sheen=0.6, knit=True)
    cx, cz = (hx0 + hx1) / 2, (hz0 + hz1) / 2
    box(c, 'house', ((hx1 - hx0) * MM, (hz1 - hz0) * MM, hw * MM), T(cx, hw / 2, cz), wall_k, bevel=0.004, segs=3)
    half = (hz1 - hz0) / 2 + 8
    rise = hr - hw
    ang = math.atan2(rise, half)
    Lr = math.hypot(rise, half) + 4
    for sgn in (-1, 1):
        zc = cz + sgn * half / 2
        box(c, 'roof', ((hx1 - hx0 + 16) * MM, Lr * MM, 7 * MM), T(cx, hw + rise / 2, zc), roof_k, bevel=0.003, segs=3,
            rot=(sgn * ang, 0, 0))
        box(c, 'roof_snow', ((hx1 - hx0 + 12) * MM, Lr * 0.55 * MM, 6 * MM), T(cx, hw + rise * 0.75 + 4, cz + sgn * half * 0.27),
            snow_k, bevel=0.003, segs=3, rot=(sgn * ang, 0, 0))
    for xg in (hx0, hx1):
        V = [(xg * MM, -(hz0) * MM, hw * MM), (xg * MM, -(hz1) * MM, hw * MM), (xg * MM, -cz * MM, hr * MM)]
        me = bpy.data.meshes.new('gable'); me.from_pydata(V, [], [(0, 1, 2)]); me.update()
        go = bpy.data.objects.new('gable', me); c.objects.link(go); me.materials.append(wall_k)
        md = go.modifiers.new('sol', 'SOLIDIFY'); md.thickness = 0.004
    # the brick chimney (crocheted red with cream mortar rows), rising through the roof at the front right
    chm = new_mat('chimney_brick')[0]
    nt = chm.node_tree; bs = nt.nodes['Principled BSDF']
    tc = N(nt, 'ShaderNodeNewGeometry'); bt = N(nt, 'ShaderNodeTexBrick', i_Scale=1.0)
    bt.inputs['Color1'].default_value = (0.42, 0.05, 0.035, 1); bt.inputs['Color2'].default_value = (0.32, 0.04, 0.03, 1)
    bt.inputs['Mortar'].default_value = (0.72, 0.66, 0.58, 1); bt.inputs['Mortar Size'].default_value = 0.0011
    bt.inputs['Brick Width'].default_value = 0.016; bt.inputs['Row Height'].default_value = 0.008
    sp_ = N(nt, 'ShaderNodeSeparateXYZ'); L(nt, tc.outputs['Position'], sp_.inputs[0])
    ad_ = N(nt, 'ShaderNodeMath', operation='ADD'); L(nt, sp_.outputs[0], ad_.inputs[0]); L(nt, sp_.outputs[1], ad_.inputs[1])
    cb_ = N(nt, 'ShaderNodeCombineXYZ'); L(nt, ad_.outputs[0], cb_.inputs[0]); L(nt, sp_.outputs[2], cb_.inputs[1])
    L(nt, cb_.outputs[0], bt.inputs['Vector']); L(nt, bt.outputs[0], bs.inputs['Base Color'])
    kn = N(nt, 'ShaderNodeTexWave', i_Scale=900.0, wave_profile='SIN'); L(nt, tc.outputs['Position'], kn.inputs['Vector'])
    mxh = N(nt, 'ShaderNodeMath', operation='MULTIPLY_ADD', i_Value_001=0.4); L(nt, kn.outputs[1], mxh.inputs[0]); L(nt, bt.outputs[1], mxh.inputs[2])
    bump(nt, bs, mxh.outputs[0], 0.6, 0.0015)
    setp(bs, Roughness=0.9, Sheen_Weight=0.08)
    chx, chz, chs, chh = 20, -58, 34, 84
    box(c, 'chimney', (chs * MM, chs * MM, chh * MM), T(chx, chh / 2, chz), chm, bevel=0.003, segs=3)
    box(c, 'chimney_cap', ((chs + 6) * MM, (chs + 6) * MM, 6 * MM), T(chx, chh - 2, chz), snow_k, bevel=0.003, segs=3)
    hole, _, _ = plain('chimney_hole', (0.02, 0.015, 0.01), 0.9)
    box(c, 'chimney_hole', ((chs - 8) * MM, (chs - 8) * MM, 1 * MM), T(chx, chh + 1.2, chz), hole, bevel=0)
    H['chimney_top'] = (chx, chh, chz)
    door_m, _, _ = plain('door', (0.36, 0.18, 0.08), 0.5)
    box(c, 'door', (20 * MM, 2 * MM, 32 * MM), T(cx - 22, 16, hz1 + 1), door_m, bevel=0.002)
    knob, _, _ = plain('knob', (0.9, 0.7, 0.3), 0.3, Metallic=1.0)
    sphere(c, 'knob', 1.6 * MM, T(cx - 16, 16, hz1 + 2.5), knob, seg=10)
    win_lit = emit('house_window', (1.0, 0.72, 0.35), 6.0)
    H['house_win'] = win_lit.node_tree.nodes['Emission']
    for wx in (cx + 14, cx + 38):
        box(c, 'hwin', (16 * MM, 2 * MM, 16 * MM), T(wx, 30, hz1 + 1), win_lit, bevel=0.001)
        box(c, 'hwin_bar', (17 * MM, 2.6 * MM, 2 * MM), T(wx, 30, hz1 + 1.2), door_m, bevel=0)
        box(c, 'hwin_bar', (2 * MM, 2.6 * MM, 17 * MM), T(wx, 30, hz1 + 1.2), door_m, bevel=0)
    H['house_light'] = point('house_light', T(cx + 26, 28, hz1 + 14), (1.0, 0.65, 0.3), 0.6, 0.01)
    # ---------------------------------------------------------------- cookies and milk (front right)
    px, pz = 100, 62
    plate_m, _, _ = plain('plate', (0.92, 0.9, 0.86), 0.15, Coat_Weight=0.6)
    cyl(c, 'plate', 0.05, 0.006, T(px, 3, pz), plate_m, verts=64, r2=0.042)
    ck_m = new_mat('cookie')[0]
    nt = ck_m.node_tree; bs = nt.nodes['Principled BSDF']
    vo = N(nt, 'ShaderNodeTexVoronoi', i_Scale=160.0)
    cr = N(nt, 'ShaderNodeValToRGB')
    cr.color_ramp.elements[0].position = 0.0; cr.color_ramp.elements[0].color = (0.1, 0.04, 0.02, 1)
    cr.color_ramp.elements[1].position = 0.18; cr.color_ramp.elements[1].color = (0.62, 0.36, 0.14, 1)
    L(nt, vo.outputs['Distance'], cr.inputs[0]); L(nt, cr.outputs[0], bs.inputs['Base Color'])
    nz = N(nt, 'ShaderNodeTexNoise', i_Scale=300.0, i_Detail=6.0)
    bump(nt, bs, nz.outputs[0], 0.5, 0.0008)
    setp(bs, Roughness=0.75)
    H['cookies'] = []
    for i, (dx, dz, h) in enumerate(((-14, -10, 9), (12, -8, 9), (0, 10, 9), (2, -2, 17))):
        ob = cyl(c, 'cookie', 0.016, 0.006, T(px + dx, h, pz + dz), ck_m, verts=32)
        md = ob.modifiers.new('bev', 'BEVEL'); md.width = 0.002; md.segments = 3
        ob.rotation_euler = (0.08 * (i - 1), 0.1 * i, i)
        H['cookies'].append(ob)
    H['cookie_m'] = ck_m
    glass_m, _, _ = plain('glass', (1, 1, 1), 0.02, Transmission_Weight=1.0, IOR=1.45)
    milk_m, _, _ = plain('milk', (0.95, 0.94, 0.9), 0.3, Subsurface_Weight=0.6, Subsurface_Scale=0.01)
    cyl(c, 'milk_glass', 0.022, 0.075, T(150, 37.5, 28), glass_m, verts=40, cap=True)
    cyl(c, 'milk', 0.0195, 0.055, T(150, 28, 28), milk_m, verts=40)
    # candy canes lying on the table
    cane_m = new_mat('cane')[0]
    nt = cane_m.node_tree; bs = nt.nodes['Principled BSDF']
    tc = N(nt, 'ShaderNodeTexCoord'); wv = N(nt, 'ShaderNodeTexWave', i_Scale=6.0, bands_direction='DIAGONAL')
    L(nt, tc.outputs['UV'], wv.inputs[0])
    gt = N(nt, 'ShaderNodeMath', operation='GREATER_THAN', i_Value_001=0.5); L(nt, wv.outputs[1], gt.inputs[0])
    mx = N(nt, 'ShaderNodeMix', data_type='RGBA'); mx.inputs[6].default_value = (0.95, 0.93, 0.9, 1); mx.inputs[7].default_value = (0.8, 0.04, 0.06, 1)
    L(nt, gt.outputs[0], mx.inputs['Factor']); L(nt, mx.outputs[2], bs.inputs['Base Color'])
    setp(bs, Roughness=0.2, Coat_Weight=0.8)
    for (x0, z0, rz) in ((-40, 70, 0.4), (40, -60, -0.9)):
        cd = bpy.data.curves.new('cane', 'CURVE'); cd.dimensions = '3D'; cd.bevel_depth = 0.004; cd.use_fill_caps = True
        sp = cd.splines.new('BEZIER'); pts = [(0, 0), (0.06, 0), (0.075, 0.012), (0.066, 0.022)]
        sp.bezier_points.add(len(pts) - 1)
        for bp, (a, b) in zip(sp.bezier_points, pts):
            bp.co = (a, b, 0.004); bp.handle_left_type = bp.handle_right_type = 'AUTO'
        ob = bpy.data.objects.new('cane', cd); c.objects.link(ob); cd.materials.append(cane_m)
        ob.location = T(x0, 0, z0); ob.rotation_euler = (0, 0, rz)
    # ---------------------------------------------------------------- the room
    floor_m = wood_mat('floor', base=(0.5, 0.33, 0.2), dark=(0.28, 0.16, 0.08), scale=0.6, coat=0.1, rough=0.5)
    box(c, 'floor', (8, 8, 0.02), (0, 1.5, -0.43), floor_m, bevel=0)
    rug = fabric_mat('rug', (0.82, 0.76, 0.66), knit=True)
    box(c, 'rug', (2.6, 1.9, 0.012), (0, 0.5, -0.414), rug, bevel=0.004)
    wall_m, nt, bs = plain('wall', (0.42, 0.18, 0.14), 0.9)
    nz = N(nt, 'ShaderNodeTexNoise', i_Scale=40.0, i_Detail=6.0); bump(nt, bs, nz.outputs[0], 0.15, 0.002)
    box(c, 'wall_back', (6, 0.05, 3.2), (0, 2.6, 1.1), wall_m, bevel=0)
    box(c, 'wall_left', (0.05, 6, 3.2), (-2.3, 1.0, 1.1), wall_m, bevel=0)
    # fireplace (back, centre-left) with a fire glow and knitted stockings
    brick = new_mat('brick')[0]
    nt = brick.node_tree; bs = nt.nodes['Principled BSDF']
    tc = N(nt, 'ShaderNodeTexCoord'); bt = N(nt, 'ShaderNodeTexBrick', i_Scale=9.0)
    bt.inputs['Color1'].default_value = (0.45, 0.17, 0.1, 1); bt.inputs['Color2'].default_value = (0.36, 0.12, 0.08, 1)
    bt.inputs['Mortar'].default_value = (0.7, 0.66, 0.6, 1)
    L(nt, tc.outputs['Object'], bt.inputs[0]); L(nt, bt.outputs[0], bs.inputs['Base Color']); bump(nt, bs, bt.outputs[1], 0.4, 0.004)
    setp(bs, Roughness=0.85)
    fx = -0.55
    box(c, 'fp_left', (0.22, 0.4, 1.0), (fx - 0.52, 2.38, 0.07), brick, bevel=0.01)
    box(c, 'fp_right', (0.22, 0.4, 1.0), (fx + 0.52, 2.38, 0.07), brick, bevel=0.01)
    box(c, 'fp_top', (1.26, 0.4, 0.3), (fx, 2.38, 0.72), brick, bevel=0.01)
    mantel_m = wood_mat('mantel', base=(0.55, 0.35, 0.2), dark=(0.3, 0.17, 0.08), scale=1.5)
    box(c, 'mantel', (1.45, 0.5, 0.06), (fx, 2.33, 0.9), mantel_m, bevel=0.01)
    soot, _, _ = plain('soot', (0.03, 0.025, 0.02), 0.9)
    box(c, 'fp_back', (0.84, 0.05, 0.75), (fx, 2.56, -0.05), soot, bevel=0)
    fire_m = emit('fire', (1.0, 0.45, 0.12), 25.0)
    H['fire_m'] = fire_m.node_tree.nodes['Emission']
    for i in range(5):
        sphere(c, 'fire', 0.06, (fx - 0.2 + 0.1 * i, 2.45, -0.3), fire_m, seg=16).scale = (1, 0.6, 1.8 - 0.25 * abs(i - 2))
    log_m = wood_mat('log', base=(0.3, 0.17, 0.08), dark=(0.1, 0.05, 0.02), scale=4)
    for i in range(3):
        cyl(c, 'log', 0.05, 0.6, (fx, 2.42 + 0.03 * i, -0.38 + 0.02 * i), log_m, verts=24, rot=(0, math.pi / 2, 0.2 * (i - 1)))
    H['fire'] = point('fire_light', (fx, 2.25, -0.2), (1.0, 0.5, 0.2), 120.0, 0.15)
    for i, col in enumerate(((0.75, 0.08, 0.1), (0.1, 0.4, 0.2), (0.9, 0.88, 0.82), (0.75, 0.08, 0.1))):
        sm = fabric_mat(f'stock{i}', col, knit=True)
        x = fx - 0.48 + 0.32 * i
        box(c, 'stocking', (0.09, 0.05, 0.24), (x, 2.1, 0.74), sm, bevel=0.03, segs=4, subsurf=2)
        box(c, 'stocking_foot', (0.14, 0.05, 0.08), (x + 0.04, 2.1, 0.62), sm, bevel=0.03, segs=4, subsurf=2)
        box(c, 'stocking_cuff', (0.11, 0.06, 0.06), (x, 2.1, 0.86), fabric_mat(f'cuff{i}', (0.95, 0.93, 0.9), knit=True), bevel=0.02, subsurf=2)
    # garland of lights along the mantel
    H['garland'] = []
    gm = fabric_mat('garland', (0.06, 0.25, 0.1), sheen=0.4, scale=200)
    for i in range(26):
        u = i / 25
        x = fx - 0.7 + 1.4 * u
        z = 0.92 - 0.08 * math.sin(math.pi * ((u * 3) % 1))
        sphere(c, 'garl', 0.035, (x, 2.1, z), gm, seg=12)
        m = emit(f'gl{i}', cols[i % 4], 18.0)
        sphere(c, 'gbulb', 0.012, (x, 2.06, z - 0.03), m, seg=10)
        H['garland'].append((m.node_tree.nodes['Emission'], i % 4))
    # the big tree, right back (bokeh)
    big = fabric_mat('bigtree', (0.05, 0.2, 0.09), sheen=0.5, scale=60)
    for i in range(6):
        u = i / 6
        bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=0.75 * (1 - u) + 0.1, radius2=0.08, depth=0.65,
                                        location=(1.25, 2.1, -0.2 + 1.9 * u + 0.3))
        ob = bpy.context.active_object; bpy.ops.object.shade_smooth(); ob.data.materials.append(big); link(ob, c)
    H['bigbulbs'] = []
    for i in range(60):
        u = random.uniform(0.0, 0.95)
        r = (0.75 * (1 - u) + 0.1) * 0.85
        a = i * 2.39996
        m = emit(f'bb{i}', cols[i % 4], 12.0)
        sphere(c, 'bbulb', 0.016, (1.25 + r * math.cos(a), 2.1 - abs(r * math.sin(a)), -0.1 + 1.9 * u + 0.2), m, seg=10)
        H['bigbulbs'].append((m.node_tree.nodes['Emission'], i % 4))
    # snowy night window (left wall) with falling snow
    win = bpy.data.materials.new('night'); win.use_nodes = True
    nt = win.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial'); em = nt.nodes.new('ShaderNodeEmission')
    tc = N(nt, 'ShaderNodeTexCoord'); gr = N(nt, 'ShaderNodeSeparateXYZ'); L(nt, tc.outputs['Object'], gr.inputs[0])
    cr = N(nt, 'ShaderNodeValToRGB')
    cr.color_ramp.elements[0].color = (0.05, 0.08, 0.2, 1); cr.color_ramp.elements[1].color = (0.15, 0.22, 0.45, 1)
    L(nt, gr.outputs[2], cr.inputs[0]); L(nt, cr.outputs[0], em.inputs[0]); em.inputs[1].default_value = 1.5
    L(nt, em.outputs[0], out.inputs[0])
    box(c, 'window', (0.02, 0.9, 1.1), (-2.27, 1.6, 0.9), win, bevel=0)
    frame_m, _, _ = plain('frame', (0.9, 0.88, 0.84), 0.4)
    box(c, 'wframe', (0.05, 0.05, 1.16), (-2.25, 1.6, 0.9), frame_m, bevel=0.003)
    box(c, 'wframe', (0.05, 0.96, 0.05), (-2.25, 1.6, 0.9), frame_m, bevel=0.003)
    snow_m = emit('snow', (0.9, 0.95, 1.0), 4.0)
    H['snow'] = []
    for i in range(70):
        s = sphere(c, 'snow', 0.006, (-2.32, random.uniform(1.18, 2.02), random.uniform(0.36, 1.44)), snow_m, seg=8)
        H['snow'].append((s, s.location.z, random.uniform(0.06, 0.12), random.uniform(0, 6.28)))
    # ---------------------------------------------------------------- soot puff balls (hidden until needed)
    sm, _, _ = plain('soot_puff', (0.32, 0.3, 0.29), 0.95, Sheen_Weight=0.8, Sheen_Roughness=0.3)
    H['puffs'] = [sphere(c, 'puff', 1.0, (0, 0, -5), sm, seg=16) for _ in range(14)]
    for b in H['puffs']:
        b.hide_render = True
    sp_m = emit('sparkle', (1.0, 0.85, 0.5), 30.0)
    H['sparks'] = [sphere(c, 'spark', 1.0, (0, 0, -5), sp_m, seg=8) for _ in range(16)]
    for b in H['sparks']:
        b.hide_render = True
    # ---------------------------------------------------------------- lights on the stage
    H['key'] = area('key', (-0.45, -0.45, 0.6), (0.0, 0.0, 0.06), 0.6, (1.0, 0.85, 0.7), 22.0)
    H['fill'] = area('fill', (0.5, -0.6, 0.25), (0.0, 0.0, 0.06), 0.6, (0.55, 0.65, 1.0), 6.0)
    H['rim'] = area('rim', (-0.3, 0.7, 0.35), (0.0, 0.0, 0.06), 0.4, (1.0, 0.55, 0.3), 10.0)
    H['party'] = area('party', (0.2, -0.5, 0.35), (0.0, 0.0, 0.05), 0.4, (1, 1, 1), 0.0)
    w = bpy.context.scene.world or bpy.data.worlds.new('w')
    bpy.context.scene.world = w
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.03, 0.02, 0.02, 1)
    w.node_tree.nodes['Background'].inputs[1].default_value = 1.0
    H['cols'] = cols
    return H
