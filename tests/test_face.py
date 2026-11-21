import numpy as np
import pytest

from face_engine.analyzers.face import AU_NAMES, FaceAnalyzer
from face_engine.observations import FrameObservation
from face_engine.sources.synthetic import random_identity, synthetic_clip, synthetic_face

from conftest import FPS, face_clip

POSES = [dict(), dict(yaw=25, pitch=-10, roll=8), dict(yaw=-30, pitch=12, iod_px=60)]


def single(expr=None, **kw):
    frames = synthetic_clip(1, FPS, lambda i: synthetic_face(expr, **kw))
    return {k: v[0] for k, v in FaceAnalyzer().analyze(frames, FPS).features.items()}


@pytest.mark.parametrize("pose", POSES)
def test_neutral_face_has_no_action_units(pose):
    f = single(None, **pose)
    assert max(f[f"au.{au}"] for au in AU_NAMES) < 0.05
    assert f["face.expressivity"] < 0.02


@pytest.mark.parametrize("pose", POSES)
def test_head_pose_is_recovered(pose):
    f = single(None, **pose)
    for axis in ("yaw", "pitch", "roll"):
        assert f[f"head.{axis}"] == pytest.approx(pose.get(axis, 0.0), abs=0.5)


# primitive -> (AUs expected high, AUs expected to stay low)
CASES = {
    "brow_raise": (("AU01", "AU02"), ("AU04", "AU12")),
    "brow_lower": (("AU04",), ("AU01", "AU02")),
    "eye_widen": (("AU05",), ("AU07",)),
    "cheek_raise": (("AU06",), ("AU07", "AU12")),
    "smile": (("AU12",), ("AU15", "AU04")),
    "frown": (("AU15",), ("AU12",)),
    "jaw_drop": (("AU26", "AU25"), ("AU12", "AU01")),
    "lip_press": (("AU23",), ("AU25", "AU26")),
    "nose_wrinkle": (("AU09",), ("AU12",)),
    "upper_lip_raise": (("AU10",), ("AU12", "AU26")),
}


@pytest.mark.parametrize("pose", POSES)
@pytest.mark.parametrize("primitive", CASES)
def test_each_primitive_activates_its_action_units(primitive, pose):
    high, low = CASES[primitive]
    f = single({primitive: 1.0}, **pose)
    for au in high:
        assert f[f"au.{au}"] > 0.7, au
    for au in low:
        assert f[f"au.{au}"] < 0.2, au


def test_intensity_scales_with_amount():
    vals = [single({"smile": a})["au.AU12"] for a in (0.25, 0.5, 0.75)]
    assert vals == pytest.approx([0.25, 0.5, 0.75], abs=0.05)


@pytest.mark.parametrize(
    "expr, label",
    [
        ({"smile": 1, "cheek_raise": 1}, "happiness"),
        ({"brow_raise": 1, "eye_widen": 1, "jaw_drop": 1}, "surprise"),
        ({"brow_inner_raise": 1, "brow_lower": 0.6, "frown": 1}, "sadness"),
        ({"nose_wrinkle": 1, "upper_lip_raise": 1}, "disgust"),
        ({"smile_l": 1}, "contempt"),
    ],
)
def test_expression_prototypes(expr, label):
    f = single(expr)
    scores = {k[5:]: v for k, v in f.items() if k.startswith("expr.")}
    assert max(scores, key=scores.get) == label
    assert scores[label] > 0.5


def test_duchenne_vs_social_smile():
    duchenne = single({"smile": 1, "cheek_raise": 1})
    social = single({"smile": 1})
    assert duchenne["smile.duchenne"] > 0.8 and duchenne["smile.social"] < 0.2
    assert social["smile.social"] > 0.8 and social["smile.duchenne"] < 0.2


def test_asymmetry_sign_follows_subject_side():
    assert single({"smile_l": 1})["asym.mouth"] > 0.8
    assert single({"smile_r": 1})["asym.mouth"] < -0.8
    assert single({"wink_r": 1})["asym.eye"] > 0.8


def test_gaze_offset():
    f = single({"gaze_h": 0.8}, yaw=15)
    assert f["gaze.h"] == pytest.approx(0.8, abs=0.1)
    assert f["gaze.averted"] == 1.0


def test_population_baseline_for_single_photo():
    frames = synthetic_clip(1, FPS, lambda i: synthetic_face())
    assert FaceAnalyzer().analyze(frames, FPS).baseline["method"] == "population_canonical"


def test_personal_baseline_removes_individual_morphology():
    """Naturally low brows are not 'brow lowering' once the person's own neutral is known."""
    identity = np.zeros_like(random_identity(np.random.default_rng(0)))
    from face_engine.topology import FACE_INDEX

    for n in ("r_brow_inner", "l_brow_inner", "r_brow_mid", "l_brow_mid"):
        identity[FACE_INDEX[n], 1] -= 0.06
    clip = face_clip(lambda t: {"smile": 1.0} if 2 <= t < 3 else {}, identity=identity)
    auto = FaceAnalyzer().analyze(clip, FPS)
    assert auto.baseline["method"] == "auto_calm_frames"
    assert np.nanmax(auto.features["au.AU04"]) < 0.1
    assert np.nanmax(auto.features["au.AU12"]) > 0.9

    photo = synthetic_clip(1, FPS, lambda i: synthetic_face(identity=identity))
    assert FaceAnalyzer().analyze(photo, FPS).features["au.AU04"][0] > 0.4
    with_ref = FaceAnalyzer().analyze(photo, FPS, neutral=photo)
    assert with_ref.baseline["method"] == "neutral_reference"
    assert with_ref.features["au.AU04"][0] < 0.05


def test_baseline_is_robust_when_expression_dominates_part_of_clip():
    clip = face_clip(lambda t: {"brow_raise": 1.0} if t < 2.5 else {}, noise_px=0.3)
    res = FaceAnalyzer().analyze(clip, FPS)
    assert np.nanmean(res.features["au.AU01"][: int(2 * FPS)]) > 0.8
    assert np.nanmean(res.features["au.AU01"][int(3 * FPS) :]) < 0.1


def test_blinks_and_squints_are_separated():
    blinks_at = (1.0, 2.5, 4.0)
    clip = face_clip(
        lambda t: {"blink": 1.0} if any(abs(t - b) < 0.1 for b in blinks_at) else {},
        noise_px=0.2,
    )
    res = FaceAnalyzer().analyze(clip, FPS)
    blinks = [e for e in res.events if e["type"] == "blink"]
    assert [round(e["peak_s"]) for e in blinks] == [1, 2, 4] or len(blinks) == 3
    assert not [e for e in res.events if e.get("au") == "AU07"]
    summary = FaceAnalyzer().summarize(res, slice(None), FPS)
    assert summary["blinks"] == 3
    assert summary["blink_rate_per_min"] == pytest.approx(30.0)


def test_long_closure_is_not_a_blink():
    clip = face_clip(lambda t: {"blink": 1.0} if 2 <= t < 3.5 else {})
    types = [e["type"] for e in FaceAnalyzer().analyze(clip, FPS).events]
    assert "eye_closure" in types and "blink" not in types


def test_brief_expression_is_flagged():
    clip = face_clip(lambda t: {"smile_l": 1.0} if 3 <= t < 3.3 else {})
    smiles = [e for e in FaceAnalyzer().analyze(clip, FPS).events if e.get("au") == "AU12"]
    assert len(smiles) == 1 and smiles[0]["brief"] is True


def test_head_nod_and_shake_events():
    def nod(t):
        return 10 * np.sin(2 * np.pi * 2 * t) if 2 <= t < 3 else 0.0

    rng = np.random.default_rng(0)
    frames = synthetic_clip(
        int(5 * FPS), FPS, lambda i: synthetic_face(pitch=nod(i / FPS), rng=rng, noise_px=0.2)
    )
    types = [e["type"] for e in FaceAnalyzer().analyze(frames, FPS).events]
    assert types.count("head_nod") == 1 and "head_shake" not in types


def test_missing_face_frames():
    frames = synthetic_clip(int(3 * FPS), FPS, lambda i: None if 30 <= i < 45 else synthetic_face())
    f = FaceAnalyzer().analyze(frames, FPS).features
    assert f["face.present"][35] == 0.0
    assert np.isnan(f["au.AU12"][35])
    assert not np.isnan(f["au.AU12"][10])


def test_face_with_nan_anchor_is_treated_as_missing():
    face = synthetic_face()
    face[0] = np.nan
    res = FaceAnalyzer().analyze([FrameObservation(0, 0.0, face=face)], FPS)
    assert res.features["face.present"][0] == 0.0


def test_missing_iris_points_only_disable_gaze():
    from face_engine.topology import FACE_INDEX

    face = synthetic_face({"smile": 1.0})
    face[[FACE_INDEX["r_iris"], FACE_INDEX["l_iris"]]] = np.nan
    f = FaceAnalyzer().analyze([FrameObservation(0, 0.0, face=face)], FPS).features
    assert f["au.AU12"][0] > 0.9
    assert np.isnan(f["gaze.h"][0])


def test_blink_count_excludes_long_closures_and_respects_segments():
    def expr(t):
        if any(abs(t - b) < 0.1 for b in (1.0, 2.0, 4.95)) or 3.0 <= t < 3.8:
            return {"blink": 1.0}
        return {}

    clip = face_clip(expr)
    fa = FaceAnalyzer()
    res = fa.analyze(clip, FPS)
    assert fa.summarize(res, slice(None), FPS)["blinks"] == 3
    # The blink around 4.95 s straddles the 5 s boundary and is counted once.
    first = fa.summarize(res, slice(0, int(5 * FPS)), FPS)["blinks"]
    second = fa.summarize(res, slice(int(5 * FPS), None), FPS)["blinks"]
    assert first + second == 3
