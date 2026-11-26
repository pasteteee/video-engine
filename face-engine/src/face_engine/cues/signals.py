"""Per-frame cue tracks built from the engine report, the raw landmarks, audio and words.

Each track is an array over the analysed frames. ``agg`` says how a window turns it into
one number: ``mean`` (level or share, NaN-aware) or ``rate`` (impulse train -> events per
minute over the valid frames of the window).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np

from face_engine import temporal as T
from face_engine.featurebank import lexicon
from face_engine.observations import FrameObservation
from face_engine.topology import BODY_INDEX, FACE_INDEX


@dataclass
class Track:
    values: np.ndarray
    agg: str = "mean"  # mean | rate
    valid: np.ndarray | None = None  # frames where the cue could be observed (rate tracks)
    min_valid_s: float | None = None  # observable seconds a window needs (default: half the window)


@dataclass
class Word:
    start: float
    end: float
    text: str  # normalised token, punctuation kept
    speaker: str | None = None

    @property
    def bare(self) -> str:
        return lexicon.bare(self.text)


@dataclass
class SpeechInfo:
    words: list[Word] = field(default_factory=list)
    questions: list[dict[str, Any]] = field(default_factory=list)


# --------------------------------------------------------------------------- helpers

def _col(report_frames: list[dict[str, Any]], key: str, n: int) -> np.ndarray:
    out = np.full(n, np.nan)
    for j, row in enumerate(report_frames[:n]):
        v = row.get(key)
        if isinstance(v, (int, float)):
            out[j] = float(v)
    return out


def _impulses(n: int, fps: float, times: Sequence[float]) -> np.ndarray:
    x = np.zeros(n)
    for t in times:
        k = int(round(t * fps))
        if 0 <= k < n:
            x[k] += 1
    return x


def _seg_dist(p: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    ab = b - a
    t = np.clip(((p - a) @ ab) / max(float(ab @ ab), 1e-9), 0, 1)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1)


def touch_zones(frames: Sequence[FrameObservation], min_vis: float = 0.5) -> dict[str, np.ndarray]:
    """Hand-to-neck and hand-to-head contact (0/1/NaN) from pose and hand landmarks."""
    n = len(frames)
    neck, head = np.full(n, np.nan), np.full(n, np.nan)
    B = BODY_INDEX
    for i, f in enumerate(frames):
        if f.body is None:
            continue
        b = np.asarray(f.body, float)
        vis = np.ones(len(b)) if f.body_visibility is None else np.asarray(f.body_visibility, float)
        ok = lambda k: bool(np.isfinite(vis[B[k]]) and vis[B[k]] >= min_vis and np.isfinite(b[B[k]]).all())  # noqa: E731
        if not (ok("l_shoulder") and ok("r_shoulder") and ok("nose")):
            continue
        ls, rs, nose = b[B["l_shoulder"], :2], b[B["r_shoulder"], :2], b[B["nose"], :2]
        sw = float(np.linalg.norm(ls - rs))
        if sw < 1e-6:
            continue
        pts = [h.points[:, :2] for h in f.hands if h.points is not None and len(h.points)]
        for s in ("l", "r"):
            for k in (f"{s}_wrist", f"{s}_index"):
                if ok(k):
                    pts.append(b[B[k], :2][None])
        if not pts:
            neck[i] = head[i] = 0.0
            continue
        p = np.vstack(pts)
        mid = (ls + rs) / 2
        if f.face is not None and np.isfinite(f.face[FACE_INDEX["chin"]]).all():
            chin = np.asarray(f.face[FACE_INDEX["chin"], :2], float)
        else:
            chin = nose + (mid - nose) * 0.45
        near_neck = _seg_dist(p, chin + (mid - chin) * 0.15, mid + (chin - mid) * 0.1) < 0.18 * sw
        neck[i] = float(np.any(near_neck & (p[:, 1] < chin[1])))
        # Above the eyes (y up) and within the head's width.
        eye_y = nose[1] + 0.12 * sw
        in_head = (p[:, 1] > eye_y) & (np.abs(p[:, 0] - nose[0]) < 0.45 * sw) & (p[:, 1] < nose[1] + 0.8 * sw)
        head[i] = float(np.any(in_head))
    return {"neck": neck, "head": head}


# --------------------------------------------------------------------------- words

FILLERS = lexicon.CATEGORIES["filler"]
HEDGE_PHRASES = (
    "i think", "i believe", "i guess", "i suppose", "i mean", "to be honest", "honestly",
    "frankly", "to the best of my", "as far as i", "sort of", "kind of", "maybe", "perhaps",
    "probably", "possibly", "i'm not sure", "not sure", "basically", "you know",
)
NON_RECALL = (
    "i don't know", "i dont know", "i don't recall", "i dont recall", "i don't remember",
    "i dont remember", "i can't remember", "i cant remember", "i can't recall",
    "no recollection", "not that i recall", "not that i remember", "i'm not aware",
    "i am not aware", "don't recall", "don't remember",
)
CERTAINTY = frozenset("absolutely definitely certainly sure positive clearly undoubtedly "
                      "obviously totally completely".split())
YES = frozenset("yes yeah yep yup correct".split())
NO = frozenset("no nope never".split())


def parse_words(raw: Sequence[Sequence[Any]] | Sequence[dict[str, Any]]) -> list[Word]:
    """Accepts [start, end, text(, speaker)] rows or {start, end, word|text, speaker} dicts."""
    out: list[Word] = []
    for w in raw:
        if isinstance(w, dict):
            s, e = float(w["start"]), float(w["end"])
            text, spk = w.get("word", w.get("text", "")), w.get("speaker")
        else:
            if len(w) < 3:
                raise ValueError("each word must be [start_s, end_s, text(, speaker)]")
            s, e, text = float(w[0]), float(w[1]), w[2]
            spk = w[3] if len(w) > 3 else None
        tok = lexicon.tokenize(str(text))
        if tok and np.isfinite([s, e]).all() and e >= s >= 0:
            out.append(Word(s, max(e, s + 1e-3), tok, None if spk is None else str(spk)))
    out.sort(key=lambda w: w.start)
    return out


def _phrase_hits(words: list[Word], phrases: Sequence[str]) -> list[float]:
    """Start times of phrase matches; overlapping matches count once."""
    toks = [w.bare for w in words]
    hits, used = [], -1
    split = [p.split() for p in phrases]
    for i in range(len(toks)):
        if i <= used:
            continue
        for ph in split:
            if toks[i:i + len(ph)] == ph:
                hits.append(words[i].start)
                used = i + len(ph) - 1
                break
    return hits


def _repairs(words: list[Word]) -> list[float]:
    """Immediate word repetitions ('I- I', 'the the') and cut-off restarts ('wa-')."""
    out = []
    for a, b in zip(words, words[1:]):
        if b.start - a.end > 1.0:
            continue
        if a.bare and a.bare == b.bare and a.bare not in ("no", "yes", "very", "that", "had"):
            out.append(b.start)
        elif re.search(r"[a-z]-$", a.text):
            out.append(b.start)
    return out


def find_questions(words: list[Word], subject: str | None,
                   explicit: Sequence[Any] = ()) -> list[dict[str, Any]]:
    """Question ends and the subject's answer onset.

    * explicit: list of end times (s) or {"end_s", "text"} dicts / [start, end, text] rows
    * else with speaker labels: every change from another speaker to the subject
    * else: words ending in '?' (only if the transcript is punctuated)
    """
    qs: list[dict[str, Any]] = []
    if explicit:
        for q in explicit:
            if isinstance(q, dict):
                qs.append({"end_s": float(q["end_s"]), "start_s": float(q.get("start_s", q["end_s"])),
                           "text": q.get("text", "")})
            elif isinstance(q, (list, tuple)):
                qs.append({"start_s": float(q[0]), "end_s": float(q[1]), "text": str(q[2]) if len(q) > 2 else ""})
            else:
                qs.append({"start_s": float(q), "end_s": float(q), "text": ""})
    elif subject is not None and any(w.speaker for w in words):
        turn: list[Word] = []
        for w in words:
            if w.speaker != subject:
                turn.append(w)
                continue
            if turn:
                qs.append({"start_s": turn[0].start, "end_s": turn[-1].end,
                           "text": " ".join(x.bare for x in turn)[-160:]})
                turn = []
    else:
        start = 0
        for j, w in enumerate(words):
            if w.text.endswith("?"):
                qs.append({"start_s": words[start].start, "end_s": w.end,
                           "text": " ".join(x.bare for x in words[start:j + 1])[-160:]})
                start = j + 1
            elif w.text[-1:] in ".!":
                start = j + 1
    qs.sort(key=lambda q: q["end_s"])
    subj = [w for w in words if subject is None or w.speaker in (None, subject)]
    for k, q in enumerate(qs):
        nxt = qs[k + 1]["start_s"] if k + 1 < len(qs) else np.inf
        ans = [w for w in subj if q["end_s"] - 0.05 <= w.start < nxt]
        if ans:
            q["answer_start_s"] = round(ans[0].start, 3)
            q["latency_s"] = round(max(0.0, ans[0].start - q["end_s"]), 3)
            q["answer_end_s"] = round(ans[-1].end, 3)
            q["answer_text"] = " ".join(w.bare for w in ans)[:200]
    return qs


# --------------------------------------------------------------------------- builder

def build_tracks(
    report: dict[str, Any],
    frames: Sequence[FrameObservation],
    fps: float,
    audio: dict[str, np.ndarray] | None = None,
    words: list[Word] | None = None,
    subject: str | None = None,
) -> tuple[dict[str, Track], dict[str, np.ndarray]]:
    """Returns (cue tracks, helper masks). The report must have one frame row per frame."""
    n = len(frames)
    rf = report["frames"]
    if len(rf) != n:
        raise ValueError("report must hold every analysed frame (run the engine with frames_fps=None)")
    c = lambda k: _col(rf, k, n)  # noqa: E731
    face_ok = (np.nan_to_num(c("face.present")) > 0) & (np.nan_to_num(c("face.reliability")) >= 0.5)
    body_ok = np.nan_to_num(c("body.present")) > 0
    fmask = lambda x: np.where(face_ok, x, np.nan)  # noqa: E731
    bmask = lambda x: np.where(body_ok, x, np.nan)  # noqa: E731
    events = report.get("events", [])
    ev_times = lambda kind, pred=lambda e: True: [e["start_s"] for e in events if e["type"] == kind and pred(e)]  # noqa: E731

    t: dict[str, Track] = {}
    au = {k: c(f"au.{k}") for k in ("AU01", "AU02", "AU04", "AU05", "AU06", "AU07", "AU09", "AU10",
                                     "AU12", "AU15", "AU17", "AU20", "AU23", "AU25")}
    t["lip_press"] = Track(fmask(au["AU23"] * (1 - np.nan_to_num(au["AU25"]))))
    t["chin_raise"] = Track(fmask(au["AU17"]))
    t["lip_corner_depress"] = Track(fmask(au["AU15"]))
    t["brow_lower"] = Track(fmask(au["AU04"]))
    t["inner_brow_raise"] = Track(fmask(np.clip(au["AU01"] - au["AU02"], 0, 1)))
    t["eyes_widen"] = Track(fmask(au["AU05"]))
    t["lid_tighten"] = Track(fmask(au["AU07"]))
    t["lip_stretch"] = Track(fmask(au["AU20"]))
    t["disgust_face"] = Track(fmask(np.fmax(au["AU09"], au["AU10"])))
    t["social_smile"] = Track(fmask(c("smile.social")))
    t["one_sided_mouth"] = Track(fmask(np.fmax(c("expr.contempt"), np.abs(c("asym.mouth")))))
    thick, lower = c("mouth.lip_thickness_rel"), c("mouth.lower_lip_rel")
    closed = 1 - np.nan_to_num(au["AU25"])
    suck = np.fmax(np.clip((0.8 - thick) / 0.5, 0, 1), np.clip((0.75 - lower) / 0.55, 0, 1)) * closed
    t["lip_suck"] = Track(fmask(suck))
    t["expressivity"] = Track(fmask(c("face.expressivity")))

    eye_ok = face_ok & np.isfinite(c("eye.closure"))
    t["blink_rate"] = Track(_impulses(n, fps, ev_times("blink")), "rate", eye_ok)
    closed = np.zeros(n)
    for e in events:
        if e["type"] == "eye_closure":
            a, b = int(round(e["start_s"] * fps)), int(round(e["end_s"] * fps))
            closed[max(0, a):min(n, b)] = 1
    t["long_closures"] = Track(np.where(eye_ok, closed, np.nan))
    gz = fmask(c("gaze.averted"))
    t["gaze_aversion"] = Track(gz)
    on = np.nan_to_num(gz) > 0.5
    shifts = np.flatnonzero(on[1:] & ~on[:-1]) + 1
    t["gaze_shifts"] = Track(_impulses(n, fps, shifts / fps), "rate", face_ok)

    t["head_motion"] = Track(fmask(c("head.angular_speed_deg_s")))
    t["head_nods"] = Track(_impulses(n, fps, ev_times("head_nod")), "rate", face_ok)
    t["head_shakes"] = Track(_impulses(n, fps, ev_times("head_shake")), "rate", face_ok)
    t["head_down"] = Track(fmask(-c("head.pitch_rel")))

    t["lean_back"] = Track(bmask(-c("body.lean_in")))
    t["posture_shifts"] = Track(_impulses(n, fps, ev_times("posture_shift")), "rate", body_ok)
    t["shrugs"] = Track(_impulses(n, fps, ev_times("shrug")), "rate", body_ok)
    t["arms_crossed"] = Track(bmask(c("body.arms_crossed")))
    torso = np.full(n, np.nan)
    for i, f in enumerate(frames):
        if f.body is not None:
            b = np.asarray(f.body, float)
            ls, rs = b[BODY_INDEX["l_shoulder"], :2], b[BODY_INDEX["r_shoulder"], :2]
            sw = np.linalg.norm(ls - rs)
            if np.isfinite(sw) and sw > 1:
                torso[i] = ((ls + rs) / 2 / sw)[0]
    sway = np.full(n, np.nan)
    sway[1:] = np.abs(np.diff(torso)) * fps
    k = max(1, int(round(0.2 * fps)))
    sway = np.convolve(np.nan_to_num(sway), np.ones(k) / k, "same")
    t["body_motion"] = Track(bmask(np.where(np.isfinite(torso), sway, np.nan)))

    t["illustrators"] = Track(bmask(c("body.gesturing")))
    t["self_touch_face"] = Track(bmask(c("body.face_touch")))
    zones = touch_zones(frames)
    t["self_touch_neck"] = Track(bmask(zones["neck"]))
    t["self_touch_head"] = Track(bmask(zones["head"]))
    t["hand_wringing"] = Track(bmask(c("body.hands_joined")))

    helpers: dict[str, np.ndarray] = {"face_ok": face_ok, "body_ok": body_ok}
    speaking = np.nan_to_num(c("mouth.speaking")) > 0.5
    if audio is not None:
        voiced = np.nan_to_num(audio["voice.voiced"][:n]) > 0.5
        # Keep the subject's voice only: their lips move (or, with labelled words, it is their
        # turn). Frames without a usable face fall back to voicing alone.
        own = np.ones(n, bool)
        if words and subject is not None and any(w.speaker for w in words):
            own = np.zeros(n, bool)
            for w in words:
                if w.speaker == subject:
                    own[max(0, int(w.start * fps)):min(n, int(np.ceil(w.end * fps)) + 1)] = True
        elif face_ok.mean() > 0.3:
            lips = T.dilate(speaking, int(round(0.3 * fps)))
            own = lips | ~face_ok
        voiced = voiced & own
        speaking = voiced
        pitch = np.where(voiced, audio["voice.pitch_st"][:n], np.nan)
        t["pitch"] = Track(pitch)
        t["pitch_variability"] = Track(pitch, "std")
        loud = np.where(voiced, audio["voice.loudness_db"][:n], np.nan)
        t["loudness"] = Track(loud)
        jit = np.where(voiced, audio["voice.jitter_like"][:n], np.nan)
        shim = audio["voice.shimmer_like_db"][:n]
        tension = np.clip(jit * 20, 0, 3) + np.clip(shim / 3, 0, 3)
        t["voice_tension"] = Track(np.where(voiced, tension, np.nan))
        # Unvoiced frames inside a speaking turn (gaps <= 3 s between voiced frames).
        sil = np.full(n, np.nan)
        idx = np.flatnonzero(voiced)
        if len(idx):
            sil[idx] = 0.0
            for a, b in zip(idx, idx[1:]):
                if 1 < b - a <= 3 * fps:
                    sil[a + 1:b] = 1.0
        t["silence"] = Track(sil)
    helpers["speaking"] = speaking

    if words:
        subj = [w for w in words if subject is None or w.speaker in (None, subject)]
        turn = np.zeros(n, bool)
        for a, b in zip(subj, subj[1:] + [None]):
            end = b.start if b is not None and b.start - a.end < 1.0 else a.end
            turn[max(0, int(a.start * fps)):min(n, int(np.ceil(end * fps)))] = True
        helpers["turn"] = turn
        t["speech_rate"] = Track(_impulses(n, fps, [w.start for w in subj]), "rate", turn, 1.0)
        t["fillers"] = Track(_impulses(n, fps, [w.start for w in subj if w.bare in FILLERS]), "rate", turn, 1.0)
        t["hedges"] = Track(_impulses(n, fps, _phrase_hits(subj, HEDGE_PHRASES)), "rate", turn, 1.0)
        t["non_recall"] = Track(_impulses(n, fps, _phrase_hits(subj, NON_RECALL)), "rate", turn, 1.0)
        t["repairs"] = Track(_impulses(n, fps, _repairs(subj)), "rate", turn, 1.0)
        nods = [(e["start_s"], e["end_s"]) for e in events if e["type"] == "head_nod"]
        shakes = [(e["start_s"], e["end_s"]) for e in events if e["type"] == "head_shake"]
        shr = [(e["start_s"], e["end_s"]) for e in events if e["type"] == "shrug"]
        near = lambda w, spans: any(s - 1.0 <= w.start <= e + 1.0 for s, e in spans)  # noqa: E731
        mism = [w.start for w in subj if (w.bare in YES and near(w, shakes)) or (w.bare in NO and near(w, nods))]
        sure = [w.start for w in subj if w.bare in CERTAINTY and near(w, shr)]
        t["yes_no_mismatch"] = Track(_impulses(n, fps, mism), "rate", turn | face_ok)
        t["certainty_shrug"] = Track(_impulses(n, fps, sure), "rate", turn | body_ok)
        helpers["mismatch_times"] = np.array(mism + sure)
    return t, helpers
