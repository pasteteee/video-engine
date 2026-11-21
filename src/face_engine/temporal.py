"""Generic time-series helpers: smoothing, runs, oscillations, events."""

from __future__ import annotations

from typing import Any

import numpy as np


def window_frames(fps: float, seconds: float) -> int:
    """Odd window length (>= 1) covering ``seconds`` at ``fps``."""
    n = max(1, int(round(fps * seconds)))
    return n if n % 2 else n + 1


def smooth(x: np.ndarray, window: int) -> np.ndarray:
    """Centred moving average that ignores NaNs and keeps NaN where input is NaN."""
    if window <= 1 or len(x) < 2:
        return x.astype(float, copy=True)
    valid = ~np.isnan(x)
    num = _box_sum(np.where(valid, x, 0.0), window)
    den = _box_sum(valid.astype(float), window)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = num / den
    out[~valid] = np.nan
    return out


def rolling_std(x: np.ndarray, window: int) -> np.ndarray:
    mean = smooth(x, window)
    sq = smooth(x * x, window)
    return np.sqrt(np.clip(sq - mean * mean, 0.0, None))


def derivative(x: np.ndarray, fps: float) -> np.ndarray:
    """Per-second rate of change (central differences); NaN-safe."""
    if len(x) < 2:
        return np.full(len(x), np.nan)
    return np.gradient(x) * fps


def runs(mask: np.ndarray, min_len: int = 1, max_gap: int = 0) -> list[tuple[int, int]]:
    """Half-open index ranges ``[start, end)`` where ``mask`` is True.

    Runs separated by at most ``max_gap`` False frames are merged first.
    """
    m = np.concatenate([[False], np.asarray(mask, dtype=bool), [False]])
    edges = np.flatnonzero(np.diff(m.astype(np.int8)))
    spans: list[tuple[int, int]] = []
    for s, e in zip(edges[::2], edges[1::2]):
        if spans and s - spans[-1][1] <= max_gap:
            spans[-1] = (spans[-1][0], int(e))
        else:
            spans.append((int(s), int(e)))
    return [(s, e) for s, e in spans if e - s >= min_len]


def dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    """Grow True regions by ``radius`` frames on both sides."""
    if radius <= 0:
        return np.asarray(mask, dtype=bool)
    return _box_sum(np.asarray(mask, dtype=float), 2 * radius + 1) > 0


def _box_sum(x: np.ndarray, window: int) -> np.ndarray:
    """Centred sum over an odd ``window``; output has the length of ``x`` even if shorter."""
    r = window // 2
    return np.convolve(x, np.ones(window), mode="full")[r : r + len(x)]


def zigzag(x: np.ndarray, threshold: float) -> list[int]:
    """Indices of alternating extrema whose successive difference is >= threshold."""
    idx = np.flatnonzero(~np.isnan(x))
    if len(idx) < 2:
        return []
    lo = hi = int(idx[0])
    pivots: list[int] = []
    direction = 0  # +1 rising toward a peak, -1 falling toward a trough
    ext = lo
    for i in map(int, idx[1:]):
        v = x[i]
        if direction == 0:
            lo = i if v < x[lo] else lo
            hi = i if v > x[hi] else hi
            if v - x[lo] >= threshold:
                pivots, direction, ext = [lo], 1, i
            elif x[hi] - v >= threshold:
                pivots, direction, ext = [hi], -1, i
        elif direction * (v - x[ext]) >= 0:
            ext = i
        elif abs(x[ext] - v) >= threshold:
            pivots.append(ext)
            direction, ext = -direction, i
    if direction:
        pivots.append(ext)
    return pivots


def oscillations(
    x: np.ndarray, fps: float, threshold: float, max_leg_s: float = 0.8, min_legs: int = 2
) -> list[tuple[int, int]]:
    """Back-and-forth movements: >= ``min_legs`` consecutive zigzag legs, each faster than ``max_leg_s``."""
    pivots = zigzag(x, threshold)
    max_leg = max_leg_s * fps
    out: list[tuple[int, int]] = []
    start = 0
    for k in range(1, len(pivots) + 1):
        if k == len(pivots) or pivots[k] - pivots[k - 1] > max_leg:
            if k - 1 - start >= min_legs:
                out.append((pivots[start], pivots[k - 1] + 1))
            start = k
    return out


def make_event(
    kind: str,
    span: tuple[int, int],
    times: np.ndarray,
    fps: float,
    signal: np.ndarray | None = None,
    **extra: Any,
) -> dict[str, Any]:
    start, end = span
    event: dict[str, Any] = {
        "type": kind,
        "start_s": round(float(times[start]), 3),
        "end_s": round(float(times[end - 1]) + 1.0 / fps, 3),
    }
    event["duration_s"] = round(event["end_s"] - event["start_s"], 3)
    if signal is not None:
        seg = signal[start:end]
        if np.any(~np.isnan(seg)):
            peak = int(np.nanargmax(seg)) + start
            event["peak"] = round(float(signal[peak]), 3)
            event["peak_s"] = round(float(times[peak]), 3)
    event.update(extra)
    # Frame range in the analysed sequence. Internal: the engine replaces it with
    # video frame numbers (frame_start / frame_end) when writing the report.
    event["_span"] = (start, end)
    return event


def threshold_events(
    kind: str,
    signal: np.ndarray,
    threshold: float,
    times: np.ndarray,
    fps: float,
    min_s: float = 0.0,
    merge_gap_s: float = 0.0,
    **extra: Any,
) -> list[dict[str, Any]]:
    min_len = max(1, int(round(min_s * fps)))
    gap = int(round(merge_gap_s * fps))
    mask = np.nan_to_num(signal, nan=-np.inf) >= threshold
    spans = runs(mask, min_len, gap)
    return [make_event(kind, s, times, fps, signal, **extra) for s in spans]


def event_span(event: dict[str, Any]) -> tuple[int, int]:
    """Frame range ``[start, end)`` of an event built with :func:`make_event`."""
    return event["_span"]
