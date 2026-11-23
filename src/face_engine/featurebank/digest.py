"""Turns one or more feature-bank files into an LLM-ready brief.

The full bank (tens of thousands of numbers) stays in JSON for the model to query;
the digest picks what differs most, groups it by research dimension and attaches
the evidence tag, so the model reads the largest contrasts first.

Usage: python -m face_engine.featurebank.digest NAME=bank.json [NAME=bank.json ...] -o brief.md
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict

from face_engine.featurebank.psych import DIMENSIONS, tag

# rough population ranges for quick single-person reading (conversational adult speech)
NORMS = {
    "event.blink.per_min": (8, 26, "blinks/min at rest-to-conversation"),
    "lang.words_per_min": (140, 170, "typical public speaking rate"),
    "timing.articulation_rate_syl_s": (4.0, 5.5, "syllables per second while talking"),
    "lang.pron_i.per_100w": (3, 7, "I-words per 100 words (Pennebaker norms ~4-6)"),
    "lang.pron_you.per_100w": (1, 4, "you-words per 100 words"),
    "timing.filled_pauses.per_min": (0, 4, "um/uh per minute (if the transcript keeps them)"),
}


RANK_FUNCS = {"mean", "median", "iqr", "std", "share_above_baseline_1sd", "share_below_baseline_1sd",
              "peaks_per_min", "high_episodes_per_min", "mean_abs_delta_per_s", "z_mean_vs_person", "autocorr_1s",
              "mean_z"}
RELATIVE_FUNCS = {"share_above_baseline_1sd", "share_below_baseline_1sd", "peaks_per_min", "high_episodes_per_min",
                  "z_mean_vs_person", "autocorr_1s", "mean_z"}


def _scale(name: str, banks: dict[str, dict]) -> float | None:
    """Per-feature scale for comparing people.

    Location/spread functionals use the signal's whole-clip spread (pooled over people), so a
    difference reads as 'how many typical moment-to-moment swings apart'. Rates, shares and
    person-relative values use a relative scale with a floor, so tiny denominators cannot explode.
    """
    if name.count("|") == 2:
        sig, _cond, fn = name.split("|")
        if fn in ("mean", "median"):
            sds = [b["features"].get(f"{sig}|all|std") for b in banks.values()]
            sds = [s for s in sds if s]
            if sds:
                return sum(sds) / len(sds)
        elif fn not in RELATIVE_FUNCS:
            # spread/rate functionals: scale by the same functional over the whole clip
            sds = [abs(b["features"].get(f"{sig}|all|{fn}") or 0) for b in banks.values()]
            sds = [s for s in sds if s]
            if sds:
                return sum(sds) / len(sds)
        if fn in ("z_mean_vs_person", "mean_z"):
            return 0.5  # already in the person's own SD units; 0.5 SD apart -> d = 1
    vals = [b["features"].get(name) for b in banks.values()]
    vals = [abs(v) for v in vals if v is not None]
    if not vals:
        return None
    m = sum(vals) / len(vals)
    return max(m, 0.1)


MIN_COVERAGE = 0.3


def _rankable(name: str) -> bool:
    if name.startswith("meta.") or name.endswith(".n") or ".max" in name or name.endswith(".p90"):
        return False
    if name.count("|") == 2:
        return name.rsplit("|", 1)[1] in RANK_FUNCS
    return True


def _signal_key(name: str) -> str:
    if name.count("|") == 2:
        return name.split("|")[0]
    parts = name.split(".")
    return ".".join(parts[:2])


def compare(banks: dict[str, dict], top: int = 12, per_signal: int = 2) -> dict:
    names = list(banks)
    a, b = names[0], names[1]
    fa, fb = banks[a]["features"], banks[b]["features"]
    rows = []
    for k in fa.keys() & fb.keys():
        va, vb = fa[k], fb[k]
        if va is None or vb is None or not _rankable(k):
            continue
        if k.count("|") == 2:
            sig, cond, _ = k.split("|")
            cov = [banks[n]["features"].get(f"{sig}|{cond}|valid_share") for n in (a, b)]
            if any(c is not None and c < MIN_COVERAGE for c in cov):
                continue
        s = _scale(k, banks)
        if not s:
            continue
        d = max(-10.0, min(10.0, (vb - va) / s))
        rows.append((abs(d), d, k, va, vb, tag(k)))
    rows.sort(key=lambda r: -r[0])
    by_dim = defaultdict(list)
    used = defaultdict(int)
    untagged = []
    for r in rows:
        sk = _signal_key(r[2])
        if used[sk] >= per_signal:
            continue
        t = r[5]
        if t is None:
            if len(untagged) < top:
                untagged.append(r)
                used[sk] += 1
            continue
        placed = False
        for dim in t.dims:
            if len(by_dim[dim]) < top:
                by_dim[dim].append(r)
                placed = True
        if placed:
            used[sk] += 1
    return {"a": a, "b": b, "n_compared": len(rows), "by_dim": by_dim, "untagged": untagged}


def _fmt(v: float) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "-"
    return f"{v:.3g}"


def render(banks: dict[str, dict], top: int = 12) -> str:
    out = ["# Behaviour feature brief", ""]
    out.append("Plain per-person quantities from video, audio and transcript. Behaviour only: no lie detection, "
               "no claims about intent or felt emotion. Interpret against the research tags and the reliability lines.")
    out.append("")
    for n, b in banks.items():
        f = b["features"]
        out.append(f"## {n}: coverage")
        out.append(f"- {b['n_features']} features, {b['n_valid']} with a value; {b['duration_s']:.0f} s; "
                   f"face visible {_fmt(f.get('meta.face.present'))}, body {_fmt(f.get('meta.body.present'))}, "
                   f"hands {_fmt(f.get('meta.body.hands_visible'))}, transcript {bool(f.get('meta.has_transcript'))}")
        for k, (lo, hi, lab) in NORMS.items():
            v = f.get(k)
            if v is not None:
                flag = "below" if v < lo else "above" if v > hi else "within"
                out.append(f"- {k} = {_fmt(v)} ({flag} {lo}-{hi}, {lab})")
        out.append("")
    if len(banks) >= 2:
        c = compare(banks, top)
        out.append(f"## Largest differences: {c['b']} relative to {c['a']}")
        out.append(f"{c['n_compared']} features compared. d = ({c['b']} - {c['a']}) / within-person spread. "
                   "Grade A = meta-analysis, B = replicated, C = single study, D = weak/practitioner.")
        out.append("")
        for dim in sorted(c["by_dim"], key=lambda x: -c["by_dim"][x][0][0]):
            out.append(f"### {dim}: {DIMENSIONS.get(dim, '')}")
            out.append(f"| feature | {c['a']} | {c['b']} | d | factor | lit. direction | grade |")
            out.append("|---|---|---|---|---|---|---|")
            for _, d, k, va, vb, t in c["by_dim"][dim]:
                out.append(f"| `{k}` | {_fmt(va)} | {_fmt(vb)} | {d:+.2f} | {t.factor} | {t.direction} | {t.grade} |")
            out.append("")
        if c["untagged"]:
            out.append("### Untagged large differences (no research prior; treat as exploratory)")
            for _, d, k, va, vb, _t in c["untagged"]:
                out.append(f"- `{k}`: {_fmt(va)} vs {_fmt(vb)} (d {d:+.2f})")
            out.append("")
    return "\n".join(out)


def main(argv=None) -> None:
    p = argparse.ArgumentParser()
    p.add_argument("banks", nargs="+", help="NAME=path.json")
    p.add_argument("-o", "--out", required=True)
    p.add_argument("--top", type=int, default=12)
    a = p.parse_args(argv)
    banks = {}
    for s in a.banks:
        n, path = s.split("=", 1)
        banks[n] = json.load(open(path))
    open(a.out, "w").write(render(banks, a.top))
    print(a.out)


if __name__ == "__main__":
    main()
