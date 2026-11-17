"""Variety rules for a shot list: the fix for 'every video looks the same'.

Defaults come from the channel profile (`variety`), these are fallbacks.
"""
from __future__ import annotations

from statistics import pstdev

from . import scenes

DEFAULTS = {
    "archival_min_share": 0.40,   # real photos/film/documents share of screen time
    "min_distinct_types": 10,     # for a full episode; scaled down for short pieces
    "max_register_run_s": 30.0,   # change archival/blueprint/illustration at least this often
    "shot_min_s": 1.5,
    "shot_max_s": 7.0,
    "max_static_s": 4.0,          # a static-risk shot longer than this needs motion
}


def check(shotlist: dict, channel: dict | None = None) -> dict:
    cfg = {**DEFAULTS, **((channel or {}).get("variety") or {})}
    shots = shotlist.get("shots", [])
    probs, stats = [], {}
    if not shots:
        return {"ok": False, "problems": [{"level": "error", "msg": "empty shot list"}], "stats": {}}

    total = sum(s["duration_s"] for s in shots)
    by_reg = {r: 0.0 for r in scenes.REGISTERS}
    for s in shots:
        st = scenes.LIBRARY.get(s["scene_type"])
        if st:
            by_reg[st.register] += s["duration_s"]
    share = {r: round(v / total, 3) for r, v in by_reg.items()}
    stats.update(total_s=round(total, 1), shots=len(shots), share=share)

    def add(level, msg):
        probs.append({"level": level, "msg": msg})

    if share[scenes.ARCHIVAL] < cfg["archival_min_share"]:
        add("error", f"real material is {share[scenes.ARCHIVAL]:.0%} of screen time, need at least "
                     f"{cfg['archival_min_share']:.0%}: find more photos, film, documents")

    # same type twice in a row
    for a, b in zip(shots, shots[1:]):
        if a["scene_type"] == b["scene_type"]:
            add("error", f"{a['id']} and {b['id']} are both {a['scene_type']}: break the repeat")

    distinct = {s["scene_type"] for s in shots}
    need = min(cfg["min_distinct_types"], max(3, len(shots) // 3))
    stats["distinct_types"] = len(distinct)
    if len(distinct) < need:
        add("error", f"only {len(distinct)} scene types, need at least {need}")

    # register runs
    run_reg, run_len, run_start = None, 0.0, None
    for s in shots:
        st = scenes.LIBRARY.get(s["scene_type"])
        reg = st.register if st else None
        if reg == run_reg:
            run_len += s["duration_s"]
        else:
            run_reg, run_len, run_start = reg, s["duration_s"], s["id"]
        if run_len > cfg["max_register_run_s"]:
            add("warn", f"{run_reg} runs {run_len:.0f}s from {run_start}: switch register")
            run_len = -1e9  # report a run once

    # shot lengths
    durs = [s["duration_s"] for s in shots]
    for s in shots:
        d = s["duration_s"]
        if d < cfg["shot_min_s"]:
            add("warn", f"{s['id']} is {d}s, shorter than {cfg['shot_min_s']}s")
        if d > cfg["shot_max_s"]:
            add("warn", f"{s['id']} is {d}s, longer than {cfg['shot_max_s']}s: split it or add a beat")
        st = scenes.LIBRARY.get(s["scene_type"])
        if st and st.static_risk and d > cfg["max_static_s"] and not s.get("motion"):
            add("error", f"{s['id']} ({s['scene_type']}) holds {d}s without motion")
    spread = pstdev(durs) if len(durs) > 1 else 0.0
    stats["duration_spread_s"] = round(spread, 2)
    if len(durs) >= 8 and spread < 0.8:
        add("warn", f"shot lengths barely vary (spread {spread:.1f}s): mix quick cuts and long holds")

    return {"ok": not any(p["level"] == "error" for p in probs), "problems": probs, "stats": stats}
