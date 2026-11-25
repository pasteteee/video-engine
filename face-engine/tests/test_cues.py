"""Behaviour map: tracks, baseline deviations, hotspots, questions and overlay."""

import numpy as np

from face_engine import cues
from face_engine.cli import build_parser
from face_engine.cues import deviation as D
from face_engine.cues.pipeline import highlights
from face_engine.cues.registry import CHANNELS, CUES
from face_engine.cues.signals import Word, find_questions, parse_words, touch_zones
from face_engine.engine import Engine
from face_engine.observations import MediaInfo
from face_engine.sources.synthetic import random_identity, synthetic_body, synthetic_clip, synthetic_face

FPS = 30.0
DUR = 40.0
HOT = (24.0, 27.0)  # the "loaded" moment


def _clip():
    rng = np.random.default_rng(3)
    ident = random_identity(rng)

    def face(i):
        t = i / FPS
        expr = {}
        if HOT[0] <= t < HOT[1]:
            expr.update(brow_lower=0.9, lip_press=0.9)
        if any(abs(t - b) < 0.1 for b in np.arange(1.5, DUR, 3.7)):
            expr["blink"] = 1.0
        return synthetic_face(expr, identity=ident, noise_px=0.2, rng=rng)

    def body(i):
        t = i / FPS
        if HOT[0] + 0.5 <= t < HOT[1]:
            return synthetic_body("face_touch")
        return synthetic_body("rest")

    return synthetic_clip(int(DUR * FPS), FPS, face, body)


def _audio(n):
    t = np.arange(n) / FPS
    voiced = ((t % 4) < 3).astype(float)
    pitch = 0.3 * np.sin(t * 3)
    pitch[(t >= HOT[0]) & (t < HOT[1])] += 4.0
    loud = np.full(n, -25.0)
    return {
        "voice.voiced": voiced,
        "voice.pitch_st": np.where(voiced > 0, pitch, np.nan),
        "voice.loudness_db": loud,
        "voice.jitter_like": np.full(n, 0.01),
        "voice.shimmer_like_db": np.full(n, 0.5),
    }


def _words():
    rows = []
    t = 0.5
    while t < DUR - 1:
        # interviewer asks, subject answers ~0.6 s later; one slow answer before the hot moment
        rows += [[t, t + 0.4, "did", "Q"], [t + 0.4, t + 0.8, "you?", "Q"]]
        gap = 2.5 if abs(t + 0.8 - (HOT[0] - 0.5)) < 2.1 else 0.6
        a = t + 0.8 + gap
        text = ["um", "i", "don't", "know"] if HOT[0] - 3 < a < HOT[1] else ["yes", "it", "was", "fine"]
        rows += [[a + 0.3 * k, a + 0.3 * k + 0.25, w, "S"] for k, w in enumerate(text)]
        t = a + 2.0
    return parse_words(rows)


def _run(**kw):
    frames = _clip()
    media = MediaInfo("synthetic", "video", FPS, 1280, 720, "synthetic")
    report = Engine().run(frames, media, frames_fps=None)
    return cues.run(report, frames, media, _audio(len(frames)), _words(), "S", **kw)[:2]


def _run3(**kw):
    frames = _clip()
    media = MediaInfo("synthetic", "video", FPS, 1280, 720, "synthetic")
    report = Engine().run(frames, media, frames_fps=None)
    return frames, cues.run(report, frames, media, _audio(len(frames)), _words(), "S", **kw)


def test_registry_ids_unique_and_channels_known():
    ids = [c.id for c in CUES]
    assert len(ids) == len(set(ids))
    assert {c.channel for c in CUES} <= set(CHANNELS)
    assert all(c.direction in ("up", "down", "both") and c.grade in "ABCD" for c in CUES)


def test_hotspot_found_at_loaded_moment_only():
    behavior, overlay = _run()
    spots = behavior["hotspots"]
    assert spots, behavior["summary"]["notes"]
    hit = [h for h in spots if h["start_s"] <= HOT[1] + 1 and h["end_s"] >= HOT[0] - 1]
    assert hit
    chans = set(hit[0]["channels"])
    assert {"face", "voice"} <= chans
    assert hit[0]["n_channels"] >= 3
    # Nothing in the calm first half.
    assert not [h for h in spots if h["end_s"] < 15]
    p = np.array(behavior["timeline"]["pressure"], float)
    t = np.array(behavior["timeline"]["t"], float)
    assert p[(t > HOT[0]) & (t < HOT[1])].max() > 3 * np.median(p[t < 15]) + 5


def test_questions_latency_and_speech_cues():
    behavior, _ = _run()
    qs = behavior["questions"]
    assert len(qs) >= 5
    slow = max(qs, key=lambda q: q["latency_s"])
    assert slow["latency_s"] > 2.0 and slow["latency_score"] >= 2.0
    tracked = {c["id"] for c in behavior["cues"] if c["tracked"]}
    assert {"fillers", "non_recall", "response_latency", "pitch", "self_touch_face", "lip_press"} <= tracked


def test_overlay_one_zone_at_a_time_and_boxes():
    behavior, overlay = _run()
    hl = overlay["highlights"]
    assert hl
    for a, b in zip(hl, hl[1:]):
        assert b["start_s"] >= a["end_s"] - 1e-6
    assert all("lying" not in h["caption"].lower() for h in hl)
    assert len(overlay["t"]) == len(overlay["pressure"])
    box = next(b for b in overlay["zones"]["mouth"] if b)
    assert len(box) == 4 and box[2] > 0 and box[3] > 0


def test_baseline_spans_and_override():
    b1, _ = _run(baseline_spans=[(0.0, 15.0)])
    assert b1["meta"]["baseline"]["spans_s"] == [[0.0, 15.0]]
    override = {k: v for k, v in b1["baseline"].items() if "median" in v and "scale" in v}
    b2, _ = _run(baseline_override=override)
    assert b2["meta"]["baseline"]["from_file"]
    assert b2["baseline"]["pitch"]["median"] == b1["baseline"]["pitch"]["median"]


def test_find_questions_by_punctuation_and_explicit():
    ws = parse_words([[0, 0.5, "Where"], [0.5, 1.0, "were"], [1.0, 1.4, "you?"], [2.4, 2.8, "Home."]])
    q = find_questions(ws, None)
    assert len(q) == 1 and abs(q[0]["latency_s"] - 1.0) < 1e-6
    q = find_questions(ws, None, [1.4])
    assert q[0]["answer_text"].startswith("home")


def test_touch_zones_neck_and_head():
    neck = synthetic_body({"l_wrist": (0.0, 0.15), "r_wrist": (-0.6, -1.5)}, with_hands=False)
    head = synthetic_body({"l_wrist": (0.1, 0.95), "r_wrist": (-0.6, -1.5)}, with_hands=False)
    rest = synthetic_body("rest", with_hands=False)
    frames = synthetic_clip(3, FPS, None, lambda i: (neck, head, rest)[i])
    z = touch_zones(frames)
    assert z["neck"].tolist() == [1.0, 0.0, 0.0]
    assert z["head"].tolist() == [0.0, 1.0, 0.0]


def test_highlights_cap_per_hotspot():
    spot = {"start_s": 1.0, "cues": [
        {"cue": "lip_press", "zone": "mouth", "channel": "face", "score": 3.0, "peak_s": 2.0},
        {"cue": "chin_raise", "zone": "mouth", "channel": "face", "score": 2.5, "peak_s": 2.0},
        {"cue": "pitch", "zone": "voice", "channel": "voice", "score": 2.2, "peak_s": 1.5},
    ]}
    hl = highlights([spot])
    assert [h["zone"] for h in hl] == ["voice", "mouth"]


def test_window_rate_counts_events_per_minute():
    from face_engine.cues.signals import Track

    n = int(60 * FPS)
    x = np.zeros(n)
    x[:: int(3 * FPS)] = 1  # one event every 3 s = 20/min
    v = D._window_values(Track(x, "rate", np.ones(n, bool)), np.array([30.0]), FPS, n, 30.0, 0.5)
    assert abs(v[0] - 20) < 2.5


def test_cli_has_behavior_command():
    args = build_parser().parse_args(["behavior", "x.mp4", "-o", "out", "--baseline", "0:30", "--z", "2.5"])
    assert args.func.__name__ == "cmd_behavior" and args.baseline == ["0:30"] and args.z == 2.5
    assert isinstance(Word(0, 1, "a"), Word)


def test_face_first_moments_and_states():
    frames, (behavior, _, mdoc) = _run3()
    groups = behavior["states"]["groups"]
    assert "speak" in groups and "listen" in groups
    ms = mdoc["moments"]
    assert ms, behavior["summary"]["notes"]
    hit = [m for m in ms if m["t_start"] <= HOT[1] and m["t_end"] >= HOT[0]]
    assert hit
    m = hit[0]
    assert m["face_events"]["twitches"] or len(m["face_events"]["cues"]) >= 2
    assert m["label"] in ("holding_back", "discomfort", "flash", "face_change", "mismatch",
                          "possible_deception_cluster")
    assert m["zone"] in ("mouth", "brow", "eyes", "face")
    assert 0 < m["score"] <= 100 and m["slowmo"][0] < m["slowmo"][1]
    assert m["face_box"] and m["baseline_frame"]["t"] is not None
    assert "lying" not in m["wording"].lower()
    # Synthetic face is ~1 IOD = 100 px tall faces? quality is reported either way.
    assert set(m["quality"]) == {"face_px", "flags", "readable"}


def test_micro_twitch_detector():
    from face_engine.cues.moments import micro_twitches

    n = int(40 * FPS)
    rng = np.random.default_rng(1)
    rows = [{"au.AU04": float(0.05 + 0.03 * rng.random()), "eye.closure": 0.0, "head.yaw": 0.0,
             "head.angular_speed_deg_s": 5.0} for _ in range(n)]
    for k in range(int(10 * FPS), int(10 * FPS) + 6):  # 0.2 s spike
        rows[k]["au.AU04"] = 0.8
    for k in range(int(14 * FPS), int(14 * FPS) + 45):  # 1.5 s: too long for a twitch
        rows[k]["au.AU04"] = 0.8
    state = np.array(["listen"] * n, dtype=object)
    cam = np.array(["front"] * n, dtype=object)
    tw, p95 = micro_twitches(rows, state, cam, np.ones(n, bool), FPS)
    assert [round(e["t"]) for e in tw if e["au"] == "AU04"] == [10]
    assert p95["listen"]["AU04"] < 0.2


def test_quality_gates():
    from face_engine.cues.moments import quality

    n = 60
    rf = [{"head.pitch_rel": -25.0, "gaze.dir_v_deg": -20.0}] * n
    q = quality(0, 2, FPS, np.full(n, 90.0), np.array(["front"] * n, dtype=object), rf)
    assert not q["readable"] and {"face_too_small", "looking_down_reading"} <= set(q["flags"])
    rf = [{"head.pitch_rel": 0.0, "gaze.dir_v_deg": 0.0}] * n
    q = quality(0, 2, FPS, np.full(n, 200.0), np.array(["front"] * n, dtype=object), rf)
    assert q["readable"] and q["flags"] == []
