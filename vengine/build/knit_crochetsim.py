"""Default knit renderer: the toy crocheted stitch by stitch as real yarn (crochetsim.toyyarn), on an accelerating
clock, with a camera that follows the piece being worked and pulls back to the whole toy. Ported from the channel's
goat-sweater-2027 short (yg4.py).

    python -m vengine.build.knit_crochetsim SPEC.json OUTDIR i/n --src CROCHETSIM_SRC [--dur 16] [--reveal 3.5]
           [--size 1080x1920] [--ss 2] [--soft 1.2] [--core 0] [--bright 1.28] [--fuzz 0.08] [--nply 2]
           [--still 2.5 | --still 1,5,9]

Writes OUTDIR/%04d.png and OUTDIR/plan.json (schema knit_plan). Run n processes with parts 0/n … n-1/n;
frames that already exist are skipped, so a render can be resumed.

Yarn look (thread, fuzz, ply, sheen) and colour stability live in crochetsim's Renderer; this adapter only decides
what is visible when and where the camera is.
"""
from __future__ import annotations

import argparse
import colorsys
import json
import math
import os
import sys

import numpy as np

FPS = 30


def build_plan(pieces, NY, dur, reveal, fps=FPS):
    def prog(t):
        """Share of all yarn made at film time t: slow first (after round 3 of the first piece), then faster."""
        x = t / dur
        p0 = pieces[0]
        s0 = (sum(p0['counts'][:3]) / sum(p0['counts'])) * (p0['end'] - p0['start']) / NY
        return s0 + (1 - s0) * (min(1.0, 0.06 * x + 0.94 * x ** 2.2) if x < 0.94 else 1.0)
    NF = int(round((dur + reveal) * fps))
    plan = []
    for i in range(NF):
        t = i / fps
        s = prog(t)
        face = min(1.0, max(0.0, (t / dur - 0.88) / 0.1))
        n = int(s * NY)
        pi = next((k for k, p in enumerate(pieces) if n < p['end']), len(pieces) - 1)
        p = pieces[pi]
        fr = (n - p['start']) / max(1, p['end'] - p['start'])
        cnt = p['counts']; q = fr * sum(cnt)
        cum = np.concatenate([[0], np.cumsum(cnt)])
        rnd = int(np.clip(np.searchsorted(cum, q, side='right'), 1, len(cnt)))
        plan.append(dict(t=round(t, 5), n=n, piece=p['part'], name=p['name'], pi=pi, round=rnd, rounds=len(cnt),
                         st=float(q), count=int(cnt[rnd - 1]), face=face, s=s))
    return plan


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('spec'); ap.add_argument('out'); ap.add_argument('part', nargs='?', default='0/1')
    ap.add_argument('--src', default=os.environ.get('CROCHETSIM_SRC'))
    ap.add_argument('--dur', type=float, default=16.0); ap.add_argument('--reveal', type=float, default=3.5)
    ap.add_argument('--size', default='1080x1920'); ap.add_argument('--ss', type=int, default=2)
    ap.add_argument('--soft', type=float, default=1.2); ap.add_argument('--core', type=float, default=0.0)
    ap.add_argument('--bright', type=float, default=1.28); ap.add_argument('--fuzz', type=float, default=0.08)
    ap.add_argument('--nply', type=int, default=2); ap.add_argument('--core-shade', type=float, default=0.62)
    ap.add_argument('--still', default=None)
    a = ap.parse_args(argv)
    if a.src:
        sys.path.insert(0, a.src)
    from crochetsim.toyyarn import toy_yarn
    from crochetsim.render import Renderer, Camera
    from crochetsim.hook import default_hook
    from PIL import Image

    spec = json.load(open(a.spec, encoding='utf-8'))
    X, D, C, pal, d, toy = toy_yarn(spec)
    pieces = toy.yarn_pieces
    NY = pieces[-1]['end']                       # yarn of the pieces; the rest is the face

    def brighten(c):
        h, l, s = colorsys.rgb_to_hls(*c)
        l2 = l + (1 - l) * (a.bright - 1) * 0.9 if 0.22 < l < 0.92 else l
        return list(colorsys.hls_to_rgb(h, min(0.95, l2), min(1, s * 1.18)))
    pal2 = [brighten(c) for c in pal]
    NP = len(pal2)
    pal2 = pal2 + [[c * a.core_shade for c in p] for p in pal2]   # a hidden darker core: no light between stitches
    core = []
    if a.core > 0:
        for p in pieces:
            if p['part'] in ('cheek',):
                continue
            seg = X[p['start']:p['end']]; c = seg.mean(0)
            nrm = seg - c; nrm /= np.linalg.norm(nrm, axis=1)[:, None] + 1e-9
            core.append((p['start'], p['end'], seg - nrm * a.core * d))

    Wd, Ht = [int(v) for v in a.size.split('x')]
    rn = Renderer(Wd, Ht, ss=a.ss, r=d / 2 / 1.2, h=0.5, soft=a.soft, palette=pal2, look=1, fuzz=a.fuzz, sheen=0.05,
                  nply=a.nply, backdrop_y=1e5, light=(-0.45, 0.70, 0.55), bg_top=(0.975, 0.955, 0.93),
                  bg_bot=(0.935, 0.905, 0.87))
    plan = build_plan(pieces, NY, a.dur, a.reveal)
    NF = len(plan)
    # camera: around what is visible, smoothed both ways, then pulled back to the whole toy
    lo_all, hi_all = X.min(0), X.max(0); gall = (lo_all + hi_all) / 2; Rall = float(np.linalg.norm(hi_all - lo_all) / 2)
    tg, rad = [], []
    for f in plan:
        p = pieces[f['pi']]
        Xi = X[max(p['start'], f['n'] - 4000):max(p['start'] + 50, f['n'])]
        lo, hi = Xi.min(0), Xi.max(0)
        tg.append((lo + hi) / 2); rad.append(max(16.0, float(np.linalg.norm(hi - lo) / 2)))
    tg, rad = np.array(tg), np.array(rad)
    for k in range(1, NF):
        tg[k] = tg[k - 1] * 0.9 + tg[k] * 0.1; rad[k] = rad[k - 1] * 0.9 + rad[k] * 0.1
    for k in range(NF - 2, -1, -1):
        tg[k] = tg[k + 1] * 0.9 + tg[k] * 0.1; rad[k] = rad[k + 1] * 0.9 + rad[k] * 0.1
    for k in range(NF):
        w = min(1.0, max(0.0, (plan[k]['t'] / a.dur - 0.7) / 0.25)); w = w * w * (3 - 2 * w)
        tg[k] = tg[k] * (1 - w) + gall * w; rad[k] = rad[k] * (1 - w) + Rall * w

    def cam_at(k):
        x = min(1.0, plan[k]['t'] / a.dur)
        az = 25 + 380 * x ** 1.7
        if plan[k]['t'] > a.dur:                       # the reveal: one fast turn that settles facing us
            u = min(1.0, (plan[k]['t'] - a.dur) / a.reveal)
            az = 405 + (720 - 405) * (1 - (1 - u) ** 3)
        az = math.radians(az)
        el = math.radians(48 - 36 * min(1, x * 1.6))
        e = np.array([math.sin(az) * math.cos(el), math.sin(el), math.cos(az) * math.cos(el)])
        return Camera(tg[k] + e * rad[k] * (3.1 if Ht > Wd else 2.6), tg[k], up=(0, 1, 0), fov=30)

    def render(k):
        f = plan[k]
        n = max(30, f['n'])
        nf = int(f['face'] * (len(X) - NY))
        idx = np.r_[0:n, NY:NY + nf] if nf else np.r_[0:n]
        Xs, Ds, Cs = [X[idx]], [D[idx]], [C[idx]]
        for s0, s1, Xc in core:
            m = min(n, s1) - s0
            if m > 20:
                Xs.append(Xc[:m]); Ds.append(D[s0:s0 + m]); Cs.append(C[s0:s0 + m] + NP)
        return rn.render(np.concatenate(Xs), np.concatenate(Ds), np.eye(3), np.array([0, 0, -1e4]), default_hook(),
                         cam_at(k), colnode=np.concatenate(Cs), hook_visible=False, gap=2.0)

    os.makedirs(a.out, exist_ok=True)
    if a.still:
        ts = [float(v) for v in a.still.split(',')]
        ims = [Image.fromarray(render(min(NF - 1, int(t * FPS)))) for t in ts]
        if len(ims) == 1:
            ims[0].save(os.path.join(a.out, 'still.png'))
        else:
            sh = Image.new('RGB', (Wd // 3 * len(ims), Ht // 3))
            for j, im in enumerate(ims):
                sh.paste(im.resize((Wd // 3, Ht // 3)), (j * Wd // 3, 0))
            sh.save(os.path.join(a.out, 'still.jpg'))
        return 0
    pi_, pn = [int(v) for v in a.part.split('/')]
    if pi_ == 0:
        meta = dict(renderer='crochetsim', fps=FPS, size=[Wd, Ht], dur=a.dur, reveal=a.reveal, frames='%04d.png',
                    plan=plan, pieces=[{k: v for k, v in p.items()} for p in pieces])
        tmp = os.path.join(a.out, 'plan.json.tmp')
        json.dump(meta, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False)
        os.replace(tmp, os.path.join(a.out, 'plan.json'))
    for k in range(NF * pi_ // pn, NF * (pi_ + 1) // pn):
        fn = os.path.join(a.out, '%04d.png' % k)
        if not os.path.exists(fn):
            Image.fromarray(render(k)).save(fn)
    return 0


if __name__ == '__main__':
    sys.exit(main())
