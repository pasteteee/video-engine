"""One single-crochet stitch as a tileable height map (1 stitch wide, 1 round tall, as amikit's stitch UVs):
two plump V legs, each a twisted 4-ply strand with fine fibres, deep grooves between stitches and rounds.
Writes stitch_h.png (16-bit height), stitch_ao.png (cavity) and stitch_ply.png (ply shading) next to it."""
import numpy as np
from PIL import Image

S = 512
rng = np.random.default_rng(7)
u, v = np.meshgrid((np.arange(S) + 0.5) / S, (np.arange(S) + 0.5) / S, indexing='xy')
v = 1 - v                                     # image row 0 is the top of the stitch (v = 1)


def leg(u, v, x0, y0, x1, y1, r, twist):
    """A yarn leg from (x0, y0) to (x1, y1): height profile, along-leg param s, across-leg param t."""
    d = np.array([x1 - x0, y1 - y0]); Lg = np.hypot(*d); d = d / Lg
    px, py = u - x0, v - y0
    s = (px * d[0] + py * d[1]) / Lg
    t = (-px * d[1] + py * d[0]) / r
    # plump in the middle, a bit thinner where it dives under the next round
    sc = np.clip(s, 0, 1)
    rr = 1.0 - 0.25 * (np.abs(sc - 0.5) * 2) ** 2
    q = np.clip(1 - (t / rr) ** 2, 0, 1)
    end = np.clip(np.minimum(s + 0.08, 1.08 - s) / 0.16, 0, 1)
    h = np.sqrt(q) * end * (0.75 + 0.25 * np.sin(np.pi * sc))
    ply = 0.5 + 0.5 * np.cos(2 * np.pi * (s * Lg * twist + t * 0.55))      # 4 plies twisted along the leg
    return h, ply, q > 0


H = np.zeros_like(u); P = np.zeros_like(u)
for du in (-1, 0, 1):
    for dv in (-1, 0, 1):
        uu, vv = u - du, v - dv
        for (x0, y0, x1, y1) in ((0.5, -0.04, 0.02, 1.0), (0.5, -0.04, 0.98, 1.0)):
            h, ply, m = leg(uu, vv, x0, y0, x1, y1, 0.29, 6.0)
            take = h > H
            H = np.where(take, h, H); P = np.where(take, ply, P)
        # the round's top chain: a soft horizontal ridge where the V legs start (back loops seen as a bar)
        bar = np.clip(1 - ((vv - 1.0) / 0.09) ** 2, 0, 1) ** 0.5 * 0.35
        H = np.maximum(H, bar)
# ply relief: plies stand out of the leg a little
Hp = H * (0.86 + 0.14 * P)
# fibres: fine directional noise along the plies
n = rng.normal(size=(S // 4, S // 4))
fib = np.array(Image.fromarray(((n - n.min()) / np.ptp(n) * 255).astype(np.uint8)).resize((S, S), Image.BICUBIC)) / 255.0
Hp = Hp + 0.03 * (fib - 0.5) * (H > 0.05)
Hp = np.clip(Hp, 0, None); Hp /= Hp.max()
Image.fromarray((Hp * 65535).astype(np.uint16)).save('/home/user/work/b3d/stitch_h.png')
# cavity: dark between the legs and rounds, light on the plies' crowns
ao = np.clip(0.25 + 0.95 * np.sqrt(np.clip(H, 0, 1)), 0, 1) * (0.9 + 0.1 * P)
Image.fromarray((ao * 255).astype(np.uint8)).save('/home/user/work/b3d/stitch_ao.png')
print('ok', H.mean().round(3))
