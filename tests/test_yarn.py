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


# --- light, material and set (studio look) -------------------------------------------------------------------------

def test_srgb_round_trip():
    from vengine.yarn.render import _lin, _srgb
    for c in (0.0, 0.02, 0.2, 0.5, 0.8, 0.97, 1.0):
        assert abs(_srgb(_lin(c)) - c) < 1e-6
    assert abs(_lin(0.5) - 0.214) < 0.002              # mid grey is ~21% of the light, not 50%


def _dome(n=2600, h=0.5, R=8.0):
    """A dome of yarn coiled round and up (like the top of a head), resting on y = 0."""
    s = np.arange(n) * h
    turns = s / (2 * np.pi * R)
    th = 2 * np.pi * turns
    phi = np.clip(turns * 1.6 / R * 1.0, 0, np.pi / 2 * 0.98)
    X = np.stack([R * np.cos(phi) * np.cos(th), R * np.sin(phi) + 0.8, R * np.cos(phi) * np.sin(th)], 1)
    T = np.gradient(X, axis=0)
    T /= np.linalg.norm(T, axis=1)[:, None]
    D = np.cross(T, [0.0, 1.0, 0.0])
    D /= np.linalg.norm(D, axis=1)[:, None] + 1e-12
    return X, D


def test_white_yarn_stays_white_and_matte():
    """Off-white yarn under the studio light reads white (as on the photo), not grey with white glints."""
    X, D = _dome()
    rn = Renderer(160, 160, ss=2, r=0.8, palette=[[0.969, 0.949, 0.918]])     # #f7f2ea
    rn.set_scene(X)
    cam = Camera([0.0, 9.0, 34.0], [0.0, 3.5, 0.0], fov=40)
    img = rn.render(X, D, cam).astype(float)
    from scipy.ndimage import binary_erosion
    yarn = binary_erosion(rn.idb.reshape(160, 2, 160, 2).min(axis=(1, 3)) == 1, iterations=3)
    lum = img[yarn] @ [0.3, 0.59, 0.11]
    p5, p50, p95 = np.percentile(lum, [5, 50, 95])
    assert p50 > 225, p50                               # was ~150 before the linear-light pipeline
    assert p95 < 254.5                                  # no clipped glints
    assert p5 > 165, p5                                 # crevices stay light, in the yarn's colour


def test_red_shade_deepens_in_its_dye():
    """A red yarn in shade gets darker red, not grey or brown: the hue holds."""
    X, D = _dome()
    rn = Renderer(160, 160, ss=2, r=0.8, palette=[[0.784, 0.196, 0.227]])     # #c8323a
    rn.set_scene(X)
    img = rn.render(X, D, Camera([0.0, 9.0, 34.0], [0.0, 3.5, 0.0], fov=40)).astype(float)
    from scipy.ndimage import binary_erosion
    yarn = binary_erosion(rn.idb.reshape(160, 2, 160, 2).min(axis=(1, 3)) == 1, iterations=3)   # away from the outline
    px = img[yarn]
    dark = px[px[:, 0] < np.percentile(px[:, 0], 15)]
    assert (dark[:, 0] > 2.2 * dark[:, 1]).all()


def test_floor_takes_a_soft_contact_shadow():
    """With no backdrop_y the floor sits under the scene: right under the yarn it is darker than the open set."""
    X, D = _dome()
    rn = Renderer(160, 160, ss=2, r=0.8, palette=[[0.969, 0.949, 0.918]])
    rn.set_scene(X)
    assert abs(rn.plane_p[1] - (X[:, 1].min() - 0.9 * rn.r * rn.soft)) < 1e-9
    img = rn.render(X, D, Camera([0.0, 9.0, 34.0], [0.0, 3.5, 0.0], fov=40)).astype(float)
    bg = (rn.idb[::2, ::2][:160, :160] == 0)
    lum = img @ [0.3, 0.59, 0.11]
    rows = np.where((rn.idb[::2, ::2][:160, :160] == 1).any(1))[0]
    below = lum[rows.max() + 2:rows.max() + 6, 60:100][bg[rows.max() + 2:rows.max() + 6, 60:100]]
    open_set = lum[150:158, 2:20]
    assert below.mean() < open_set.mean() - 8
    off = Renderer(160, 160, ss=2, r=0.8, palette=[[0.969, 0.949, 0.918]], shadow_floor=0.0)
    off.set_scene(X)
    im2 = off.render(X, D, Camera([0.0, 9.0, 34.0], [0.0, 3.5, 0.0], fov=40)).astype(float)
    assert np.abs(im2 @ [0.3, 0.59, 0.11] - lum)[bg].max() > 8      # the shadow is the floor's doing
