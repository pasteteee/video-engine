"""vengine.yarn: the crochet yarn renderer.  Needs numba + scipy (requirements-yarn.txt); amikit for the toy tests."""
import json
import math
import os
import sys

import numpy as np
import pytest

pytest.importorskip("numba")
pytest.importorskip("scipy")

from vengine.yarn.render import Camera, Renderer, downsample  # noqa: E402
from vengine.yarn.stable import second_diff  # noqa: E402


def _coil(n=700, h=0.5):
    """A flat spiral of yarn, h apart along its length (like the first rounds of a piece)."""
    s = np.arange(n) * h
    th = np.sqrt(s * 4.0)
    rad = 1.0 + 0.55 * th
    X = np.stack([rad * np.cos(th), rad * np.sin(th), np.zeros(n)], 1)
    T = np.gradient(X, axis=0)
    T /= np.linalg.norm(T, axis=1)[:, None]
    D = np.cross(T, [0.0, 0.0, 1.0])
    D /= np.linalg.norm(D, axis=1)[:, None] + 1e-12
    return X, D


def _cam(az=0.0):
    a = math.radians(az)
    return Camera([18 * math.sin(a), -40.0, 60.0 * math.cos(a)], [0.0, 0.0, 0.0], up=(0, 1, 0), fov=40)


@pytest.fixture(scope="module")
def rn():
    r = Renderer(96, 96, ss=2, r=0.75, palette=[[0.85, 0.2, 0.25], [0.2, 0.5, 0.9]])
    X, _ = _coil()
    r.set_scene(X)
    return r


def test_draws_yarn_and_is_deterministic(rn):
    X, D = _coil()
    a = rn.render(X, D, _cam())
    b = rn.render(X, D, _cam())
    assert a.shape == (96, 96, 3) and a.dtype == np.uint8
    assert np.array_equal(a, b)
    bg = np.array([0.975, 0.955, 0.93]) * 255
    assert (np.abs(a.astype(float) - bg).sum(2) > 60).mean() > 0.05   # the yarn covers part of the frame


def test_colour_follows_the_yarn(rn):
    """The second half of the yarn is blue: blue pixels appear, and only where that half is."""
    X, D = _coil()
    col = np.zeros(len(X), np.int32)
    col[len(X) // 2:] = 1
    img = rn.render(X, D, _cam(), colnode=col).astype(int)
    blue = (img[..., 2] > img[..., 0] + 30).mean()
    red = (img[..., 0] > img[..., 2] + 30).mean()
    assert blue > 0.01 and red > 0.01
    only_red = rn.render(X[:len(X) // 2], D[:len(X) // 2], _cam(), colnode=col[:len(X) // 2]).astype(int)
    assert (only_red[..., 2] > only_red[..., 0] + 30).mean() == 0


def test_tapered_tip_draws_nothing_at_zero_radius(rn):
    X, D = _coil()
    empty = rn.render(X, D, _cam(), radius=np.zeros(len(X)))
    bg = rn.render(X[:2], D[:2], _cam(), radius=np.zeros(2))
    assert np.array_equal(empty, bg)


def test_small_camera_steps_change_the_picture_smoothly(rn):
    """A turn of a twentieth of a degree per frame: the second difference stays small next to the change itself."""
    X, D = _coil()
    fr = [rn.render(X, D, _cam(0.05 * k)) for k in range(5)]
    first = np.mean([np.abs(fr[i + 1].astype(float) - fr[i]).mean() for i in range(4)])
    assert second_diff(fr) < 0.8 * first + 0.05


def test_gaussian_downsample_keeps_flat_colour():
    img = np.full((12, 18, 3), 0.4, np.float32)
    out = downsample(img, 3, 0.5)
    assert out.shape == (4, 6, 3)
    assert np.allclose(out, 0.4, atol=1e-5)


def _amikit():
    root = os.environ.get("AMIKIT", "/home/user")
    if root not in sys.path:
        sys.path.insert(0, root)
    try:
        import amikit.toy  # noqa: F401
    except Exception:
        return None
    return root


TOY = {
    "name": "stripe_ball", "yarn": {"thickness_mm": 1.9},
    "colours": {"white": "#fbf9f4", "red": "#d8333b"},
    "parts": [{"id": "ball", "rounds": ["mr 6", "inc 6 to 24", "even 4", "dec 6 to 6"], "colour": "white",
               "colours": [{"rounds": [6, 7], "colour": "red"}]}],
    "assembly": [{"part": "ball", "axis": [0, 1, 0]}],
}


@pytest.mark.skipif(_amikit() is None, reason="amikit not found (set AMIKIT)")
def test_toy_colour_zones_reach_the_yarn():
    from vengine.yarn.toy import toy_yarn
    X, D, C, pal, d, toy = toy_yarn(TOY)
    assert len(pal) == 2 and set(np.unique(C)) == {0, 1}
    p = toy.yarn_pieces[0]
    red = np.where(C[p['start']:p['end']] == 1)[0]
    # the red rounds are one band of the yarn, worked after the white rounds 1-5
    assert red.min() > 0.3 * (p['end'] - p['start'])
    assert red.max() - red.min() < 0.6 * (p['end'] - p['start'])


@pytest.mark.skipif(_amikit() is None, reason="amikit not found (set AMIKIT)")
def test_grow_plan_and_camera_are_smooth(tmp_path):
    from vengine.yarn.grow import Grow, main
    g = Grow(TOY, (108, 192), dur=4.0, reveal=2.0, ss=1)
    assert len(g.plan) == g.NF == 180
    assert all(b['s'] >= a['s'] for a, b in zip(g.plan, g.plan[1:]))
    v = np.diff(g.az)
    assert (v >= -1e-9).all()                                # always turning the same way
    assert abs(np.diff(v)).max() < 0.6                       # no jumps in speed
    assert abs(g.az[-1] % 360) < 1e-6 or abs(g.az[-1] % 360 - 360) < 1e-6   # ends facing the viewer
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps(TOY))
    out = tmp_path / "frames"
    assert main([str(spec), str(out), "--size", "108x192", "--dur", "2", "--reveal", "1", "--ss", "1",
                 "--frames", "0:2"]) == 0
    assert (out / "0000.png").exists() and (out / "0001.png").exists()
    plan = json.loads((out / "plan.json").read_text())
    assert len(plan["plan"]) == 90 and plan["renderer"] == "yarn"
    mtime = (out / "0000.png").stat().st_mtime_ns
    main([str(spec), str(out), "--size", "108x192", "--dur", "2", "--reveal", "1", "--ss", "1", "--frames", "0:1"])
    assert (out / "0000.png").stat().st_mtime_ns == mtime       # existing frames are kept


def test_sc_is_a_short_wide_v():
    """The front of a sc reads as a plump V wider than tall (about 1.3 on a real toy), not a long knit-like leaf."""
    from vengine.yarn.toy import SC
    front = [(dv, du) for k, dv, du, nn in SC if nn > 0.2]
    rnd, st = 3.6, 4.0                                      # round height and stitch width, mm (amikit default)
    width = (max(du for _, du in front) - min(du for _, du in front)) / 2 * st
    height = (max(dv for dv, _ in front) - min(dv for dv, _ in front)) * rnd
    assert 1.2 <= width / height <= 1.6


def test_yarn_width_follows_the_stitch():
    from vengine.yarn.toy import yarn_width
    assert yarn_width({'stitch_mm': 4.0, 'thickness_mm': 1.9}) == pytest.approx(2.32)
    assert yarn_width({'stitch_mm': 2.0, 'thickness_mm': 1.9}) == 1.9


def test_magic_ring_is_a_closed_circle():
    """Rounds 1-2 of a flat circle: the tops of the stitches lie on one even circle (no star or flower points)."""
    from vengine.yarn.toy import _FlatDisc, piece_yarn
    disc = _FlatDisc(np.zeros(3), np.array([0.0, 0.0, 1.0]), np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0]),
                     12.0, 12.0, 4)
    X, sid = piece_yarn(disc, 0.0, 2.3, with_stitch=True)
    top = []
    for q in np.unique(sid[sid // 100000 == 2]):
        P = X[sid == q]
        top.append(np.linalg.norm(P[:, :2], axis=1).max())
    top = np.array(top[:-1])                               # the last one runs on into round 3
    assert top.std() / top.mean() < 0.06
