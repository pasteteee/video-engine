"""Feature bank: turns one person's clip into thousands of named, plain quantities.

Naming: ``<signal>|<condition>|<functional>`` for time-series features, and
``<family>.<name>`` for event, language, timing and cross-modal features.
Nothing here is a judgement; ``psych.py`` attaches the research tags and the
interpretation is left to the downstream model.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Sequence

import numpy as np

from face_engine.featurebank import functionals, lexicon
from face_engine.featurebank.signals import audio_signals, engine_signals, geometry_signals, kinematic_signals
from face_engine.observations import FrameObservation

FULL_CONDITIONS = ("all", "speaking", "silent", "third1", "third2", "third3")
FOCUS_CONDITIONS = ("emphasis", "self_ref", "other_ref", "question", "clause_start", "clause_end", "long_pause")
FOCUS_FUNCS = ("mean", "std", "p90", "share_above_baseline_1sd", "peaks_per_min", "z_mean_vs_person", "mean_abs_delta_per_s")

CROSS_KEYS = ("kin.head_angular_speed", "au.AU12", "au.AU06", "au.AU01", "au.AU02", "au.AU04", "gaze.averted",
              "eye.closure", "face.expressivity", "body.gesture_activity", "geo.mouth_open", "geo.brow_height",
              "voice.loudness_db", "voice.pitch_st", "voice.onset_strength", "geo.face_scale", "body.lean_in")


def _words(words: Sequence[Sequence[Any]]) -> list[tuple[float, float, str]]:
    out = []
    for w in words:
        tok = lexicon.tokenize(str(w[2]))
        if tok:
            out.append((float(w[0]), float(w[1]), tok))
    return out


def _clauses(ws: list[tuple[float, float, str]], gap: float = 0.3) -> list[list[tuple[float, float, str]]]:
    cl, cur = [], []
    for i, w in enumerate(ws):
        if cur and (w[0] - cur[-1][1] >= gap or cur[-1][2][-1:] in ".?!"):
            cl.append(cur)
            cur = []
        cur.append(w)
    if cur:
        cl.append(cur)
    return cl


def _mask(n: int, fps: float, spans: list[tuple[float, float]]) -> np.ndarray:
    m = np.zeros(n, bool)
    for s, e in spans:
        a, b = max(0, int(s * fps)), min(n, int(np.ceil(e * fps)) + 1)
        if b > a:
            m[a:b] = True
    return m


def _stats(prefix: str, x: Sequence[float], out: dict[str, float]) -> None:
    x = np.asarray([v for v in x if v is not None and np.isfinite(v)], float)
    out[f"{prefix}.n"] = float(len(x))
    if len(x):
        out[f"{prefix}.mean"] = float(x.mean())
        out[f"{prefix}.median"] = float(np.median(x))
        out[f"{prefix}.std"] = float(x.std())
        out[f"{prefix}.max"] = float(x.max())
        out[f"{prefix}.p90"] = float(np.quantile(x, 0.9))


class FeatureBank:
    def __init__(self, fps: float, duration_s: float):
        self.fps, self.dur = fps, duration_s

    # ------------------------------------------------------------------ main
    def run(self, report: dict[str, Any], frames: Sequence[FrameObservation], clip: str | None,
            words: Sequence[Sequence[Any]] | None) -> dict[str, Any]:
        fps, n = self.fps, len(frames)
        sig: dict[str, np.ndarray] = {}
        sig.update(engine_signals(report, n))
        sig.update(geometry_signals(frames, fps))
        sig.update(kinematic_signals(sig, fps))
        audio = None
        if clip:
            au = audio_signals(clip, n, fps)
            audio = au.pop("_audio_raw")
            sig.update(au)
        ws = _words(words or [])
        clauses = _clauses(ws)
        cond = self._conditions(n, sig, ws, clauses)
        feats: dict[str, float] = {}
        self._timeseries(sig, cond, feats)
        self._events(report.get("events", []), cond, feats)
        self._language(ws, clauses, feats)
        self._timing(ws, clauses, sig, feats)
        self._cross(sig, cond, ws, clauses, report.get("events", []), feats)
        self._reliability(sig, ws, feats)
        clean = {k: (round(float(v), 5) if v is not None and np.isfinite(v) else None) for k, v in feats.items()}
        return {
            "schema": "featurebank/1",
            "duration_s": self.dur, "fps": fps, "n_frames": n,
            "n_features": len(clean), "n_valid": sum(v is not None for v in clean.values()),
            "conditions": {k: round(float(m.mean()), 4) for k, m in cond.items()},
            "features": clean,
        }

    # ------------------------------------------------------------ conditions
    def _conditions(self, n, sig, ws, clauses) -> dict[str, np.ndarray]:
        fps = self.fps
        cond = {"all": np.ones(n, bool)}
        if ws:
            speaking = _mask(n, fps, [(s - 0.05, e + 0.05) for s, e, _ in ws])
        elif "mouth.speaking" in sig:
            speaking = np.nan_to_num(sig["mouth.speaking"]) > 0.5
        else:
            speaking = np.zeros(n, bool)
        cond["speaking"], cond["silent"] = speaking, ~speaking
        for j in range(3):
            m = np.zeros(n, bool)
            m[j * n // 3:(j + 1) * n // 3] = True
            cond[f"third{j + 1}"] = m
        if ws:
            # emphasis = the loudest 20% of words (by mean loudness over the word)
            if "voice.loudness_db" in sig:
                ld = sig["voice.loudness_db"]
                lw = [np.nanmean(ld[int(s * fps):max(int(s * fps) + 1, int(e * fps))]) for s, e, _ in ws]
                thr = np.nanquantile(lw, 0.8)
                cond["emphasis"] = _mask(n, fps, [(s - 0.15, e + 0.15) for (s, e, _), l in zip(ws, lw) if l >= thr])
            b = lexicon.bare
            cond["self_ref"] = _mask(n, fps, [(s - 0.3, e + 0.3) for s, e, t in ws if b(t) in lexicon.CATEGORIES["pron_i"]])
            cond["other_ref"] = _mask(n, fps, [(s - 0.3, e + 0.3) for s, e, t in ws
                                               if b(t) in lexicon.CATEGORIES["pron_you"] | lexicon.CATEGORIES["pron_we"]])
            cond["question"] = _mask(n, fps, [(c[0][0], c[-1][1] + 1.0) for c in clauses
                                              if lexicon.clause_is_question([w[2] for w in c])])
            cond["clause_start"] = _mask(n, fps, [(c[0][0] - 0.3, c[0][0] + 0.7) for c in clauses])
            cond["clause_end"] = _mask(n, fps, [(c[-1][1] - 0.5, c[-1][1] + 0.5) for c in clauses])
            gaps = [(a[1], b_[0]) for a, b_ in zip(ws, ws[1:]) if b_[0] - a[1] >= 1.0]
            cond["long_pause"] = _mask(n, fps, gaps)
        return cond

    # ----------------------------------------------------------- time series
    def _timeseries(self, sig, cond, feats):
        fps = self.fps
        for name, x in sig.items():
            v = x[np.isfinite(x)]
            if len(v) < 5:
                feats[f"{name}|all|valid_share"] = len(v) / len(x)
                continue
            mu, sd = float(np.mean(v)), float(np.std(v))
            for c, m in cond.items():
                if m.sum() < max(5, fps * 0.5):
                    continue
                xc = np.where(m, x, np.nan)
                r = functionals.compute(xc, fps, mu, sd)
                if c in FOCUS_CONDITIONS:
                    r = {k: r[k] for k in FOCUS_FUNCS if k in r}
                for k, val in r.items():
                    feats[f"{name}|{c}|{k}"] = val
            # contrasts that matter for rapport: speaking vs silent, last third vs first third
            for a, b in (("speaking", "silent"), ("third3", "third1"), ("other_ref", "self_ref"), ("emphasis", "all")):
                ka, kb = f"{name}|{a}|mean", f"{name}|{b}|mean"
                if ka in feats and kb in feats and sd > 1e-9:
                    feats[f"{name}|{a}_minus_{b}|mean_z"] = (feats[ka] - feats[kb]) / sd

    # ---------------------------------------------------------------- events
    def _events(self, events, cond, feats):
        fps, mins = self.fps, self.dur / 60
        by = {}
        for e in events:
            by.setdefault(e.get("type", "?"), []).append(e)
        types = set(by) | {"blink", "smile", "head_nod", "head_shake", "gaze_averted", "gesture", "posture_shift",
                           "shrug", "face_touch", "open_palms", "eye_closure", "expression", "action_unit"}
        sp = cond["speaking"]
        for t in sorted(types):
            ev = by.get(t, [])
            p = f"event.{t}"
            feats[f"{p}.count"] = len(ev)
            feats[f"{p}.per_min"] = len(ev) / mins if mins else np.nan
            if not ev:
                continue
            _stats(f"{p}.duration_s", [e.get("duration_s") for e in ev], feats)
            _stats(f"{p}.peak", [e.get("peak") for e in ev], feats)
            starts = sorted(e["start_s"] for e in ev)
            if len(starts) > 2:
                iei = np.diff(starts)
                feats[f"{p}.interval_mean_s"] = float(iei.mean())
                feats[f"{p}.interval_cv"] = float(iei.std() / iei.mean()) if iei.mean() > 0 else np.nan
            idx = [min(len(sp) - 1, int(e.get("peak_s", e["start_s"]) * fps)) for e in ev]
            feats[f"{p}.share_while_speaking"] = float(np.mean([sp[i] for i in idx]))
            for c in ("third1", "third2", "third3", "emphasis", "question", "clause_end", "long_pause"):
                if c in cond and cond[c].sum() > 0:
                    rate = sum(cond[c][i] for i in idx) / (cond[c].sum() / fps / 60)
                    feats[f"{p}.per_min_in_{c}"] = rate
            sub = Counter(str(e.get("au") or e.get("label") or e.get("kind") or e.get("direction") or "") for e in ev)
            for k, cnt in sub.items():
                if k:
                    feats[f"{p}.kind.{k}.per_min"] = cnt / mins

    # -------------------------------------------------------------- language
    def _language(self, ws, clauses, feats):
        mins = self.dur / 60
        toks = [lexicon.bare(t) for _, _, t in ws if lexicon.bare(t)]
        n = len(toks)
        feats["lang.words"] = n
        feats["lang.words_per_min"] = n / mins if mins else np.nan
        if not n:
            return
        cnt = Counter(toks)
        thirds = [toks[j * n // 3:(j + 1) * n // 3] for j in range(3)]
        for cat, lex in lexicon.CATEGORIES.items():
            c = sum(cnt[w] for w in lex)
            feats[f"lang.{cat}.count"] = c
            feats[f"lang.{cat}.per_100w"] = 100 * c / n
            feats[f"lang.{cat}.per_min"] = c / mins
            for j, th in enumerate(thirds):
                if th:
                    feats[f"lang.{cat}.per_100w_third{j + 1}"] = 100 * sum(w in lex for w in th) / len(th)
        C = lexicon.CATEGORIES
        def r(a, b):
            ca, cb = sum(cnt[w] for w in C[a]), sum(cnt[w] for w in C[b])
            return ca / (ca + cb) if ca + cb else np.nan
        feats["lang.ratio.you_vs_i"] = r("pron_you", "pron_i")
        feats["lang.ratio.we_vs_i"] = r("pron_we", "pron_i")
        feats["lang.ratio.posemo_vs_negemo"] = r("posemo", "negemo")
        feats["lang.ratio.certainty_vs_hedge"] = r("certainty", "hedge")
        feats["lang.ratio.future_vs_past"] = r("future", "past")
        feats["lang.type_token_ratio"] = len(cnt) / n
        feats["lang.mattr_50"] = float(np.mean([len(set(toks[i:i + 50])) / 50 for i in range(0, max(1, n - 50), 10)])) if n >= 50 else np.nan
        feats["lang.hapax_share"] = sum(1 for v in cnt.values() if v == 1) / n
        feats["lang.mean_word_len"] = float(np.mean([len(t) for t in toks]))
        feats["lang.long_words_share"] = float(np.mean([len(t) >= 7 for t in toks]))
        syl = [lexicon.syllables(t) for t in toks]
        feats["lang.syllables_per_word"] = float(np.mean(syl))
        feats["lang.numbers.per_100w"] = 100 * sum(bool(lexicon.RE_NUMBER.match(t)) or t in C["number_word"] for t in toks) / n
        # clause/sentence structure
        cl_len = [len(c) for c in clauses]
        _stats("lang.clause_len_words", cl_len, feats)
        feats["lang.clauses_per_min"] = len(clauses) / mins
        wpc = np.mean(cl_len) if cl_len else np.nan
        feats["lang.flesch_reading_ease"] = 206.835 - 1.015 * wpc - 84.6 * float(np.mean(syl))
        feats["lang.fk_grade"] = 0.39 * wpc + 11.8 * float(np.mean(syl)) - 15.59
        qs = [c for c in clauses if lexicon.clause_is_question([w[2] for w in c])]
        n_q = sum(len(lexicon.question_onsets([w[2] for w in c])) for c in clauses)
        feats["lang.questions.count"] = n_q
        feats["lang.questions.per_min"] = n_q / mins
        feats["lang.questions.share_of_clauses"] = len(qs) / len(clauses) if clauses else np.nan
        feats["lang.questions.with_you_share"] = (
            np.mean([any(lexicon.bare(w[2]) in C["pron_you"] for w in c) for c in qs]) if qs else np.nan)
        # repetition / rhetorical devices
        bigrams = Counter(zip(toks, toks[1:]))
        trigrams = Counter(zip(toks, toks[1:], toks[2:]))
        feats["lang.repeated_bigram_share"] = sum(v for v in bigrams.values() if v > 1) / max(1, len(toks) - 1)
        feats["lang.repeated_trigram_types"] = sum(1 for v in trigrams.values() if v > 1)
        starts = Counter(lexicon.bare(c[0][2]) for c in clauses)
        feats["lang.anaphora_max_same_opening"] = max(starts.values()) if starts else 0
        feats["lang.anaphora_share"] = sum(v for v in starts.values() if v > 1) / len(clauses) if clauses else np.nan
        triads = sum(1 for i in range(len(toks) - 4) if toks[i + 1] in (",", "and") or (toks[i + 3] == "and" and toks[i + 1] != toks[i]))
        feats["lang.and_lists.per_min"] = triads / mins
        feats["lang.contrast_pairs.per_min"] = sum(cnt[w] for w in ("but", "not", "instead", "rather")) / mins
        feats["lang.because_justifications.per_min"] = cnt["because"] / mins
        feats["lang.direct_address_names.per_min"] = sum(cnt[w] for w in ("governor", "president", "senator", "friends", "folks", "americans")) / mins
        feats["lang.self_repairs.per_min"] = sum(1 for a, b in zip(toks, toks[1:]) if a == b) / mins
        feats["lang.first_person_opening_share"] = (
            np.mean([lexicon.bare(c[0][2]) in C["pron_i"] for c in clauses]) if clauses else np.nan)

    # ---------------------------------------------------------------- timing
    def _timing(self, ws, clauses, sig, feats):
        if len(ws) < 3:
            return
        fps = self.fps
        gaps = np.array([b[0] - a[1] for a, b in zip(ws, ws[1:])])
        gaps = np.clip(gaps, 0, None)
        pauses = gaps[gaps >= 0.25]
        _stats("timing.pause_s", pauses, feats)
        mins = self.dur / 60
        for thr in (0.25, 0.5, 1.0, 1.5, 2.0):
            feats[f"timing.pauses_ge_{thr}s.per_min"] = float((gaps >= thr).sum() / mins)
        feats["timing.long_pause_share_of_time"] = float(gaps[gaps >= 1.0].sum() / self.dur)
        feats["timing.silence_share"] = float(1 - sum(e - s for s, e, _ in ws) / self.dur)
        dur_words = np.array([e - s for s, e, _ in ws])
        _stats("timing.word_duration_s", dur_words, feats)
        syl = np.array([lexicon.syllables(lexicon.bare(t)) for _, _, t in ws])
        speech_time = dur_words.sum()
        feats["timing.articulation_rate_syl_s"] = float(syl.sum() / speech_time) if speech_time else np.nan
        feats["timing.speech_rate_syl_s"] = float(syl.sum() / self.dur)
        # rate in 10 s windows
        win = []
        for t0 in np.arange(0, self.dur - 5, 5):
            win.append(sum(1 for s, _, _ in ws if t0 <= s < t0 + 10) * 6)
        _stats("timing.wpm_10s_window", win, feats)
        if len(win) > 2:
            feats["timing.wpm_10s_window.cv"] = float(np.std(win) / np.mean(win)) if np.mean(win) else np.nan
        # what the pause sits next to
        C = lexicon.CATEGORIES
        b = lexicon.bare
        after_q, before_key = [], []
        for c_i, c in enumerate(clauses[:-1]):
            nxt = clauses[c_i + 1][0][0] - c[-1][1]
            if lexicon.clause_is_question([w[2] for w in c]):
                after_q.append(nxt)
        _stats("timing.pause_after_question_s", after_q, feats)
        for i in range(1, len(ws)):
            if b(ws[i][2]) in C["pron_you"] | C["pron_we"]:
                before_key.append(ws[i][0] - ws[i - 1][1])
        _stats("timing.pause_before_you_we_s", before_key, feats)
        fills = [i for i, (_, _, t) in enumerate(ws) if b(t) in ("um", "uh", "er", "ah", "erm")]
        feats["timing.filled_pauses.per_min"] = len(fills) / mins
        # clause-final pitch movement: rising vs falling terminals (uptalk / declarative fall)
        if "voice.pitch_st" in sig:
            ps = sig["voice.pitch_st"]
            slopes, resets, ranges = [], [], []
            prev_end = None
            for c in clauses:
                s, e = c[0][0], c[-1][1]
                seg = ps[int(s * fps):int(e * fps) + 1]
                tail = ps[int(max(s, e - 0.6) * fps):int(e * fps) + 1]
                tv = np.where(np.isfinite(tail))[0]
                if len(tv) >= 4:
                    slopes.append(np.polyfit(tv / fps, tail[tv], 1)[0])
                fv = seg[np.isfinite(seg)]
                if len(fv) >= 5:
                    ranges.append(np.quantile(fv, 0.9) - np.quantile(fv, 0.1))
                    if prev_end is not None:
                        resets.append(np.median(fv[:5]) - prev_end)
                    prev_end = float(np.median(fv[-5:]))
            _stats("timing.clause_terminal_slope_st_s", slopes, feats)
            if slopes:
                feats["timing.clause_terminal_rise_share"] = float(np.mean(np.array(slopes) > 2))
                feats["timing.clause_terminal_fall_share"] = float(np.mean(np.array(slopes) < -2))
            _stats("timing.clause_pitch_range_st", ranges, feats)
            _stats("timing.pitch_reset_st", resets, feats)

    # ----------------------------------------------------------- cross-modal
    def _cross(self, sig, cond, ws, clauses, events, feats):
        fps = self.fps
        keys = [k for k in CROSS_KEYS if k in sig and np.isfinite(sig[k]).sum() > fps * 5]
        for state in ("all", "speaking"):
            m = cond.get(state)
            if m is None:
                continue
            for i, a in enumerate(keys):
                for b in keys[i + 1:]:
                    xa, xb = sig[a], sig[b]
                    ok = m & np.isfinite(xa) & np.isfinite(xb)
                    if ok.sum() > fps * 5 and np.std(xa[ok]) > 1e-9 and np.std(xb[ok]) > 1e-9:
                        feats[f"cross.corr.{a}~{b}|{state}"] = float(np.corrcoef(xa[ok], xb[ok])[0, 1])
        # lagged coupling of face/body with the voice: at what lag does movement best track loudness?
        L = int(fps)
        for a in ("kin.head_angular_speed", "au.AU01", "au.AU02", "body.gesture_activity", "au.AU12", "eye.closure"):
            for b in ("voice.loudness_db", "voice.onset_strength", "voice.pitch_st"):
                if a not in sig or b not in sig:
                    continue
                xa, xb = sig[a], sig[b]
                best, blag = -2.0, 0
                for lag in range(-L, L + 1, max(1, L // 10)):
                    ya = xa[max(0, lag):len(xa) + min(0, lag)]
                    yb = xb[max(0, -lag):len(xb) + min(0, -lag)]
                    ok = np.isfinite(ya) & np.isfinite(yb)
                    if ok.sum() > fps * 5 and np.std(ya[ok]) > 1e-9 and np.std(yb[ok]) > 1e-9:
                        c = np.corrcoef(ya[ok], yb[ok])[0, 1]
                        if c > best:
                            best, blag = c, lag
                if best > -2:
                    feats[f"cross.xcorr.{a}~{b}.peak"] = best
                    feats[f"cross.xcorr.{a}~{b}.lag_ms"] = blag / fps * 1000  # >0: movement leads voice
        # event alignment with speech structure
        b = lexicon.bare
        word_on = np.array([s for s, _, _ in ws]) if ws else np.array([])
        stressed = []
        if ws and "voice.loudness_db" in sig:
            ld = sig["voice.loudness_db"]
            lw = np.array([np.nanmean(ld[int(s * fps):max(int(s * fps) + 1, int(e * fps))]) for s, e, _ in ws])
            stressed = word_on[lw >= np.nanquantile(lw, 0.8)]
        cl_end = np.array([c[-1][1] for c in clauses]) if clauses else np.array([])
        cl_start = np.array([c[0][0] for c in clauses]) if clauses else np.array([])
        for t in ("head_nod", "head_shake", "blink", "smile", "gaze_averted", "gesture", "shrug", "posture_shift"):
            ts = np.array([e.get("peak_s", e["start_s"]) for e in events if e.get("type") == t])
            if not len(ts):
                continue
            for lab, ref, w in (("stressed_word", stressed, 0.3), ("clause_end", cl_end, 0.6), ("clause_start", cl_start, 0.6),
                                ("word_onset", word_on, 0.2)):
                if len(ref):
                    d = np.array([np.min(np.abs(ref - x)) for x in ts])
                    feats[f"align.{t}.near_{lab}_share"] = float(np.mean(d <= w))
                    feats[f"align.{t}.to_{lab}_median_ms"] = float(np.median(d) * 1000)
            if "long_pause" in cond:
                idx = np.clip((ts * fps).astype(int), 0, len(cond["long_pause"]) - 1)
                feats[f"align.{t}.in_long_pause_share"] = float(np.mean(cond["long_pause"][idx]))
        # gaze while speaking vs while silent: 'visual dominance ratio' proxy (Exline/Dovidio)
        if "gaze.averted" in sig:
            g = sig["gaze.averted"]
            on_sp = np.nanmean(1 - g[cond["speaking"]]) if cond["speaking"].any() else np.nan
            on_si = np.nanmean(1 - g[cond["silent"]]) if cond["silent"].any() else np.nan
            feats["cross.gaze_on_speaking"] = on_sp
            feats["cross.gaze_on_silent"] = on_si
            feats["cross.visual_dominance_ratio"] = on_sp / on_si if on_si and np.isfinite(on_si) and on_si > 0 else np.nan

    def _reliability(self, sig, ws, feats):
        for k in ("face.present", "body.present", "body.hands_visible", "face.reliability"):
            if k in sig:
                feats[f"meta.{k}"] = float(np.nanmean(sig[k]))
        feats["meta.duration_s"] = self.dur
        feats["meta.has_transcript"] = float(bool(ws))
        feats["meta.has_audio"] = float("voice.loudness_db" in sig)
        if "geo.face_scale" in sig:
            feats["meta.face_px_scale_var"] = float(np.nanstd(sig["geo.face_scale"]))
