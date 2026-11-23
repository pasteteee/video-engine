import numpy as np

from face_engine.featurebank import FeatureBank, lexicon
from face_engine.featurebank.digest import render
from face_engine.featurebank.functionals import compute
from face_engine.featurebank.psych import tag
from face_engine.observations import FrameObservation


def _fake(n=300, fps=30.0, seed=0):
    rng = np.random.default_rng(seed)
    frames, rows = [], []
    for i in range(n):
        face = rng.normal(0, 1, (35, 3)) + np.array([[x * 10, 0, 0] for x in range(35)])
        frames.append(FrameObservation(i, i / fps, face=face))
        rows.append({"i": i, "t": i / fps, "head.yaw": float(np.sin(i / 10) * 5), "head.pitch": 0.0,
                     "head.roll": 0.0, "au.AU12": float(rng.random()), "gaze.averted": float(i % 50 == 0)})
    report = {"frames": rows, "events": [{"type": "head_nod", "start_s": 2.0, "peak_s": 2.1, "duration_s": 0.4}]}
    words = [[0.2, 0.5, "are"], [0.5, 0.7, "you"], [0.7, 1.0, "better"], [1.0, 1.3, "off"],
             [3.0, 3.3, "we"], [3.3, 3.6, "will"], [3.6, 4.0, "win"], [6.0, 6.2, "i"], [6.2, 6.5, "think"]]
    return frames, report, words, fps


def test_bank_produces_thousands_of_named_quantities():
    frames, report, words, fps = _fake()
    res = FeatureBank(fps, len(frames) / fps).run(report, frames, None, words)
    f = res["features"]
    assert res["n_features"] > 1000
    assert f["lang.pron_you.count"] == 1
    assert f["lang.questions.count"] == 1
    assert "head.yaw|speaking|mean" in f
    assert "event.head_nod.per_min" in f


def test_functionals_baseline_relative():
    x = np.r_[np.zeros(100), np.ones(20) * 5, np.zeros(100)]
    r = compute(x, 30.0, 0.0, 1.0)
    assert abs(r["share_above_baseline_1sd"] - 20 / 220) < 1e-9
    assert r["longest_high_run_s"] == 20 / 30


def test_questions_without_punctuation():
    assert lexicon.question_onsets("ask yourself are you better off".split()) == [2]
    assert lexicon.question_onsets("i think it would be well".split()) == []


def test_tags_and_digest():
    assert tag("au.AU12|all|mean").grade == "A"
    frames, report, words, fps = _fake()
    a = FeatureBank(fps, 10).run(report, frames, None, words)
    frames, report, words, fps = _fake(seed=1)
    b = FeatureBank(fps, 10).run(report, frames, None, words[:4])
    md = render({"A": a, "B": b})
    assert "Largest differences" in md
