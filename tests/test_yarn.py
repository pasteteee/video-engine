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
    assert abs((g.az[-1] - 32.0) % 360) < 1e-6 or abs((g.az[-1] - 32.0) % 360 - 360) < 1e-6   # ends in the photo's view
    assert g.el[-1] == pytest.approx(12.0) and g.fov == 18.0
    x0, y0, x1, y1 = g.final_box()                          # the finished toy fills the box: 62% wide or 40% tall
    assert max((x1 - x0) / 108 / 0.62, (y1 - y0) / 192 / 0.40) == pytest.approx(1.0, abs=0.03)
    assert ((x0 + x1) / 2 / 108) == pytest.approx(0.5, abs=0.02) and ((y0 + y1) / 2 / 192) == pytest.approx(0.48, abs=0.02)
    h = Grow(TOY, (108, 192), dur=4.0, reveal=2.0, ss=1, view=dict(az=50.0, el=6.0), rest=5.0)
    assert h.k_rest == 150 and h.az[150] == pytest.approx(h.az[-1]) and h.el[-1] == pytest.approx(6.0)
    assert (h.az[-1] - 50.0) % 360 == pytest.approx(0.0, abs=1e-6) or (h.az[-1] - 50.0) % 360 == pytest.approx(360.0)
    assert (np.diff(h.az) >= -1e-9).all() and abs(np.diff(np.diff(h.az))).max() < 0.6
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps(TOY))
    out = tmp_path / "frames"
    assert main([str(spec), str(out), "--size", "108x192", "--dur", "2", "--reveal", "1", "--ss", "1",
                 "--frames", "0:2"]) == 0
    assert (out / "0000.png").exists() and (out / "0001.png").exists()
    plan = json.loads((out / "plan.json").read_text())
    assert len(plan["plan"]) == 90 and plan["renderer"] == "yarn"
    assert plan["final"]["az"] == 32.0 and not plan["final"]["matched"] and len(plan["final"]["box"]) == 4
    mtime = (out / "0000.png").stat().st_mtime_ns
    main([str(spec), str(out), "--size", "108x192", "--dur", "2", "--reveal", "1", "--ss", "1", "--frames", "0:1"])
    assert (out / "0000.png").stat().st_mtime_ns == mtime       # existing frames are kept


# ------------------------------------------------------------------------------------------- the photo's angle (match)
def _blob(shape, cx, cy, s):
    """A toy-like silhouette: a body, a head and two ears, centred at cx, cy, size s (pixels)."""
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    m = ((xx - cx) / (0.5 * s)) ** 2 + ((yy - cy - 0.25 * s) / (0.45 * s)) ** 2 < 1
    m |= (xx - cx) ** 2 + (yy - cy + 0.35 * s) ** 2 < (0.38 * s) ** 2
    for e in (-1, 1):
        m |= ((xx - cx - e * 0.45 * s) / (0.2 * s)) ** 2 + ((yy - cy + 0.45 * s) / (0.1 * s)) ** 2 < 1
    return m


def test_align_recovers_scale_and_shift():
    from vengine.yarn.match import align, iou, warp
    a = _blob((200, 200), 90, 110, 100)
    b = _blob((300, 260), 140, 160, 130)
    f = align(a, b)
    assert f["iou"] > 0.96 and f["s"] == pytest.approx(1.3, abs=0.04)
    assert iou(warp(a, f["s"], f["tx"], f["ty"], b.shape), b) == pytest.approx(f["iou"])


def test_toy_mask_keeps_the_toy_and_drops_its_shadow():
    from vengine.yarn.match import toy_mask
    H = W = 240
    yy, xx = np.mgrid[0:H, 0:W]
    bg = np.stack([246 + 6 * yy / H, 231 + 9 * yy / H, 216 + 12 * yy / H], -1)       # warm seamless backdrop
    img = bg.copy()
    from scipy.ndimage import gaussian_filter
    sh = ((xx - 150) / 70.0) ** 2 + ((yy - 200) / 18.0) ** 2 < 1                   # soft contact shadow
    k = gaussian_filter(sh.astype(float), 6)[..., None]
    img = img * (1 - k * (1 - np.array([0.82, 0.78, 0.72])))
    toy = _blob((H, W), 110, 120, 110)
    rng = np.random.default_rng(1)
    img[toy] = np.array([200, 30, 35]) + rng.normal(0, 18, (toy.sum(), 1))         # red yarn with texture
    m = toy_mask(img.clip(0, 255).astype(np.uint8), W)
    assert (m & toy).sum() / toy.sum() > 0.97
    assert (m & sh & ~toy).sum() / (sh & ~toy).sum() < 0.1
