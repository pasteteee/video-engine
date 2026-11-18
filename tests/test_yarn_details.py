"""vengine.yarn.details: face, felt, embroidery, appliques and ribbing on the yarn toy.  Needs numba, scipy, amikit."""
import json
import math
import os
import sys

import numpy as np
import pytest

pytest.importorskip("numba")
pytest.importorskip("scipy")


def _amikit():
    root = os.environ.get('AMIKIT', '/home/user')
    if os.path.isdir(os.path.join(root, 'amikit')):
        sys.path.insert(0, root)
        return root
    return None


pytestmark = pytest.mark.skipif(_amikit() is None, reason="amikit not found (set AMIKIT)")

TOY = {
    "name": "face_ball", "yarn": {"thickness_mm": 1.9, "stitch_mm": 4.0, "round_mm": 3.6},
    "colours": {"white": "#fbf9f4", "red": "#d8333b", "amber": "#e0a226", "black": "#161313", "pink": "#f4a9a6",
                "brown": "#4a2c22"},
    "parts": [
        {"id": "ball", "rounds": ["mr 6", "inc 6 to 36", "even 6", "dec 6 to 6"], "colour": "white"},
        {"id": "collar", "rounds": ["ring 30", "rib 30 x1"], "colour": "red", "end": "open", "stuff": "none"},
        {"id": "star", "colour": "white", "motif": {"kind": "star", "points": 5, "length": 3}},
    ],
    "assembly": [
        {"part": "ball", "axis": [0, 1, 0]},
        {"part": "collar", "on": "ball", "at": {"round": 10}, "around": True, "dir": [0, -1, 0]},
        {"part": "star", "on": "ball", "at": {"round": 9, "az": 60}, "applique": True, "lift": 1.0},
    ],
    "face": [
        {"type": "felt", "on": "ball", "at": {"round": 6, "az": 22}, "size_mm": [9, 8], "colour": "amber", "mirror": True},
        {"type": "satin", "on": "ball", "at": {"round": 6, "az": 22}, "width_mm": 5, "height_mm": 2, "colour": "black",
         "thickness_mm": 1.0, "lift_mm": 0.6, "mirror": True},
        {"type": "satin", "on": "ball", "at": {"round": 8, "az": 0}, "width_mm": 5, "height_mm": 3.5, "colour": "brown",
         "thickness_mm": 1.2},
        {"type": "stitch", "on": "ball", "points": [[9, -12], [9.5, 0], [9, 12]], "colour": "brown", "thickness_mm": 1.0},
        {"type": "blush", "on": "ball", "at": {"round": 8, "az": 40}, "colour": "pink", "size_mm": 8},
        {"type": "sparkle", "on": "ball", "at": {"round": 4, "az": 0}},
    ],
}


@pytest.fixture(scope="module")
def toy():
    from vengine.yarn.toy import toy_yarn
    return toy_yarn(json.loads(json.dumps(TOY)))


def _cam(X, az=0.0, el=8.0, dist=2.6):
    from vengine.yarn.render import Camera
    lo, hi = X.min(0), X.max(0)
    g = (lo + hi) / 2
    R = float(np.linalg.norm(hi - lo)) / 2
    a, e = math.radians(az), math.radians(el)
    return Camera(g + np.array([math.sin(a) * math.cos(e), math.sin(e), math.cos(a) * math.cos(e)]) * R * dist, g, fov=30)


def test_every_face_item_and_applique_is_built(toy, capsys):
    X, D, C, pal, d, t = toy
    det = t.details
    # 2 felt + 2 pupils + nose + mouth + the star; the blush dyes yarn; the unknown type is reported, not dropped
    assert len(det.items) == 7
    assert {int(it['row'][1]) for it in det.items} == {0, 1, 2, 3}
    names = [p['part'] for p in t.yarn_pieces]
    assert 'star' not in names                               # sewn on flat: a detail, not rounds of yarn
    from vengine.yarn.toy import toy_yarn
    toy_yarn(json.loads(json.dumps(TOY)))
    assert "'sparkle'" in capsys.readouterr().err


def test_details_rest_on_the_yarn(toy):
    """The felt eyes sit on the tops of the stitches: not floating off the yarn, not sunk into it."""
    X, D, C, pal, d, t = toy
    it = t.details.items[1]                                  # first felt eye (item 0 is the star)
    n0 = it['row'][12:15]
    V = it['V']
    above = 3.0 - t.details.envelope(V - n0 * 3.0, n0)       # height of each vertex over the yarn top under it
    assert np.isfinite(above).mean() > 0.9
    assert -0.6 < np.nanmedian(above) < 2.5                 # felt 1 mm thick on the tops of the stitches


def test_ribbing_makes_posts_two_rounds_tall(toy):
    X, D, C, pal, d, t = toy
    p = next(q for q in t.yarn_pieces if q['part'] == 'collar')
    seg = X[p['start']:p['end']]
    assert len(seg) > 30 * 20                                # a post per stitch, not one plain round
    red = pal.index(next(c for c in pal if abs(c[0] - 0xd8 / 255) < 1e-6))
    assert (C[p['start']:p['end']] == red).all()


def test_render_draws_details_and_is_deterministic(toy):
    from vengine.yarn.render import Renderer
    X, D, C, pal, d, t = toy
    rn = Renderer(160, 160, ss=2, r=d / 2 / 1.2, soft=1.2, palette=pal)
    rn.set_scene(X)
    cam = _cam(X)
    a = rn.render(X, D, cam, colnode=C, spheres=t.spheres, details=t.details)
    b = rn.render(X, D, cam, colnode=C, spheres=t.spheres, details=t.details)
    assert np.array_equal(a, b)
    assert (rn.idb == 4).mean() > 0.01
    img = a.astype(int)
    amber = (img[..., 0] > 150) & (img[..., 1] > 90) & (img[..., 2] < 90) & (img[..., 0] - img[..., 2] > 100)
    assert amber.sum() > 20                                  # the felt eyes are there, in their own colour
    hidden = rn.render(X, D, cam, colnode=C, spheres=t.spheres, details=t.details, details_t=0.0)
    assert not (rn.idb == 4).any() and not np.array_equal(hidden, a)


def test_reveal_is_gradual(toy):
    det = toy[5].details
    assert det.frame(0.0) is None
    n = [len(det.frame(t)[3]) for t in (0.3, 0.6, 1.0)]
    assert n[0] < n[1] <= n[2]


def test_details_do_not_crawl_when_the_camera_turns(toy):
    """A fifth-of-a-pixel turn changes the face smoothly (second difference small, like the yarn's)."""
    from vengine.yarn.render import Renderer
    from vengine.yarn.stable import second_diff
    X, D, C, pal, d, t = toy
    rn = Renderer(160, 160, ss=2, r=d / 2 / 1.2, soft=1.2, palette=pal)
    rn.set_scene(X)
    fr = [rn.render(X, D, _cam(X, 10 + 0.05 * k), colnode=C, spheres=t.spheres, details=t.details) for k in range(5)]
    fy = [rn.render(X, D, _cam(X, 10 + 0.05 * k), colnode=C, spheres=t.spheres) for k in range(5)]
    assert second_diff(fr) <= second_diff(fy) * 1.15 + 0.05
