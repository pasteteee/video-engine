import numpy as np
import pytest
from face_engine.featurebank.bank import _mask, FeatureBank
from face_engine.analyzers.body import BodyAnalyzer
from face_engine.observations import FrameObservation


def test_mask_uses_half_open_intervals():
    np.testing.assert_array_equal(_mask(6, 10, [(0.11, .4)]), [False, False, True, True, False, False])
    assert not _mask(6, 10, [(.1, .1)]).any()


def test_overlapping_words_do_not_make_negative_silence():
    out = {}
    ws = [(0., 2., 'one'), (.5, 3., 'two'), (1., 4., 'three')]
    FeatureBank(10, 3)._timing(ws, [ws], {}, out)
    assert out['timing.silence_share'] == 0


@pytest.mark.parametrize('body,vis', [(np.zeros((2,3)), None), (np.zeros((15,3)), np.ones(2)), (np.full((15,3), np.inf), None)])
def test_bad_body_is_missing(body, vis):
    result = BodyAnalyzer().analyze([FrameObservation(0,0,body=body,body_visibility=vis)],30)
    assert result.features['body.present'][0] == 0



def test_geometry_rejects_malformed_body_and_face():
    from face_engine.featurebank.signals import geometry_signals
    f = FrameObservation(0, 0, face=np.ones((35, 2)), body=np.ones((2, 3)), body_visibility=np.ones(2))
    signals = geometry_signals([f], 30)
    assert all(np.isnan(v).all() for v in signals.values())



def test_hidden_wrists_are_unknown_not_negative_behavior():
    from face_engine.sources.synthetic import synthetic_body
    from face_engine.topology import BODY_INDEX
    body, vis, hands = synthetic_body('rest')
    vis = vis.copy()
    for name in ('l_wrist', 'r_wrist', 'l_index', 'r_index'):
        vis[BODY_INDEX[name]] = 0
    analyzer = BodyAnalyzer()
    result = analyzer.analyze([FrameObservation(i,i/30,body=body,body_visibility=vis) for i in range(30)],30)
    summary = analyzer.summarize(result,slice(None),30)
    for name in ('gesturing_share','face_touch_share','arms_crossed_share','hands_joined_share','open_palms_share'):
        assert summary[name] is None



def test_landmarker_creation_failure_closes_created_models(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from face_engine.sources.mediapipe_source import MediaPipeSource
    import sys
    closed = []
    detector = SimpleNamespace(close=lambda: closed.append(True))
    fake_class = SimpleNamespace(create_from_options=lambda _:detector)
    options = lambda **kw: kw
    vision = SimpleNamespace(RunningMode=SimpleNamespace(VIDEO=1, IMAGE=0),
        FaceLandmarker=fake_class, FaceLandmarkerOptions=options,
        PoseLandmarker=fake_class, PoseLandmarkerOptions=options,
        HandLandmarker=fake_class, HandLandmarkerOptions=options)
    monkeypatch.setitem(sys.modules,'mediapipe.tasks.python',SimpleNamespace(BaseOptions=options,vision=vision))
    (tmp_path/'face_landmarker.task').write_bytes(b'fake')
    with pytest.raises(FileNotFoundError):
        MediaPipeSource(tmp_path)._landmarkers(video=True)
    assert closed == [True]


def test_video_capture_released_if_models_fail(monkeypatch):
    cv2 = pytest.importorskip('cv2')
    from types import SimpleNamespace
    from pathlib import Path
    from face_engine.sources.mediapipe_source import MediaPipeSource
    released = []
    cap = SimpleNamespace(isOpened=lambda:True, get=lambda _:30, release=lambda:released.append(True))
    monkeypatch.setattr(cv2,'VideoCapture',lambda _:cap)
    source = MediaPipeSource()
    def fail(**kw):
        raise FileNotFoundError('model absent')
    monkeypatch.setattr(source,'_landmarkers',fail)
    with pytest.raises(FileNotFoundError):
        source._read_video(Path('fake.mp4'),None,None)
    assert released == [True]
