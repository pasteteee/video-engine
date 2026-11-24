"""Export a toy as the site's model (amikit: smooth plump pieces with stitch UVs, embroidery, safety eyes, felt) plus
the rig (parents, joints, arm directions) taken from the yarn Dancer export and mapped into the same space.
Usage: python3 export_ami.py tid[:height] ..."""
import sys, json, pickle
sys.path.insert(0, '/home/user')
import numpy as np
from amikit.toy import Toy

ROOT = '/home/user/video-engine/channels/amigurumi'


def load_spec(tid):
    if tid == 'knife':
        sys.path.insert(0, '/home/user/work/story')
        from engine import subspec
        return subspec(load_spec('goose-knife-meme'), ['dagger'])
    for sub in ('toys', 'props'):
        try:
            return json.load(open(f'{ROOT}/{sub}/{tid}/spec.json'))
        except FileNotFoundError:
            pass
    raise FileNotFoundError(tid)


def export(tid, height=None):
    sp = load_spec(tid)
    toy = Toy(sp)
    parts = toy.build(ku=3, kv=3, relief=0.0)
    allV = np.concatenate([p['V'] for p in parts])
    h0 = allV[:, 1].max() - allV[:, 1].min()
    s = (height / h0) if height else 1.0
    y0 = allV[:, 1].min()
    out = []
    for p in parts:
        nm = p['name']
        piece = nm.split('@')[1] if '@' in nm else nm.split('#')[0]
        fi = p.get('face_item')
        fid = fi.get('id') if isinstance(fi, dict) else fi
        V = (p['V'] - [0, y0, 0]) * s
        out.append(dict(name=nm, piece=piece, mat=int(p['mat']), V=V.astype(np.float32), F=p['F'].astype(np.int32),
                        C=p['C'].astype(np.float32), N=p['N'].astype(np.float32),
                        UV=(p['UV'] if p.get('UV') is not None else np.zeros((len(V), 2))).astype(np.float32),
                        H=np.asarray(p.get('H', np.ones(len(V))), np.float32), fid=fid))
    # rig from the Dancer export, mapped by a least-squares fit of piece centroids (scale + offset)
    rig = None
    try:
        z = np.load(f'/home/user/work/b3d/{tid}.npz', allow_pickle=True)
        pcs = json.loads(str(z['pieces']))
        A, B = [], []
        for pc in pcs:
            Vs = [o['V'] for o in out if o['name'] == pc['name']]
            if Vs:
                A.append(z['X'][pc['start']:pc['end']].mean(0)); B.append(Vs[0].mean(0))
        A, B = np.array(A), np.array(B)
        ma, mb = A.mean(0), B.mean(0)
        k = float(((A - ma) * (B - mb)).sum() / ((A - ma) ** 2).sum()) if len(A) > 1 else 1.0
        f = lambda X: (np.asarray(X) - ma) * k + mb
        print(tid, 'fit scale', round(k, 4), 'resid', np.abs(f(A) - B).max().round(2))
        arm = {kk: dict(E=f(v['E']).tolist(), ax=v['ax'], L=v['L'] * k, tip=f(v['tip']).tolist())
               for kk, v in json.loads(str(z['arm'])).items()}
        for pc in pcs:
            pc['joint'] = f(pc['joint']).tolist()
        sph = []
        for row in z['spheres']:
            sph.append([row[0], *f(row[1:4]), row[4] * k, row[5]])
        rig = dict(pieces=pcs, arm=arm, spheres=sph)
    except FileNotFoundError:
        rig = dict(pieces=[dict(name=o['piece'], role='stiff', side=0.0, parent=-1, joint=[0, 0, 0], dir=[0, -1, 0])
                           for o in out[:1]], arm={}, spheres=[])
    allV = np.concatenate([o['V'] for o in out])
    res = dict(parts=out, rig=rig, height=float(allV[:, 1].max()), width=float(allV[:, 0].max() - allV[:, 0].min()))
    pickle.dump(res, open(f'/home/user/work/b3d/{tid}.ami.pkl', 'wb'))
    print(tid, len(out), 'meshes', sum(len(o['V']) for o in out), 'verts', 'h', round(res['height'], 1))


if __name__ == '__main__':
    for arg in sys.argv[1:]:
        tid, _, h = arg.partition(':')
        export(tid, float(h) if h else None)
