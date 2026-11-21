"""Synthetic landmarks with known ground truth, for tests and demos.

Faces start from the canonical neutral face; named "expression primitives"
move specific points by amounts matching the engine's full-scale constants,
so ``{"smile": 1.0}`` should read back as AU12 close to 1.
"""

from __future__ import annotations

from typing import Callable, Mapping

import numpy as np

from face_engine.geometry import rotation_from_angles
from face_engine.topology import BODY_INDEX, BODY_POINTS, CANONICAL_FACE, FACE_INDEX, HAND_NUM_POINTS
from face_engine.observations import FrameObservation, Hand


def _move(pts: np.ndarray, names: tuple[str, ...], delta: tuple[float, float, float], a: float) -> None:
    for n in names:
        pts[FACE_INDEX[n]] += a * np.asarray(delta)


def _lids(side: str) -> tuple[str, str, str, str]:
    return tuple(f"{side}_lid_{k}" for k in ("up1", "up2", "lo1", "lo2"))  # type: ignore[return-value]


def _close_eye(pts: np.ndarray, side: str, a: float) -> None:
    up1, up2, lo1, lo2 = (FACE_INDEX[n] for n in _lids(side))
    for up, lo in ((up1, lo1), (up2, lo2)):
        pts[up, 1] -= a * (pts[up, 1] - pts[lo, 1])


def _apply(pts: np.ndarray, name: str, a: float) -> None:
    both = ("r", "l")
    if name == "brow_raise":
        for s in both:
            _move(pts, (f"{s}_brow_inner", f"{s}_brow_mid", f"{s}_brow_outer"), (0, 0.10, 0), a)
    elif name == "brow_inner_raise":
        _move(pts, ("r_brow_inner", "l_brow_inner"), (0, 0.10, 0), a)
    elif name == "brow_lower":
        _move(pts, ("r_brow_inner",), (0.035, -0.07, 0), a)
        _move(pts, ("l_brow_inner",), (-0.035, -0.07, 0), a)
    elif name == "eye_widen":
        for s in both:
            _move(pts, (f"{s}_lid_up1", f"{s}_lid_up2"), (0, 0.037, 0), a)
    elif name in ("blink", "wink_l", "wink_r"):
        for s in both if name == "blink" else (name[-1],):
            _close_eye(pts, s, a)
    elif name == "cheek_raise":
        for s in both:
            _move(pts, (f"{s}_lid_lo1", f"{s}_lid_lo2"), (0, 0.03, 0), a)
    elif name in ("smile", "smile_l", "smile_r"):
        sides = both if name == "smile" else (name[-1],)
        for s in sides:
            out = 0.04 if s == "l" else -0.04
            _move(pts, (f"{s}_mouth_corner",), (out, 0.08, 0), a)
    elif name == "frown":
        _move(pts, ("r_mouth_corner", "l_mouth_corner"), (0, -0.06, 0), a)
    elif name == "jaw_drop":
        _move(pts, ("chin",), (0, -0.35, 0), a)
        _move(pts, ("lower_lip_inner", "lower_lip_bottom"), (0, -0.25, 0), a)
        _move(pts, ("r_mouth_corner", "l_mouth_corner"), (0, -0.125, 0), a)
    elif name == "lip_press":
        _move(pts, ("upper_lip_top",), (0, -0.04, 0), a)
        _move(pts, ("lower_lip_bottom",), (0, 0.04, 0), a)
    elif name == "nose_wrinkle":
        _move(pts, ("r_alar", "l_alar"), (0, 0.05, 0), a)
    elif name == "upper_lip_raise":
        _move(pts, ("upper_lip_top", "upper_lip_inner"), (0, 0.06, 0), a)
    elif name == "gaze_h":
        _move(pts, ("r_iris", "l_iris"), (0.2054, 0, 0), a)
    elif name == "gaze_v":
        _move(pts, ("r_iris", "l_iris"), (0, 0.2054, 0), a)
    else:
        raise ValueError(f"unknown expression primitive: {name}")


def synthetic_face(
    expression: Mapping[str, float] | None = None,
    yaw: float = 0.0,
    pitch: float = 0.0,
    roll: float = 0.0,
    iod_px: float = 120.0,
    center: tuple[float, float, float] = (640.0, -360.0, 0.0),
    identity: np.ndarray | None = None,
    noise_px: float = 0.0,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Face points in the internal frame (pixels) for a given expression and pose.

    ``identity`` is an optional (K, 3) offset in IOD units that gives the face
    a personal morphology (e.g. naturally low brows) to exercise baselines.
    """
    pts = CANONICAL_FACE.copy()
    if identity is not None:
        pts += identity
    for name, amount in (expression or {}).items():
        _apply(pts, name, amount)
    rot = rotation_from_angles(yaw, pitch, roll)
    out = iod_px * pts @ rot.T + np.asarray(center)
    if noise_px:
        out += (rng or np.random.default_rng(0)).normal(0.0, noise_px, out.shape)
    return out


def random_identity(rng: np.random.Generator, scale: float = 0.03) -> np.ndarray:
    """Smooth, symmetric personal morphology offsets in IOD units."""
    offsets = rng.normal(0.0, scale, CANONICAL_FACE.shape)
    for name in FACE_INDEX:
        if name.startswith("l_"):
            mirror = offsets[FACE_INDEX["r_" + name[2:]]]
            offsets[FACE_INDEX[name]] = mirror * np.array([-1.0, 1.0, 1.0])
        elif not name.startswith("r_"):
            offsets[FACE_INDEX[name], 0] = 0.0
    return offsets


# ----------------------------------------------------------------- body
_REST_BODY = {
    "nose": (0.0, 0.9), "l_ear": (0.25, 0.95), "r_ear": (-0.25, 0.95),
    "mouth_l": (0.08, 0.8), "mouth_r": (-0.08, 0.8),
    "l_shoulder": (0.5, 0.0), "r_shoulder": (-0.5, 0.0),
    "l_hip": (0.35, -1.5), "r_hip": (-0.35, -1.5),
}

POSTURES: dict[str, dict[str, tuple[float, float]]] = {
    "rest": {"l_wrist": (0.6, -1.5), "r_wrist": (-0.6, -1.5)},
    "open": {"l_wrist": (1.3, -0.6), "r_wrist": (-1.3, -0.6)},
    "crossed": {"l_wrist": (-0.4, -0.7), "r_wrist": (0.4, -0.75)},
    "face_touch": {"l_wrist": (0.6, -1.5), "r_wrist": (-0.05, 0.62)},
    "hands_joined": {"l_wrist": (0.06, -0.8), "r_wrist": (-0.06, -0.8)},
    "raised": {"l_wrist": (0.9, 0.5), "r_wrist": (-0.9, 0.5)},
}


def synthetic_hand(side: str, palm_to_camera: bool, wrist: np.ndarray, size: float) -> np.ndarray:
    """21 hand points, fingers up.

    Right hand, palm to camera: the thumb points toward the body midline (+x).
    """
    # Layout below has the thumb at -x; it is mirrored where needed.
    base_x = {1: -0.35, 5: -0.2, 9: 0.0, 13: 0.18, 17: 0.33}
    pts = np.zeros((HAND_NUM_POINTS, 3))
    for root, x in base_x.items():
        for j in range(4):
            pts[root + j] = (x * (1 + 0.15 * j), 0.45 + 0.2 * j if root != 1 else 0.1 + 0.15 * j, 0)
    mirror = (side == "r") == palm_to_camera
    if mirror:
        pts[:, 0] *= -1
    return wrist + size * pts


def synthetic_body(
    posture: str | Mapping[str, tuple[float, float]] = "rest",
    sw_px: float = 200.0,
    center: tuple[float, float] = (640.0, -500.0),
    scale: float = 1.0,
    with_hands: bool = True,
    palms_to_camera: bool = False,
) -> tuple[np.ndarray, np.ndarray, list[Hand]]:
    """Body points (internal frame, pixels), visibility and hands for a posture."""
    layout = dict(_REST_BODY)
    layout.update(POSTURES[posture] if isinstance(posture, str) else posture)
    for s, sx in (("l", 0.5), ("r", -0.5)):
        wx, wy = layout[f"{s}_wrist"]
        layout[f"{s}_elbow"] = ((sx + wx) / 2 + 0.15 * np.sign(sx), (0.0 + wy) / 2 - 0.1)
        layout[f"{s}_index"] = (wx, wy + 0.15)
    sw = sw_px * scale
    pts = np.zeros((len(BODY_POINTS), 3))
    for name, (x, y) in layout.items():
        pts[BODY_INDEX[name]] = (center[0] + sw * x, center[1] + sw * y, 0.0)
    vis = np.ones(len(BODY_POINTS))
    hands = []
    if with_hands:
        for s in ("l", "r"):
            wrist = pts[BODY_INDEX[f"{s}_wrist"]]
            hands.append(Hand(synthetic_hand(s, palms_to_camera, wrist, 0.35 * sw), side=s))
    return pts, vis, hands


def synthetic_clip(
    n_frames: int,
    fps: float,
    face_fn: Callable[[int], np.ndarray | None] | None = None,
    body_fn: Callable[[int], tuple[np.ndarray, np.ndarray, list[Hand]] | None] | None = None,
) -> list[FrameObservation]:
    frames = []
    for i in range(n_frames):
        body = body_fn(i) if body_fn else None
        frames.append(
            FrameObservation(
                index=i,
                time_s=i / fps,
                face=face_fn(i) if face_fn else None,
                body=body[0] if body else None,
                body_visibility=body[1] if body else None,
                hands=body[2] if body else [],
            )
        )
    return frames
