"""From-scratch face analyzer.

Pipeline per frame:
  1. Similarity-align the rigid anchor points onto the canonical face
     (Umeyama). The rotation gives head pose; the aligned shape is pose- and
     scale-free, in IOD units.
  2. Read a small set of geometric measurements off the aligned shape
     (brow heights, lid opening, lip-corner height, ...).
Then over the whole clip:
  3. Estimate the person's own neutral ("baseline") measurements.
  4. Deviations from the baseline are mapped to FACS-like action-unit
     intensities (0..1), then to expression prototypes, asymmetry, gaze, blinks.
"""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from face_engine import temporal as T
from face_engine.analyzers.base import (
    AnalyzerResult,
    clip01,
    fraction,
    mask_absent,
    measurement_table,
    nanstat,
    rnd,
)
from face_engine.config import FaceConfig
from face_engine.geometry import dist, head_angles, umeyama
from face_engine.topology import CANONICAL_FACE, FACE_ANCHORS, FACE_INDEX, SIDES
from face_engine.observations import FrameObservation, Table

_ANCHORS = [FACE_INDEX[n] for n in FACE_ANCHORS]

# Prototype displays (after EMFACS). Scores measure similarity of the facial
# configuration to the prototype, not a felt emotion.
EXPRESSIONS: dict[str, tuple[str, ...]] = {
    "happiness": ("AU06", "AU12"),
    "sadness": ("AU01", "AU04", "AU15"),
    "surprise": ("AU01", "AU02", "AU05", "AU26"),
    "fear": ("AU01", "AU02", "AU04", "AU05", "AU20"),
    "anger": ("AU04", "AU07", "AU23"),
    "disgust": ("AU09", "AU10"),
}

# Prototypes that do not co-occur with a lip-corner smile.
SMILE_INHIBITED = frozenset({"sadness", "anger", "disgust"})

AU_NAMES: dict[str, str] = {
    "AU01": "inner brow raiser",
    "AU02": "outer brow raiser",
    "AU04": "brow lowerer",
    "AU05": "upper lid raiser (eyes widen)",
    "AU06": "cheek raiser (lower lid pushed up)",
    "AU07": "lid tightener (squint)",
    "AU09": "nose wrinkler",
    "AU10": "upper lip raiser",
    "AU12": "lip corner puller (smile)",
    "AU15": "lip corner depressor",
    "AU17": "chin raiser",
    "AU20": "lip stretcher",
    "AU23": "lip tightener / presser",
    "AU25": "lips part",
    "AU26": "jaw drop",
}
LATERAL_AUS = ("AU01", "AU02", "AU04", "AU06", "AU12", "AU15")


def align_face(points: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """Return (aligned points in IOD units, head rotation head->camera, IOD in pixels).

    The similarity fit fixes the rotation; the scale is then re-anchored on the
    eye centres. Detectors distort the outer face (temples, depth) under strong
    head roll, which biases the fitted scale by 10-15% and would show up as fake
    action units; the eye distance stays reliable.
    """
    sim = umeyama(points[_ANCHORS], CANONICAL_FACE[_ANCHORS])
    aligned = sim.apply(points)
    iod = float(np.linalg.norm(_eye_centre(aligned, "l") - _eye_centre(aligned, "r")))
    origin = aligned[FACE_INDEX["nose_bridge"]]
    return (aligned - origin) / iod, sim.rotation.T, iod / sim.scale


def _eye_centre(a: np.ndarray, side: str) -> np.ndarray:
    return (a[FACE_INDEX[f"{side}_eye_outer"]] + a[FACE_INDEX[f"{side}_eye_inner"]]) / 2


def face_measurements(a: np.ndarray) -> dict[str, float]:
    """Geometric measurements of an aligned face (IOD units, y up)."""

    def p(name: str) -> np.ndarray:
        return a[FACE_INDEX[name]]

    m: dict[str, float] = {}
    lip_mid_y = (p("upper_lip_inner")[1] + p("lower_lip_inner")[1]) / 2
    for s in SIDES:
        outer, inner = p(f"{s}_eye_outer"), p(f"{s}_eye_inner")
        centre = (outer + inner) / 2
        m[f"brow_inner_h_{s}"] = p(f"{s}_brow_inner")[1] - centre[1]
        m[f"brow_outer_h_{s}"] = (p(f"{s}_brow_mid")[1] + p(f"{s}_brow_outer")[1]) / 2 - centre[1]
        up1, lo1, up2, lo2 = (p(f"{s}_lid_{k}") for k in ("up1", "lo1", "up2", "lo2"))
        m[f"eye_open_{s}"] = ((up1 - lo1)[1] + (up2 - lo2)[1]) / 2
        m[f"lower_lid_h_{s}"] = (lo1[1] + lo2[1]) / 2 - centre[1]
        m[f"nose_eye_{s}"] = dist(p(f"{s}_alar"), inner)
        m[f"corner_h_{s}"] = p(f"{s}_mouth_corner")[1] - lip_mid_y
        # Eye axis pointing to image right, for both eyes.
        axis = (outer - inner) if s == "l" else (inner - outer)
        half = np.linalg.norm(axis) / 2
        iris = p(f"{s}_iris") - centre
        m[f"gaze_h_{s}"] = float(iris @ axis / (2 * half * half))
        m[f"gaze_v_{s}"] = iris[1] / half
    m["brow_gap"] = p("l_brow_inner")[0] - p("r_brow_inner")[0]
    m["sub_lip"] = p("subnasale")[1] - p("upper_lip_top")[1]
    m["lip_thick"] = (p("upper_lip_top")[1] - p("upper_lip_inner")[1]) + (
        p("lower_lip_inner")[1] - p("lower_lip_bottom")[1]
    )
    m["lip_gap"] = p("upper_lip_inner")[1] - p("lower_lip_inner")[1]
    m["mouth_width"] = dist(p("r_mouth_corner"), p("l_mouth_corner"))
    m["jaw_open"] = dist(p("nose_tip"), p("chin"))
    m["lip_chin"] = p("lower_lip_bottom")[1] - p("chin")[1]
    return {k: float(v) for k, v in m.items()}


POSE_KEYS = ("head_yaw", "head_pitch", "head_roll", "iod_px")
MEASURE_KEYS = tuple(face_measurements(CANONICAL_FACE))
_NAN_ROW = {k: float("nan") for k in MEASURE_KEYS + POSE_KEYS}


def measure_frame(face: np.ndarray | None) -> dict[str, float]:
    if face is None or np.isnan(face[_ANCHORS]).any():
        return dict(_NAN_ROW)
    aligned, rotation, iod_px = align_face(face)
    yaw, pitch, roll = head_angles(rotation)
    row = face_measurements(aligned)
    row.update(head_yaw=yaw, head_pitch=pitch, head_roll=roll, iod_px=iod_px)
    return row


class FaceAnalyzer:
    name = "face"

    def __init__(self, config: FaceConfig | None = None) -> None:
        self.cfg = config or FaceConfig()
        c = self.cfg
        # Rough per-measurement scale used to rank frames by "calmness".
        self._scale = {
            **{f"brow_inner_h_{s}": c.brow_raise_full for s in SIDES},
            **{f"brow_outer_h_{s}": c.brow_raise_full for s in SIDES},
            **{f"eye_open_{s}": c.eye_open_scale for s in SIDES},
            **{f"lower_lid_h_{s}": c.lower_lid_raise_full for s in SIDES},
            **{f"nose_eye_{s}": c.nose_wrinkle_full for s in SIDES},
            **{f"corner_h_{s}": c.corner_raise_full for s in SIDES},
            "brow_gap": c.brow_gap_full,
            "sub_lip": c.upper_lip_raise_full,
            "lip_thick": c.lip_press_full,
            "lip_gap": c.lip_part_full,
            "mouth_width": c.mouth_stretch_full,
            "jaw_open": c.jaw_drop_full,
        }

    # ------------------------------------------------------------------ public
    def analyze(
        self,
        frames: Sequence[FrameObservation],
        fps: float,
        neutral: Sequence[FrameObservation] = (),
    ) -> AnalyzerResult:
        m = measurement_table([measure_frame(f.face) for f in frames])
        times = np.array([f.time_s for f in frames], dtype=float)
        neutral_m = measurement_table([measure_frame(f.face) for f in neutral])
        compensated = self._compensate_pose(m, neutral_m, fps)
        baseline = self._baseline(m, neutral_m)
        baseline["pose_compensation"] = compensated
        features = self._interpret(m, baseline["measurements"], baseline["head_pose"], fps)
        events = self._events(features, times, fps) if len(frames) > 1 else []
        return AnalyzerResult(features, baseline, events, GLOSSARY)

    def summarize(self, result: AnalyzerResult, sl: slice, fps: float) -> dict[str, Any]:
        f = {k: v[sl] for k, v in result.features.items()}
        present = f["face.present"] > 0
        if not present.any():
            return {"face_visible": 0.0}
        n_frames = len(present)
        out: dict[str, Any] = {"face_visible": fraction(present, np.ones_like(present))}
        peaks = {au: nanstat(np.max, f[f"au.{au}"]) for au in AU_NAMES}
        out["action_units"] = {
            au: {"mean": nanstat(np.mean, f[f"au.{au}"]), "peak": peak}
            for au, peak in peaks.items()
            if (peak or 0) >= 0.2
        }
        expr = {k: nanstat(np.mean, f[f"expr.{k}"]) for k in (*EXPRESSIONS, "contempt")}
        top = max(expr, key=lambda k: expr[k] or 0)
        out["expressions_mean"] = expr
        out["dominant_expression"] = top if (expr[top] or 0) >= 0.15 else "neutral"
        out["expressivity_mean"] = nanstat(np.mean, f["face.expressivity"])
        out["smile"] = {
            "duchenne_mean": nanstat(np.mean, f["smile.duchenne"]),
            "social_mean": nanstat(np.mean, f["smile.social"]),
        }
        out["asymmetry_mean"] = {
            k: nanstat(np.mean, f[f"asym.{k}"]) for k in ("mouth", "brow", "eye")
        }
        duration_min = n_frames / fps / 60.0
        start, stop, _ = sl.indices(len(result.features["face.present"]))
        blinks = sum(
            1 for e in result.events if e["type"] == "blink" and start <= T.event_span(e)[0] < stop
        )
        out["blinks"] = blinks
        out["blink_rate_per_min"] = rnd(blinks / duration_min) if n_frames > 1 else None
        out["head"] = {
            "yaw_mean": nanstat(np.mean, f["head.yaw_rel"]),
            "pitch_mean": nanstat(np.mean, f["head.pitch_rel"]),
            "roll_mean": nanstat(np.mean, f["head.roll_rel"]),
            "movement_std_deg": nanstat(
                np.mean, np.array([np.nanstd(f[f"head.{a}_rel"]) for a in ("yaw", "pitch")])
            ),
        }
        out["gaze_averted_share"] = fraction(f["gaze.averted"] > 0, present)
        out["speaking_share"] = fraction(f["mouth.speaking"] > 0, present)
        out["reliability_mean"] = nanstat(np.mean, f["face.reliability"])
        return out

    # ---------------------------------------------------------- pose model
    def _compensate_pose(self, m: Table, neutral_m: Table, fps: float) -> bool:
        """Make the neutral a function of head pose, fitted on the clip itself.

        2-D landmark detectors foreshorten the face when the head pitches or
        turns, so a fixed neutral turns pose into fake action units. Frames are
        grouped into head-pose bins; the median of each bin is that pose's
        typical face (expressions are brief, so medians ignore them, and every
        pose counts the same however long it was held). A quadratic in
        (yaw, pitch) through the bin medians gives the pose-dependent part of
        each measurement, which is subtracted from the clip and from the neutral
        reference, leaving values "as if at the typical pose".
        """
        c = self.cfg
        valid = ~np.isnan(m["head_yaw"])
        if not c.pose_compensation or valid.sum() < c.pose_min_seconds * fps:
            return False
        yaw0, pitch0 = np.nanmedian(m["head_yaw"]), np.nanmedian(m["head_pitch"])
        spread = max(np.nanstd(m["head_yaw"]), np.nanstd(m["head_pitch"]))
        if spread < c.pose_min_spread_deg:
            return False

        def design(t: Table) -> np.ndarray:
            y = np.radians(t["head_yaw"] - yaw0)
            p = np.radians(t["head_pitch"] - pitch0)
            return np.stack([y, p, y * y, p * p, y * p], axis=1)

        x = design(m)
        idx = np.flatnonzero(valid)
        keys = np.floor(x[idx, :2] / np.radians(c.pose_bin_deg)).astype(int)
        _, bin_of, counts = np.unique(keys, axis=0, return_inverse=True, return_counts=True)
        bin_of = bin_of.ravel()
        min_count = max(3, int(c.pose_bin_min_s * fps))
        bins = [idx[bin_of == b] for b in np.flatnonzero(counts >= min_count)]
        n_terms = 5 if len(bins) >= 8 else 2 if len(bins) >= 3 else 0
        if not n_terms:
            return False
        xb = np.array([np.median(x[rows], axis=0) for rows in bins])[:, :n_terms]
        xb1 = np.column_stack([np.ones(len(bins)), xb])
        for k in MEASURE_KEYS:
            yb = np.array([np.nanmedian(m[k][rows]) for rows in bins])
            ok = ~np.isnan(yb)
            if ok.sum() <= n_terms:
                continue
            beta = np.linalg.lstsq(xb1[ok], yb[ok], rcond=None)[0][1:]
            m[k] = m[k] - x[:, :n_terms] @ beta
            if neutral_m:
                neutral_m[k] = neutral_m[k] - design(neutral_m)[:, :n_terms] @ beta
        return True

    # ---------------------------------------------------------------- baseline
    def _baseline(self, m: Table, neutral_m: Table) -> dict[str, Any]:
        valid = ~np.isnan(m["head_yaw"])
        nvalid = ~np.isnan(neutral_m["head_yaw"]) if neutral_m else np.zeros(0, bool)
        if nvalid.any():
            rows, method = nvalid, "neutral_reference"
            source = neutral_m
        elif valid.sum() >= 2:
            rows, method = self._calm_frames(m, valid), "auto_calm_frames"
            source = m
        else:
            canon = face_measurements(CANONICAL_FACE)
            return {
                "method": "population_canonical",
                "frames_used": 0,
                "measurements": canon,
                "head_pose": {"yaw": 0.0, "pitch": 0.0, "roll": 0.0},
            }
        meas = {k: float(np.nanmedian(source[k][rows])) for k in MEASURE_KEYS}
        pose = {a: float(np.nanmedian(source[f"head_{a}"][rows])) for a in ("yaw", "pitch", "roll")}
        return {
            "method": method,
            "frames_used": int(rows.sum()),
            "measurements": meas,
            "head_pose": pose,
        }

    def _calm_frames(self, m: Table, valid: np.ndarray) -> np.ndarray:
        """Frames closest to the clip median (in scale units) and roughly frontal."""
        med = {k: np.nanmedian(m[k][valid]) for k in self._scale}
        score = sum(np.abs(m[k] - med[k]) / s for k, s in self._scale.items())
        yaw_off = np.abs(m["head_yaw"] - np.nanmedian(m["head_yaw"][valid]))
        ok = valid & (yaw_off < self.cfg.reliable_yaw_deg)
        if not ok.any():
            ok = valid
        cut = np.quantile(score[ok], self.cfg.baseline_quantile)
        return ok & (score <= cut)

    # -------------------------------------------------------------- features
    def _interpret(
        self, m: Table, base: dict[str, float], base_pose: dict[str, float], fps: float
    ) -> Table:
        c = self.cfg
        w = T.window_frames(fps, c.smoothing_s)
        s = {k: T.smooth(v, w) for k, v in m.items()}
        d = {k: s[k] - base[k] for k in MEASURE_KEYS}
        present = ~np.isnan(m["head_yaw"])
        f: Table = {"face.present": present.astype(float)}

        for a in ("yaw", "pitch", "roll"):
            f[f"head.{a}"] = s[f"head_{a}"]
            f[f"head.{a}_rel"] = s[f"head_{a}"] - base_pose[a]
        f["face.reliability"] = clip01(
            1.0 - (np.abs(f["head.yaw_rel"]) - c.reliable_yaw_deg) / (2 * c.reliable_yaw_deg)
        )

        au: dict[str, np.ndarray] = {}
        for side in SIDES:
            # Eye opening is judged against the person's own neutral opening.
            base_open = max(base[f"eye_open_{side}"], 1e-6)
            f[f"eye.closure_{side}"] = clip01(1.0 - s[f"eye_open_{side}"] / base_open)
            rel_open = d[f"eye_open_{side}"] / base_open
            au[f"AU01_{side}"] = clip01(d[f"brow_inner_h_{side}"] / c.brow_raise_full)
            au[f"AU02_{side}"] = clip01(d[f"brow_outer_h_{side}"] / c.brow_raise_full)
            # Brows drawn together is the key cue: in the sad brow (AU1+AU4) the
            # inner brows rise while still being pulled toward each other.
            au[f"AU04_{side}"] = clip01(
                np.maximum(
                    -d[f"brow_inner_h_{side}"] / c.brow_lower_full, -d["brow_gap"] / c.brow_gap_full
                )
            )
            au[f"AU05_{side}"] = clip01(rel_open / c.eye_widen_full_rel)
            # Lid geometry is meaningless while the eye is (nearly) shut, so the
            # lid-based units AU6/AU7 are blanked around blinks.
            near_blink = T.dilate(f[f"eye.closure_{side}"] >= c.blink_closure, w)
            au[f"AU06_{side}"] = np.where(
                near_blink, 0.0, clip01(d[f"lower_lid_h_{side}"] / c.lower_lid_raise_full)
            )
            # Squint, not a blink: fades out once the eye is mostly closed. The part
            # of the narrowing explained by the lower lid rising (AU6) is removed.
            narrowing = -(d[f"eye_open_{side}"] + d[f"lower_lid_h_{side}"]) / base_open
            squint = clip01(narrowing / c.lid_tighten_full_rel)
            au[f"AU07_{side}"] = np.where(near_blink, 0.0, squint)
            au[f"AU09_{side}"] = clip01(-d[f"nose_eye_{side}"] / c.nose_wrinkle_full)
            au[f"AU12_{side}"] = clip01(d[f"corner_h_{side}"] / c.corner_raise_full)
            au[f"AU15_{side}"] = clip01(-d[f"corner_h_{side}"] / c.corner_depress_full)
        closure = (f["eye.closure_r"] + f["eye.closure_l"]) / 2
        f["eye.closure"] = closure
        for code in {k[:-2] for k in au}:
            au[code] = (au[f"{code}_r"] + au[f"{code}_l"]) / 2
        au["AU10"] = clip01(-d["sub_lip"] / c.upper_lip_raise_full)
        au["AU17"] = clip01(-d["lip_chin"] / c.chin_raise_full)
        au["AU20"] = clip01(d["mouth_width"] / c.mouth_stretch_full) * (1.0 - au["AU12"])
        au["AU23"] = clip01(-d["lip_thick"] / c.lip_press_full)
        au["AU25"] = clip01(d["lip_gap"] / c.lip_part_full)
        au["AU26"] = clip01(d["jaw_open"] / c.jaw_drop_full)

        for code in AU_NAMES:
            f[f"au.{code}"] = au[code]
        for code in LATERAL_AUS:
            f[f"au.{code}_r"], f[f"au.{code}_l"] = au[f"{code}_r"], au[f"{code}_l"]

        for name, parts in EXPRESSIONS.items():
            stack = np.stack([au[p] for p in parts])
            score = stack.mean(axis=0) * (stack >= 0.2).mean(axis=0)
            if name in SMILE_INHIBITED:
                # A broad smile also raises the nose wings, lifts the upper lip and
                # thins the lips (AU9/10/23 proxies); those prototypes exclude a smile.
                score = score * (1.0 - np.maximum(au["AU12"], f["expr.happiness"]))
            f[f"expr.{name}"] = score
        f["expr.contempt"] = np.abs(au["AU12_l"] - au["AU12_r"]) * (
            1.0 - np.minimum(au["AU12_l"], au["AU12_r"])
        )
        all_aus = np.stack([au[k] for k in AU_NAMES if k != "AU25"])
        f["face.expressivity"] = np.sqrt((all_aus**2).mean(axis=0))

        f["smile.duchenne"] = np.minimum(au["AU06"], au["AU12"])
        f["smile.social"] = au["AU12"] * (1.0 - au["AU06"])

        f["asym.mouth"] = np.clip((d["corner_h_l"] - d["corner_h_r"]) / c.corner_raise_full, -1, 1)
        brow_l = d["brow_inner_h_l"] + d["brow_outer_h_l"]
        brow_r = d["brow_inner_h_r"] + d["brow_outer_h_r"]
        f["asym.brow"] = np.clip((brow_l - brow_r) / (2 * c.brow_raise_full), -1, 1)
        f["asym.eye"] = np.clip(f["eye.closure_r"] - f["eye.closure_l"], -1, 1)

        gaze_h = (d["gaze_h_r"] + d["gaze_h_l"]) / 2
        gaze_v = (d["gaze_v_r"] + d["gaze_v_l"]) / 2
        # Eye-in-head rotation is ignored while the eyes are closed.
        open_eyes = closure < c.blink_closure
        gaze_h = np.where(open_eyes, gaze_h, 0.0)
        gaze_v = np.where(open_eyes, gaze_v, 0.0)
        f["gaze.h"], f["gaze.v"] = gaze_h, gaze_v
        dir_h = f["head.yaw_rel"] + c.eye_rotation_deg * np.nan_to_num(gaze_h)
        dir_v = f["head.pitch_rel"] + c.eye_rotation_deg * np.nan_to_num(gaze_v)
        f["gaze.dir_h_deg"], f["gaze.dir_v_deg"] = dir_h, dir_v
        f["gaze.averted"] = (np.hypot(dir_h, dir_v) > c.gaze_averted_deg).astype(float)

        lip_std = T.rolling_std(s["lip_gap"], T.window_frames(fps, 0.5))
        f["mouth.activity"] = lip_std
        f["mouth.speaking"] = (lip_std > c.speaking_lip_std).astype(float)

        return mask_absent(f, present, keep="face.present")

    # ---------------------------------------------------------------- events
    def _events(self, f: Table, times: np.ndarray, fps: float) -> list[dict[str, Any]]:
        c = self.cfg
        ev: list[dict[str, Any]] = []
        closed = np.nan_to_num(f["eye.closure"]) >= c.blink_closure
        for span in T.runs(closed):
            dur = (span[1] - span[0]) / fps
            kind = "blink" if dur <= c.blink_max_s else "eye_closure"
            ev.append(T.make_event(kind, span, times, fps, f["eye.closure"]))

        # AU25 (lips part) is left out: it fires constantly during speech.
        sources = [
            (f"au.{code}", {"type": "action_unit", "au": code, "label": label})
            for code, label in AU_NAMES.items()
            if code != "AU25"
        ]
        sources += [
            (f"expr.{name}", {"type": "expression", "expression": name})
            for name in (*EXPRESSIONS, "contempt")
        ]
        # No AU/expression events while the face is turned too far to read reliably.
        w = T.window_frames(fps, c.smoothing_s)
        readable = ~T.dilate(np.nan_to_num(f["face.reliability"]) < 0.5, w)
        for col, extra in sources:
            kind = extra.pop("type")
            signal = np.where(readable, f[col], np.nan)
            for e in T.threshold_events(kind, signal, c.event_threshold, times, fps, **extra):
                e["brief"] = e["duration_s"] < c.brief_event_s
                ev.append(e)
        for e in T.threshold_events("smile", f["au.AU12"], c.event_threshold, times, fps):
            sl = slice(*T.event_span(e))
            e["duchenne"] = bool(np.nanmax(f["au.AU06"][sl]) >= 0.3)
            e["asymmetry"] = rnd(np.nanmean(f["asym.mouth"][sl]))
            ev.append(e)
        ev += T.threshold_events(
            "gaze_averted", f["gaze.averted"], 0.5, times, fps, min_s=0.3, merge_gap_s=0.2
        )
        for axis, kind in (("pitch", "head_nod"), ("yaw", "head_shake")):
            for span in T.oscillations(f[f"head.{axis}_rel"], fps, c.nod_amplitude_deg):
                ev.append(T.make_event(kind, span, times, fps))
        return ev


GLOSSARY: dict[str, str] = {
    "face.present": "1 if a face was detected in the frame.",
    "face.reliability": "0..1; drops as the head turns away from the person's neutral pose "
    "(asymmetry and AU values degrade beyond ~20 deg yaw).",
    "head.yaw|pitch|roll": "Head angles vs camera, degrees. yaw>0 turned to the subject's left, "
    "pitch>0 chin up, roll>0 subject's left eye higher.",
    "head.*_rel": "Same angles relative to the person's own neutral head pose.",
    "eye.closure[_l|_r]": "0 = eye as open as in the neutral face, 1 = fully closed.",
    "au.AUxx": "Geometric proxy of a FACS action unit, intensity 0..1, relative to the person's "
    "neutral face. _l/_r are the subject's left/right sides. "
    + "; ".join(f"{k} {v}" for k, v in AU_NAMES.items()),
    "expr.*": "0..1 similarity of the face configuration to a prototypical display "
    "(happiness, sadness, surprise, fear, anger, disgust, contempt). It describes visible "
    "muscle movement, not what the person feels.",
    "face.expressivity": "RMS of all action units: how far the face is from its neutral.",
    "smile.duchenne": "Smile with cheek raise (AU6+AU12), the 'eye-involving' smile.",
    "smile.social": "Lip-corner smile without cheek raise (AU12 without AU6).",
    "asym.mouth|brow": "-1..1, >0 means the subject's left side moved up more than the right.",
    "asym.eye": "-1..1, >0 means the right eye is more closed than the left.",
    "gaze.h|v": "Iris offset vs neutral, in half eye-widths. h>0 toward image right, v>0 up.",
    "gaze.dir_h_deg|dir_v_deg": "Approximate gaze direction (head + eyes) vs neutral, degrees.",
    "gaze.averted": "1 when the approximate gaze direction is more than 15 deg off neutral.",
    "mouth.activity": "Rolling std of lip opening (IOD units); high while talking.",
    "mouth.speaking": "1 when mouth movement looks like speech. Mouth AUs are less "
    "trustworthy while speaking.",
}
