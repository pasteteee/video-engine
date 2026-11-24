import json
import numpy as np
import pytest
from face_engine.behavior import enrich, summarize_behavior
from face_engine.engine import Engine
from face_engine.observations import FrameObservation
from face_engine.featurebank.signals import engine_signals
from face_engine.featurebank.functionals import compute
from face_engine.analyzers.base import rnd


def table(n=20):
    return {k: np.zeros(n) for k in ['eye.closure_l', 'eye.closure_r', 'head.yaw', 'head.pitch', 'head.roll']} | {'face.present': np.ones(n), 'face.reliability': np.ones(n)}


def test_closure_denominator_gap_and_wink():
    f = table()
    f['eye.closure_l'][2:12] = 1
    f['eye.closure_r'][2:12] = 1
    f['face.present'][7] = 0
    f['eye.closure_l'][15:18] = 1  # unilateral closure excluded
    enrich(f, 10)
    s = summarize_behavior(f, 10)
    assert s['eye_observed_s'] == 1.9
    assert s['eye_closed80_share'] == pytest.approx(9/19, abs=.001)
    assert s['eye_slow_closed80_share'] == pytest.approx(5/19, abs=.001)
    assert s['eye_longest_closed80_s'] == .5


def test_speed_wrap_and_gap():
    f = table(5)
    f['head.yaw'][:] = [178, 179, -179, -178, -177]
    f['face.present'][3] = 0
    enrich(f, 10)
    assert f['head.angular_speed_deg_s'][2] == 20
    assert np.isnan(f['head.angular_speed_deg_s'][3:]).all()


def test_all_missing_and_photo():
    f = table(1)
    f['face.present'][:] = 0
    enrich(f, 30)
    s = summarize_behavior(f, 30)
    assert s['eye_closed80_share'] is None
    assert s['head_angular_speed_mean_deg_s'] is None
    json.dumps(s, allow_nan=False)


def test_nonconsecutive_frame_mapping():
    report = {'frames': [{'i': 10, 'head.yaw': 3}, {'i': 14, 'head.yaw': 7}]}
    x = engine_signals(report, 3, [10, 12, 14])['head.yaw']
    np.testing.assert_allclose(x, [3, np.nan, 7], equal_nan=True)


@pytest.mark.parametrize('fps', [0, -1, float('nan'), float('inf')])
def test_invalid_fps(media, fps):
    media.fps = fps
    with pytest.raises(ValueError, match='fps'):
        Engine().run([FrameObservation(0, 0)], media)


@pytest.mark.parametrize('times', [[0, 0], [1, 0], [0, float('nan')], [0, .9]])
def test_invalid_time_grid(media, times):
    with pytest.raises(ValueError):
        Engine().run([FrameObservation(i, t) for i, t in enumerate(times)], media)


def test_nonfinite_json_and_low_fps():
    assert rnd(float('inf')) is None
    r = compute(np.r_[np.arange(20), np.inf], .2, 0, 1)
    assert r['valid_share'] == 20/21
    assert all(np.isfinite(v) for v in r.values())


def test_empty_analyzer_list(media):
    r = Engine(analyzers=[]).run([FrameObservation(0, 0)], media)
    assert r['meta']['analyzers'] == []


@pytest.mark.parametrize('points', [np.zeros((35, 3)), np.zeros((2, 3)), np.full((35, 3), np.inf)])
def test_malformed_face_does_not_crash(points, media):
    r = Engine().run([FrameObservation(0, 0, face=points)], media)
    assert r['summary']['face']['face_visible'] == 0
    json.dumps(r, allow_nan=False)


@pytest.mark.parametrize('fps', [1, 5, 15, 30, 60])
def test_closed_eye_duration_at_multiple_rates(fps):
    f = table(2 * fps)
    f['eye.closure_l'][:fps] = 1
    f['eye.closure_r'][:fps] = 1
    enrich(f, fps)
    s = summarize_behavior(f, fps)
    assert s['eye_closed80_share'] == .5
    assert s['eye_slow_closed80_share'] == .5
    assert s['eye_longest_closed80_s'] == 1


@pytest.mark.parametrize('words', [[[0, 0, 'a']], [[-1, 2, 'a']], [[0, float('inf'), 'a']], [[1, 2, 'a'], [0, 1, 'b']], [[0, 1]]])
def test_invalid_word_timestamps(words):
    from face_engine.featurebank.bank import _words
    with pytest.raises(ValueError):
        _words(words)


@pytest.mark.parametrize('frequency', [0, 150])
def test_audio_extraction_pcm(monkeypatch, frequency):
    pytest.importorskip('librosa')
    from types import SimpleNamespace
    from face_engine.featurebank.signals import audio_signals
    t = np.arange(32000) / 16000
    pcm = (np.sin(2*np.pi*frequency*t) * 10000).astype(np.int16).tobytes()
    monkeypatch.setattr('face_engine.featurebank.signals.subprocess.run', lambda *a, **k: SimpleNamespace(stdout=pcm))
    signals = audio_signals('mock.wav', 60, 30)
    assert len(signals['voice.loudness_db']) == 60
    assert np.isfinite(signals['voice.loudness_db']).all()
    assert not any(np.isinf(v).any() for k, v in signals.items())
    if frequency:
        assert np.nanmedian(signals['voice.pitch_hz']) == pytest.approx(frequency, abs=5)



def test_new_metrics_in_summary_without_frames(media):
    from face_engine.sources.synthetic import synthetic_clip, synthetic_face
    frames = synthetic_clip(60, media.fps, lambda i: synthetic_face({'blink': 1} if 20 <= i < 40 else {}))
    r = Engine().run(frames, media, frames_fps=0)
    assert 'frames' not in r
    assert r['summary']['face']['eye_closed80_share'] > 0
    assert 'head_angular_speed_mean_deg_s' in r['segments'][0]['face']
    json.dumps(r, allow_nan=False)


def test_featurebank_npz_cache_recomputes_report(tmp_path, monkeypatch, capsys):
    from face_engine.sources.synthetic import synthetic_clip, synthetic_face
    from face_engine.featurebank import run
    from face_engine.sources import save_landmarks
    from face_engine.observations import MediaInfo
    clip = tmp_path / 'sample.mp4'
    clip.write_bytes(b'placeholder')
    frames = synthetic_clip(30, 30, lambda i: synthetic_face({}))
    media = MediaInfo(str(clip), 'video', 30, 640, 480, 'synthetic')
    cache = str(clip) + '.fbcache.npz'
    save_landmarks(cache, media, frames)
    import os
    stamp = clip.stat().st_mtime + 10
    os.utime(cache, (stamp, stamp))
    monkeypatch.setattr('face_engine.featurebank.bank.audio_signals', lambda *a: {'_audio_raw': np.zeros(1)})
    out = tmp_path / 'bank.json'
    run.main([str(clip), '-', str(out)])
    bank = json.loads(out.read_text(encoding='utf-8'))
    assert bank['n_frames'] == 30
    assert 'eye.closed80|all|mean' in bank['features']



def test_featurebank_rejects_nonzero_origin():
    from face_engine.featurebank import FeatureBank
    with pytest.raises(ValueError, match='timestamps'):
        FeatureBank(30, 1).run({'frames': []}, [FrameObservation(0, 1)], None, [])
