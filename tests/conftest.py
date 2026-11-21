import numpy as np
import pytest

from face_engine.observations import MediaInfo
from face_engine.sources.synthetic import synthetic_clip, synthetic_face

FPS = 30.0


@pytest.fixture
def media():
    return MediaInfo("synthetic", "video", FPS, 1280, 720, "synthetic")


def face_clip(expr_at, n=FPS * 6, **face_kw):
    """Clip whose expression at time t is ``expr_at(t)``; neutral most of the time."""
    rng = np.random.default_rng(0)
    return synthetic_clip(
        int(n), FPS, lambda i: synthetic_face(expr_at(i / FPS), rng=rng, **face_kw)
    )
