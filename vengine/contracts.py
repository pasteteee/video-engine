"""Schema validation of every handoff file plus cross-file reference checks.

Problems come back as a list of dicts: {"level": "error"|"warn", "file", "msg"}.
An agent may hand over only when there are no errors for its files.
"""
from __future__ import annotations

import datetime as dt
import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

from . import formats, scenes
from .episode import EXTRA, STAGES, Episode

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"


@lru_cache(maxsize=None)
def validator(name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def validate_obj(name: str, obj: dict, file: str = "") -> list[dict]:
    out = []
    for e in sorted(validator(name).iter_errors(obj), key=lambda e: list(e.absolute_path)):
        where = "/".join(str(p) for p in e.absolute_path) or "(root)"
        out.append({"level": "error", "file": file or name, "msg": f"{where}: {e.message}"})
    return out


def _load(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8")), None
    except json.JSONDecodeError as e:
        return None, f"invalid JSON: {e}"


def validate_episode(ep: Episode, channel: dict | None = None) -> list[dict]:
    fmt = ep.state.get("format")
    if channel is not None and fmt and "format" not in channel:
        channel = formats.effective(channel, fmt)
    probs: list[dict] = []
    docs: dict[str, dict] = {}
    files = [(s.output, s.schema) for s in STAGES if s.schema] + list(EXTRA.items())
    for rel, schema in files:
        p = ep.path(rel)
        if not p.exists():
            continue
        obj, err = _load(p)
        if err:
            probs.append({"level": "error", "file": rel, "msg": err})
            continue
        docs[schema] = obj
        probs += validate_obj(schema, obj, rel)
    probs += cross_check(docs, ep, channel)
    probs += format_check(docs, ep, channel)
    return probs


def cross_check(docs: dict[str, dict], ep: Episode | None = None, channel: dict | None = None) -> list[dict]:
    P = []

    def err(file, msg):
        P.append({"level": "error", "file": file, "msg": msg})

    def warn(file, msg):
        P.append({"level": "warn", "file": file, "msg": msg})

    f, media, script, shots = (docs.get(k) for k in ("findings", "media", "script", "shotlist"))
    facts = {x["id"]: x for x in (f or {}).get("facts", [])}
    media_ids = {m["id"] for m in (media or {}).get("items", [])}

    if f:
        src = {s["id"] for s in f.get("sources", [])}
        calcs = {c["id"] for c in f.get("calculations", [])}
        for x in f.get("facts", []):
            for sid in x.get("source_ids", []):
                if sid not in src:
                    err("findings", f"fact {x['id']} cites unknown source {sid}")
        for c in f.get("conclusions", []):
            for b in c.get("based_on", []):
                if b not in facts and b not in calcs:
                    err("findings", f"conclusion {c['id']} is based on unknown {b}")
        if not any(s.get("kind") in ("primary", "data") for s in f.get("sources", [])):
            warn("findings", "no primary or data source: the episode would only retell others")
        if not f.get("calculations"):
            warn("findings", "no own calculation: add at least one 'our measurement'")

    if media and ep:
        for m in media.get("items", []):
            if not (ep.folder / "02_research" / m["path"]).exists() and not (ep.folder / m["path"]).exists():
                warn("media", f"{m['id']}: file {m['path']} not found")

    if script:
        ids = [l["id"] for l in script.get("lines", [])]
        if len(ids) != len(set(ids)):
            err("script", "duplicate line ids")
        loops = {l["id"] for l in script["lines"] if l.get("hook") == "open_loop"}
        closed = {l.get("closes_loop") for l in script["lines"] if l.get("closes_loop")}
        for lid in sorted(loops - closed):
            warn("script", f"open loop {lid} is never paid off")
        for l in script["lines"]:
            for fid in l.get("fact_ids", []):
                if f is not None and fid not in facts:
                    err("script", f"line {l['id']} uses unknown fact {fid}")
                elif fid in facts and facts[fid]["status"] in ("disputed", "rejected"):
                    err("script", f"line {l['id']} states fact {fid} which is {facts[fid]['status']}")
                elif fid in facts and facts[fid]["status"] == "likely":
                    warn("script", f"line {l['id']} uses 'likely' fact {fid}: wording must hedge")
            for mid in l.get("media_ids", []):
                if media is not None and mid not in media_ids:
                    err("script", f"line {l['id']} wants unknown media {mid}")
        if not script["lines"] or script["lines"][0].get("hook") != "cold_open":
            warn("script", "first line is not marked as cold_open")

    if shots:
        allowed = scenes.allowed_for(channel or {})
        line_ids = {l["id"] for l in (script or {}).get("lines", [])}
        covered = set()
        for s in shots.get("shots", []):
            st = s["scene_type"]
            if st not in scenes.LIBRARY:
                err("shotlist", f"shot {s['id']}: unknown scene type {st}")
            elif st not in allowed:
                err("shotlist", f"shot {s['id']}: scene type {st} not allowed for this channel")
            elif scenes.LIBRARY[st].needs_media and not s.get("media_ids"):
                err("shotlist", f"shot {s['id']}: {st} needs media_ids")
            elif scenes.LIBRARY[st].static_risk and not s.get("motion"):
                warn("shotlist", f"shot {s['id']}: {st} tends to look frozen, describe its motion")
            for mid in s.get("media_ids", []):
                if media is not None and mid not in media_ids:
                    err("shotlist", f"shot {s['id']}: unknown media {mid}")
            for lid in s.get("line_ids", []):
                if script is not None and lid not in line_ids:
                    err("shotlist", f"shot {s['id']}: unknown line {lid}")
                covered.add(lid)
            if st in scenes.LIBRARY and scenes.LIBRARY[st].register != scenes.BLUEPRINT and not s.get("source_line"):
                err("shotlist", f"shot {s['id']}: archival or illustration shot without source_line")
        for lid in sorted(line_ids - covered):
            err("shotlist", f"line {lid} has no shot")
    return P


def format_check(docs: dict[str, dict], ep: Episode | None = None, channel: dict | None = None,
                 today: dt.date | None = None) -> list[dict]:
    """Rules of the episode's format (see vengine/formats.py) and of the commented work."""
    P = []
    fmt = (channel or {}).get("format")
    if not fmt:
        return P

    def err(file, msg):
        P.append({"level": "error", "file": file, "msg": msg})

    def warn(file, msg):
        P.append({"level": "warn", "file": file, "msg": msg})

    topic, media, script = docs.get("topic_card"), docs.get("media"), docs.get("script")

    if topic and topic.get("format") and topic["format"] != fmt["id"]:
        err("topic_card", f"format {topic['format']} but the episode was started as {fmt['id']}")

    # official release: never before the chapter is out on the official source
    released = None
    if fmt.get("release_gate") and topic:
        rel = topic.get("release")
        if not rel:
            err("topic_card", "release missing: this format needs the chapter and its official release date")
        else:
            released = rel["chapter"]
            day = dt.date.fromisoformat(rel["official_at"][:10])
            if day > (today or dt.date.today()):
                err("topic_card", f"chapter {released} is not officially out until {day}: no leaks, wait for the release")
    if media and released is not None:
        for m in media.get("items", []):
            if m.get("kind") == "panel" and m.get("chapter", 0) > released:
                err("media", f"{m['id']}: panel from chapter {m['chapter']}, newer than the released {released}")
    credit = ((channel or {}).get("source_work") or {}).get("credit_line")
    if media and credit:
        for m in media.get("items", []):
            if m.get("kind") == "panel" and credit.split()[0].lower() not in (m.get("credit") or "").lower():
                warn("media", f"{m['id']}: credit should read like '{credit}'")

    if script:
        lines = script.get("lines", [])
        beats = {l.get("beat") for l in lines}
        for b in fmt.get("required_beats", []):
            if b not in beats:
                err("script", f"format {fmt['id']} needs a '{b}' line")
        words = [len(l["text"].split()) for l in lines]
        total = sum(words) or 1
        cap = fmt.get("max_recap_share")
        if cap is not None:
            recap = sum(w for l, w in zip(lines, words) if l.get("beat") == "recap") / total
            if recap > cap:
                err("script", f"recap is {recap:.0%} of the narration, at most {cap:.0%}: the video must be our argument")
        if fmt.get("claims_required"):
            for l in lines:
                if l.get("beat") in formats.CLAIM_BEATS and not l.get("claim"):
                    err("script", f"line {l['id']} ({l['beat']}) has no claim tag: canon, inference, speculation or community")
                if l.get("claim") == "canon" and not l.get("chapter_refs"):
                    warn("script", f"line {l['id']} is canon but cites no chapter_refs")
        if released is not None:
            for l in lines:
                for c in l.get("chapter_refs", []):
                    if c > released:
                        err("script", f"line {l['id']} cites chapter {c}, newer than the released {released}")
    return P
