"""From-scratch body and hands analyzer.

All positions are expressed relative to the shoulder midpoint in shoulder
widths (SW), so the features do not depend on image size or distance to the
camera. The person's own typical posture over the clip is the baseline.
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
    nanmax,
    nanmedian,
    nanmin,
    nanstat,
)
from face_engine.config import BodyConfig
from face_engine.topology import BODY_INDEX, HAND_INDEX_MCP, HAND_PINKY_MCP, HAND_WRIST, SIDES
from face_engine.observations import FrameObservation, Hand, Table

_FACE_PARTS = ("nose", "mouth_l", "mouth_r", "l_ear", "r_ear")
_KEYS = (
    "sw_px",
    "shoulder_roll",
    "lateral_lean",
    "head_x",
    "head_y",
    "neck",
    "wrist_x_l",
    "wrist_y_l",
    "wrist_x_r",
    "wrist_y_r",
    "touch_face_l",
    "touch_face_r",
    "hands_dist",
    "palm_l",
    "palm_r",
)
_NAN_ROW = {k: float("nan") for k in _KEYS}


def palm_facing(points: np.ndarray, side: str) -> float:
    """+1 when the palm faces the camera, -1 when the back of the hand does.

    With the palm toward the camera and fingers up, the thumb of the subject's
    right hand points toward the body midline (image +x); in-plane rotation
    does not change the sign of the 2-D cross product used here.
    """
    a = points[HAND_INDEX_MCP, :2] - points[HAND_WRIST, :2]
    b = points[HAND_PINKY_MCP, :2] - points[HAND_WRIST, :2]
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm < 1e-9:
        return float("nan")
    cross = (a[0] * b[1] - a[1] * b[0]) / norm
    return float(cross if side == "r" else -cross)


def _assign_sides(hands: list[Hand], body: np.ndarray, visible: dict[str, bool]) -> dict[str, Hand]:
    out: dict[str, Hand] = {}
    for hand in hands:
        side = hand.side
        if side is None:
            cands = [s for s in SIDES if visible[f"{s}_wrist"]]
            if not cands:
                continue
            wrist = hand.points[HAND_WRIST, :2]
            side = min(
                cands, key=lambda s: np.linalg.norm(body[BODY_INDEX[f"{s}_wrist"], :2] - wrist)
            )
        out.setdefault(side, hand)
    return out


def measure_frame(obs: FrameObservation, min_visibility: float) -> dict[str, float]:
    if obs.body is None:
        return dict(_NAN_ROW)
    body = obs.body
    vis = obs.body_visibility if obs.body_visibility is not None else np.ones(len(body))
    visible = {n: bool(vis[i] >= min_visibility) for n, i in BODY_INDEX.items()}
    if not (visible["l_shoulder"] and visible["r_shoulder"]):
        return dict(_NAN_ROW)

    def p(n: str) -> np.ndarray:
        return body[BODY_INDEX[n], :2]

    ls, rs = p("l_shoulder"), p("r_shoulder")
    mid, sw = (ls + rs) / 2, float(np.linalg.norm(ls - rs))
    if sw < 1e-6:
        return dict(_NAN_ROW)

    def rel(n: str) -> np.ndarray:
        return (p(n) - mid) / sw if visible[n] else np.array([np.nan, np.nan])

    row = dict(_NAN_ROW)
    row["sw_px"] = sw
    row["shoulder_roll"] = float(np.degrees(np.arctan2(ls[1] - rs[1], ls[0] - rs[0])))
    if visible["l_hip"] and visible["r_hip"]:
        torso = mid - (p("l_hip") + p("r_hip")) / 2
        row["lateral_lean"] = float(np.degrees(np.arctan2(torso[0], torso[1])))
    row["head_x"], row["head_y"] = rel("nose")
    ears = [rel(e)[1] for e in ("l_ear", "r_ear") if visible[e]]
    row["neck"] = float(np.mean(ears)) if ears else float("nan")
    for s in SIDES:
        row[f"wrist_x_{s}"], row[f"wrist_y_{s}"] = rel(f"{s}_wrist")

    hands = _assign_sides(obs.hands, body, visible)
    hand_pts: dict[str, np.ndarray] = {}
    for s in SIDES:
        if s in hands:
            hand_pts[s] = hands[s].points[:, :2]
            row[f"palm_{s}"] = palm_facing(hands[s].points, s)
        else:
            pts = [p(n) for n in (f"{s}_wrist", f"{s}_index") if visible[n]]
            if pts:
                hand_pts[s] = np.array(pts)
    face_pts = np.array([p(n) for n in _FACE_PARTS if visible[n]]).reshape(-1, 2)
    for s, pts in hand_pts.items():
        if len(face_pts):
            row[f"touch_face_{s}"] = _min_dist(pts, face_pts) / sw
    if len(hand_pts) == 2:
        row["hands_dist"] = _min_dist(hand_pts["l"], hand_pts["r"]) / sw
    return row


def _min_dist(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.min(np.linalg.norm(a[:, None, :] - b[None, :, :], axis=-1)))


class BodyAnalyzer:
    name = "body"

    def __init__(self, config: BodyConfig | None = None) -> None:
        self.cfg = config or BodyConfig()

    def analyze(
        self,
        frames: Sequence[FrameObservation],
        fps: float,
        neutral: Sequence[FrameObservation] = (),
    ) -> AnalyzerResult:
        c = self.cfg
        m = measurement_table([measure_frame(f, c.min_visibility) for f in frames])
        times = np.array([f.time_s for f in frames], dtype=float)
        neutral_m = measurement_table([measure_frame(f, c.min_visibility) for f in neutral])
        baseline = self._baseline(m, neutral_m)
        features = self._interpret(m, baseline["measurements"], fps)
        events = self._events(features, times, fps) if len(frames) > 1 else []
        return AnalyzerResult(features, baseline, events, GLOSSARY)

    def _baseline(self, m: Table, neutral_m: Table) -> dict[str, Any]:
        keys = ("sw_px", "shoulder_roll", "lateral_lean", "neck", "arm_span")
        for table, method in ((neutral_m, "neutral_reference"), (m, "clip_median")):
            if table and (~np.isnan(table["sw_px"])).any():
                span = np.abs(table["wrist_x_l"] - table["wrist_x_r"])
                values = {**table, "arm_span": span}
                meas = {k: nanmedian(values[k]) for k in keys}
                # Pixel size depends on resolution and zoom, so it always comes from
                # the clip itself, even when a separate neutral recording is given.
                meas["sw_px"] = nanmedian(m["sw_px"])
                n = int((~np.isnan(table["sw_px"])).sum())
                return {"method": method, "frames_used": n, "measurements": meas}
        return {"method": "none", "frames_used": 0, "measurements": {k: float("nan") for k in keys}}

    def _interpret(self, m: Table, base: dict[str, float], fps: float) -> Table:
        c = self.cfg
        w = T.window_frames(fps, c.smoothing_s)
        s = {k: T.smooth(v, w) for k, v in m.items()}
        present = ~np.isnan(m["sw_px"])
        f: Table = {"body.present": present.astype(float)}

        f["body.lean_in"] = s["sw_px"] / base["sw_px"] - 1.0
        f["body.shoulder_roll_rel"] = s["shoulder_roll"] - base["shoulder_roll"]
        f["body.lateral_lean_rel"] = s["lateral_lean"] - np.nan_to_num(base["lateral_lean"])
        f["body.shrug"] = clip01(-(s["neck"] - base["neck"]) / c.shrug_full)

        speeds = []
        for side in SIDES:
            x, y = s[f"wrist_x_{side}"], s[f"wrist_y_{side}"]
            f[f"body.hand_height_{side}"] = y
            speeds.append(np.hypot(T.derivative(x, fps), T.derivative(y, fps)))
        speed = nanmax(*speeds)
        f["body.gesture_speed"] = speed
        f["body.gesture_activity"] = clip01(speed / c.gesture_speed_full)
        f["body.gesturing"] = (np.nan_to_num(speed) > c.gesture_speed).astype(float)
        f["body.hands_visible"] = sum((~np.isnan(m[f"wrist_x_{sd}"])).astype(float) for sd in SIDES)

        lx, rx = s["wrist_x_l"], s["wrist_x_r"]
        ly, ry = s["wrist_y_l"], s["wrist_y_r"]
        span = np.abs(lx - rx)
        f["body.arm_openness"] = span
        f["body.arm_openness_rel"] = span - base["arm_span"]
        with np.errstate(invalid="ignore"):
            crossed = (
                (lx < rx) & (ly < -0.2) & (ry < -0.2) & (np.abs(lx) < 1.0) & (np.abs(rx) < 1.0)
            )
            joined = (s["hands_dist"] < c.hands_joined_dist) & ~crossed
            touch = nanmin(s["touch_face_l"], s["touch_face_r"]) < c.face_touch_dist
            palm = nanmax(s["palm_l"], s["palm_r"])
        f["body.arms_crossed"] = crossed.astype(float)
        f["body.hands_joined"] = joined.astype(float)
        f["body.face_touch"] = touch.astype(float)
        f["body.palm_to_camera"] = palm
        # Hands resting on the arms or on each other are not "shown" palms, and
        # hand landmarks are least reliable exactly in those configurations.
        shown = (np.nan_to_num(palm, nan=-1.0) > c.palm_facing) & ~crossed & ~joined
        f["body.open_palms"] = shown.astype(float)

        return mask_absent(f, present, keep="body.present")

    def _events(self, f: Table, times: np.ndarray, fps: float) -> list[dict[str, Any]]:
        c = self.cfg
        ev: list[dict[str, Any]] = []
        for col, kind in (
            ("body.gesturing", "gesture"),
            ("body.face_touch", "face_touch"),
            ("body.arms_crossed", "arms_crossed"),
            ("body.hands_joined", "hands_joined"),
            ("body.open_palms", "open_palms"),
        ):
            ev += T.threshold_events(
                kind, f[col], 0.5, times, fps, min_s=c.min_event_s, merge_gap_s=c.merge_gap_s
            )
        for e in ev:
            if e["type"] == "gesture":
                e["peak_speed_sw_s"] = nanstat(
                    np.max, f["body.gesture_speed"][slice(*T.event_span(e))]
                )
        ev += T.threshold_events("shrug", f["body.shrug"], 0.5, times, fps)
        lean = f["body.lean_in"]
        pivots = T.zigzag(lean, c.posture_shift)
        for a, b in zip(pivots, pivots[1:]):
            delta = float(lean[b] - lean[a])
            ev.append(
                T.make_event(
                    "posture_shift",
                    (a, b + 1),
                    times,
                    fps,
                    direction="toward_camera" if delta > 0 else "away_from_camera",
                    delta=round(delta, 3),
                )
            )
        return ev

    def summarize(self, result: AnalyzerResult, sl: slice, fps: float) -> dict[str, Any]:
        f = {k: v[sl] for k, v in result.features.items()}
        present = f["body.present"] > 0
        if not present.any():
            return {"body_visible": 0.0}

        def share(col: str) -> float | None:
            return fraction(np.nan_to_num(f[col]) > 0.5, present)

        return {
            "body_visible": fraction(present, np.ones_like(present)),
            "hands_visible_mean": nanstat(np.mean, f["body.hands_visible"]),
            "gesturing_share": share("body.gesturing"),
            "gesture_activity_mean": nanstat(np.mean, f["body.gesture_activity"]),
            "face_touch_share": share("body.face_touch"),
            "arms_crossed_share": share("body.arms_crossed"),
            "hands_joined_share": share("body.hands_joined"),
            "open_palms_share": share("body.open_palms"),
            "arm_openness_mean": nanstat(np.mean, f["body.arm_openness"]),
            "arm_openness_rel_mean": nanstat(np.mean, f["body.arm_openness_rel"]),
            "lean_in_mean": nanstat(np.mean, f["body.lean_in"]),
            "shoulder_roll_rel_mean": nanstat(np.mean, f["body.shoulder_roll_rel"]),
            "shrug_peak": nanstat(np.max, f["body.shrug"]),
        }


GLOSSARY: dict[str, str] = {
    "body.*": "Body positions are relative to the shoulder midpoint in shoulder widths (SW).",
    "body.lean_in": "Apparent torso size vs the person's typical size; >0 = leaning toward camera.",
    "body.shoulder_roll_rel": "Shoulder-line tilt vs typical, degrees; >0 = subject's left shoulder higher.",
    "body.lateral_lean_rel": "Torso sideways lean vs typical, degrees (needs hips in view).",
    "body.shrug": "0..1, shoulders raised toward the ears vs typical.",
    "body.hand_height_l|r": "Wrist height vs shoulder line in SW (>0 above the shoulders).",
    "body.gesture_speed": "Fastest wrist speed relative to the torso, SW per second.",
    "body.gesture_activity": "0..1 normalised gesture speed.",
    "body.gesturing": "1 while a hand moves faster than 0.6 SW/s.",
    "body.arm_openness": "Horizontal distance between wrists in SW; _rel is vs the person's typical.",
    "body.arms_crossed": "1 when the wrists are swapped across the body midline below the shoulders.",
    "body.hands_joined": "1 when the hands touch each other (clasping, steepling, wringing).",
    "body.face_touch": "1 when a hand is close to the face (self-touch / adaptor gesture).",
    "body.palm_to_camera": "-1..1, +1 palm facing the camera (needs hand landmarks).",
    "body.open_palms": "1 when at least one palm clearly faces the camera "
    "(not while arms are crossed or hands joined).",
}
