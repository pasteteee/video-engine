"""Command line: python -m vengine <command> ...

  init      CHANNEL SLUG [--root DIR]   create the episode folder
  status    EPISODE_DIR [--json]        where the episode is and who acts next
  validate  EPISODE_DIR                 schemas + cross-file references
  variety   SHOTLIST.json [--channel ID] variety rules of the edit plan
  ailint    SCRIPT.json | TEXT_FILE [--json] [--print-rules]
  approve   EPISODE_DIR GATE [--note ..] record the owner's approval (topic|script|final)
  revoke    EPISODE_DIR GATE
  channels                              list channel profiles
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import ailint, contracts, variety
from .episode import GATES, ROOT, Episode, load_channel


def _channel_of(ep: Episode) -> dict | None:
    cid = ep.state.get("channel")
    try:
        return load_channel(cid) if cid else None
    except FileNotFoundError:
        return None


def _print_problems(probs: list[dict]) -> int:
    for p in probs:
        mark = "✗" if p["level"] == "error" else "!"
        where = f"{p['file']}: " if p.get("file") else ""
        print(f"{mark} {where}{p['msg']}")
    errs = sum(p["level"] == "error" for p in probs)
    print(f"\n{errs} errors, {len(probs) - errs} warnings")
    return 1 if errs else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="vengine", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init"); p.add_argument("channel"); p.add_argument("slug"); p.add_argument("--root")
    p = sub.add_parser("status"); p.add_argument("episode"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("validate"); p.add_argument("episode")
    p = sub.add_parser("variety"); p.add_argument("shotlist"); p.add_argument("--channel")
    p = sub.add_parser("ailint"); p.add_argument("file", nargs="?"); p.add_argument("--json", action="store_true")
    p.add_argument("--print-rules", action="store_true")
    for name in ("approve", "revoke"):
        p = sub.add_parser(name); p.add_argument("episode"); p.add_argument("gate", choices=GATES)
        if name == "approve":
            p.add_argument("--note", default="")
    sub.add_parser("channels")

    a = ap.parse_args(argv)

    if a.cmd == "channels":
        for d in sorted((ROOT / "channels").glob("*/channel.json")):
            c = json.loads(d.read_text(encoding="utf-8"))
            print(f"{c['id']:<16} {c['name']} · {c['promise']}")
        return 0

    if a.cmd == "init":
        ch = load_channel(a.channel)
        root = Path(a.root or ch.get("episodes_root", "episodes/{slug}").replace("{slug}", a.slug))
        ep = Episode.init(root if a.root is None else root / a.slug, ch["id"], a.slug)
        print(f"episode folder: {ep.folder}")
        return 0

    if a.cmd == "status":
        st = Episode(Path(a.episode)).status()
        if a.json:
            print(json.dumps(st, ensure_ascii=False, indent=2))
            return 0
        for r in st["stages"]:
            gate = ""
            if r["gate"]:
                gate = f"  [owner: {r['gate']} {'✓' if r['approved'] else '…'}]"
            print(f"{'✓' if r['done'] else '·'} {r['stage']:<9} {r['agent']:<13}{gate}")
        if st["waiting_for_owner"]:
            print(f"\nwaiting for the owner to approve: {st['waiting_for_owner']}")
        elif st["next"]:
            print(f"\nnext: {st['next']}")
        else:
            print("\nepisode published")
        return 0

    if a.cmd == "validate":
        ep = Episode(Path(a.episode))
        return _print_problems(contracts.validate_episode(ep, _channel_of(ep)))

    if a.cmd == "variety":
        sl = json.loads(Path(a.shotlist).read_text(encoding="utf-8"))
        ch = load_channel(a.channel) if a.channel else None
        res = variety.check(sl, ch)
        print(json.dumps(res["stats"], ensure_ascii=False))
        return _print_problems(res["problems"])

    if a.cmd == "ailint":
        if a.print_rules:
            for r in ailint.RULES:
                print(f"{r.id:<18} {r.level:<5} {r.category}")
            return 0
        if not a.file:
            ap.error("ailint needs a file")
        raw = Path(a.file).read_text(encoding="utf-8")
        if a.file.endswith(".json"):
            lines = [{"id": l["id"], "text": l["text"]} for l in json.loads(raw)["lines"]]
        elif all("|" in x for x in raw.splitlines() if x.strip()):
            # "line_id|text" per line, the format of the older voice scripts
            lines = [{"id": x.split("|", 1)[0], "text": x.split("|", 1)[1]} for x in raw.splitlines() if x.strip()]
        else:
            lines = [{"id": f"p{i + 1}", "text": t} for i, t in enumerate(x for x in raw.split("\n\n") if x.strip())]
        rep = ailint.lint_lines(lines)
        print(json.dumps(rep, ensure_ascii=False, indent=2) if a.json else ailint.format_report(rep))
        return 0 if rep["ok"] else 1

    if a.cmd in ("approve", "revoke"):
        ep = Episode(Path(a.episode))
        ep.approve(a.gate, a.note) if a.cmd == "approve" else ep.revoke(a.gate)
        print(f"{a.gate}: {'approved' if a.cmd == 'approve' else 'revoked'}")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
