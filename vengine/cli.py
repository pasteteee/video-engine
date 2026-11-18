"""Command line: python -m vengine <command> ...

  init      CHANNEL SLUG [--format F] [--root DIR]   create the episode folder
  status    EPISODE_DIR [--json]        where the episode is and who acts next
  validate  EPISODE_DIR                 schemas + cross-file references
  variety   SHOTLIST.json [--channel ID] variety rules of the edit plan
  ailint    SCRIPT.json | TEXT_FILE [--json] [--print-rules]
  approve   EPISODE_DIR GATE [--note ..] record the owner's approval (topic|script|final)
  revoke    EPISODE_DIR GATE
  channels                              list channel profiles (and their formats)
  formats   CHANNEL                     formats of a channel with their structure
  lore      call TOOL [--args JSON] | top [--n N]   LoreSquare data (theories channel)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import ailint, contracts, formats, variety
from .episode import GATES, ROOT, Episode, load_channel


def _channel_of(ep: Episode) -> dict | None:
    """Channel profile with the episode's format applied."""
    return ep.channel()


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
    p.add_argument("--format")
    p = sub.add_parser("status"); p.add_argument("episode"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("validate"); p.add_argument("episode")
    p = sub.add_parser("variety"); p.add_argument("shotlist"); p.add_argument("--channel"); p.add_argument("--format")
    p = sub.add_parser("look"); p.add_argument("episode"); p.add_argument("--write", action="store_true")
    p = sub.add_parser("shorts"); p.add_argument("episode"); p.add_argument("--n", type=int, default=3)
    p.add_argument("--write", action="store_true"); p.add_argument("--check", action="store_true")
    p = sub.add_parser("ailint"); p.add_argument("file", nargs="?"); p.add_argument("--json", action="store_true")
    p.add_argument("--print-rules", action="store_true")
    for name in ("approve", "revoke"):
        p = sub.add_parser(name); p.add_argument("episode"); p.add_argument("gate", choices=GATES)
        if name == "approve":
            p.add_argument("--note", default="")
    sub.add_parser("channels")
    p = sub.add_parser("formats"); p.add_argument("channel")
    p = sub.add_parser("lore"); p.add_argument("action", choices=["call", "top"]); p.add_argument("tool", nargs="?")
    p.add_argument("--args", default="{}"); p.add_argument("--channel"); p.add_argument("--lore")
    p.add_argument("--n", type=int, default=5); p.add_argument("--out")

    a = ap.parse_args(argv)

    if a.cmd == "channels":
        for d in sorted((ROOT / "channels").glob("*/channel.json")):
            c = json.loads(d.read_text(encoding="utf-8"))
            print(f"{c['id']:<16} {c['name']} · {c['promise']}")
            for f in formats.names(c):
                print(f"{'':<16}   --format {f}")
        return 0

    if a.cmd == "formats":
        ch = load_channel(a.channel)
        for fid in formats.names(ch):
            f = ch["formats"][fid]
            eff = formats.effective(ch, fid)
            mins = (eff.get("script") or {}).get("target_minutes")
            print(f"{fid}  ·  {f['name']}  ·  {eff.get('aspect', '16:9')}  ·  {mins} min")
            print(f"  {f['what']}")
            for i, step in enumerate(f.get("structure", []), 1):
                print(f"   {i}. {step}")
            print(f"  beats: {', '.join(f['required_beats'])}")
            print()
        return 0

    if a.cmd == "lore":
        from . import lore
        ch = load_channel(a.channel) if a.channel else None
        url = lore.url_of(ch)
        if a.action == "call":
            if not a.tool:
                ap.error("lore call needs a TOOL")
            res = lore.call(a.tool, json.loads(a.args), url)
        else:
            res = {"tool": "top_theories", "url": url, "items": lore.top_theories(a.n, a.lore, url)}
        text = json.dumps(res, ensure_ascii=False, indent=2)
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(text, encoding="utf-8")
            print(f"written: {a.out}")
        else:
            print(text)
        return 0

    if a.cmd == "init":
        ch = load_channel(a.channel)
        if ch.get("formats") and not a.format:
            ap.error(f"channel {ch['id']} has formats, pass --format ({', '.join(formats.names(ch))})")
        if a.format:
            formats.get(ch, a.format)
        root = Path(a.root or ch.get("episodes_root", "episodes/{slug}").replace("{slug}", a.slug))
        ep = Episode.init(root if a.root is None else root / a.slug, ch["id"], a.slug, a.format)
        print(f"episode folder: {ep.folder}" + (f"  (format {a.format})" if a.format else ""))
        return 0

    if a.cmd == "status":
        st = Episode(Path(a.episode)).status()
        if a.json:
            print(json.dumps(st, ensure_ascii=False, indent=2))
            return 0
        if st.get("format"):
            print(f"format: {st['format']}")
        for r in st["stages"]:
            if r.get("skipped"):
                print(f"- {r['stage']:<9} {r['agent']:<13}  (off for this channel)")
                continue
            gate = ""
            if r["gate"]:
                gate = f"  [owner: {r['gate']} {'✓' if r['approved'] else '…'}]"
            print(f"{'✓' if r['done'] else '·'} {r['stage']:<9} {r['agent']:<13}{gate}")
        if st["waiting_for_owner"]:
            print(f"\nwaiting for the owner to approve: {st['waiting_for_owner']}")
        elif st["next"]:
            print(f"\nnext: {st['next']}")
        elif "publish" in st.get("skipped", []):
            print("\nepisode ready: publishing is off for this channel")
        else:
            print("\nepisode published")
        return 0

    if a.cmd == "validate":
        ep = Episode(Path(a.episode))
        return _print_problems(contracts.validate_episode(ep, _channel_of(ep)))

    if a.cmd == "variety":
        sl = json.loads(Path(a.shotlist).read_text(encoding="utf-8"))
        ch = formats.effective(load_channel(a.channel), a.format) if a.channel else None
        res = variety.check(sl, ch)
        print(json.dumps(res["stats"], ensure_ascii=False))
        return _print_problems(res["problems"])

    if a.cmd == "look":
        from . import look
        res = look.for_episode(Path(a.episode))
        print(json.dumps(res, ensure_ascii=False, indent=2))
        if a.write:
            out = Path(a.episode) / "04_shots/look.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"written: {out}")
        return 0

    if a.cmd == "shorts":
        from . import shorts
        ep = Path(a.episode)
        if a.check:
            plan = json.loads((ep / "06_render/shorts/shorts.json").read_text(encoding="utf-8"))
            return _print_problems(shorts.check_plan(plan))
        res = shorts.for_episode(ep, a.n)
        for c in res["picked"]:
            print(f"{c['id']}: {c['score']:>5}  {c['start_s']:>6}-{c['end_s']:<6} {','.join(c['line_ids'])}  ({'; '.join(c['why'])})")
        if a.write:
            out = ep / "06_render/shorts/candidates.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"written: {out}")
        return 0

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
