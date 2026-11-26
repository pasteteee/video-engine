"""Behaviour map: engine report + landmarks (+ audio, words) -> behavior.json and overlay.json."""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from face_engine import __version__
from face_engine.cues import deviation as D
from face_engine.cues import moments as M
from face_engine.cues.registry import CHANNELS, CUE_BY_ID, CUES, DISCLAIMER
from face_engine.cues.signals import SpeechInfo, Track, Word, _impulses, build_tracks, find_questions
from face_engine.observations import FrameObservation, MediaInfo
from face_engine.topology import BODY_INDEX, FACE_INDEX

SCHEMA = "behavior/1.0"

_FACE_ZONES = {
    "eyes": (("r_eye_outer", "r_eye_inner", "l_eye_inner", "l_eye_outer"), (1.25, 0.45)),
    "brow": (("r_brow_inner", "l_brow_inner", "r_brow_mid", "l_brow_mid"), (1.2, 0.35)),
    "mouth": (("r_mouth_corner", "l_mouth_corner", "upper_lip_top", "lower_lip_bottom"), (0.85, 0.45)),
    "face": (("nose_tip",), (1.6, 2.0)),
}


def zone_boxes(frames: Sequence[FrameObservation]) -> dict[str, np.ndarray]:
    """Per frame [cx, cy, rx, ry] in source-video pixels (y down) for every overlay zone."""
    n = len(frames)
    z = {k: np.full((n, 4), np.nan) for k in ("eyes", "brow", "mouth", "face", "head", "shoulders", "hands", "torso")}
    for i, f in enumerate(frames):
        if f.face is not None:
            p = np.asarray(f.face, float)
            iod = float(np.linalg.norm(p[FACE_INDEX["r_iris"], :2] - p[FACE_INDEX["l_iris"], :2]))
            if not np.isfinite(iod) or iod < 1:
                iod = float(np.linalg.norm(p[FACE_INDEX["r_eye_outer"], :2] - p[FACE_INDEX["l_eye_outer"], :2])) * 0.65
            if np.isfinite(iod) and iod >= 1:
                for name, (pts, (rx, ry)) in _FACE_ZONES.items():
                    c = p[[FACE_INDEX[k] for k in pts], :2].mean(0)
                    z[name][i] = (c[0], -c[1], rx * iod, ry * iod)
                c = p[FACE_INDEX["nose_bridge"], :2]
                z["head"][i] = (c[0], -c[1] - 0.3 * iod, 2.0 * iod, 2.6 * iod)
        if f.body is not None:
            b = np.asarray(f.body, float)
            vis = np.ones(len(b)) if f.body_visibility is None else np.asarray(f.body_visibility, float)
            ok = lambda k: bool(vis[BODY_INDEX[k]] >= 0.5 and np.isfinite(b[BODY_INDEX[k]]).all())  # noqa: E731
            if ok("l_shoulder") and ok("r_shoulder"):
                ls, rs = b[BODY_INDEX["l_shoulder"], :2], b[BODY_INDEX["r_shoulder"], :2]
                sw = float(np.linalg.norm(ls - rs))
                m = (ls + rs) / 2
                z["shoulders"][i] = (m[0], -m[1], 0.75 * sw, 0.3 * sw)
                z["torso"][i] = (m[0], -m[1] + 0.6 * sw, 0.7 * sw, 0.8 * sw)
                pts = [b[BODY_INDEX[k], :2] for k in ("l_wrist", "r_wrist", "l_elbow", "r_elbow") if ok(k)]
                pts += [h.points[:, :2].mean(0) for h in f.hands]
                if pts:
                    q = np.array(pts)
                    c = q.mean(0)
                    z["hands"][i] = (c[0], -c[1], max(0.4 * sw, np.ptp(q[:, 0]) / 2 + 0.2 * sw),
                                     max(0.3 * sw, np.ptp(q[:, 1]) / 2 + 0.2 * sw))
    # Light temporal median to steady the glow.
    for k, a in z.items():
        out = a.copy()
        for i in range(n):
            seg = a[max(0, i - 3):i + 4]
            ok = np.isfinite(seg[:, 0])
            if ok.any():
                out[i] = np.median(seg[ok], 0)
        z[k] = out
    return z


def _rl(x: np.ndarray, d: int = 2) -> list:
    return [None if not np.isfinite(v) else round(float(v), d) for v in x]


def caption(cue: str, score: float) -> str:
    """Opinion-safe on-screen wording."""
    spec = CUE_BY_ID[cue]
    if cue in ("yes_no_mismatch", "certainty_shrug"):
        return f"{spec.label.upper()} · words and body disagree"
    if spec.direction == "down":
        return f"{spec.label.upper()} · {score:.1f} SD below own baseline"
    return f"{spec.label.upper()} · {score:.1f} SD from own baseline"


def highlights(spots: list[dict[str, Any]], max_per_spot: int = 3, hold_s: float = 1.6) -> list[dict[str, Any]]:
    """One glowing zone at a time: the strongest cues of each hotspot, one per zone."""
    out = []
    for h_i, h in enumerate(spots):
        picked, zones = [], set()
        for c in h["cues"]:
            if c["zone"] in zones:
                continue
            picked.append(c)
            zones.add(c["zone"])
            if len(picked) >= max_per_spot:
                break
        picked.sort(key=lambda c: c["peak_s"])
        t = h["start_s"]
        for c in picked:
            s = max(t, c["peak_s"] - hold_s / 2)
            e = s + hold_s
            out.append({"hotspot": h_i, "start_s": round(s, 2), "end_s": round(e, 2), "zone": c["zone"],
                        "cue": c["cue"], "channel": c["channel"], "score": c["score"],
                        "caption": caption(c["cue"], c["score"])})
            t = e
    return out


def run(
    report: dict[str, Any],
    frames: Sequence[FrameObservation],
    media: MediaInfo,
    audio: dict[str, np.ndarray] | None = None,
    words: list[Word] | None = None,
    subject: str | None = None,
    questions: Sequence[Any] = (),
    baseline_spans: Sequence[tuple[float, float]] | None = None,
    baseline_override: dict[str, dict[str, float]] | None = None,
    cfg: D.DeviationConfig | None = None,
    overlay_fps: float = 10.0,
    states: Sequence[Sequence[Any]] = (),
    state_override: dict[str, dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Returns (behavior, overlay, moments)."""
    cfg = cfg or D.DeviationConfig()
    fps, n = media.fps, len(frames)
    tracks, helpers = build_tracks(report, frames, fps, audio, words, subject)
    rf = report["frames"]
    state, cam = M.frame_states(rf, helpers["speaking"], fps, states)
    ftimes = np.arange(n) / fps
    base_frames = D.spans_mask(ftimes, baseline_spans)
    twitches, p95 = M.micro_twitches(rf, state, cam, base_frames, fps)
    tracks["micro_twitch"] = Track(_impulses(n, fps, [e["t"] for e in twitches]), "rate", helpers["face_ok"])
    centres = np.arange(0.0, n / fps + 1e-9, cfg.hop_s)
    keys = M.hop_keys(centres, state, cam, fps)
    res = D.analyse(tracks, fps, n, cfg, baseline_spans, baseline_override, keys, state_override)
    spots = D.hotspots(res, cfg)
    speech = SpeechInfo(words or [])
    if words or questions:
        speech.questions = find_questions(speech.words, subject, questions)
    qreads, lat_base = D.question_reads(res, speech.questions, cfg, baseline_spans) if speech.questions else ([], None)
    heights = M.face_heights(frames)
    moments = M.find_moments(res, twitches, qreads, speech.words or None, fps, heights, cam, rf)
    stills = M.baseline_frames(rf, state, cam, base_frames, fps, [(m["t_start"], m["t_end"]) for m in moments])
    for m in moments:
        sl = slice(int(m["t_start"] * fps), max(int(m["t_start"] * fps) + 1, int(m["t_end"] * fps)))
        st, cnt = np.unique(state[sl], return_counts=True)
        m["state"] = str(st[cnt.argmax()])
        m["baseline_frame"] = ({"state": m["state"], "t": stills[m["state"]]} if m["state"] in stills
                               else next(({"state": k, "t": v} for k, v in stills.items()), None))
    for h in spots:
        h["question"] = next((q.get("text") or f"question ending {q['end_s']:.1f}s" for q in speech.questions
                              if h["start_s"] - 6 <= q["end_s"] <= h["start_s"] + 1), None)

    centres = res["centres"]
    available = set(res["scores"])
    cue_summary = {}
    for cue in available:
        s = res["scores"][cue]
        ok = np.isfinite(s)
        cue_summary[cue] = {
            "active_share": round(float((s[ok] >= cfg.z).mean()), 3) if ok.any() else None,
            "max_score": round(float(np.nanmax(s)), 2) if ok.any() else None,
            "max_at_s": round(float(centres[int(np.nanargmax(s))]), 2) if ok.any() else None,
            "baseline": res["baseline"][cue],
        }
    t0 = frames[0].time_s if frames else 0.0
    behavior = {
        "schema": SCHEMA,
        "generator": f"face-engine {__version__} behaviour map",
        "disclaimer": DISCLAIMER,
        "meta": {
            "source": media.path, "fps": fps, "frames": n, "duration_s": round(n / fps, 3),
            "time_offset_s": round(t0, 3),
            "inputs": {"video": True, "audio": audio is not None, "words": bool(words),
                       "speaker_labels": bool(words and any(w.speaker for w in words)), "subject": subject,
                       "questions": len(speech.questions)},
            "baseline": {"spans_s": [list(s) for s in baseline_spans] if baseline_spans else "whole clip",
                         "from_file": bool(baseline_override)},
            "config": {"hop_s": cfg.hop_s, "z": cfg.z, "min_channels": cfg.min_channels,
                       "cluster_s": cfg.cluster_s, "windows_s": D.WINDOW_S},
        },
        "cues": [{"id": c.id, "channel": c.channel, "label": c.label, "unit": c.unit,
                  "direction": c.direction, "zone": c.zone, "grade": c.grade, "note": c.note,
                  "tracked": c.id in available or (c.id == "response_latency" and lat_base is not None)}
                 for c in CUES],
        "baseline": {**res["baseline"], **({"response_latency": lat_base} if lat_base else {})},
        "summary": {
            "hotspots": len(spots),
            "channels_tracked": [ch for ch in CHANNELS if ch in res["channels"]],
            "pressure_median": round(float(np.median(res["pressure"])), 1) if len(centres) else None,
            "pressure_p90": round(float(np.quantile(res["pressure"], 0.9)), 1) if len(centres) else None,
            "cues": cue_summary,
            "moments": len(moments),
            "readable_moments": sum(m["quality"]["readable"] for m in moments),
            "notes": _notes(cue_summary, spots, cfg) + [
                f"Face-first moments: {len(moments)} ({sum(m['quality']['readable'] for m in moments)} readable); "
                + ", ".join(f"{m['t_start']:.1f}s {m['label']} {m['score']:.0f}" for m in moments[:6])],
        },
        "states": {
            "groups": res["states"],
            "twitch_p95": p95,
            "baseline_frame_s": stills,
            "idiolect": M.idiolect(res["states"], [e for e in twitches if base_frames[min(n - 1, int(e["t"] * fps))]], None),
            "share": {str(k): round(float(v) / n, 3) for k, v in zip(*np.unique(state, return_counts=True))},
            "camera_share": {str(k): round(float(v) / n, 3) for k, v in zip(*np.unique(cam, return_counts=True))},
        },
        "twitches": twitches,
        "moments": moments,
        "hotspots": spots,
        "questions": qreads,
        "mismatches": sorted(round(float(t), 2) for t in helpers.get("mismatch_times", [])),
        "timeline": {
            "hop_s": cfg.hop_s, "t": _rl(centres + t0),
            "pressure": _rl(res["pressure"], 1),
            "channels": {ch: _rl(v) for ch, v in res["channels"].items()},
            "lead_cue": res["lead"],
            "cues": {c: _rl(v) for c, v in res["scores"].items()},
            "values": {c: _rl(v, 3) for c, v in res["values"].items()},
        },
    }

    # ---- overlay: what a renderer needs, sampled at overlay_fps on the source clock
    step = max(1, int(round(fps / overlay_fps)))
    idx = np.arange(0, n, step)
    times = np.array([frames[i].time_s for i in idx])
    rel = times - t0
    boxes = zone_boxes(frames)
    overlay = {
        "schema": "behavior-overlay/1.0",
        "source": media.path, "width": media.width, "height": media.height,
        "fps": round(fps / step, 3), "video_fps": fps,
        "coords": "source pixels, y down; zone = [cx, cy, rx, ry] ellipse",
        "style": "one zone glows at a time; captions are opinion, never 'lying'",
        "t": _rl(times, 3),
        "pressure": _rl(np.interp(rel, centres, res["pressure"]), 1),
        "channels": {ch: _rl(np.interp(rel, centres, np.nan_to_num(v, nan=0.0))) for ch, v in res["channels"].items()},
        "zones": {k: [None if not np.isfinite(r[0]) else [int(round(x)) for x in r] for r in v[idx]]
                  for k, v in boxes.items()},
        "highlights": [{**h, "start_s": round(h["start_s"] + t0, 2), "end_s": round(h["end_s"] + t0, 2)}
                       for h in highlights(spots)],
        "hotspots": [{"start_s": round(h["start_s"] + t0, 2), "end_s": round(h["end_s"] + t0, 2),
                      "peak_s": round(h["peak_s"] + t0, 2), "pressure_peak": h["pressure_peak"],
                      "channels": h["channels"], "question": h.get("question")} for h in spots],
    }
    step_t = 1.0 / overlay.get("fps", overlay_fps)
    mdoc = {
        "schema": "behavior-moments/1.0",
        "source": media.path, "person": subject or "subject", "video_fps": fps,
        "rule": "face first: a moment starts from a face event (micro twitch, or 2+ face cues "
                "at z>=2.5) and needs one supporting channel at z>=2 or a second face event",
        "wording_rule": "opinion only; never 'lying'. Say once early: one signal proves nothing.",
        "idiolect": behavior["states"]["idiolect"],
        "moments": [],
    }
    for m in moments:
        a, b = m["t_start"], m["t_end"]
        box = [(round(float(tt), 2), bx) for tt, bx in zip(times, overlay["zones"]["face"])
               if a + t0 <= tt <= b + t0 and bx]
        mdoc["moments"].append({**m, "t_start": round(a + t0, 2), "t_end": round(b + t0, 2),
                                "peak_s": round(m["peak_s"] + t0, 2),
                                "slowmo": [round(x + t0, 2) for x in m["slowmo"]],
                                "face_box": box, "face_box_step_s": round(step_t, 3)})
    return behavior, overlay, mdoc


def _notes(cues: dict[str, Any], spots: list[dict[str, Any]], cfg: D.DeviationConfig) -> list[str]:
    out = [f"{len(spots)} moment(s) where {cfg.min_channels}+ channels moved at least {cfg.z} SD "
           f"from this person's baseline within {cfg.cluster_s:.0f} s."]
    top = sorted(((v["max_score"], k) for k, v in cues.items() if v["max_score"] is not None), reverse=True)[:5]
    if top:
        out.append("Largest single deviations: " + ", ".join(
            f"{CUE_BY_ID[k].label} {s:.1f} SD" for s, k in top) + ".")
    for h in spots[:5]:
        names = ", ".join(c["label"] for c in h["cues"][:4])
        q = f" after \"{h['question'][-60:]}\"" if h.get("question") else ""
        out.append(f"{h['start_s']:.1f}-{h['end_s']:.1f} s{q}: {names}.")
    return out
