"""Smoke tests for the visual outputs (needs opencv and matplotlib)."""

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")
pytest.importorskip("matplotlib")

from face_engine import viz  # noqa: E402
from face_engine.engine import Engine  # noqa: E402
from face_engine.observations import MediaInfo  # noqa: E402
from face_engine.sources.synthetic import synthetic_body, synthetic_clip, synthetic_face  # noqa: E402


def test_overlay_video_and_timeline(tmp_path):
    fps, n, w, h = 10.0, 30, 640, 480
    video = tmp_path / "in.mp4"
    writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    for _ in range(n):
        writer.write(np.full((h, w, 3), 90, np.uint8))
    writer.release()
    frames = synthetic_clip(
        n,
        fps,
        lambda i: synthetic_face(
            {"smile": 1.0} if 10 <= i < 20 else {}, iod_px=60, center=(320, -150, 0)
        ),
        lambda i: synthetic_body("open", sw_px=150, center=(320, -300)),
    )
    report = Engine().run(frames, MediaInfo(str(video), "video", fps, w, h, "synthetic"))
    out = viz.render_overlay(video, frames, report, tmp_path / "out.mp4")
    cap = cv2.VideoCapture(str(out))
    assert int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) == n
    ok, img = cap.read()
    assert ok and img.shape[1] == w + 260
    png = viz.plot_timeline(report, tmp_path / "t.png")
    assert png.stat().st_size > 10_000
