"""Face-first reading: states, per-state micro twitches, quality gates and "moments".

Owner rule for On the Record (25 Nov 2026): every on-screen read starts from the face,
measured against the person's own norm for the same kind of moment; head/gaze, hands/body,
voice and speech only support it. Spec: Content Hub production-map/otr-visual-first-spec.md.

States: ``speak`` / ``listen`` from voice + lip movement, or labels the user supplies
(``positive``, ``negative_safe`` ...). Camera bucket: ``front`` (|yaw| < 15 deg) or
``side`` (15-35 deg); beyond 35 deg the face is not read.
"""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from face_engine.cues.registry import CUE_BY_ID
from face_engine.cues.signals import Word
from face_engine.topology import FACE_INDEX

TWITCH_AUS = ("AU01", "AU02", "AU04", "AU05", "AU06", "AU07", "AU09", "AU10", "AU12", "AU15",
              "AU17", "AU20", "AU23")
SIDED = ("AU01", "AU02", "AU04", "AU06", "AU12", "AU15")
SPEECH_AUS = frozenset({"AU10", "AU17", "AU20", "AU23"})  # move with articulation
FACE_WEIGHTS = {"face": 50, "head_gaze": 15, "body": 15, "voice": 10, "speech": 10}
GROUP = {"face": "face", "eyes": "head_gaze", "head": "head_gaze", "body": "body", "hands": "body",
         "voice": "voice", "speech": "speech", "mismatch": "speech"}
FLASH_AUS = frozenset({"AU09", "AU10", "AU04", "AU12"})  # AU12 one-sided = AU14-like
EVASION = ("non_recall", "hedges", "fillers", "response_latency", "repairs")


# --------------------------------------------------------------------------- states

def frame_states(rf: list[dict[str, Any]], speaking: np.ndarray, fps: float,
                 labels: Sequence[Sequence[Any]] = ()) -> tuple[np.ndarray, np.ndarray]:
    """Per frame: state and camera bucket ('front' | 'side' | 'off')."""
    n = len(rf)
    state = np.where(np.asarray(speaking[:n], bool), "speak", "listen").astype(object)
    for lab in labels:
        a, b, name = float(lab[0]), float(lab[1]), str(lab[2])
        state[max(0, int(a * fps)):min(n, int(np.ceil(b * fps)))] = name
    yaw = np.array([abs(r.get("head.yaw", np.nan)) if isinstance(r.get("head.yaw"), (int, float)) else np.nan
                    for r in rf])
    cam = np.where(yaw < 15, "front", np.where(yaw <= 35, "side", "off")).astype(object)
    cam[~np.isfinite(yaw)] = "off"
    return state, cam


def hop_keys(centres: np.ndarray, state: np.ndarray, cam: np.ndarray, fps: float,
             win_s: float = 2.0) -> np.ndarray:
    n = len(state)
    half = int(round(win_s * fps / 2))
    out = []
    for c in centres:
        k = int(round(c * fps))
        a, b = max(0, k - half), min(n, k + half + 1)
        if b <= a:
            out.append("listen|off")
            continue
        st, cnt = np.unique(state[a:b], return_counts=True)
        cm, cc = np.unique(cam[a:b], return_counts=True)
        out.append(f"{st[cnt.argmax()]}|{cm[cc.argmax()]}")
    return np.array(out, dtype=object)


# --------------------------------------------------------------------------- twitches

def _col(rf: list[dict[str, Any]], key: str) -> np.ndarray:
    return np.array([r[key] if isinstance(r.get(key), (int, float)) else np.nan for r in rf], float)


def micro_twitches(rf: list[dict[str, Any]], state: np.ndarray, cam: np.ndarray, base: np.ndarray,
                   fps: float, max_s: float = 0.5, margin: float = 0.1,
                   min_peak: float = 0.3, min_rise: float = 0.25, max_head_speed: float = 60.0) -> tuple[list[dict[str, Any]], dict[str, dict[str, float]]]:
    """AU spikes that rise above the person's p95 for this state and fall back within 0.5 s."""
    n = len(rf)
    readable = cam != "off"
    head_fast = np.nan_to_num(_col(rf, "head.angular_speed_deg_s")) > max_head_speed
    ctx = max(2, int(round(0.3 * fps)))
    blink = _col(rf, "eye.closure") >= 0.5
    near_blink = np.convolve(blink.astype(float), np.ones(int(fps * 0.2) * 2 + 1), "same") > 0
    out, p95s = [], {}
    max_len, min_len = int(round(max_s * fps)), max(2, int(round(0.05 * fps)))
    for au in TWITCH_AUS:
        sides = [(au, None)] + ([(f"{au}_l", "l"), (f"{au}_r", "r")] if au in SIDED else [])
        for key, side in sides:
            x = _col(rf, f"au.{key}")
            if not np.isfinite(x).any():
                continue
            thr = np.full(n, np.nan)
            for st in np.unique(state):
                sel = (state == st) & base & readable & np.isfinite(x)
                if sel.sum() < fps * 5:
                    sel = base & readable & np.isfinite(x)
                if not sel.any():
                    continue
                p95 = float(np.quantile(x[sel], 0.95))
                p95s.setdefault(st, {})[key] = round(p95, 3)
                thr[state == st] = max(p95 + margin, min_peak)
            above = np.nan_to_num(x, nan=-1) > thr
            if au in SPEECH_AUS:
                above &= state != "speak"
            if au in ("AU05", "AU06", "AU07"):
                above &= ~near_blink
            above &= readable
            i = 0
            while i < n:
                if not above[i]:
                    i += 1
                    continue
                j = i
                while j < n and above[j]:
                    j += 1
                pre, post = x[max(0, i - ctx):i], x[j:j + ctx]
                level = max(np.nanmedian(pre) if np.isfinite(pre).any() else np.inf,
                            np.nanmedian(post) if np.isfinite(post).any() else np.inf)
                if (min_len <= j - i <= max_len and i > 0 and j < n and not head_fast[i:j].any()
                        and np.nanmax(x[i:j]) - level >= min_rise):
                    k = i + int(np.nanargmax(x[i:j]))
                    out.append({"t": round(k / fps, 3), "start_s": round(i / fps, 3), "end_s": round(j / fps, 3),
                                "au": au, "side": side, "peak": round(float(x[k]), 3),
                                "p95": round(float(thr[k] - margin), 3), "state": str(state[k])})
                i = j
    # A sided twitch also shows in the bilateral mean: keep the strongest per AU and moment.
    out.sort(key=lambda e: (e["au"], e["t"], -e["peak"]))
    dedup: list[dict[str, Any]] = []
    for e in out:
        if dedup and dedup[-1]["au"] == e["au"] and abs(dedup[-1]["t"] - e["t"]) < 0.3:
            if e["side"] and not dedup[-1]["side"]:
                dedup[-1] = {**e, "peak": max(e["peak"], dedup[-1]["peak"])}
            continue
        dedup.append(e)
    dedup.sort(key=lambda e: e["t"])
    return dedup, p95s


# --------------------------------------------------------------------------- quality

def face_heights(frames: Sequence[Any]) -> np.ndarray:
    h = np.full(len(frames), np.nan)
    for i, f in enumerate(frames):
        if f.face is not None:
            p = np.asarray(f.face, float)
            h[i] = float(np.linalg.norm(p[FACE_INDEX["forehead"], :2] - p[FACE_INDEX["chin"], :2]))
    return h


def quality(a: float, b: float, fps: float, heights: np.ndarray, cam: np.ndarray, rf: list[dict[str, Any]],
            min_face_px: float = 120.0) -> dict[str, Any]:
    n = len(cam)
    sl = slice(max(0, int(a * fps)), min(n, int(np.ceil(b * fps))))
    flags = []
    h = heights[sl]
    hp = float(np.nanmedian(h)) if np.isfinite(h).any() else 0.0
    if not np.isfinite(h).any() or np.isfinite(h).mean() < 0.5:
        flags.append("face_missing")
    if hp < min_face_px:
        flags.append("face_too_small")
    if (cam[sl] == "off").mean() > 0.5:
        flags.append("turned_away")
    if fps < 25:
        flags.append("low_fps")
    pitch = _col(rf[sl], "head.pitch_rel")
    gv = _col(rf[sl], "gaze.dir_v_deg")
    down = np.fmin(pitch, gv)
    if np.isfinite(down).any() and (down[np.isfinite(down)] < -15).mean() >= 0.3:
        flags.append("looking_down_reading")
    hard = {"face_missing", "face_too_small", "turned_away", "looking_down_reading"}
    return {"face_px": round(hp), "flags": flags, "readable": not (set(flags) & hard)}


# --------------------------------------------------------------------------- moments

def _label(face_cues: set[str], twitch_aus: set[str], support: set[str], evasion: int) -> str:
    discomfort = bool(face_cues & {"lip_suck", "lip_corner_depress", "inner_brow_raise"})
    holding = bool(face_cues & {"lip_press", "chin_raise"}) or "blink_rate" in support
    mismatch = bool(support & {"yes_no_mismatch", "certainty_shrug"})
    if (discomfort or holding) and mismatch and evasion:
        return "possible_deception_cluster"
    if mismatch:
        return "mismatch"
    if discomfort:
        return "discomfort"
    if holding:
        return "holding_back"
    if twitch_aus & FLASH_AUS or "one_sided_mouth" in face_cues or "disgust_face" in face_cues:
        return "flash"
    return "face_change"


WORDING = {
    "discomfort": "Here, to us, they look uncomfortable.",
    "holding_back": "One reading: holding something back.",
    "flash": "For a fraction of a second, something else crossed the face.",
    "mismatch": "The words say one thing. The body says something else.",
    "possible_deception_cluster": "In our opinion, this may not be the whole story.",
    "face_change": "The face moved away from its own normal here.",
}


def find_moments(res: dict[str, Any], twitches: list[dict[str, Any]], questions: list[dict[str, Any]],
                 words: list[Word] | None, fps: float, heights: np.ndarray, cam: np.ndarray,
                 rf: list[dict[str, Any]], window_s: float = 5.0, face_z: float = 2.5,
                 support_z: float = 2.0) -> list[dict[str, Any]]:
    centres, scores = res["centres"], res["scores"]
    dur = len(rf) / fps
    # Candidate windows: after each question; plus every face event when no stimulus covers it.
    wins = [(q["end_s"], q["end_s"] + window_s, q) for q in questions]
    face_ids = [c for c in scores if CUE_BY_ID[c].channel == "face" and c != "expressivity"]
    onsets = [e["t"] for e in twitches]
    for c in face_ids:
        hot = np.nan_to_num(scores[c], nan=-np.inf) >= face_z
        onsets += list(centres[np.flatnonzero(hot[1:] & ~hot[:-1]) + 1]) + ([centres[0]] if hot[:1].any() else [])
    for t in sorted(onsets):
        if not any(a - 0.5 <= t <= b for a, b, _ in wins):
            wins.append((max(0.0, t - 1.0), min(dur, t - 1.0 + window_s), None))
    wins.sort(key=lambda w: w[0])

    out = []
    for a, b, q in wins:
        sel = (centres >= a) & (centres <= b)
        if not sel.any():
            continue
        tw = [e for e in twitches if a <= e["t"] <= b]
        face_hits = {}
        support: dict[str, dict[str, Any]] = {}
        for c, s in scores.items():
            seg = np.where(sel, np.nan_to_num(s, nan=-np.inf), -np.inf)
            k = int(seg.argmax())
            z = float(seg[k])
            spec = CUE_BY_ID[c]
            row = {"cue": c, "label": spec.label, "channel": spec.channel, "z": round(z, 2),
                   "t": round(float(centres[k]), 2), "value": _r(res["values"][c][k]),
                   "zone": spec.zone, "grade": spec.grade}
            if c in face_ids and z >= face_z:
                face_hits[c] = row
            elif spec.channel != "face" and z >= support_z:
                support[c] = row
        if q is not None and q.get("latency_score") is not None and q["latency_score"] >= support_z:
            support["response_latency"] = {"cue": "response_latency", "label": "answer delay", "channel": "speech",
                                           "z": q["latency_score"], "t": q.get("answer_start_s"),
                                           "value": q.get("latency_s"), "zone": "voice", "grade": "B"}
        face_event = bool(tw) or len(face_hits) >= 2
        if not face_event:
            continue
        two_face = len(tw) >= 2 or (tw and face_hits) or len(face_hits) >= 3
        if not support and not two_face:
            continue
        # Weighted 0..100 score, per group.
        parts = {}
        for g, w in FACE_WEIGHTS.items():
            zs = [r["z"] for r in list(face_hits.values()) + list(support.values()) if GROUP[r["channel"]] == g]
            f = max([min(1.0, max(0.0, (z - 1) / 3)) for z in zs], default=0.0)
            if g == "face" and tw:
                f = max(f, min(1.0, 0.5 + 0.15 * len(tw)))
            parts[g] = round(w * f, 1)
        score = round(sum(parts.values()), 1)
        # Strongest face event decides the zone, peak and slow-motion window.
        cand = [(r["z"], r["t"], r["zone"]) for r in face_hits.values()]
        cand += [(3.0 + e["peak"], e["t"], _twitch_zone(e["au"])) for e in tw]
        _, peak, zone = max(cand)
        evasion = sum(1 for c in support if c in EVASION)
        label = _label(set(face_hits), {e["au"] for e in tw}, set(support), evasion)
        qual = quality(a, b, fps, heights, cam, rf)
        n_groups = sum(1 for v in parts.values() if v > 0)
        conf = "high" if n_groups >= 3 and qual["readable"] else "medium" if qual["readable"] else "low"
        m = {
            "t_start": round(a, 2), "t_end": round(b, 2), "peak_s": round(peak, 2),
            "stimulus": ({"text": q.get("text", ""), "t": q["end_s"]} if q else None),
            "label": label, "wording": WORDING[label], "score": score, "score_parts": parts,
            "zone": zone, "face_events": {"twitches": tw, "cues": sorted(face_hits.values(), key=lambda r: -r["z"])},
            "support": sorted(support.values(), key=lambda r: -r["z"]),
            "onset_latency_s": round(min([e["t"] for e in tw] + [r["t"] for r in face_hits.values()]) - a, 2)
            if q else None,
            "slowmo": [round(max(a, peak - 0.75), 2), round(min(b, peak + 0.75), 2)],
            "confidence": conf, "quality": qual,
        }
        if words:
            ws = [w for w in words if a <= w.start <= b]
            m["speech"] = {"words": " ".join(w.bare for w in ws),
                           "fillers": sum(w.bare in ("um", "uh", "er", "erm", "ah") for w in ws)}
        pk = np.flatnonzero(sel)
        p = res["pressure"][pk]
        after = np.flatnonzero((centres > peak) & (res["pressure"] <= np.median(res["pressure"]) + 5))
        m["return_to_baseline_s"] = round(float(centres[after[0]] - peak), 2) if len(after) else None
        m["pressure_peak"] = round(float(p.max()), 1)
        out.append(m)
    return _merge(out)


def _twitch_zone(au: str) -> str:
    return {"AU01": "brow", "AU02": "brow", "AU04": "brow", "AU05": "eyes", "AU06": "eyes",
            "AU07": "eyes"}.get(au, "mouth")


def _merge(ms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Overlapping windows: keep the higher-scoring moment (a stimulus wins ties)."""
    ms.sort(key=lambda m: (-m["score"], m["stimulus"] is None))
    kept: list[dict[str, Any]] = []
    for m in ms:
        if all(m["t_end"] <= k["t_start"] or m["t_start"] >= k["t_end"] for k in kept):
            kept.append(m)
    return sorted(kept, key=lambda m: m["t_start"])


def baseline_frames(rf: list[dict[str, Any]], state: np.ndarray, cam: np.ndarray, base: np.ndarray,
                    fps: float, exclude: Sequence[tuple[float, float]] = ()) -> dict[str, float]:
    """Per state: the most typical, frontal moment (for the 'normal for them' still),
    away from any moment window."""
    base = base.copy()
    for a, b in exclude:
        base[max(0, int((a - 1) * fps)):int((b + 1) * fps)] = False
    keys = [f"au.{a}" for a in TWITCH_AUS]
    m = np.vstack([_col(rf, k) for k in keys]).T
    out = {}
    for st in np.unique(state):
        level = (np.abs(np.nan_to_num(_col(rf, "head.pitch_rel"), nan=99)) < 10) & \
            (np.abs(np.nan_to_num(_col(rf, "gaze.dir_v_deg"), nan=99)) < 12)
        ok = (state == st) & base & level & np.isfinite(m).all(1) & (_col(rf, "eye.closure") < 0.3)
        sel = ok & (cam == "front")
        if sel.sum() < fps:
            sel = ok & (cam == "side")
        if not sel.any():
            continue
        med = np.median(m[sel], 0)
        dist = np.where(sel, np.abs(m - med).sum(1), np.inf)
        out[str(st)] = round(float(np.argmin(dist)) / fps, 3)
    return out


def idiolect(state_info: dict[str, Any], twitches: list[dict[str, Any]], base_spans: np.ndarray | None,
             top: int = 5) -> dict[str, list[dict[str, Any]]]:
    """Habitual face cues per state: high baseline level -> 'normal for this person'."""
    out = {}
    for g, info in state_info.items():
        if "|" in g:
            continue
        rows = []
        for cue, b in info.get("cues", {}).items():
            spec = CUE_BY_ID[cue]
            if spec.channel == "face" and spec.unit == "0..1" and b["median"] >= 0.15:
                rows.append({"cue": cue, "label": spec.label, "baseline_median": b["median"]})
        rows.sort(key=lambda r: -r["baseline_median"])
        tw = [e for e in twitches if e["state"] == g]
        if tw:
            aus, cnt = np.unique([e["au"] for e in tw], return_counts=True)
            for k in np.argsort(-cnt)[:2]:
                rows.append({"cue": "micro_twitch", "label": f"{aus[k]} flicks", "count": int(cnt[k])})
        out[g] = rows[:top]
    return out


def _r(x: float) -> float | None:
    return None if x is None or not np.isfinite(x) else round(float(x), 3)
