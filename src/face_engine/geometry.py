"""Small linear-algebra helpers: similarity alignment and head-pose angles."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Similarity:
    """Transform ``y = scale * R @ x + t`` mapping source points onto a target."""

    scale: float
    rotation: np.ndarray  # (3, 3)
    translation: np.ndarray  # (3,)

    def apply(self, points: np.ndarray) -> np.ndarray:
        return self.scale * points @ self.rotation.T + self.translation


def umeyama(src: np.ndarray, dst: np.ndarray) -> Similarity:
    """Least-squares similarity transform from ``src`` to ``dst`` (Umeyama 1991).

    Both arrays are (N, 3) with N >= 3 non-collinear points.
    """
    if src.shape != dst.shape or src.ndim != 2 or src.shape[0] < 3:
        raise ValueError(f"need matching (N>=3, D) arrays, got {src.shape} and {dst.shape}")
    mu_s, mu_d = src.mean(axis=0), dst.mean(axis=0)
    xs, xd = src - mu_s, dst - mu_d
    var_s = (xs**2).sum() / len(src)
    if var_s <= 1e-12:
        raise ValueError("source points are degenerate")
    cov = xd.T @ xs / len(src)
    u, d, vt = np.linalg.svd(cov)
    sign = np.eye(src.shape[1])
    if np.linalg.det(u) * np.linalg.det(vt) < 0:
        sign[-1, -1] = -1.0
    rotation = u @ sign @ vt
    scale = float(np.trace(np.diag(d) @ sign) / var_s)
    translation = mu_d - scale * rotation @ mu_s
    return Similarity(scale, rotation, translation)


def head_angles(head_rotation: np.ndarray) -> tuple[float, float, float]:
    """Yaw, pitch, roll in degrees for a head rotation (head frame -> camera frame).

    yaw   > 0: face turned toward the subject's left (image right)
    pitch > 0: face tilted up
    roll  > 0: head tilted so the subject's left eye is higher
    """
    forward = head_rotation[:, 2]
    yaw = np.degrees(np.arctan2(forward[0], forward[2]))
    pitch = np.degrees(np.arctan2(forward[1], np.hypot(forward[0], forward[2])))
    # Remove yaw and pitch; what is left is an in-plane rotation about z.
    residual = (rotation_from_angles(yaw, pitch, 0.0)).T @ head_rotation
    roll = np.degrees(np.arctan2(residual[1, 0], residual[0, 0]))
    return float(yaw), float(pitch), float(roll)


def rotation_from_angles(yaw: float, pitch: float, roll: float) -> np.ndarray:
    """Inverse of :func:`head_angles` (degrees in, head->camera rotation out)."""
    y, p, r = np.radians([yaw, pitch, roll])
    ry = np.array([[np.cos(y), 0, np.sin(y)], [0, 1, 0], [-np.sin(y), 0, np.cos(y)]])
    # Positive pitch = nose up, i.e. rotation about +x by -p.
    rx = np.array([[1, 0, 0], [0, np.cos(p), np.sin(p)], [0, -np.sin(p), np.cos(p)]])
    rz = np.array([[np.cos(r), -np.sin(r), 0], [np.sin(r), np.cos(r), 0], [0, 0, 1]])
    return ry @ rx @ rz


def dist(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b))
