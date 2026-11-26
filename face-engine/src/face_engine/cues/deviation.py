"""Sliding-window cue values, the person's own baseline, deviation scores and hotspots.

1. Every cue track becomes a window value every ``hop_s`` (level: mean, rate: per minute).
2. Baseline = robust centre and spread of the window values inside the baseline spans
   (default: the whole clip, so 'deviation' means 'unusual for this person here').
3. score = (value - median) / spread, signed by the cue's direction (``both`` -> |z|).
4. A channel's score at a moment is its strongest cue. Pressure index = mean of the three
   strongest channels, counting only the part above 1 SD and capped at 4 SD, as 0..100
   (0 = everything within the person's normal range).
5. Hotspot = at least ``min_channels`` channels at or above ``z`` within ``cluster_s``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

from face_engine.cues.registry import CHANNELS, CUE_BY_ID
from face_engine.cues.signals import Track

WINDOW_S = {"mean": 2.0, "std": 3.0, "rate": 8.0}

# Minimum spread per cue, so a cue that is flat in the baseline does not explode.
FLOORS: dict[str, float] = {
    "pitch": 1.0, "pitch_variability": 0.7, "loudness": 3.0, "voice_tension": 0.15,
    "silence": 0.12, "head_motion": 6.0, "head_down": 4.0, "lean_back": 0.04,
    "body_motion": 0.05, "speech_rate": 30.0, "expressivity": 0.05,
}
# ...and relative to the baseline level for cues measured on a ratio scale.
REL_FLOORS: dict[str, float] = {
    "voice_tension": 0.15, "head_motion": 0.25, "body_motion": 0.25, "pitch_variability": 0.15,
    "expressivity": 0.15,
}
SHARE_FLOOR = 0.12  # 0..1 levels and shares
# Single events that should count on their own: one event in the window -> z = 3.
SINGLE_EVENT = ("yes_no_mismatch", "certainty_shrug")


@dataclass(frozen=True)
class DeviationConfig:
    hop_s: float = 0.5
    z: float = 2.0
    min_channels: int = 3
    cluster_s: float = 5.0
    min_valid: float = 0.5  # share of a window that must be observable
    pressure_top: int = 3
    min_state_windows: int = 20  # 10 s of a state before it gets its own baseline
    thin_baseline_s: float = 30.0


def _window_values(tr: Track, centres: np.ndarray, fps: float, n: int, win_s: float,
                   min_valid: float) -> np.ndarray:
    half = int(round(win_s * fps / 2))
    vals = tr.values
    out = np.full(len(centres), np.nan)
    finite = np.isfinite(vals)
    valid = finite if tr.valid is None else (np.asarray(tr.valid, bool) & finite)
    csum = np.concatenate([[0], np.cumsum(np.where(valid, vals, 0.0))])
    ccnt = np.concatenate([[0], np.cumsum(valid)])
    for j, c in enumerate(centres):
        k = int(round(c * fps))
        a, b = max(0, k - half), min(n, k + half + 1)
        cnt = ccnt[b] - ccnt[a]
        need = min_valid * (2 * half + 1) if tr.min_valid_s is None else tr.min_valid_s * fps
        if b <= a or cnt < need:
            continue
        if tr.agg == "rate":
            out[j] = (csum[b] - csum[a]) / (cnt / fps) * 60.0
        elif tr.agg == "std":
            seg = vals[a:b][valid[a:b]]
            out[j] = float(np.std(seg)) if len(seg) >= 5 else np.nan
        else:
            out[j] = (csum[b] - csum[a]) / cnt
    return out


def _robust(x: np.ndarray, cue: str, agg: str, win_s: float) -> dict[str, float] | None:
    x = x[np.isfinite(x)]
    if len(x) < 3:
        return None
    med = float(np.median(x))
    mad = 1.4826 * float(np.median(np.abs(x - med)))
    q1, q3 = np.quantile(x, [0.25, 0.75])
    spread = max(mad, float(q3 - q1) / 1.349)
    if cue in SINGLE_EVENT:
        floor = 60.0 / win_s / 3.0
    elif agg == "rate":
        floor = 1.5 * 60.0 / win_s
    else:
        floor = max(FLOORS.get(cue, SHARE_FLOOR), REL_FLOORS.get(cue, 0.0) * abs(med))
    return {"median": round(med, 4), "scale": round(max(spread, floor), 4),
            "mean": round(float(x.mean()), 4), "p95": round(float(np.quantile(x, 0.95)), 4),
            "n_windows": int(len(x))}


def spans_mask(centres: np.ndarray, spans: Sequence[tuple[float, float]] | None) -> np.ndarray:
    if not spans:
        return np.ones(len(centres), bool)
    m = np.zeros(len(centres), bool)
    for a, b in spans:
        m |= (centres >= a) & (centres < b)
    return m


def analyse(tracks: dict[str, Track], fps: float, n: int, cfg: DeviationConfig,
            baseline_spans: Sequence[tuple[float, float]] | None = None,
            baseline_override: dict[str, dict[str, float]] | None = None,
            keys: np.ndarray | None = None,
            state_override: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    """``keys``: per-window baseline group, e.g. ``"speak|front"``. Each window is scored
    against the baseline of its own group, falling back to its state (``"speak"``) and then
    to the whole baseline when a group has fewer than ``cfg.min_state_windows`` windows."""
    dur = n / fps
    centres = np.arange(0.0, dur + 1e-9, cfg.hop_s)
    in_base = spans_mask(centres, baseline_spans)
    keys = np.array(["all"] * len(centres), dtype=object) if keys is None else np.asarray(keys, dtype=object)
    states = np.array([k.split("|")[0] for k in keys], dtype=object)
    groups = sorted(set(keys) | set(states))
    values, scores, baseline = {}, {}, {}
    by_group: dict[str, dict[str, Any]] = {}
    used = np.array(["all"] * len(centres), dtype=object)
    for cue, tr in tracks.items():
        spec = CUE_BY_ID[cue]
        win = WINDOW_S[tr.agg]
        v = _window_values(tr, centres, fps, n, win, cfg.min_valid)
        b = (baseline_override or {}).get(cue) or _robust(v[in_base], cue, tr.agg, win)
        if b is None:
            continue
        med = np.full(len(centres), b["median"])
        scale = np.full(len(centres), b["scale"])
        for g in groups:
            sel = (keys == g) if "|" in g else (states == g)
            ov = ((state_override or {}).get(g) or {}).get("cues", {}).get(cue)
            gb = ov or _robust(v[in_base & sel], cue, tr.agg, win)
            if gb is None or (not ov and gb["n_windows"] < cfg.min_state_windows):
                continue
            by_group.setdefault(g, {})[cue] = gb
        for j in range(len(centres)):
            for g in (keys[j], states[j]):
                gb = by_group.get(g, {}).get(cue)
                if gb is not None:
                    med[j], scale[j] = gb["median"], gb["scale"]
                    used[j] = g if used[j] == "all" or "|" in g else used[j]
                    break
        z = (v - med) / scale
        s = -z if spec.direction == "down" else np.abs(z) if spec.direction == "both" else z
        values[cue], scores[cue], baseline[cue] = v, s, {**b, "window_s": win, "agg": tr.agg}

    state_info = {}
    for g in groups:
        sel = ((keys == g) if "|" in g else (states == g)) & in_base
        if g in by_group or sel.any():
            nwin = int(sel.sum())
            state_info[g] = {"duration_s": round(nwin * cfg.hop_s, 1),
                             "thin": nwin * cfg.hop_s < cfg.thin_baseline_s,
                             "used": g in by_group, "cues": by_group.get(g, {})}

    chan = {}
    lead = {}
    for ch in CHANNELS:
        cues = [c for c in scores if CUE_BY_ID[c].channel == ch]
        if not cues:
            continue
        m = np.vstack([np.nan_to_num(scores[c], nan=-np.inf) for c in cues])
        best = m.max(0)
        chan[ch] = np.where(np.isfinite(best), best, np.nan)
        lead[ch] = [cues[k] for k in m.argmax(0)]
    pressure = np.zeros(len(centres))
    if chan:
        stack = np.vstack([np.clip(np.nan_to_num(chan[ch], nan=0.0) - 1.0, 0, 3) for ch in chan])
        top = -np.sort(-stack, axis=0)[: cfg.pressure_top]
        pressure = 100.0 * top.mean(0) / 3.0
        k = max(1, int(round(1.0 / cfg.hop_s)))
        pressure = np.convolve(pressure, np.ones(k) / k, "same")
    return {"centres": centres, "values": values, "scores": scores, "baseline": baseline,
            "channels": chan, "lead": lead, "pressure": pressure, "in_baseline": in_base,
            "keys": keys, "states": state_info}


def hotspots(res: dict[str, Any], cfg: DeviationConfig) -> list[dict[str, Any]]:
    centres, chan, scores = res["centres"], res["channels"], res["scores"]
    if not len(centres) or not chan:
        return []
    names = list(chan)
    active = np.vstack([np.nan_to_num(chan[ch], nan=-np.inf) >= cfg.z for ch in names])
    span = max(1, int(round(cfg.cluster_s / cfg.hop_s)))
    hot = np.zeros(len(centres), bool)
    for i in range(len(centres)):
        sl = slice(i, min(len(centres), i + span))
        if active[:, sl].any(1).sum() >= cfg.min_channels:
            cols = np.flatnonzero(active[:, sl].any(0)) + i
            hot[cols.min():cols.max() + 1] = True
    out = []
    i = 0
    while i < len(centres):
        if not hot[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(centres) and hot[j + 1]:
            j += 1
        sl = slice(i, j + 1)
        cues = []
        for cue, s in scores.items():
            seg = np.nan_to_num(s[sl], nan=-np.inf)
            if seg.max() >= cfg.z:
                k = int(seg.argmax()) + i
                spec = CUE_BY_ID[cue]
                cues.append({"cue": cue, "channel": spec.channel, "label": spec.label,
                             "zone": spec.zone, "score": round(float(seg.max()), 2),
                             "peak_s": round(float(centres[k]), 2),
                             "value": _r(res["values"][cue][k]),
                             "baseline": res["baseline"][cue]["median"], "grade": spec.grade})
        cues.sort(key=lambda c: -c["score"])
        chs = sorted({c["channel"] for c in cues}, key=lambda ch: -max(c["score"] for c in cues if c["channel"] == ch))
        peak = int(np.argmax(res["pressure"][sl])) + i
        out.append({
            "start_s": round(float(centres[i]), 2), "end_s": round(float(centres[j]) + cfg.hop_s, 2),
            "peak_s": round(float(centres[peak]), 2),
            "pressure_peak": round(float(res["pressure"][peak]), 1),
            "n_channels": len(chs), "channels": chs, "cues": cues,
            "in_baseline": bool(res["in_baseline"][sl].any()),
        })
        i = j + 1
    return out


def question_reads(res: dict[str, Any], questions: list[dict[str, Any]], cfg: DeviationConfig,
                   baseline_spans: Sequence[tuple[float, float]] | None, after_s: float = 5.0) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Per question: answer latency vs the person's other answers, cues 0-5 s after the question."""
    lat = np.array([q.get("latency_s", np.nan) for q in questions], float)
    ends = np.array([q["end_s"] for q in questions], float)
    base = spans_mask(ends, baseline_spans) & np.isfinite(lat)
    if base.sum() < 3:
        base = np.isfinite(lat)
    lat_b = None
    if base.sum() >= 3:
        med = float(np.median(lat[base]))
        spread = max(1.4826 * float(np.median(np.abs(lat[base] - med))), 0.25)
        lat_b = {"median": round(med, 3), "scale": round(spread, 3), "n": int(base.sum())}
    centres, pressure = res["centres"], res["pressure"]
    p_base = float(np.median(pressure[res["in_baseline"]])) if len(pressure) else 0.0
    out = []
    for q in questions:
        a = q["end_s"]
        sl = (centres >= a) & (centres <= a + after_s)
        cues = []
        for cue, s in res["scores"].items():
            seg = np.where(sl, np.nan_to_num(s, nan=-np.inf), -np.inf)
            if seg.max() >= cfg.z:
                cues.append({"cue": cue, "channel": CUE_BY_ID[cue].channel, "label": CUE_BY_ID[cue].label,
                             "score": round(float(seg.max()), 2), "peak_s": round(float(centres[int(seg.argmax())]), 2)})
        r = dict(q)
        if lat_b and np.isfinite(q.get("latency_s", np.nan)):
            z = (q["latency_s"] - lat_b["median"]) / lat_b["scale"]
            r["latency_score"] = round(float(z), 2)
            if z >= cfg.z:
                cues.append({"cue": "response_latency", "channel": "speech", "label": "answer delay",
                             "score": round(float(z), 2), "peak_s": round(a, 2)})
        cues.sort(key=lambda c: -c["score"])
        r["cues"] = cues
        r["channels"] = sorted({c["channel"] for c in cues})
        r["cluster"] = len(r["channels"]) >= cfg.min_channels
        if sl.any():
            k = int(np.argmax(np.where(sl, pressure, -1)))
            r["pressure_peak"] = round(float(pressure[k]), 1)
            r["pressure_peak_s"] = round(float(centres[k]), 2)
            after = np.flatnonzero((centres > centres[k]) & (pressure <= p_base + 5))
            r["recovery_s"] = round(float(centres[after[0]] - centres[k]), 2) if len(after) else None
        out.append(r)
    return out, lat_b


def _r(x: float) -> float | None:
    return None if x is None or not np.isfinite(x) else round(float(x), 3)
