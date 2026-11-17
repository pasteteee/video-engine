"""Shorts: find the moments of an episode that work alone in 15–59 s, and check a shorts plan.

    python -m vengine shorts <episode> [--n 3] [--write]

Picks windows of consecutive narration lines and scores them for a cold viewer
scrolling a feed: does the first second stop the thumb, is there a payoff inside
the window, is it full of numbers and real records, does it make sense without
the rest of the episode. Writes candidates to `06_render/shorts/candidates.json`;
rs-shorts turns the best ones into `06_render/shorts/shorts.json` (schema `shorts`),
a vertical-native plan the kit renders at 1080x1920.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import scenes

MIN_S, MAX_S, TARGET_S = 18.0, 55.0, 35.0

HOOK_W = {"cold_open": 3.0, "question": 3.0, "twist": 3.0, "reveal": 2.5, "stakes": 2.5, "open_loop": 2.0, "payoff": 0.5}
END_W = {"payoff": 2.5, "reveal": 2.5, "twist": 2.0}
BAIT = re.compile(r"\b(first|never|only|wrong|nobody|no one|impossible|record|secret|lost|missing|died|survived|"
                  r"million|billion|thousand|hundred|minutes?|miles?|feet|km|days?|years?)\b", re.I)
NUM = re.compile(r"\d|\b(one|two|three|four|five|six|seven|eight|nine|ten|hundred|thousand)\b", re.I)
CONTEXT_START = re.compile(r"^(and|but|so|that|this|it|he|she|they|their|his|her|its|then|there|here|in the same|the same)\b", re.I)


def _line_times(words: dict) -> dict[str, tuple[float, float]]:
    return {l["id"]: (l["start"], l["end"]) for l in words["lines"]}


def candidates(script: dict, shotlist: dict, words: dict) -> list[dict]:
    lines = script["lines"]
    t = _line_times(words)
    shots = shotlist.get("shots", [])
    out = []
    for i in range(len(lines)):
        for j in range(i, len(lines)):
            a, b = lines[i], lines[j]
            if a["id"] not in t or b["id"] not in t:
                continue
            start, end = t[a["id"]][0], t[b["id"]][1]
            dur = end - start
            if dur > MAX_S:
                break
            if dur < MIN_S:
                continue
            win = lines[i:j + 1]
            ids = [l["id"] for l in win]
            why, score = [], 0.0
            # 1. the first second
            hw = HOOK_W.get(a.get("hook"), 0.0)
            if hw:
                score += hw; why.append(f"opens on a {a['hook']}")
            if NUM.search(a["text"].split(".")[0]):
                score += 1.0; why.append("number in the first sentence")
            if CONTEXT_START.match(a["text"]):
                score -= 2.5; why.append("first line needs context")
            # 2. payoff inside
            loops = {l["id"] for l in win if l.get("hook") == "open_loop"}
            closed = [l for l in win if l.get("closes_loop") in loops]
            if closed:
                score += 3.0; why.append("opens and closes its own loop")
            ew = END_W.get(b.get("hook"), 0.0)
            if ew:
                score += ew; why.append(f"ends on a {b['hook']}")
            elif len(b["text"].split()) <= 6:
                score += 0.8; why.append("ends on a short punch line")
            if b.get("hook") == "open_loop":
                score -= 2.0; why.append("ends on an open question")
            # 3. bait density
            text = " ".join(l["text"] for l in win)
            bait = len(BAIT.findall(text)) + len(NUM.findall(text)) * 0.5
            score += min(4.0, bait * 0.35)
            # 4. what is on screen
            sh = [s for s in shots if set(s.get("line_ids", [])) & set(ids)]
            customs = sum(1 for s in sh if s["scene_type"] == "custom")
            arch = sum(1 for s in sh if scenes.register_of(s) == scenes.ARCHIVAL)
            if customs:
                score += 1.5 * customs; why.append(f"{customs} custom scene(s)")
            score += 0.3 * arch
            # 5. length: near the target, chapters crossed
            score -= abs(dur - TARGET_S) / 12
            chapters = len({l.get("chapter") for l in win})
            if chapters > 2:
                score -= 1.5 * (chapters - 2)
            out.append({"line_ids": ids, "start_s": round(start, 2), "end_s": round(end, 2),
                        "duration_s": round(dur, 1), "score": round(score, 2), "why": why,
                        "shot_ids": [s["id"] for s in sh]})
    out.sort(key=lambda c: -c["score"])
    return out


def pick(cands: list[dict], n: int = 3, max_overlap: float = 0.3) -> list[dict]:
    """Best n windows that do not overlap much (a feed of three shorts from one episode)."""
    chosen: list[dict] = []
    for c in cands:
        ok = True
        for d in chosen:
            ov = max(0.0, min(c["end_s"], d["end_s"]) - max(c["start_s"], d["start_s"]))
            if ov > max_overlap * min(c["duration_s"], d["duration_s"]):
                ok = False
                break
        if ok:
            chosen.append(c)
        if len(chosen) == n:
            break
    for k, c in enumerate(chosen, 1):
        c["id"] = f"short{k}"
    return chosen


def for_episode(folder: Path, n: int = 3) -> dict:
    folder = Path(folder)
    script = json.loads((folder / "03_script/script.json").read_text(encoding="utf-8"))
    shotlist = json.loads((folder / "04_shots/shotlist.json").read_text(encoding="utf-8"))
    words = json.loads((folder / "05_voice/words.json").read_text(encoding="utf-8"))
    cands = candidates(script, shotlist, words)
    return {"picked": pick(cands, n), "top": cands[:12]}


# ---- plan check (rs-shorts output) --------------------------------------

LANDSCAPE_LAYOUTS = {"letterbox", "pillarbox", "landscape", "blur_fill", "center_crop_16x9"}


def check_plan(plan: dict) -> list[dict]:
    probs = []
    add = lambda lvl, msg: probs.append({"level": lvl, "msg": msg})
    if plan.get("width", 1080) != 1080 or plan.get("height", 1920) != 1920:
        add("error", "shorts render at 1080x1920")
    for s in plan.get("shorts", []):
        sid = s.get("id", "?")
        dur = s.get("end_s", 0) - s.get("start_s", 0)
        if not 15 <= dur <= 59:
            add("error", f"{sid} is {dur:.0f}s, keep 15–59 s")
        hook = s.get("hook_text", "")
        if not hook or len(hook.split()) > 6:
            add("error", f"{sid}: hook_text must be 1–6 words, on screen in the first second")
        for sh in s.get("shots", []):
            lay = sh.get("layout", "")
            if lay in LANDSCAPE_LAYOUTS or not lay.startswith("v_"):
                add("error", f"{sid}/{sh.get('id')}: layout '{lay}' is not vertical-native "
                             "(compose for 9:16: v_photo_pan, v_type, v_number, v_split, v_custom...)")
            if sh.get("duration_s", 0) > 4.5:
                add("warn", f"{sid}/{sh.get('id')}: {sh['duration_s']}s; shorts cut every 1.5–4 s")
        if not s.get("loop_end"):
            add("warn", f"{sid}: no loop_end: the last frame should lead back into the first")
    return probs
