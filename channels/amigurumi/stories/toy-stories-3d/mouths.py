"""Replacement mouths, as in stop-motion: extra embroidered face items built by amikit in the toy's own style
(satin lining, tongue, teeth), swapped in while the toy opens its mouth.  Saved per toy and state to
<tid>.mouths.pkl: {state: [mesh dicts like export_ami]}."""
import sys, json, math, pickle, copy
sys.path.insert(0, '/home/user')
import numpy as np
from amikit.toy import Toy

ROOT = '/home/user/video-engine/channels/amigurumi/toys'
RND = 3.6   # mm per round on a face


def at_xy(x, y):
    """Face applique position (round, az) of a point x mm right, y mm below the face centre."""
    return {'round': math.hypot(x, y) / RND, 'az': math.degrees(math.atan2(x, -y)) % 360 if (x or y) else 0}


def shark_states():
    out = {}
    for st, (w, h, cy) in {'half': (20, 11, 15.0), 'open': (24, 18, 16.5)}.items():
        items = [dict(type='satin', on='face', at=at_xy(0, cy), width_mm=w, height_mm=h, shape='oval', colour='mouth',
                      thickness_mm=1.2, id=f'm_{st}_lining'),
                 dict(type='satin', on='face', at=at_xy(0, cy + h * 0.26), width_mm=w * 0.5, height_mm=h * 0.36, shape='oval',
                      colour='light pink', thickness_mm=1.0, lift_mm=0.5, id=f'm_{st}_tongue')]
        ty = cy - h / 2 + 2.0
        for i, x in enumerate(np.linspace(-w * 0.3, w * 0.3, 4)):
            items.append(dict(type='satin', on='face', at=at_xy(float(x), ty), width_mm=3.4, height_mm=3.0,
                              shape='triangle', colour='white', thickness_mm=1.0, lift_mm=0.9, id=f'm_{st}_tooth{i}'))
        out[st] = items
    return out


def frog_states():
    out = {}
    for st, (w, h) in {'half': (10, 7), 'open': (14, 11)}.items():
        out[st] = [dict(type='satin', on='body', at={'round': 18.4, 'az': 0}, width_mm=w, height_mm=h, shape='oval',
                        colour='mouth', thickness_mm=1.2, id=f'm_{st}_lining'),
                   dict(type='satin', on='body', at={'round': 17.8, 'az': 0}, width_mm=w * 0.5, height_mm=h * 0.35,
                        shape='oval', colour='pink', thickness_mm=1.0, lift_mm=0.5, id=f'm_{st}_tongue')]
    return out


def build(tid, height, states, drop):
    sp = json.load(open(f'{ROOT}/{tid}/spec.json'))
    base = pickle.load(open(f'/home/user/work/b3d/{tid}.ami.pkl', 'rb'))
    allV0 = None
    res = {}
    for st, items in states.items():
        s = copy.deepcopy(sp)
        s['colours']['mouth'] = '#5b1d2c'
        s['face'] = [f for f in s['face'] if f.get('id') not in drop] + items
        toy = Toy(s)
        parts = toy.build(ku=3, kv=3, relief=0.0)
        allV = np.concatenate([p['V'] for p in parts if p['mat'] == 0])
        h0 = allV[:, 1].max() - allV[:, 1].min()
        sc = height / h0
        y0 = allV[:, 1].min()
        ms = []
        for p in parts:
            fi = p.get('face_item')
            fid = fi.get('id') if isinstance(fi, dict) else fi
            if not (fid or '').startswith('m_'):
                continue
            nm = p['name']
            ms.append(dict(name=nm, piece=nm.split('@')[1], mat=int(p['mat']), V=((p['V'] - [0, y0, 0]) * sc).astype(np.float32),
                           F=p['F'].astype(np.int32), C=p['C'].astype(np.float32), N=p['N'].astype(np.float32),
                           UV=(p['UV'] if p.get('UV') is not None else np.zeros((len(p['V']), 2))).astype(np.float32),
                           H=np.ones(len(p['V']), np.float32), fid=fid))
        res[st] = ms
        print(tid, st, len(ms), 'meshes')
    pickle.dump(res, open(f'/home/user/work/b3d/{tid}.mouths.pkl', 'wb'))


if __name__ == '__main__':
    build('shark-in-a-hoodie', 115, shark_states(), ('mouth', 'tooth_0', 'tooth_1', 'tooth_2', 'tooth_3'))
    build('frog-crying-tears', 88, frog_states(), ('mouth',))
