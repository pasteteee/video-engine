"""LoreSquare data for the theories channel, through the site's public MCP endpoint.

The endpoint is stateless JSON-RPC over HTTP (POST one message, get JSON back),
read-only and without auth, so a plain urllib call is enough. Agents that have
the LoreSquare connector may call the same tools directly; this module is for
scripts and for runs on the owner's PC.

    python -m vengine lore call mystery_board --args '{"sort": "hot", "limit": 8}'
    python -m vengine lore top --channel loresquare --n 5 --out ep/02_research/raw/top.json

`top` ranks theories for the "top theories" format: it walks the hottest open
questions, takes their competing theories, opens the best ones and scores them
by confidence, how far confidence moved, argument votes and chapter-cited
evidence. The ranking is a proposal; the owner still picks at the topic gate.
"""
from __future__ import annotations

import json
import math
import re
import urllib.parse
import urllib.request
from typing import Callable

DEFAULT_URL = "https://loresquare.com/api/mcp"
UTM = {"utm_source": "youtube", "utm_medium": "video"}

Transport = Callable[[str, dict], dict]


def http_transport(url: str, payload: dict, timeout: float = 30) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json",
                 "User-Agent": "video-engine/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def url_of(channel: dict | None) -> str:
    return (((channel or {}).get("data_sources") or {}).get("loresquare") or {}).get("mcp_url", DEFAULT_URL)


def call(tool: str, args: dict | None = None, url: str = DEFAULT_URL, transport: Transport | None = None) -> dict:
    """Call one tool; returns its structuredContent (or the parsed text content)."""
    msg = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool, "arguments": args or {}}}
    res = (transport or http_transport)(url, msg)
    if "error" in res:
        raise RuntimeError(f"{tool}: {res['error'].get('message', res['error'])}")
    out = res.get("result") or {}
    if out.get("isError"):
        text = " ".join(c.get("text", "") for c in out.get("content", []))
        raise RuntimeError(f"{tool}: {text or 'tool error'}")
    if "structuredContent" in out:
        return out["structuredContent"]
    for c in out.get("content", []):
        if c.get("type") == "text":
            try:
                return json.loads(c["text"])
            except json.JSONDecodeError:
                return {"text": c["text"]}
    return out


_CH = re.compile(r"Ch\.?\s*(\d+)", re.I)


def chapters_in(text: str) -> list[int]:
    return sorted({int(x) for x in _CH.findall(text or "")})


def score(theory_view: dict) -> dict:
    """Score one get_theory view. Higher = better material for a video segment."""
    t = theory_view["theory"]
    conf = t.get("confidence") or 0
    hist = [h for h in theory_view.get("history", []) if h is not None]
    was = hist[0] if hist else conf
    moved = conf - was
    args = theory_view.get("arguments", [])
    cited = [a for a in args if chapters_in(a.get("source", ""))]
    votes = sum(a.get("votes", 0) for a in args)
    against = [a for a in args if a.get("stance") == "against"]
    points = (conf * 0.5 + abs(moved) * 0.8 + min(len(cited), 4) * 6
              + math.log1p(votes) * 4 + math.log1p(t.get("votes", 0)) * 3
              + (8 if against else -10))  # no counterpoint = no honest segment
    why = [f"confidence {conf:g}%"]
    if moved:
        why.append(f"moved {moved:+g} from {was:g}")
    why.append(f"{len(cited)} chapter-cited arguments")
    if not against:
        why.append("no argument against yet")
    return {"score": round(points, 1), "confidence": conf, "was": was, "moved": moved, "why": why}


def top_theories(n: int = 5, lore: str | None = None, url: str = DEFAULT_URL,
                 transport: Transport | None = None, per_mystery: int = 2, board_size: int = 12) -> list[dict]:
    """Best theories for a countdown, at most one per question unless the board is thin."""
    base = {"lore": lore} if lore else {}
    board = call("mystery_board", {**base, "sort": "hot", "open_only": True, "limit": board_size}, url, transport)
    picked: list[dict] = []
    for item in board.get("items", []):
        myst = call("get_mystery", {**base, "ref": item["ref"]}, url, transport)
        ranked = sorted(myst.get("theories", []), key=lambda t: -(t.get("confidence") or 0))[:per_mystery]
        for th in ranked:
            view = call("get_theory", {**base, "ref": th["ref"]}, url, transport)
            s = score(view)
            t = view["theory"]
            picked.append({
                "ref": t["ref"], "title": t["title"], "author": t.get("author"), "url": t.get("url"),
                "summary": t.get("summary"), "mystery": myst["mystery"]["question"],
                "mystery_ref": myst["mystery"]["ref"], "image_url": t.get("imageUrl"),
                "arguments": [{"stance": a["stance"], "text": a["text"], "source": a.get("source", ""),
                               "chapters": chapters_in(a.get("source", "")), "votes": a.get("votes", 0)}
                              for a in view.get("arguments", [])],
                "chapters": sorted({c for a in view.get("arguments", []) for c in chapters_in(a.get("source", ""))}),
                **s,
            })
    picked.sort(key=lambda x: -x["score"])
    out, seen = [], set()
    for p in picked:  # one theory per question first
        if p["mystery_ref"] not in seen:
            out.append(p)
            seen.add(p["mystery_ref"])
    for p in picked:
        if len(out) >= n:
            break
        if p not in out:
            out.append(p)
    return out[:n]


def with_utm(url: str, campaign: str, medium: str = "video") -> str:
    """Site link for a description or end card; replaces the connector's own utm tags."""
    parts = urllib.parse.urlsplit(url)
    q = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query) if not k.startswith("utm_")]
    q += list({**UTM, "utm_medium": medium, "utm_campaign": campaign}.items())
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(q)))
