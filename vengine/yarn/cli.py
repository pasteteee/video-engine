"""python -m vengine yarn <command> ...

  grow   SPEC.json OUTDIR [--size WxH] [--dur S] [--reveal S] [--frames a:b | --part i/n] [--still t1,t2]
         growth-shot frames OUTDIR/%04d.png + OUTDIR/plan.json (existing frames are skipped)
  still  SPEC.json OUT.png [--size N] [--views front,34,back]   look check of the finished toy
  probe  SPEC.json OUTDIR [--size WxH]                          frame-to-frame flicker numbers (stable.py)
"""
from __future__ import annotations

import argparse
import sys


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if not argv or argv[0] in ('-h', '--help'):
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == 'grow':
        from .grow import main as grow_main
        return grow_main(rest)
    if cmd == 'probe':
        from .stable import main as probe_main
        return probe_main(rest)
    if cmd == 'still':
        ap = argparse.ArgumentParser(prog='vengine yarn still')
        ap.add_argument('spec'); ap.add_argument('out'); ap.add_argument('--size', type=int, default=900)
        ap.add_argument('--views', default='front,34,back'); ap.add_argument('--rmax', type=int); ap.add_argument('--parts')
        a = ap.parse_args(rest)
        from .toy import still
        print(still(a.spec, a.out, a.size, a.views, a.rmax, a.parts))
        return 0
    print(__doc__)
    return 2
