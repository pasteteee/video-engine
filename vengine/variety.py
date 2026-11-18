"""Variety rules for a shot list: the fix for 'every video looks the same'.

Defaults come from the channel profile (`variety`), these are fallbacks.

`variety.groups` caps or floors a set of scene types, e.g. third-party manga
panels (at most a third of the runtime, 3-5 s each, never two in a row, always
with our commentary on screen) or the channel's own site screens in a promo:

    "groups": {"manga_panels": {"scene_types": ["panel_callout", "panel_setup_payoff"],
               "max_share": 0.33, "shot_min_s": 3, "shot_max_s": 5,
               "max_consecutive": 1, "needs_on_screen_text": true}}

Group rules are errors, not warnings: they usually protect against a strike.
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
    "custom_min": 2,              # scenes built for this episode's subject
    "unredact_max": 3,            # the channel signature, used sparingly
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
        reg = scenes.register_of(s)
        if reg:
            by_reg[reg] += s["duration_s"]
    share = {r: round(v / total, 3) for r, v in by_reg.items()}
    stats.update(total_s=round(total, 1), shots=len(shots), share=share)

    def add(level, msg):
        probs.append({"level": level, "msg": msg})

    if share[scenes.ARCHIVAL] < cfg["archival_min_share"]:
        add("error", f"real material is {share[scenes.ARCHIVAL]:.0%} of screen time, need at least "
                     f"{cfg['archival_min_share']:.0%}: find more photos, film, documents")

    # same type twice in a row (two different custom scenes may follow each other)
    for a, b in zip(shots, shots[1:]):
        if a["scene_type"] == b["scene_type"] and not (
                a["scene_type"] == "custom"
                and (a.get("custom") or {}).get("component") != (b.get("custom") or {}).get("component")):
            add("error", f"{a['id']} and {b['id']} are both {a['scene_type']}: break the repeat")

    distinct = {s["scene_type"] for s in shots}
    need = min(cfg["min_distinct_types"], max(3, len(shots) // 3))
    stats["distinct_types"] = len(distinct)
    if len(distinct) < need:
        add("error", f"only {len(distinct)} scene types, need at least {need}")

    # variants: a library scene must name one the kit has; the same type must not
    # come back in the same variant (the eye notices the second identical globe)
    seen: dict[str, str] = {}
    for s in shots:
        t, v = s["scene_type"], s.get("variant")
        st = scenes.LIBRARY.get(t)
        if t == "custom":
            c = s.get("custom") or {}
            if not c.get("component") or not c.get("brief"):
                add("error", f"{s['id']} is custom but has no custom.component / custom.brief")
            continue
        if not st or not st.variants:
            continue
        if v is None:
            add("warn", f"{s['id']} ({t}) has no variant: the kit falls back to {st.variants[0]}")
            v = st.variants[0]
        elif v not in st.variants:
            add("error", f"{s['id']}: {t} has no variant '{v}' (kit has: {', '.join(st.variants)})")
        if seen.get(t) == v and len(st.variants) > 1:
            add("warn", f"{s['id']}: {t} again in variant '{v}': pick another one")
        seen[t] = v

    customs = {(s.get("custom") or {}).get("component") for s in shots if s["scene_type"] == "custom"}
    customs.discard(None)
    stats["custom_scenes"] = len(customs)
    need_c = cfg["custom_min"] if total >= 90 else min(1, cfg["custom_min"])
    if len(customs) < need_c:
        add("error", f"{len(customs)} scenes made for this episode, need at least {need_c}: "
                     "invent a scene from the subject itself (its instrument, object, mechanism)")

    unredacts = sum(1 for s in shots if s.get("variant") == "unredact")
    if unredacts > cfg["unredact_max"]:
        add("warn", f"unredact used {unredacts} times, keep the signature to {cfg['unredact_max']}")

    # register runs
    run_reg, run_len, run_start = None, 0.0, None
    for s in shots:
        reg = scenes.register_of(s)
        if reg == run_reg:
            run_len += s["duration_s"]
        else:
            run_reg, run_len, run_start = reg, s["duration_s"], s["id"]
        if run_len > cfg["max_register_run_s"]:
            add("warn", f"{run_reg} runs {run_len:.0f}s from {run_start}: switch register")
            run_len = -1e9  # report a run once

    for name, rule in (cfg.get("groups") or {}).items():
        probs += _group(name, rule, shots, total, stats)

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


def _group(name: str, rule: dict, shots: list[dict], total: float, stats: dict) -> list[dict]:
    types = set(rule.get("scene_types", []))
    out = []

    def err(msg):
        out.append({"level": "error", "msg": f"{name}: {msg}"})

    members = [s for s in shots if s["scene_type"] in types]
    share = sum(s["duration_s"] for s in members) / total if total else 0.0
    stats.setdefault("groups", {})[name] = {"shots": len(members), "share": round(share, 3)}
    if "max_share" in rule and share > rule["max_share"]:
        err(f"{share:.0%} of screen time, at most {rule['max_share']:.0%}: replace some with own graphics")
    if "min_share" in rule and share < rule["min_share"]:
        err(f"{share:.0%} of screen time, need at least {rule['min_share']:.0%}")
    for s in members:
        d = s["duration_s"]
        if "shot_min_s" in rule and d < rule["shot_min_s"]:
            err(f"{s['id']} holds {d}s, at least {rule['shot_min_s']}s so the comment can be read")
        if "shot_max_s" in rule and d > rule["shot_max_s"]:
            err(f"{s['id']} holds {d}s, at most {rule['shot_max_s']}s")
        if rule.get("needs_on_screen_text") and not s.get("on_screen_text"):
            err(f"{s['id']} has no on_screen_text: every frame of this kind carries our commentary")
    limit = rule.get("max_consecutive")
    if limit:
        run = 0
        for s in shots:
            run = run + 1 if s["scene_type"] in types else 0
            if run == limit + 1:
                err(f"{s['id']} makes {run} in a row, at most {limit}: put own graphics between them")
    return out
