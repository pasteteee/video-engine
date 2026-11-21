"""Runs the analyzers over a clip and assembles the LLM-oriented report."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from typing import Any, Sequence

import numpy as np

from face_engine import __version__
from face_engine.analyzers.base import Analyzer, AnalyzerResult, rnd
from face_engine.analyzers.body import BodyAnalyzer
from face_engine.analyzers.face import AU_NAMES, FaceAnalyzer
from face_engine.config import EngineConfig
from face_engine.observations import FrameObservation, MediaInfo

SCHEMA_VERSION = "1.0"

DISCLAIMER = (
    "This file describes observable behaviour (facial muscle movements, head, gaze, posture, "
    "gestures) relative to the same person's own neutral baseline. It does not detect lies, "
    "intentions or felt emotions. Expression labels mean 'resembles the prototypical display', "
    "nothing more. Interpret markers in context (speech content, situation, culture, camera "
    "angle) and prefer patterns repeated over time to single events."
)

# Segment metrics compared against the whole clip to surface notable windows.
_CONTRAST = (
    ("face", "expressivity_mean", "facial expressivity"),
    ("face", "blink_rate_per_min", "blink rate per minute"),
    ("face", "gaze_averted_share", "share of time gaze is averted"),
    ("body", "gesturing_share", "share of time gesturing"),
    ("body", "face_touch_share", "share of time touching the face"),
    ("body", "arms_crossed_share", "share of time with arms crossed"),
    ("body", "open_palms_share", "share of time showing open palms"),
)


class Engine:
    def __init__(
        self,
        analyzers: Sequence[Analyzer] | None = None,
        config: EngineConfig | None = None,
    ) -> None:
        self.config = config or EngineConfig()
        self.analyzers: list[Analyzer] = list(
            analyzers or (FaceAnalyzer(self.config.face), BodyAnalyzer(self.config.body))
        )

    def run(
        self,
        frames: Sequence[FrameObservation],
        media: MediaInfo,
        neutral: Sequence[FrameObservation] = (),
        frames_fps: float | None = None,
    ) -> dict[str, Any]:
        if not frames:
            raise ValueError("no frames to analyze")
        fps = media.fps
        results = {a.name: a.analyze(frames, fps, neutral) for a in self.analyzers}
        times = np.array([f.time_s for f in frames])
        events = sorted(
            ({"source": name, **e} for name, r in results.items() for e in r.events),
            key=lambda e: (e["start_s"], e["type"]),
        )
        whole = slice(0, len(frames))
        summary = {name: a.summarize(results[name], whole, fps) for name, a in self._named()}
        segments = self._segments(results, times, events, fps, summary)
        summary["event_counts"] = dict(Counter(e["type"] for e in events))
        summary["highlights"] = _highlights(summary, events, times[-1] - times[0] + 1 / fps)

        report: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "generator": f"face-engine {__version__} (from-scratch geometric analyzers)",
            "disclaimer": DISCLAIMER,
            "meta": {
                **asdict(media),
                "frames": len(frames),
                "duration_s": rnd(len(frames) / fps),
                "analyzers": list(results),
            },
            "glossary": {k: v for r in results.values() for k, v in r.glossary.items()},
            "baseline": {name: _jsonable(r.baseline) for name, r in results.items()},
            "summary": summary,
            "segments": segments,
            "events": events,
        }
        stride = _stride(fps, frames_fps)
        if stride:
            report["frames"] = _frames(results, frames, stride)
        return report

    def _named(self):
        return ((a.name, a) for a in self.analyzers)

    def _segments(
        self,
        results: dict[str, AnalyzerResult],
        times: np.ndarray,
        events: list[dict[str, Any]],
        fps: float,
        clip_summary: dict[str, Any],
    ) -> list[dict[str, Any]]:
        seg_len = max(1, int(round(self.config.segment_s * fps)))
        out = []
        for k, start in enumerate(range(0, len(times), seg_len)):
            sl = slice(start, min(start + seg_len, len(times)))
            t0, t1 = float(times[sl.start]), float(times[sl.stop - 1]) + 1 / fps
            seg: dict[str, Any] = {"index": k, "start_s": rnd(t0), "end_s": rnd(t1)}
            for name, a in self._named():
                seg[name] = a.summarize(results[name], sl, fps)
            lo, hi = rnd(t0), rnd(t1)  # same rounding as event times
            inside = [e for e in events if lo <= e["start_s"] < hi]
            seg["event_counts"] = dict(Counter(e["type"] for e in inside))
            seg["notable_vs_clip"] = _contrast(seg, clip_summary)
            out.append(seg)
        return out


def _contrast(seg: dict[str, Any], clip: dict[str, Any]) -> dict[str, Any]:
    notable = {}
    for group, key, label in _CONTRAST:
        a, b = seg.get(group, {}).get(key), clip.get(group, {}).get(key)
        if a is None or b is None:
            continue
        if abs(a - b) >= max(0.1, 0.5 * abs(b)):
            notable[key] = {"label": label, "segment": a, "clip": b}
    return notable


def _stride(fps: float, frames_fps: float | None) -> int:
    if frames_fps is None:
        return 1
    if frames_fps <= 0:
        return 0
    return max(1, int(round(fps / frames_fps)))


def _frames(
    results: dict[str, AnalyzerResult], frames: Sequence[FrameObservation], stride: int
) -> list[dict[str, Any]]:
    cols = {k: v for r in results.values() for k, v in r.features.items()}
    rows = []
    for i in range(0, len(frames), stride):
        row: dict[str, Any] = {"i": frames[i].index, "t": rnd(frames[i].time_s)}
        for k, v in cols.items():
            val = rnd(v[i])
            if val is not None:
                row[k] = val
        rows.append(row)
    return rows


def _jsonable(x: Any) -> Any:
    if isinstance(x, dict):
        return {k: _jsonable(v) for k, v in x.items()}
    if isinstance(x, (float, np.floating)):
        return rnd(x, 4)
    if isinstance(x, np.integer):
        return int(x)
    return x


def _highlights(summary: dict[str, Any], events: list[dict[str, Any]], duration: float) -> list[str]:
    """Plain-English sentences an LLM can quote or build on."""
    out: list[str] = []
    face, body = summary.get("face", {}), summary.get("body", {})
    by_type: dict[str, list[dict[str, Any]]] = {}
    for e in events:
        by_type.setdefault(e["type"], []).append(e)

    if face.get("face_visible"):
        dom = face.get("dominant_expression")
        out.append(f"Dominant facial configuration over the clip: {dom}.")
        rate = face.get("blink_rate_per_min")
        if rate is not None and duration >= 10:
            note = "above" if rate > 26 else "below" if rate < 8 else "within"
            out.append(f"Blink rate {rate:.1f}/min ({note} the usual conversational range of ~8-26/min).")
        smiles = by_type.get("smile", [])
        if smiles:
            duch = sum(e.get("duchenne", False) for e in smiles)
            asym = sum(abs(e.get("asymmetry") or 0) >= 0.4 for e in smiles)
            out.append(
                f"{len(smiles)} smile(s): {duch} with cheek raise (Duchenne), "
                f"{len(smiles) - duch} lip-only; {asym} clearly one-sided."
            )
        brief = [e for e in by_type.get("action_unit", []) if e.get("brief")]
        if brief:
            top = Counter(e["au"] for e in brief).most_common(3)
            names = ", ".join(f"{au} {AU_NAMES[au]} x{n}" for au, n in top)
            out.append(f"{len(brief)} brief (<0.5 s) facial movements; most frequent: {names}.")
        for kind, label in (("head_nod", "head nods"), ("head_shake", "head shakes")):
            if by_type.get(kind):
                out.append(f"{len(by_type[kind])} {label}.")
        share = face.get("gaze_averted_share")
        if share:
            out.append(f"Gaze averted from the neutral direction {share:.0%} of the time.")
    if body.get("body_visible"):
        for key, label in (
            ("gesturing_share", "gesturing"),
            ("arms_crossed_share", "with arms crossed"),
            ("open_palms_share", "showing open palms"),
            ("hands_joined_share", "with hands joined"),
        ):
            if body.get(key):
                out.append(f"Body: {label} {body[key]:.0%} of visible time.")
        touches = by_type.get("face_touch", [])
        if touches:
            out.append(f"{len(touches)} hand-to-face touch(es).")
        shifts = by_type.get("posture_shift", [])
        if shifts:
            out.append(f"{len(shifts)} posture shift(s) toward/away from the camera.")
    return out
