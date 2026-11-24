"""The cozy living room, all 3D: coffee table, sofa with a chunky knitted blanket, cushions, a shelf with books and a
plant, fairy lights, a floor lamp, a night window, a candle, the popcorn bucket and a cola glass.  Materials and lights
for Cycles.  Metres, z up, table top at z = 0, the camera looks along +y."""
import math, random
import numpy as np
import bpy

random.seed(7)


# ------------------------------------------------------------------ node helpers
def new_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    bs = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(bs.outputs[0], out.inputs[0])
    return m, nt, bs


def N(nt, kind, **kw):
    n = nt.nodes.new(kind)
    for k, v in kw.items():
        if k.startswith('i_'):
            nm = k[2:]
            sock = next((x for x in n.inputs if x.identifier == nm), None) or n.inputs[nm.replace('_', ' ')]
            sock.default_value = v
        else:
            setattr(n, k, v)
    return n


def L(nt, a, b):
    nt.links.new(a, b)


def setp(bs, **kw):
    for k, v in kw.items():
        bs.inputs[k.replace('_', ' ')].default_value = v


def bump(nt, bs, height, strength=0.4, dist=0.0005):
    b = N(nt, 'ShaderNodeBump', i_Strength=strength, i_Distance=dist)
    L(nt, height, b.inputs['Height'])
    L(nt, b.outputs[0], bs.inputs['Normal'])
    return b


def materials():
    M = {}
    # yarn: vertex colour, cotton sheen, twisted plies along the tube UV, fine fuzz
    m, nt, bs = new_mat('yarn')
    at = N(nt, 'ShaderNodeAttribute', attribute_name='col')
    L(nt, at.outputs['Color'], bs.inputs['Base Color'])
    setp(bs, Roughness=0.82, Sheen_Weight=0.9, Sheen_Roughness=0.35, Subsurface_Weight=0.06, Subsurface_Scale=0.002)
    uv = N(nt, 'ShaderNodeUVMap', uv_map='UVMap')
    sx = N(nt, 'ShaderNodeSeparateXYZ')
    L(nt, uv.outputs[0], sx.inputs[0])
    a = N(nt, 'ShaderNodeMath', operation='MULTIPLY', i_Value_001=1.45)
    L(nt, sx.outputs[0], a.inputs[0])
    b = N(nt, 'ShaderNodeMath', operation='MULTIPLY_ADD')
    L(nt, sx.outputs[1], b.inputs[0]); b.inputs[1].default_value = 2.0; L(nt, a.outputs[0], b.inputs[2])
    s = N(nt, 'ShaderNodeMath', operation='PINGPONG', i_Value_001=0.5)
    L(nt, b.outputs[0], s.inputs[0])
    nz = N(nt, 'ShaderNodeTexNoise', i_Scale=900.0, i_Detail=2.0)
    mix = N(nt, 'ShaderNodeMath', operation='MULTIPLY_ADD', i_Value_001=0.25)
    L(nt, nz.outputs[0], mix.inputs[0]); L(nt, s.outputs[0], mix.inputs[2])
    bump(nt, bs, mix.outputs[0], 0.55, 0.0004)
    M['yarn'] = m
    # felt (eye whites, cheeks)
    m, nt, bs = new_mat('felt')
    at = N(nt, 'ShaderNodeAttribute', attribute_name='col')
    L(nt, at.outputs['Color'], bs.inputs['Base Color'])
    setp(bs, Roughness=1.0, Sheen_Weight=1.0, Sheen_Roughness=0.5)
    nz = N(nt, 'ShaderNodeTexNoise', i_Scale=2500.0, i_Detail=4.0)
    bump(nt, bs, nz.outputs[0], 0.3, 0.0002)
    M['felt'] = m
    # satin stitches (mouth, teeth, buttons)
    m, nt, bs = new_mat('satin')
    at = N(nt, 'ShaderNodeAttribute', attribute_name='col')
    L(nt, at.outputs['Color'], bs.inputs['Base Color'])
    setp(bs, Roughness=0.42, Sheen_Weight=0.5, Sheen_Roughness=0.3)
    wv = N(nt, 'ShaderNodeTexWave', i_Scale=1400.0, wave_profile='SAW')
    bump(nt, bs, wv.outputs[1], 0.25, 0.0002)
    M['satin'] = m
    # glossy safety eyes
    m, nt, bs = new_mat('eye')
    setp(bs, Base_Color=(0.006, 0.005, 0.006, 1), Roughness=0.08, Coat_Weight=1.0, Coat_Roughness=0.02, Specular_IOR_Level=0.7)
    M['eye'] = m
    m, nt, bs = new_mat('throat')
    setp(bs, Base_Color=(0.09, 0.012, 0.02, 1), Roughness=0.55, Subsurface_Weight=0.2, Subsurface_Scale=0.003)
    M['throat'] = m
    m, nt, bs = new_mat('tongue')
    setp(bs, Base_Color=(0.75, 0.22, 0.28, 1), Roughness=0.35, Subsurface_Weight=0.35, Subsurface_Scale=0.003, Sheen_Weight=0.4)
    nz = N(nt, 'ShaderNodeTexNoise', i_Scale=600.0)
    bump(nt, bs, nz.outputs[0], 0.3, 0.0003)
    M['tongue'] = m
    # remote LED (animated emission)
    m, nt, bs = new_mat('led')
    setp(bs, Base_Color=(0.6, 0.05, 0.03, 1), Emission_Color=(1.0, 0.12, 0.05, 1), Emission_Strength=0.0, Roughness=0.2)
    M['led'] = m
    return M


def wood_mat(name, base=(0.36, 0.19, 0.09), dark=(0.16, 0.07, 0.03), scale=2.0, coat=0.35, rough=0.38):
    m, nt, bs = new_mat(name)
    tc = N(nt, 'ShaderNodeTexCoord')
    mp = N(nt, 'ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (scale, scale * 9, scale)
    L(nt, tc.outputs['Object'], mp.inputs[0])
    nz = N(nt, 'ShaderNodeTexNoise', i_Scale=1.8, i_Detail=6.0, i_Distortion=0.6)
    L(nt, mp.outputs[0], nz.inputs[0])
    wv = N(nt, 'ShaderNodeTexWave', wave_type='RINGS', i_Scale=3.5, i_Distortion=9.0, i_Detail=4.0)
    L(nt, mp.outputs[0], wv.inputs[0])
    ramp = N(nt, 'ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (*dark, 1)
    ramp.color_ramp.elements[1].color = (*base, 1)
    mx = N(nt, 'ShaderNodeMath', operation='MULTIPLY_ADD', i_Value_001=0.6)
    L(nt, wv.outputs[1], mx.inputs[0]); L(nt, nz.outputs[0], mx.inputs[2])
    L(nt, mx.outputs[0], ramp.inputs[0])
    L(nt, ramp.outputs[0], bs.inputs['Base Color'])
    setp(bs, Roughness=rough, Coat_Weight=coat, Coat_Roughness=0.12)
    bump(nt, bs, mx.outputs[0], 0.08, 0.001)
    return m


def fabric_mat(name, col, sheen=1.0, scale=900.0, knit=False):
    m, nt, bs = new_mat(name)
    setp(bs, Base_Color=(*col, 1), Roughness=0.95, Sheen_Weight=sheen, Sheen_Roughness=0.45)
    if knit:
        # chunky knit: rows of V stitches from a sheared sine pattern on object coords
        tc = N(nt, 'ShaderNodeTexCoord')
        sx = N(nt, 'ShaderNodeSeparateXYZ')
        L(nt, tc.outputs['UV'], sx.inputs[0])
        fx = N(nt, 'ShaderNodeMath', operation='MULTIPLY', i_Value_001=60.0)
        L(nt, sx.outputs[0], fx.inputs[0])
        ab = N(nt, 'ShaderNodeMath', operation='PINGPONG', i_Value_001=0.5)
        L(nt, fx.outputs[0], ab.inputs[0])
        fy = N(nt, 'ShaderNodeMath', operation='MULTIPLY_ADD', i_Value_001=90.0)
        L(nt, sx.outputs[1], fy.inputs[0]); L(nt, ab.outputs[0], fy.inputs[2])
        sn = N(nt, 'ShaderNodeMath', operation='SINE')
        m2 = N(nt, 'ShaderNodeMath', operation='MULTIPLY', i_Value_001=6.2832)
        L(nt, fy.outputs[0], m2.inputs[0]); L(nt, m2.outputs[0], sn.inputs[0])
        cc = N(nt, 'ShaderNodeMath', operation='ABSOLUTE')
        L(nt, sn.outputs[0], cc.inputs[0])
        bump(nt, bs, cc.outputs[0], 0.9, 0.004)
        ao = N(nt, 'ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY')
        ao.inputs['Factor'].default_value = 0.45
        ao.inputs[6].default_value = (*col, 1)
        L(nt, cc.outputs[0], ao.inputs[7])
        L(nt, ao.outputs[2], bs.inputs['Base Color'])
    else:
        nz = N(nt, 'ShaderNodeTexNoise', i_Scale=scale, i_Detail=3.0)
        bump(nt, bs, nz.outputs[0], 0.25, 0.0005)
    return m


def plain(name, col, rough=0.6, **kw):
    m, nt, bs = new_mat(name)
    setp(bs, Base_Color=(*col, 1), Roughness=rough, **kw)
    return m, nt, bs


def emit(name, col, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    e = nt.nodes.new('ShaderNodeEmission')
    e.inputs[0].default_value = (*col, 1)
    e.inputs[1].default_value = strength
    nt.links.new(e.outputs[0], out.inputs[0])
    return m


# ------------------------------------------------------------------ geometry helpers
def coll(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c


def link(ob, c):
    for x in ob.users_collection:
        x.objects.unlink(ob)
    c.objects.link(ob)


def box(c, name, size, loc, mat, bevel=0.01, segs=4, subsurf=0, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = size
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        md = ob.modifiers.new('bev', 'BEVEL'); md.width = bevel; md.segments = segs
    if subsurf:
        md = ob.modifiers.new('sub', 'SUBSURF'); md.levels = subsurf; md.render_levels = subsurf
    bpy.ops.object.shade_smooth()
    ob.data.materials.append(mat)
    link(ob, c)
    return ob


def cyl(c, name, r, h, loc, mat, verts=48, r2=None, cap=True, rot=(0, 0, 0)):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc, rotation=rot,
                                            end_fill_type='NGON' if cap else 'NOTHING')
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=h, location=loc, rotation=rot,
                                        end_fill_type='NGON' if cap else 'NOTHING')
    ob = bpy.context.active_object
    ob.name = name
    bpy.ops.object.shade_smooth()
    ob.data.materials.append(mat)
    link(ob, c)
    return ob


def sphere(c, name, r, loc, mat, seg=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, radius=r, location=loc)
    ob = bpy.context.active_object
    ob.name = name
    bpy.ops.object.shade_smooth()
    ob.data.materials.append(mat)
    link(ob, c)
    return ob


def area(name, loc, look, size, col, power, shape='RECTANGLE', sy=None):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.shape = shape
    ld.size = size
    if sy:
        ld.size_y = sy
    ld.color = col
    ld.energy = power
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    d = np.array(look) - np.array(loc)
    ob.rotation_euler = _look_euler(d)
    return ob


def point(name, loc, col, power, radius=0.02):
    ld = bpy.data.lights.new(name, 'POINT')
    ld.color = col
    ld.energy = power
    ld.shadow_soft_size = radius
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    return ob


def _look_euler(d):
    from mathutils import Vector
    return Vector(d).to_track_quat('-Z', 'Y').to_euler()


# ------------------------------------------------------------------ the room
def build_room():
    c = coll('room')
    H = {}
    wood = wood_mat('wood_table', base=(0.42, 0.22, 0.1), dark=(0.17, 0.075, 0.03), scale=1.4)
    # coffee table
    box(c, 'table_top', (1.15, 0.78, 0.036), (0, 0.2, -0.018), wood, bevel=0.008, segs=5)
    for sx in (-0.5, 0.5):
        for sy in (-0.12, 0.52):
            cyl(c, 'leg', 0.022, 0.39, (sx, sy, -0.23), wood, verts=24, r2=0.016)
    # knitted coaster + cola glass (back right)
    coaster_m = fabric_mat('coaster', (0.55, 0.62, 0.48), knit=True)
    cyl(c, 'coaster', 0.042, 0.004, (0.205, 0.17, 0.002), coaster_m, verts=40)
    glass_m, nt, bs = plain('glass', (1, 1, 1), 0.02, Transmission_Weight=1.0, IOR=1.45)
    cola_m, nt, bs = plain('cola', (0.12, 0.035, 0.01), 0.05, Transmission_Weight=0.85, IOR=1.34, Subsurface_Weight=0.0)
    cyl(c, 'glass', 0.03, 0.095, (0.205, 0.17, 0.0515), glass_m, verts=48, cap=True)
    cyl(c, 'cola', 0.027, 0.07, (0.205, 0.17, 0.039), cola_m, verts=40)
    ice_m, nt, bs = plain('ice', (0.9, 0.95, 1), 0.08, Transmission_Weight=1.0, IOR=1.31)
    for i in range(3):
        box(c, 'ice', (0.016, 0.016, 0.014), (0.198 + 0.01 * i, 0.165 + 0.006 * (i % 2), 0.07 + 0.006 * i), ice_m, bevel=0.003, rot=(0.3 * i, 0.5, i))
    straw_m, nt, bs = plain('straw', (0.85, 0.15, 0.2), 0.4)
    cyl(c, 'straw', 0.0035, 0.14, (0.218, 0.178, 0.09), straw_m, verts=12, rot=(0.25, 0.18, 0))
    # popcorn bucket (paper, red and cream stripes), behind the frog
    bk_m, nt, bs = new_mat('bucket')
    tc = N(nt, 'ShaderNodeTexCoord')
    gr = N(nt, 'ShaderNodeTexGradient', gradient_type='RADIAL')
    L(nt, tc.outputs['Object'], gr.inputs[0])
    mm = N(nt, 'ShaderNodeMath', operation='MULTIPLY', i_Value_001=14.0)
    L(nt, gr.outputs[1], mm.inputs[0])
    fr = N(nt, 'ShaderNodeMath', operation='FRACT')
    L(nt, mm.outputs[0], fr.inputs[0])
    gt = N(nt, 'ShaderNodeMath', operation='GREATER_THAN', i_Value_001=0.5)
    L(nt, fr.outputs[0], gt.inputs[0])
    mx = N(nt, 'ShaderNodeMix', data_type='RGBA')
    mx.inputs[6].default_value = (0.75, 0.04, 0.05, 1)
    mx.inputs[7].default_value = (0.92, 0.86, 0.74, 1)
    L(nt, gt.outputs[0], mx.inputs['Factor'])
    L(nt, mx.outputs[2], bs.inputs['Base Color'])
    setp(bs, Roughness=0.55, Sheen_Weight=0.2)
    bpy.ops.mesh.primitive_cone_add(vertices=56, radius1=0.026, radius2=0.034, depth=0.066, location=(0, 0, 0.033), end_fill_type='NGON')
    bucket = bpy.context.active_object
    bucket.name = 'bucket'
    md = bucket.modifiers.new('sol', 'SOLIDIFY'); md.thickness = 0.0012
    bpy.ops.object.shade_smooth()
    bucket.data.materials.append(bk_m)
    link(bucket, c)
    # remove the top cap so it is open
    import bmesh
    bm = bmesh.new(); bm.from_mesh(bucket.data)
    top = [f for f in bm.faces if f.calc_center_median().z > 0.03 and len(f.verts) > 4]
    bmesh.ops.delete(bm, geom=top, context='FACES'); bm.to_mesh(bucket.data); bm.free()
    bucket.location = (0.0, 0.0, 0.0)
    pivot = bpy.data.objects.new('bucket_pivot', None)
    c.objects.link(pivot)
    bucket.parent = pivot
    from mathutils import Matrix as _M
    bucket.matrix_basis = _M(((1000, 0, 0, 0), (0, 0, 1000, 33.0), (0, -1000, 0, 0), (0, 0, 0, 1)))
    H['bucket'] = pivot
    H['bucket_mesh'] = bucket
    # magazine, foreground left (out of focus depth)
    mag_m, nt, bs = plain('magazine', (0.15, 0.32, 0.45), 0.3, Coat_Weight=0.3)
    box(c, 'magazine', (0.21, 0.28, 0.006), (-0.27, -0.07, 0.003), mag_m, bevel=0.001, rot=(0, 0, 0.35))
    # candle (back left) with a flame and its light
    wax, nt, bs = plain('wax', (0.92, 0.85, 0.72), 0.5, Subsurface_Weight=0.6, Subsurface_Scale=0.01)
    jar, nt, bs = plain('jar', (0.9, 0.75, 0.55), 0.05, Transmission_Weight=1.0, IOR=1.45)
    cyl(c, 'candle_jar', 0.032, 0.075, (-0.26, 0.3, 0.0375), jar, verts=40, cap=False)
    cyl(c, 'candle', 0.029, 0.05, (-0.26, 0.3, 0.025), wax, verts=40)
    fl = sphere(c, 'flame', 0.0045, (-0.26, 0.3, 0.062), emit('flame', (1.0, 0.62, 0.25), 60.0), seg=16)
    fl.scale = (1, 1, 2.2)
    H['flame'] = fl
    H['candle_light'] = point('candle_light', (-0.26, 0.3, 0.075), (1.0, 0.6, 0.3), 1.6, 0.006)
    # floor + knitted rug
    floor_m = wood_mat('floor', base=(0.5, 0.33, 0.2), dark=(0.28, 0.16, 0.08), scale=0.6, coat=0.1, rough=0.5)
    box(c, 'floor', (8, 8, 0.02), (0, 1.5, -0.43), floor_m, bevel=0)
    rug = fabric_mat('rug', (0.78, 0.7, 0.58), knit=True)
    box(c, 'rug', (2.4, 1.7, 0.012), (0, 0.4, -0.414), rug, bevel=0.004)
    # walls
    wall_m, nt, bs = plain('wall', (0.55, 0.42, 0.33), 0.9)
    nz = N(nt, 'ShaderNodeTexNoise', i_Scale=40.0, i_Detail=6.0)
    bump(nt, bs, nz.outputs[0], 0.15, 0.002)
    box(c, 'wall_back', (6, 0.05, 3.2), (0, 2.5, 1.1), wall_m, bevel=0)
    box(c, 'wall_left', (0.05, 6, 3.2), (-2.2, 1.0, 1.1), wall_m, bevel=0)
    # sofa
    sofa_m = fabric_mat('sofa', (0.08, 0.2, 0.22), sheen=1.0, scale=600)
    box(c, 'sofa_base', (2.3, 0.95, 0.3), (0, 1.75, -0.27), sofa_m, bevel=0.05, segs=6)
    box(c, 'sofa_seat_l', (1.1, 0.85, 0.16), (-0.56, 1.7, -0.04), sofa_m, bevel=0.06, segs=6)
    box(c, 'sofa_seat_r', (1.1, 0.85, 0.16), (0.56, 1.7, -0.04), sofa_m, bevel=0.06, segs=6)
    box(c, 'sofa_back', (2.3, 0.25, 0.62), (0, 2.18, 0.2), sofa_m, bevel=0.08, segs=6)
    box(c, 'sofa_arm_l', (0.22, 0.95, 0.48), (-1.2, 1.75, -0.02), sofa_m, bevel=0.08, segs=6)
    box(c, 'sofa_arm_r', (0.22, 0.95, 0.48), (1.2, 1.75, -0.02), sofa_m, bevel=0.08, segs=6)
    for x, col, rz in ((-0.65, (0.85, 0.45, 0.3), 0.15), (-0.15, (0.9, 0.82, 0.65), -0.1), (0.55, (0.75, 0.55, 0.2), 0.12)):
        cm = fabric_mat(f'cushion{x}', col, knit=(x > 0))
        box(c, 'cushion', (0.42, 0.14, 0.4), (x, 1.98, 0.24), cm, bevel=0.06, segs=4, subsurf=2, rot=(-0.25, rz, 0))
    # chunky knitted blanket draped over the left seat and the front
    bl_m = fabric_mat('blanket', (0.92, 0.88, 0.8), knit=True)
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=60, y_subdivisions=60, size=1.0, location=(0, 0, 0))
    bl = bpy.context.active_object
    bl.name = 'blanket'
    V = np.zeros(len(bl.data.vertices) * 3)
    bl.data.vertices.foreach_get('co', V)
    V = V.reshape(-1, 3)
    u, v = V[:, 0] + 0.5, V[:, 1] + 0.5
    x = -0.95 + u * 0.95
    yy = 1.35 + v * 0.75
    zz = 0.045 + 0.012 * np.sin(u * 19) * np.sin(v * 11) + 0.025 * np.exp(-((u - 0.6) ** 2 + (v - 0.4) ** 2) / 0.02)
    front = yy < 1.42
    zz = np.where(front, 0.045 - (1.42 - yy) * 4.0, zz)
    yy = np.where(front, 1.3 + 0.03 * np.sin(u * 13), yy)
    V2 = np.stack([x, yy, zz], 1)
    bl.data.vertices.foreach_set('co', V2.ravel())
    bl.data.update()
    md = bl.modifiers.new('sol', 'SOLIDIFY'); md.thickness = 0.015
    md = bl.modifiers.new('sub', 'SUBSURF'); md.levels = 1; md.render_levels = 1
    bpy.ops.object.shade_smooth()
    bl.data.materials.append(bl_m)
    link(bl, c)
    # shelf with books, a plant and a picture
    shelf_m = wood_mat('shelf', base=(0.6, 0.42, 0.25), dark=(0.35, 0.22, 0.12), scale=2.0, coat=0.0, rough=0.6)
    box(c, 'shelf', (1.2, 0.22, 0.03), (-0.35, 2.38, 0.95), shelf_m, bevel=0.004)
    bx = -0.9
    pal = [(0.55, 0.12, 0.1), (0.12, 0.25, 0.4), (0.8, 0.65, 0.3), (0.2, 0.35, 0.2), (0.85, 0.82, 0.75), (0.4, 0.18, 0.35)]
    for i in range(14):
        w = random.uniform(0.025, 0.045)
        h = random.uniform(0.18, 0.27)
        bm_, nt, bs = plain(f'book{i}', pal[i % len(pal)], 0.6)
        box(c, 'book', (w, 0.16, h), (bx + w / 2, 2.38, 0.965 + h / 2), bm_, bevel=0.003, rot=(0, 0.12 if i == 9 else 0, 0))
        bx += w + 0.004
    pot_m, nt, bs = plain('pot', (0.75, 0.42, 0.28), 0.7)
    cyl(c, 'pot', 0.07, 0.13, (0.12, 2.38, 1.03), pot_m, verts=32, r2=0.085)
    leaf_m, nt, bs = plain('leaf', (0.06, 0.25, 0.08), 0.45, Subsurface_Weight=0.2, Subsurface_Scale=0.01)
    for i in range(16):
        a = i * 2.4
        L_ = random.uniform(0.18, 0.32)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=1, location=(0.12 + math.cos(a) * L_ * 0.4, 2.38 + math.sin(a) * 0.08, 1.1 + L_ * 0.5))
        lf = bpy.context.active_object
        lf.scale = (L_ * 0.25, 0.006, L_ * 0.5)
        lf.rotation_euler = (0, math.cos(a) * 0.9, a * 0.3)
        bpy.ops.object.shade_smooth()
        lf.data.materials.append(leaf_m)
        link(lf, c)
    frame_m, nt, bs = plain('frame', (0.08, 0.06, 0.05), 0.4)
    art_m, nt, bs = new_mat('art')
    tc = N(nt, 'ShaderNodeTexCoord')
    ws = N(nt, 'ShaderNodeTexWave', i_Scale=2.0, i_Distortion=6.0)
    L(nt, tc.outputs['Object'], ws.inputs[0])
    cr = N(nt, 'ShaderNodeValToRGB')
    cr.color_ramp.elements[0].color = (0.9, 0.55, 0.3, 1)
    cr.color_ramp.elements[1].color = (0.15, 0.3, 0.45, 1)
    L(nt, ws.outputs[1], cr.inputs[0]); L(nt, cr.outputs[0], bs.inputs['Base Color'])
    box(c, 'pframe', (0.5, 0.03, 0.38), (0.55, 2.46, 1.15), frame_m, bevel=0.005)
    box(c, 'art', (0.44, 0.01, 0.32), (0.55, 2.44, 1.15), art_m, bevel=0)
    # night window on the right with city bokeh
    win_m = bpy.data.materials.new('night')
    win_m.use_nodes = True
    nt = win_m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    tc = N(nt, 'ShaderNodeTexCoord')
    vo = N(nt, 'ShaderNodeTexVoronoi', i_Scale=22.0, feature='F1')
    L(nt, tc.outputs['Object'], vo.inputs[0])
    cr = N(nt, 'ShaderNodeValToRGB')
    cr.color_ramp.elements[0].position = 0.0
    cr.color_ramp.elements[0].color = (1.0, 0.75, 0.4, 1)
    cr.color_ramp.elements[1].position = 0.07
    cr.color_ramp.elements[1].color = (0.01, 0.02, 0.06, 1)
    L(nt, vo.outputs['Distance'], cr.inputs[0])
    L(nt, cr.outputs[0], em.inputs[0])
    em.inputs[1].default_value = 3.0
    L(nt, em.outputs[0], out.inputs[0])
    box(c, 'window', (0.7, 0.02, 1.0), (1.35, 2.47, 0.85), win_m, bevel=0)
    box(c, 'window_frame', (0.78, 0.04, 0.06), (1.35, 2.45, 0.85), frame_m, bevel=0.003)
    box(c, 'window_frame', (0.04, 0.04, 1.06), (1.35, 2.45, 0.85), frame_m, bevel=0.003)
    curt = fabric_mat('curtain', (0.75, 0.6, 0.45), sheen=0.6)
    for x0 in (0.92, 1.78):
        bpy.ops.mesh.primitive_grid_add(x_subdivisions=40, y_subdivisions=4, size=1.0)
        cu = bpy.context.active_object
        V = np.zeros(len(cu.data.vertices) * 3); cu.data.vertices.foreach_get('co', V); V = V.reshape(-1, 3)
        u, v = V[:, 0] + 0.5, V[:, 1] + 0.5
        cu.data.vertices.foreach_set('co', np.stack([x0 + (u - 0.5) * 0.3, 2.4 + 0.03 * np.sin(u * 40), -0.4 + v * 2.0], 1).ravel())
        cu.data.update()
        bpy.ops.object.shade_smooth()
        cu.data.materials.append(curt)
        link(cu, c)
    # fairy lights: two sagging strings of warm bulbs over the sofa
    wire_m, nt, bs = plain('wire', (0.05, 0.05, 0.04), 0.5)
    H['bulbs'] = []
    bulb_m = emit('bulb', (1.0, 0.72, 0.38), 40.0)
    for (x0, x1, z0, sag) in ((-1.3, 0.2, 0.78, 0.16), (0.2, 1.0, 0.8, 0.12)):
        pts = []
        for i in range(19):
            u = i / 18
            x = x0 + (x1 - x0) * u
            z = z0 - sag * 4 * u * (1 - u)
            pts.append((x, 2.44, z))
            sphere(c, 'bulb', 0.008, (x, 2.43, z - 0.012), bulb_m, seg=12)
        cd = bpy.data.curves.new('wire', 'CURVE'); cd.dimensions = '3D'; cd.bevel_depth = 0.0012
        sp = cd.splines.new('POLY'); sp.points.add(len(pts) - 1)
        for p_, q in zip(sp.points, pts):
            p_.co = (*q, 1)
        wo = bpy.data.objects.new('wire', cd); c.objects.link(wo); cd.materials.append(wire_m)
    # floor lamp, back left, behind the sofa arm
    metal, nt, bs = plain('brass', (0.8, 0.55, 0.25), 0.3, Metallic=1.0)
    cyl(c, 'lamp_pole', 0.012, 1.4, (-1.5, 2.15, 0.28), metal, verts=16)
    shade_m, nt, bs = plain('shade', (0.95, 0.85, 0.7), 0.8, Transmission_Weight=0.3, Emission_Color=(1, 0.7, 0.4, 1), Emission_Strength=1.2)
    cyl(c, 'lamp_shade', 0.2, 0.28, (-1.5, 2.15, 1.0), shade_m, verts=48, r2=0.14, cap=False)
    H['lamp'] = point('lamp_bulb', (-1.5, 2.15, 1.0), (1.0, 0.66, 0.36), 70.0, 0.08)
    # lights on the toys
    H['key'] = area('key', (-0.55, -0.35, 0.55), (0.0, 0.05, 0.05), 0.6, (1.0, 0.8, 0.6), 22.0)
    H['tv'] = area('tv', (0.15, -0.95, 0.18), (0.0, 0.05, 0.06), 0.55, (0.45, 0.6, 1.0), 14.0, sy=0.32)
    H['rim'] = area('rim', (0.5, 0.6, 0.35), (0.0, 0.03, 0.06), 0.3, (1.0, 0.7, 0.45), 6.0)
    w = bpy.context.scene.world or bpy.data.worlds.new('w')
    bpy.context.scene.world = w
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.02, 0.018, 0.022, 1)
    w.node_tree.nodes['Background'].inputs[1].default_value = 1.0
    return H
