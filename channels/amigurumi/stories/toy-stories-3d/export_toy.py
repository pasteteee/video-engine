"""Export a toy (or prop) built by the yarn engine to an npz the Blender scene reads: yarn polylines per piece, core,
colours, rig (parents, joints, arm directions), eyes and face details."""
import sys, json, os
sys.path.insert(0, '/home/user/work/story')
import numpy as np
from engine import Actor, load_spec, subspec

def export(tid, height, out, spec=None):
    a = Actor(tid, tid, height=height, spec=spec)
    dn = a.dn
    pcs = []
    for k, p in enumerate(dn.pieces):
        pcs.append(dict(name=p['name'], role=p['role'], side=float(p.get('side', 0.0)), parent=-1 if p['parent'] is None else int(p['parent']),
                        start=int(p['start']), end=int(p['end']), joint=[float(v) for v in p['joint']], dir=[float(v) for v in p.get('dir', [0, -1, 0])]))
    core = [(k, Xc) for k, Xc in dn.core]
    det_V, det_F, det_info = [], [], []
    off = 0
    for k, it in dn.items:
        det_V.append(it['V']); det_F.append(it['F'] + off); off += len(it['V'])
        det_info.append([k, int(it['row'][0]), int(it['row'][1]), float(it['row'][4]), len(it['V']), len(it['F'])])
    np.savez_compressed(out, X=dn.X, C=dn.C, pal=np.array(dn.pal), d=dn.d,
                        core_k=np.array([k for k, _ in core]), core_len=np.array([len(x) for _, x in core]),
                        core_X=np.concatenate([x for _, x in core]) if core else np.zeros((0, 3)),
                        det_V=np.concatenate(det_V) if det_V else np.zeros((0, 3)), det_F=np.concatenate(det_F) if det_F else np.zeros((0, 3), int),
                        det_info=np.array(det_info), spheres=np.array([[k] + list(s) for k, s in dn.spheres]).reshape(-1, 6),
                        arm=json.dumps({str(k): dict(E=v['E'].tolist(), ax=v['ax'].tolist(), L=v['L'], tip=v['tip'].tolist()) for k, v in a.arm.items()}),
                        pieces=json.dumps(pcs), height=a.height, width=a.width)
    print(tid, len(dn.X), 'pts', len(pcs), 'pieces', len(det_info), 'details', len(dn.spheres), 'eyes')

if __name__ == '__main__':
    for arg in sys.argv[1:]:
        tid, h = arg.split(':')
        spec = subspec(load_spec('goose-knife-meme'), ['dagger']) if tid == 'knife' else None
        export('goose-knife-meme' if tid == 'knife' else tid, float(h), f'/home/user/work/b3d/{tid}.npz', spec=spec)
