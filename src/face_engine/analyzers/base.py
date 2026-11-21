"""The plug-in point for feature extraction.

An analyzer turns detector observations into named, interpretable time series.
The engine only depends on this protocol, so a ready-made library (py-feat,
OpenFace, MediaPipe blendshapes, ...) can be wrapped as another analyzer and
compared with, or combined with, the from-scratch ones.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence

import numpy as np

from face_engine.observations import FrameObservation, Table


@dataclass
class AnalyzerResult:
    features: Table  # per-frame columns, all of length n_frames
    baseline: dict[str, Any]  # the personal neutral the features are relative to
    events: list[dict[str, Any]] = field(default_factory=list)
    glossary: dict[str, str] = field(default_factory=dict)


class Analyzer(Protocol):
    name: str

    def analyze(
        self,
        frames: Sequence[FrameObservation],
        fps: float,
        neutral: Sequence[FrameObservation] = (),
    ) -> AnalyzerResult:
        """Compute per-frame features, a baseline and discrete events."""

    def summarize(self, result: AnalyzerResult, sl: slice, fps: float) -> dict[str, Any]:
        """Compact, LLM-readable digest of ``result`` over the frame range ``sl``."""


def measurement_table(rows: list[dict[str, float]]) -> Table:
    """Turn per-frame measurement dicts (same keys) into a column table."""
    if not rows:
        return {}
    return {k: np.array([r[k] for r in rows], dtype=float) for k in rows[0]}


def fraction(mask: np.ndarray, valid: np.ndarray) -> float | None:
    """Share of valid frames where ``mask`` holds, or None if nothing is valid."""
    n = int(valid.sum())
    return round(float((mask & valid).sum()) / n, 3) if n else None


def rnd(value: Any, digits: int = 3) -> Any:
    """Round floats for compact JSON; NaN becomes None."""
    if value is None:
        return None
    value = float(value)
    return None if np.isnan(value) else round(value, digits) + 0.0  # + 0.0 drops "-0.0"


def nanstat(fn, x: np.ndarray) -> float | None:
    x = x[~np.isnan(x)]
    return rnd(fn(x)) if len(x) else None
