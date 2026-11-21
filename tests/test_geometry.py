import numpy as np
import pytest

from face_engine.geometry import head_angles, rotation_from_angles, umeyama


def test_umeyama_recovers_similarity():
    rng = np.random.default_rng(1)
    src = rng.normal(size=(10, 3))
    rot = rotation_from_angles(30, -12, 7)
    dst = 2.5 * src @ rot.T + np.array([1.0, -2.0, 3.0])
    sim = umeyama(src, dst)
    assert sim.scale == pytest.approx(2.5)
    np.testing.assert_allclose(sim.rotation, rot, atol=1e-9)
    np.testing.assert_allclose(sim.apply(src), dst, atol=1e-9)


def test_umeyama_never_returns_reflection():
    rng = np.random.default_rng(2)
    src = rng.normal(size=(8, 3))
    sim = umeyama(src, src * np.array([-1.0, 1.0, 1.0]))
    assert np.linalg.det(sim.rotation) == pytest.approx(1.0)


@pytest.mark.parametrize("bad", [np.zeros((5, 3)), np.ones((2, 3))])
def test_umeyama_rejects_degenerate_input(bad):
    with pytest.raises(ValueError):
        umeyama(bad, bad)


@pytest.mark.parametrize("angles", [(0, 0, 0), (35, 0, 0), (0, -20, 0), (0, 0, 15), (25, 10, -8)])
def test_head_angles_roundtrip(angles):
    assert head_angles(rotation_from_angles(*angles)) == pytest.approx(angles, abs=1e-9)


def test_head_angle_sign_conventions():
    # Turning toward the subject's left moves the nose toward image right (+x).
    assert (rotation_from_angles(30, 0, 0) @ [0, 0, 1])[0] > 0
    # Positive pitch lifts the nose (+y).
    assert (rotation_from_angles(0, 20, 0) @ [0, 0, 1])[1] > 0
    # Positive roll lifts the subject's left side (+x side) of the head.
    assert (rotation_from_angles(0, 0, 10) @ [1, 0, 0])[1] > 0
