"""Video formats: one channel, several kinds of video.

A channel profile may declare `formats` ({id: format}). An episode picks one at
`init --format <id>` (stored in state.json) and the topic card repeats it. The
format then:

- overrides parts of the channel profile (`variety`, `script`, `aspect`), so a
  45 s promo is not checked against the limits of a 10 min breakdown;
- adds rules the contracts check:
    required_beats     script line `beat`s that must be present
    max_recap_share    share of narration words in `recap` lines
    claims_required    evidence/theory lines must say canon/inference/speculation/community
    release_gate       topic must name an officially released chapter; panels only up to it

Everything is data in channel.json; the engine knows no channel or format by name.
"""
from __future__ import annotations

import copy

MERGED_KEYS = ("variety", "script")
REPLACED_KEYS = ("aspect",)

# Script beats that make a claim and so need a `claim` tag when the format asks.
CLAIM_BEATS = {"evidence", "motive", "author_intent", "setup_payoff", "theory", "counter", "prediction"}


def names(channel: dict) -> list[str]:
    return sorted((channel or {}).get("formats", {}))


def get(channel: dict, fmt: str) -> dict:
    fm = (channel or {}).get("formats", {})
    if fmt not in fm:
        known = ", ".join(sorted(fm)) or "none"
        raise KeyError(f"channel '{channel.get('id')}' has no format '{fmt}' (known: {known})")
    return fm[fmt]


def effective(channel: dict | None, fmt: str | None) -> dict | None:
    """Channel profile as seen by one format: overrides merged, rules under `format`."""
    if channel is None or not fmt:
        return channel
    f = get(channel, fmt)
    out = copy.deepcopy(channel)
    for k in MERGED_KEYS:
        if k in f:
            base = dict(out.get(k) or {})
            for key, val in f[k].items():
                # groups merge by name so a format can tighten one group and keep the rest
                if key == "groups" and isinstance(val, dict):
                    g = dict(base.get("groups") or {})
                    for name, rule in val.items():
                        g[name] = {**g.get(name, {}), **rule}
                    base["groups"] = g
                else:
                    base[key] = val
            out[k] = base
    for k in REPLACED_KEYS:
        if k in f:
            out[k] = f[k]
    out["format"] = {"id": fmt, **f}
    return out
