"""End-to-end check on a real photo. Needs mediapipe, the models and a sample.

Set FACE_ENGINE_SAMPLES to a folder with portrait.jpg (a smiling person with
crossed arms, e.g. MediaPipe's test asset) and FACE_ENGINE_MODELS to the models.
"""

import os
from pathlib import Path

import pytest

pytest.importorskip("mediapipe")
pytest.importorskip("cv2")
samples = os.environ.get("FACE_ENGINE_SAMPLES")
pytestmark = pytest.mark.skipif(not samples, reason="FACE_ENGINE_SAMPLES not set")


def test_portrait_smile_and_crossed_arms():
    from face_engine.engine import Engine
    from face_engine.sources.mediapipe_source import MediaPipeSource

    media, frames = MediaPipeSource().read(Path(samples) / "portrait.jpg")
    assert frames[0].face is not None and frames[0].body is not None
    f = Engine().run(frames, media)["frames"][0]
    assert f["expr.happiness"] > 0.5 and f["smile.duchenne"] > 0.5
    assert abs(f["head.yaw"]) < 10
    assert f["body.arms_crossed"] == 1.0
