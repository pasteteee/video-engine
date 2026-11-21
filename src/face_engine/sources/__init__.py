"""Landmark sources (detectors) and landmark caching."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol, Sequence

import numpy as np

from face_engine.observations import FrameObservation, Hand, MediaInfo
from face_engine.topology import BODY_POINTS, FACE_POINTS, HAND_NUM_POINTS


class LandmarkSource(Protocol):
    """Any detector backend: turns a media file into named landmarks per frame."""

    name: str

    def read(
        self, path: str | Path, sample_fps: float | None = None, max_seconds: float | None = None
    ) -> tuple[MediaInfo, list[FrameObservation]]: ...


_SIDES = ("l", "r")


def save_landmarks(path: str | Path, media: MediaInfo, frames: Sequence[FrameObservation]) -> None:
    """Store detector output so analysis can be re-run without the detector."""
    n = len(frames)
    face = np.full((n, len(FACE_POINTS), 3), np.nan)
    body = np.full((n, len(BODY_POINTS), 3), np.nan)
    vis = np.zeros((n, len(BODY_POINTS)))
    hands = np.full((n, 2, HAND_NUM_POINTS, 3), np.nan)
    hand_side = np.zeros((n, 2), dtype=np.int8)  # 0 unknown, 1 left, 2 right
    for i, f in enumerate(frames):
        if f.face is not None:
            face[i] = f.face
        if f.body is not None:
            body[i] = f.body
            vis[i] = f.body_visibility if f.body_visibility is not None else 1.0
        for j, h in enumerate(f.hands[:2]):
            hands[i, j] = h.points
            hand_side[i, j] = 0 if h.side is None else 1 + _SIDES.index(h.side)
    np.savez_compressed(
        path,
        media=json.dumps(media.__dict__),
        index=np.array([f.index for f in frames]),
        time_s=np.array([f.time_s for f in frames]),
        face=face, body=body, body_visibility=vis, hands=hands, hand_side=hand_side,
    )


def load_landmarks(path: str | Path) -> tuple[MediaInfo, list[FrameObservation]]:
    with np.load(path, allow_pickle=False) as z:
        data = {k: z[k] for k in z.files}  # decompress every array once
    media = MediaInfo(**json.loads(str(data["media"])))
    frames = []
    for i, (index, time_s) in enumerate(zip(data["index"], data["time_s"])):
        face, body = data["face"][i], data["body"][i]
        has_body = not np.isnan(body).all()
        hands = [
            Hand(data["hands"][i, j], None if s == 0 else _SIDES[s - 1])
            for j, s in enumerate(data["hand_side"][i])
            if not np.isnan(data["hands"][i, j]).all()
        ]
        frames.append(
            FrameObservation(
                index=int(index),
                time_s=float(time_s),
                face=None if np.isnan(face).all() else face,
                body=body if has_body else None,
                body_visibility=data["body_visibility"][i] if has_body else None,
                hands=hands,
            )
        )
    return media, frames
