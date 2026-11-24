"""Core data containers passed between the detector and the analyzers."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

# Column-oriented time series: feature name -> array of length n_frames (NaN = missing).
Table = dict[str, np.ndarray]


@dataclass
class Hand:
    """One detected hand: (21, 3) points in the internal frame (pixels)."""

    points: np.ndarray
    # Which arm of the subject the hand belongs to ("l" / "r"), or None if unknown.
    side: str | None = None


@dataclass
class FrameObservation:
    """Everything a detector saw in one frame, already in the internal frame.

    Internal frame: x -> image right, y -> up, z -> toward camera, units = pixels.
    ``face`` rows follow ``topology.FACE_POINTS``; ``body`` rows follow
    ``topology.BODY_POINTS``; ``body_visibility`` holds per-point confidence 0..1.
    """

    index: int
    time_s: float
    face: np.ndarray | None = None
    body: np.ndarray | None = None
    body_visibility: np.ndarray | None = None
    hands: list[Hand] = field(default_factory=list)


@dataclass
class MediaInfo:
    path: str
    kind: str  # "image" | "video"
    fps: float
    width: int
    height: int
    detector: str
