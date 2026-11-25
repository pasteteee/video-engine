"""Command line: python -m vengine <command> ...

  init      CHANNEL SLUG [--root DIR]   create the episode folder
  status    EPISODE_DIR [--json]        where the episode is and who acts next
  validate  EPISODE_DIR                 schemas + cross-file references
  variety   SHOTLIST.json [--channel ID] variety rules of the edit plan
  ailint    SCRIPT.json | TEXT_FILE [--json] [--print-rules]
  approve   EPISODE_DIR GATE [--note ..] record the owner's approval (topic|script|final)
  revoke    EPISODE_DIR GATE
  channels                              list channel profiles
  yarn      grow|still ...              crochet-growth frames of a toy (vengine/yarn; `vengine yarn -h`)
  catalog   search|info|view CHANNEL ..   the channel's models (amigurumi.ai): find, facts, 3D viewer
  catalog   pull EPISODE_DIR TOY_ID      spec, GLB, photo and a draft storyboard into the episode
  build     STEP EPISODE_DIR [...]       build shorts (amigurumi): knit | still | events | video | audio | finish | all
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import ailint, contracts, variety
from .episode import GATES, ROOT, Episode, load_channel


def _channel_of(ep: Episode) -> dict | None:
    return ep.channel


def _print_problems(probs: list[dict]) -> int:
    for p in probs:
        mark = "✗" if p["level"] == "error" else "!"
        where = f"{p['file']}: " if p.get("file") else ""
        print(f"{mark} {where}{p['msg']}")
    errs = sum(p["level"] == "error" for p in probs)
    print(f"\n{errs} errors, {len(probs) - errs} warnings")
    return 1 if errs else 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else list(argv)
    if args[:1] == ["yarn"]:                     # its own parser: numba and amikit are needed only there
        from .yarn.cli import main as yarn_main
        return yarn_main(args[1:])
    ap = argparse.ArgumentParser(prog="vengine", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init"); p.add_argument("channel"); p.add_argument("slug"); p.add_argument("--root")
    p = sub.add_parser("status"); p.add_argument("episode"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("validate"); p.add_argument("episode")
    p = sub.add_parser("variety"); p.add_argument("shotlist"); p.add_argument("--channel")
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
    p = sub.add_parser("catalog", help="the channel's models: search, info, 3D view, pull into an episode")
    p.add_argument("action", choices=["search", "info", "view", "pull"])
    p.add_argument("target", help="channel id (search/info/view) or episode folder (pull)")
    p.add_argument("arg", nargs="?", default="", help="query (search) or toy id")
    p.add_argument("--n", type=int, default=12); p.add_argument("--json", action="store_true")
    p.add_argument("--out")
    p = sub.add_parser("build", help="build shorts: a toy crocheted on screen")
    p.add_argument("step", choices=["knit", "still", "events", "video", "audio", "finish", "all", "check"])
    p.add_argument("episode"); p.add_argument("--jobs", type=int); p.add_argument("--part")
    p.add_argument("--at", default="0.8,3,8,12,16,18,21,26", help="still: seconds")
    p.add_argument("--out")

    a = ap.parse_args(argv)

    if a.cmd == "channels":
        for d in sorted((ROOT / "channels").glob("*/channel.json")):
            c = json.loads(d.read_text(encoding="utf-8"))
            print(f"{c['id']:<16} {c['name']} · {c['promise']}")
        return 0

    if a.cmd == "init":
        ch = load_channel(a.channel)
        root = Path(a.root or ch.get("episodes_root", "episodes/{slug}").replace("{slug}", a.slug))
        ep = Episode.init(root if a.root is None else root / a.slug, ch["id"], a.slug, ch.get("format", "documentary"))
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

    if a.cmd == "catalog":
        from . import catalog as cat
        if a.action == "pull":
            ep = Episode(Path(a.target))
            info = cat.Catalog((ep.channel or {}).get("catalog", {})).pull(a.arg, ep.folder)
            print(cat.format_info(info))
            print("\nwritten: " + ", ".join(info["local"].values()))
            return 0
        c = cat.Catalog(load_channel(a.target).get("catalog", {}))
        if a.action == "search":
            hits = c.search(a.arg, a.n)
            if a.json:
                print(json.dumps(hits, ensure_ascii=False, indent=2)); return 0
            for h in hits:
                print(f"{h['id']:<34} {h.get('name', ''):<32} {h.get('heightCm') or '':>5} cm  {h.get('hours') or '':>3} h  "
                      f"{h.get('yarnWeight') or ''}")
            return 0
        if not a.arg:
            ap.error("catalog info/view needs a toy id")
        info = c.info(a.arg)
        if a.action == "info":
            print(json.dumps(info, ensure_ascii=False, indent=2) if a.json else cat.format_info(info))
            return 0
        out = Path(a.out or f"{a.arg}.html")
        out.write_text(cat.viewer_html(info), encoding="utf-8")
        print(f"viewer: {out.resolve()}")
        return 0

    if a.cmd == "build":
        from .build import knit as knit_mod, render
        ep = Episode(Path(a.episode))
        if a.step == "knit":
            print(f"knit frames: {render.run_knit(ep, a.jobs)}")
            return _print_problems(knit_mod.check(ep.path(render.KNIT_DIR)))
        if a.step == "check":
            return _print_problems(knit_mod.check(ep.path(render.KNIT_DIR), schema=False) + contracts.validate_episode(ep, ep.channel))
        if a.step == "still":
            print(render.still(ep, [float(v) for v in a.at.split(",")], Path(a.out) if a.out else None))
            return 0
        if a.step == "events":
            print(render.write_events(ep)); return 0
        if a.step == "video":
            print(render.video(ep, a.part)); return 0
        if a.step == "audio":
            print(render.music(ep)); return 0
        res = render.finish(ep) if a.step == "finish" else render.run_all(ep, a.jobs)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0

    if a.cmd in ("approve", "revoke"):
        ep = Episode(Path(a.episode))
        ep.approve(a.gate, a.note) if a.cmd == "approve" else ep.revoke(a.gate)
        print(f"{a.gate}: {'approved' if a.cmd == 'approve' else 'revoked'}")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
