import numpy as np
import pytest

from face_engine.analyzers.body import BodyAnalyzer, palm_facing
from face_engine.observations import FrameObservation, Hand
from face_engine.sources.synthetic import synthetic_body, synthetic_clip, synthetic_hand

FPS = 30.0
FLAGS = ("arms_crossed", "hands_joined", "face_touch", "open_palms")


def single(posture, **kw):
    frames = synthetic_clip(1, FPS, body_fn=lambda i: synthetic_body(posture, **kw))
    return {k: v[0] for k, v in BodyAnalyzer().analyze(frames, FPS).features.items()}


@pytest.mark.parametrize(
    "posture, expected",
    [
        ("rest", set()),
        ("open", set()),
        ("raised", set()),
        ("crossed", {"arms_crossed"}),
        ("face_touch", {"face_touch"}),
        ("hands_joined", {"hands_joined"}),
    ],
)
@pytest.mark.parametrize("with_hands", [True, False])
def test_posture_flags(posture, expected, with_hands):
    f = single(posture, with_hands=with_hands)
    assert {k for k in FLAGS if f[f"body.{k}"] == 1.0} == expected


def test_openness_orders_postures():
    spans = [single(p)["body.arm_openness"] for p in ("hands_joined", "crossed", "rest", "open")]
    assert spans == sorted(spans)


@pytest.mark.parametrize("side", ["l", "r"])
def test_palm_facing_sign(side):
    wrist = np.zeros(3)
    assert palm_facing(synthetic_hand(side, True, wrist, 50.0), side) > 0.5
    assert palm_facing(synthetic_hand(side, False, wrist, 50.0), side) < -0.5


def test_open_palms_needs_a_shown_palm():
    assert single("open", palms_to_camera=True)["body.open_palms"] == 1.0
    assert single("open", palms_to_camera=False)["body.open_palms"] == 0.0
    # Hands resting on crossed arms are not "shown" palms.
    assert single("crossed", palms_to_camera=True)["body.open_palms"] == 0.0


def test_hand_side_is_assigned_from_pose_wrists():
    body, vis, hands = synthetic_body("open", palms_to_camera=True)
    unlabeled = [Hand(h.points) for h in hands[::-1]]
    obs = FrameObservation(0, 0.0, body=body, body_visibility=vis, hands=unlabeled)
    f = BodyAnalyzer().analyze([obs], FPS).features
    assert f["body.palm_to_camera"][0] > 0.5


def test_features_are_scale_invariant():
    a = single("open", scale=0.5)
    b = single("open", scale=2.0)
    for k in ("body.arm_openness", "body.hand_height_l"):
        assert a[k] == pytest.approx(b[k])


def test_gesture_events_merge_turning_points():
    def body(i):
        t = i / FPS
        swing = 0.5 * np.sin(2 * np.pi * 1.0 * t) if 1 <= t < 3 else 0.0
        return synthetic_body({"l_wrist": (1.0 + swing, -0.5), "r_wrist": (-0.6, -1.5)})

    res = BodyAnalyzer().analyze(synthetic_clip(int(5 * FPS), FPS, body_fn=body), FPS)
    gestures = [e for e in res.events if e["type"] == "gesture"]
    assert len(gestures) == 1
    assert 0.8 <= gestures[0]["start_s"] <= 1.3 and 2.7 <= gestures[0]["end_s"] <= 3.3
    assert gestures[0]["peak_speed_sw_s"] > 2.5


def test_posture_shift_toward_camera():
    def body(i):
        return synthetic_body("rest", scale=1.0 if i < 60 else 1.25)

    res = BodyAnalyzer().analyze(synthetic_clip(120, FPS, body_fn=body), FPS)
    shifts = [e for e in res.events if e["type"] == "posture_shift"]
    assert [e["direction"] for e in shifts] == ["toward_camera"]
    lean = res.features["body.lean_in"]
    assert np.nanmax(lean) - np.nanmin(lean) == pytest.approx(0.25 / 1.125, abs=0.01)


def test_shrug():
    def body(i):
        layout = {"l_ear": (0.25, 0.75), "r_ear": (-0.25, 0.75)} if 30 <= i < 45 else {}
        return synthetic_body({"l_wrist": (0.6, -1.5), "r_wrist": (-0.6, -1.5), **layout})

    res = BodyAnalyzer().analyze(synthetic_clip(90, FPS, body_fn=body), FPS)
    assert [e["type"] for e in res.events].count("shrug") == 1


def test_invisible_shoulders_mean_no_body():
    body, vis, hands = synthetic_body("rest")
    vis = vis.copy()
    vis[:] = 0.1
    obs = FrameObservation(0, 0.0, body=body, body_visibility=vis, hands=hands)
    res = BodyAnalyzer().analyze([obs], FPS)
    assert res.features["body.present"][0] == 0.0
    assert BodyAnalyzer().summarize(res, slice(None), FPS) == {"body_visible": 0.0}


def test_low_visibility_wrist_is_ignored():
    body, vis, _ = synthetic_body("crossed")
    vis = vis.copy()
    from face_engine.topology import BODY_INDEX

    vis[BODY_INDEX["l_wrist"]] = 0.1
    vis[BODY_INDEX["l_index"]] = 0.1
    obs = FrameObservation(0, 0.0, body=body, body_visibility=vis)
    f = BodyAnalyzer().analyze([obs], FPS).features
    assert f["body.hands_visible"][0] == 1.0
    assert f["body.arms_crossed"][0] == 0.0


def test_lean_in_ignores_resolution_of_neutral_reference():
    clip = synthetic_clip(30, FPS, body_fn=lambda i: synthetic_body("rest"))
    neutral = synthetic_clip(1, FPS, body_fn=lambda i: synthetic_body("rest", scale=3.0))
    res = BodyAnalyzer().analyze(clip, FPS, neutral=neutral)
    assert res.baseline["method"] == "neutral_reference"
    assert np.nanmax(np.abs(res.features["body.lean_in"])) < 1e-9
