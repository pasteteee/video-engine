"""Re-time an old shot list (and shorts plan) to a new voice, using the old->new anchor map
written by assemble_inserts.py (05_voice/timemap.json). Linear inside each line or insert.

    python retime_from_map.py EPISODE OLD_SHOTLIST.json [OLD_SHORTS.json]
Writes 04_shots/shotlist.json and 06_render/shorts/shorts.json in EPISODE.
"""
import json, bisect, sys
EP, OLD_SL = sys.argv[1], sys.argv[2]; OLD_SH = sys.argv[3] if len(sys.argv) > 3 else None
A = sorted(set(tuple(a) for a in json.load(open(f'{EP}/05_voice/timemap.json'))))
xs = [a[0] for a in A]; ys = [a[1] for a in A]
def M(t):
    i = max(0, min(bisect.bisect_right(xs, t) - 1, len(xs) - 2))
    x0, x1, y0, y1 = xs[i], xs[i + 1], ys[i], ys[i + 1]
    return y0 + (t - x0) * (y1 - y0) / (x1 - x0) if x1 > x0 else y0
r = lambda v: round(v, 3)
S = json.load(open(OLD_SL))
for s in S['shots']:
    a = s['params']['start_s']; b = a + s['duration_s']
    s['params']['start_s'] = r(M(a)); s['duration_s'] = r(M(b) - M(a))
json.dump(S, open(f'{EP}/04_shots/shotlist.json', 'w'), indent=1)
if OLD_SH:
    H = json.load(open(OLD_SH))
    for sh in H['shorts']:
        a0 = sh['start_s']; n0 = M(a0)
        for v in sh['shots']:
            a = a0 + v['start_s']; b = a + v['duration_s']
            v['start_s'] = r(M(a) - n0); v['duration_s'] = r(M(b) - M(a))
        sh['start_s'] = r(n0); sh['end_s'] = r(M(sh['end_s']))
    json.dump(H, open(f'{EP}/06_render/shorts/shorts.json', 'w'), indent=1)
print('end', r(S['shots'][-1]['params']['start_s'] + S['shots'][-1]['duration_s']))
