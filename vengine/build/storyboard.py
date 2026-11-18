"""Storyboard of a build short: timing, captions and music events, all derived from the knit plan.

The knit plan (schema `knit_plan`) says, frame by frame, which piece and round is being worked and how much of
the yarn is made. From it come the captions ("Magic ring", "Increase", "+ head"…), the round chip for the first
piece, the speed chip and the stitch ticks of the music, so picture and sound always agree.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

DEFAULT_TIMING = {"hook": 2.0, "grow": 15.0, "done": 3.0, "real": 4.0, "cta": 6.0, "beat": 0.5}
YARN_DONE_AT = 0.94          # the crochetsim clock finishes the yarn at this share of the knit `dur`
MIN_CAPTION_GAP = 0.4        # s; a caption that would show for less than this is dropped


@dataclass
class Timing:
    hook: float
    grow: float
    done: float
    real: float
    cta: float
    beat: float = 0.5

    @property
    def t_grow(self) -> float:
        return self.hook

    @property
    def t_done(self) -> float:
        return self.hook + self.grow

    @property
    def breath(self) -> float:          # a held breath before "Done!": no new text, the music drops out
        return self.t_done - self.beat / 2

    @property
    def t_real(self) -> float:
        return self.t_done + self.done

    @property
    def t_cta(self) -> float:
        return self.t_real + self.real

    @property
    def t_end(self) -> float:
        return self.t_cta + self.cta

    def knit_args(self) -> dict:
        """dur / reveal for the knit renderer so the yarn completes exactly at t_done."""
        return {"dur": round(self.grow / YARN_DONE_AT, 3), "reveal": round(self.done + 0.5, 3)}


def timing(sb: dict, channel: dict | None) -> Timing:
    t = {**DEFAULT_TIMING, **((channel or {}).get("build", {}).get("timing", {})), **sb.get("timing", {})}
    return Timing(**{k: float(t[k]) for k in DEFAULT_TIMING})


def resolve(sb: dict, channel: dict | None) -> dict:
    """Storyboard with the channel defaults filled in (cta, done, real, thumbnail)."""
    b = (channel or {}).get("build", {})
    out = json.loads(json.dumps(sb))
    out.setdefault("cta", {})
    for k, v in b.get("cta", {}).items():
        out["cta"].setdefault(k, v)
    out.setdefault("done", {}).setdefault("title", "Done!")
    out["done"].setdefault("sub", "{pieces} pieces. {stitches} stitches.")
    out.setdefault("real", {}).setdefault("lines", ["And in", "real life"])
    if "chip" not in out["real"]:
        out["real"]["chip"] = stats_line(sb.get("toy", {}).get("stats", {}))
    th = out.setdefault("thumbnail", {})
    th.setdefault("lines", [l["text"] for l in sb["hook"]["lines"] if l.get("accent")] or [sb["toy"]["title"]])
    th.setdefault("pill", "Free crochet pattern")
    out.setdefault("effects", {}).setdefault("snow", False)
    out.setdefault("music", {})
    for k, v in b.get("music", {}).items():
        out["music"].setdefault(k, v)
    return out


def stats_line(st: dict) -> str:
    bits = []
    if st.get("size_cm"):
        bits.append(f"{st['size_cm']:g} cm")
    if st.get("hours"):
        bits.append(f"{st['hours']:g} hours")
    if st.get("yarn_m"):
        bits.append(f"{st['yarn_m']:g} m of {st.get('yarn_weight', '')} yarn".replace("  ", " "))
    return "  ·  ".join(bits)


# ---------------------------------------------------------------- the pattern in words
def round_text(counts: list[int], k: int) -> str:
    """The written instruction of round k (0-based) of a piece worked in rounds."""
    c = counts[k]
    if k == 0:
        return f"{c} sc in a magic ring"
    p = counts[k - 1]
    if c == p:
        return "sc around"
    if c > p:
        n = c - p
        if c == 2 * p:
            return "inc in every st"
        if p % n == 0:
            return f"({p // n - 1} sc, inc) x {n}"
        return f"{n} inc evenly ({c})"
    n = p - c
    if p == 2 * c:
        return "dec all around"
    if p % n == 0 and p // n >= 2:
        return f"({p // n - 2} sc, dec) x {n}"
    return f"{n} dec evenly ({c})"


def total_stitches(pieces: list[dict]) -> int:
    return sum(sum(p["counts"]) for p in pieces)


def _plural(part: str, n: int) -> str:
    word = part.replace("_", " ")
    return word + ("s" if n > 1 and not word.endswith("s") else "")


def captions(knit: dict, sb: dict, tm: Timing) -> list[tuple[float, str]]:
    """[(film second, text)]: the moments of the build, in order, never closer than MIN_CAPTION_GAP."""
    plan, pieces = knit["plan"], knit["pieces"]
    labels = sb.get("captions", {}).get("part_labels", {})
    skip = set(sb.get("captions", {}).get("skip", []))
    c0 = pieces[0]["counts"]
    caps: list[tuple[float, str]] = [(0.0, "Magic ring")]
    if len(c0) > 1 and c0[1] > c0[0]:
        caps.append((min(0.9, max(0.5, tm.grow * 0.06)), "Increase"))

    def first(pred):
        return next((f["t"] for f in plan if pred(f)), None)

    r = lambda f: f["round"]
    t = first(lambda f: f["pi"] == 0 and r(f) > 1 and c0[r(f) - 1] == c0[r(f) - 2])
    if t is not None:
        caps.append((t, "Straight up"))
    t = first(lambda f: f["pi"] == 0 and r(f) > 1 and c0[r(f) - 1] < c0[r(f) - 2])
    if t is not None:
        caps.append((t, "Decrease"))
    count = {}
    for p in pieces:
        count[p["part"]] = count.get(p["part"], 0) + 1
    seen = {pieces[0]["part"]}
    parts = []
    for f in plan:
        if f["piece"] not in seen:
            seen.add(f["piece"])
            parts.append((f["t"], labels.get(f["piece"], "+ " + _plural(f["piece"], count.get(f["piece"], 1)))))
    for t, s in parts:                      # parts that start together share one caption: "+ ears & horns"
        if caps and t - caps[-1][0] < 0.6 and caps[-1][1].startswith("+ ") and len(caps[-1][1]) + len(s) < 26:
            caps[-1] = (caps[-1][0], caps[-1][1] + " & " + s[2:])
        else:
            caps.append((t, s))
    t = first(lambda f: f.get("face", 0) > 0)
    if t is not None:
        caps.append((t, "Face time"))
    caps += [(float(a), str(b)) for a, b in sb.get("captions", {}).get("extra", [])]
    caps = sorted((tm.t_grow + t, s) for t, s in caps if s not in skip)
    caps = [c for c in caps if c[0] < tm.breath - 0.3]
    out = []
    for c in caps:
        if out and c[0] - out[-1][0] < MIN_CAPTION_GAP:
            if len(out) > 1:             # the later moment wins, but the opening caption always stays
                out[-1] = c
        else:
            out.append(c)
    return [(round(a, 3), b) for a, b in out]


def speed(knit: dict, k: int, fps: int, total: int) -> int:
    """How many times faster than real crochet (3 s a stitch) frame k runs, rounded the way a chip shows it."""
    plan = knit["plan"]
    a, b = plan[max(0, k - 3)], plan[min(len(plan) - 1, k + 3)]
    frames = max(1, min(len(plan) - 1, k + 3) - max(0, k - 3))
    rate = (b["s"] - a["s"]) / frames * fps * total          # stitches per second
    x = rate * 3.0
    return max(10, int(round(x / 10.0)) * 10) if x >= 10 else max(2, int(round(x)))


def events(knit: dict, sb: dict, tm: Timing, fps: int = 30) -> dict:
    """Everything the music needs: section times, caption hits and a tick per stitch (locked to the grid when fast)."""
    plan = knit["plan"]
    total = total_stitches(knit["pieces"])
    ticks, last = [], tm.t_grow
    for k in range(1, len(plan)):
        f = plan[k]
        t = tm.t_grow + f["t"]
        if t >= tm.breath:
            break
        rate = (f["s"] - plan[k - 1]["s"]) * fps * total
        if rate < 6:                                   # slow: a tick per stitch at its own time
            gap = 1.0 / max(rate, 1e-3)
            while last + gap <= t:
                last = max(last + gap, tm.t_grow + 0.05)
                ticks.append([round(last, 4), round(f["s"], 3), 0])
        else:                                          # fast: the stitches lock onto the 8th / 16th grid
            q = tm.beat / 4 if t < tm.t_grow + tm.grow * 0.66 else tm.beat / 8
            g = math.ceil((last + 1e-6) / q) * q
            while g <= t:
                ticks.append([round(g, 4), round(f["s"], 3), 1])
                last = g
                g += q
    return dict(T_GROW=tm.t_grow, T_DONE=tm.t_done, BREATH=tm.breath, T_REAL=tm.t_real, T_CTA=tm.t_cta,
                T_END=tm.t_end, BEAT=tm.beat, caps=[list(c) for c in captions(knit, sb, tm)], ticks=ticks,
                button=tm.t_cta + 2 * tm.beat, hook_words=[i * tm.beat for i in range(len(sb["hook"]["lines"]))])


# ---------------------------------------------------------------- checks used by `vengine validate`
def check(sb: dict, ep=None, knit: dict | None = None) -> list[dict]:
    P = []
    err = lambda m: P.append({"level": "error", "file": "storyboard", "msg": m})
    warn = lambda m: P.append({"level": "warn", "file": "storyboard", "msg": m})
    if ep is not None:
        spec = Path(sb.get("toy", {}).get("spec", ""))
        if not spec.is_absolute():
            spec = ep.folder / spec
        if not spec.exists():
            err(f"toy spec {sb.get('toy', {}).get('spec')} not found")
        for k in ("hook", "real", "cta"):
            p = sb.get("photos", {}).get(k)
            if p and not (ep.folder / p).exists() and not Path(p).exists():
                err(f"photos.{k}: {p} not found")
        if not sb.get("photos", {}).get("hook"):
            warn("no hook photo: the hook falls back to the finished knit; a studio photo of the toy stops the thumb better")
    tm = timing(sb, ep.channel if ep is not None else None)
    if tm.hook > 3:
        warn(f"hook is {tm.hook:g} s: the knit should start by 3 s")
    if tm.t_end > 59:
        err(f"short is {tm.t_end:g} s: Shorts must stay under 60 s")
    if knit is not None:
        need = (tm.grow + tm.done)
        have = knit["plan"][-1]["t"]
        if have + 1e-6 < need - 1.0 / knit.get("fps", 30):
            err(f"knit plan covers {have:.2f} s, the storyboard needs {need:.2f} s (re-run `vengine build knit`)")
    return P
