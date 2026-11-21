import json

import numpy as np
import pytest

from face_engine.cli import main
from face_engine.engine import Engine
from face_engine.observations import MediaInfo
from face_engine.sources import load_landmarks, save_landmarks
from face_engine.sources.synthetic import synthetic_body, synthetic_clip, synthetic_face

from conftest import FPS


def clip(n=int(12 * FPS)):
    rng = np.random.default_rng(0)

    def face(i):
        t = i / FPS
        if 6 <= t < 6.5:
            return None
        return synthetic_face(
            {"smile": 1.0, "cheek_raise": 1.0} if 2 <= t < 3 else {}, rng=rng, noise_px=0.2
        )

    def body(i):
        return synthetic_body("crossed" if 7 <= i / FPS < 9 else "rest")

    return synthetic_clip(n, FPS, face, body)


def test_report_structure_and_json_safety(media):
    report = Engine().run(clip(), media, frames_fps=5)
    text = json.dumps(report, allow_nan=False)  # NaN must never reach the file
    assert "disclaimer" in report and "lie" not in " ".join(report["summary"]["highlights"])
    assert set(report) >= {
        "meta",
        "glossary",
        "baseline",
        "summary",
        "segments",
        "events",
        "frames",
    }
    assert report["meta"]["frames"] == 360 and report["meta"]["duration_s"] == 12.0
    assert len(report["segments"]) == 3
    assert len(report["frames"]) == 60
    assert report["summary"]["face"]["dominant_expression"] == "neutral"
    seg0 = report["segments"][0]
    assert seg0["face"]["dominant_expression"] == "happiness"
    assert "AU12" in seg0["face"]["action_units"]
    assert report["segments"][1]["body"]["arms_crossed_share"] == pytest.approx(0.4)
    times = [e["start_s"] for e in report["events"]]
    assert times == sorted(times)
    assert {e["source"] for e in report["events"]} == {"face", "body"}
    assert all("_span" not in e and e["frame_start"] <= e["frame_end"] for e in report["events"])
    assert len(text) < 400_000


def test_notable_segments_are_contrasted_with_clip(media):
    report = Engine().run(clip(), media, frames_fps=0)
    assert "frames" not in report
    notable = report["segments"][1]["notable_vs_clip"]
    assert "arms_crossed_share" in notable


def test_single_photo_report():
    frames = synthetic_clip(
        1, 1.0, lambda i: synthetic_face({"smile": 1.0}), lambda i: synthetic_body("open")
    )
    media = MediaInfo("photo.jpg", "image", 1.0, 800, 600, "synthetic")
    report = Engine().run(frames, media)
    json.dumps(report, allow_nan=False)
    assert report["events"] == []
    assert report["baseline"]["face"]["method"] == "population_canonical"
    assert report["frames"][0]["au.AU12"] > 0.9


def test_empty_input_is_rejected(media):
    with pytest.raises(ValueError):
        Engine().run([], media)


def test_custom_analyzer_can_replace_builtin(media):
    from face_engine.analyzers.base import AnalyzerResult

    class Constant:
        name = "other"

        def analyze(self, frames, fps, neutral=()):
            return AnalyzerResult(
                {"other.x": np.ones(len(frames))},
                {"method": "none"},
                [{"type": "ping", "start_s": 0.0, "end_s": 0.1}],
                {"other.x": "1"},
            )

        def summarize(self, result, sl, fps):
            return {"n": int(result.features["other.x"][sl].sum())}

    report = Engine(analyzers=[Constant()]).run(clip(60), media)
    assert report["summary"]["other"] == {"n": 60}
    ev = report["events"][0]
    assert ev["source"] == "other"
    # Plug-in events without a frame span get one from their times.
    assert (ev["frame_start"], ev["frame_end"]) == (0, 2)


def test_landmarks_roundtrip(tmp_path, media):
    frames = clip(30)
    path = tmp_path / "lm.npz"
    save_landmarks(path, media, frames)
    media2, frames2 = load_landmarks(path)
    assert media2 == media
    assert len(frames2) == len(frames)
    np.testing.assert_allclose(frames2[5].face, frames[5].face)
    assert [h.side for h in frames2[5].hands] == [h.side for h in frames[5].hands]
    r1 = Engine().run(frames, media)
    r2 = Engine().run(frames2, media2)
    assert r1["summary"] == r2["summary"]


def test_cli_demo_and_npz_analyze(tmp_path, media):
    out = tmp_path / "demo.json"
    assert main(["demo", "-o", str(out)]) == 0
    demo = json.loads(out.read_text())
    assert demo["summary"]["event_counts"]["blink"] == 4

    lm = tmp_path / "lm.npz"
    save_landmarks(lm, media, clip(90))
    out2 = tmp_path / "a.json"
    assert main(["analyze", str(lm), "-o", str(out2), "--segment", "1", "--frames-fps", "0"]) == 0
    assert len(json.loads(out2.read_text())["segments"]) == 3


def test_cli_neutral_loader_follows_its_own_file_type(tmp_path, media, monkeypatch):
    lm = tmp_path / "clip.npz"
    save_landmarks(lm, media, clip(30))
    calls = []

    class FakeSource:
        def __init__(self, *a, **kw):
            pass

        def read(self, path, **kw):
            calls.append(path)
            return media, clip(1)

    import face_engine.sources.mediapipe_source as mps

    monkeypatch.setattr(mps, "MediaPipeSource", FakeSource)
    out = tmp_path / "r.json"
    assert main(["analyze", str(lm), "--neutral", "rest.jpg", "-o", str(out)]) == 0
    assert calls == ["rest.jpg"]
    assert json.loads(out.read_text())["baseline"]["face"]["method"] == "neutral_reference"


def test_segment_event_counts_use_same_rounding(media):
    fps = 29.97
    frames = synthetic_clip(
        int(10 * fps),
        fps,
        lambda i: synthetic_face({"blink": 1.0} if 150 <= i < 153 else {}),
    )
    m = MediaInfo("x", "video", fps, 1280, 720, "synthetic")
    report = Engine().run(frames, m, frames_fps=0)
    blink = next(e for e in report["events"] if e["type"] == "blink")
    seg = next(s for s in report["segments"] if s["start_s"] <= blink["start_s"] < s["end_s"])
    assert seg["event_counts"].get("blink") == 1
    assert sum(s["event_counts"].get("blink", 0) for s in report["segments"]) == 1
