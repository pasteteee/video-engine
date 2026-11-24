import numpy as np
import pytest

from face_engine import temporal as T


def test_runs_and_merging():
    mask = np.array([0, 1, 1, 0, 1, 0, 0, 0, 1, 1], bool)
    assert T.runs(mask) == [(1, 3), (4, 5), (8, 10)]
    assert T.runs(mask, min_len=2) == [(1, 3), (8, 10)]
    assert T.runs(mask, max_gap=1) == [(1, 5), (8, 10)]
    assert T.runs(np.zeros(4, bool)) == []


def test_smooth_keeps_length_and_nans_even_for_short_input():
    for n in (1, 2, 3, 10):
        x = np.arange(n, dtype=float)
        assert len(T.smooth(x, 7)) == n
    x = np.array([1.0, np.nan, 3.0, 3.0, 3.0])
    out = T.smooth(x, 3)
    assert np.isnan(out[1])
    assert out[0] == 1.0  # the NaN neighbour is ignored, not treated as 0
    assert out[3] == 3.0


def test_dilate_keeps_length():
    assert T.dilate(np.array([True]), 3).tolist() == [True]
    assert T.dilate(np.array([0, 0, 1, 0, 0, 0], bool), 1).tolist() == [0, 1, 1, 1, 0, 0]


def test_oscillation_detects_back_and_forth_only():
    t = np.arange(0, 3, 1 / 30)
    nod = np.where((t > 1) & (t < 2), 10 * np.sin(2 * np.pi * 2 * t), 0.0)
    spans = T.oscillations(nod, 30, threshold=6)
    assert len(spans) == 1
    s, e = spans[0]
    assert 0.9 <= t[s] and t[e - 1] <= 2.1
    # A single slow turn is not an oscillation.
    turn = np.linspace(0, 30, 90)
    assert T.oscillations(turn, 30, threshold=6) == []


def test_threshold_events_report_peak_and_duration():
    sig = np.zeros(30)
    sig[10:16] = [0.4, 0.6, 0.9, 0.7, 0.5, 0.4]
    times = np.arange(30) / 30
    (ev,) = T.threshold_events("x", sig, 0.35, times, 30.0, label="demo")
    assert ev["type"] == "x" and ev["label"] == "demo"
    assert ev["peak"] == 0.9 and ev["peak_s"] == round(12 / 30, 3)
    assert ev["duration_s"] == 0.2
    assert T.event_span(ev) == (10, 16)


@pytest.mark.parametrize("fps", [30.0, 29.97, 25.0, 60.0])
def test_event_span_roundtrips_every_span(fps):
    times = np.arange(200) / fps
    for start in range(0, 190, 7):
        for length in (1, 2, 3, 9):
            ev = T.make_event("x", (start, start + length), times, fps)
            assert T.event_span(ev) == (start, start + length)



def test_hysteresis_expands_boundaries_without_low_only_events():
    from face_engine.temporal import hysteresis_runs
    x = np.array([0.,.3,.7,.3,0.,.3,.4,.3,0.])
    assert hysteresis_runs(x,.5,.25) == [(1,4)]
    assert hysteresis_runs(x,.5,.5) == [(2,3)]


def test_hysteresis_never_bridges_missing_data():
    from face_engine.temporal import hysteresis_runs
    assert hysteresis_runs(np.array([.3,.7,np.nan,.3,.7,.3]),.5,.25) == [(0,2),(3,6)]
