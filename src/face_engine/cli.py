"""Command line interface: ``face-engine analyze|models|demo``."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

from face_engine.config import EngineConfig
from face_engine.engine import Engine
from face_engine.observations import MediaInfo


def _write(report: dict, out: str | None) -> None:
    text = json.dumps(report, ensure_ascii=False, indent=1)
    if out:
        Path(out).write_text(text, encoding="utf-8")
        print(f"wrote {out}", file=sys.stderr)
    else:
        print(text)


def cmd_analyze(args: argparse.Namespace) -> int:
    from face_engine.sources import load_landmarks, save_landmarks

    if Path(args.input).suffix == ".npz":
        media, frames = load_landmarks(args.input)
        neutral = load_landmarks(args.neutral)[1] if args.neutral else []
    else:
        from face_engine.sources.mediapipe_source import MediaPipeSource

        models = Path(args.models) if args.models else None
        source = MediaPipeSource(models, use_body=not args.no_body, use_hands=not args.no_hands)
        media, frames = source.read(args.input, args.sample_fps, args.max_seconds)
        neutral = source.read(args.neutral)[1] if args.neutral else []
        if args.save_landmarks:
            save_landmarks(args.save_landmarks, media, frames)
    config = replace(EngineConfig(), segment_s=args.segment)
    report = Engine(config=config).run(frames, media, neutral, frames_fps=args.frames_fps)
    _write(report, args.output)
    return 0


def cmd_models(args: argparse.Namespace) -> int:
    from face_engine.sources.mediapipe_source import download_models

    for p in download_models(Path(args.dir) if args.dir else None, force=args.force):
        print(p)
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    """Analyze a synthetic 12-second clip; needs no detector or models."""
    from face_engine.sources.synthetic import random_identity, synthetic_body, synthetic_clip, synthetic_face

    fps = 30.0
    rng = np.random.default_rng(7)
    identity = random_identity(rng)

    def face(i: int) -> np.ndarray:
        t = i / fps
        expr: dict[str, float] = {}
        if 2.0 <= t < 3.5:
            expr.update(smile=1.0, cheek_raise=0.8)
        if 5.0 <= t < 5.3:
            expr["smile_l"] = 0.8
        if 7.0 <= t < 8.0:
            expr.update(brow_lower=0.9, lip_press=0.8)
        if any(abs(t - b) < 0.1 for b in (1.0, 4.2, 6.1, 9.5)):
            expr["blink"] = 1.0
        yaw = 12 * np.sin(2 * np.pi * 2 * t) if 10.0 <= t < 11.0 else 0.0
        return synthetic_face(expr, yaw=yaw, identity=identity, noise_px=0.2, rng=rng)

    def body(i: int):
        t = i / fps
        if 3.0 <= t < 6.0:
            return synthetic_body("crossed")
        if 8.0 <= t < 9.0:
            return synthetic_body("face_touch")
        swing = 0.4 * np.sin(2 * np.pi * 1.5 * t) if 0.5 <= t < 2.0 else 0.0
        return synthetic_body({"l_wrist": (1.1 + swing, -0.5), "r_wrist": (-0.6, -1.5)},
                              palms_to_camera=t < 2.0)

    frames = synthetic_clip(int(12 * fps), fps, face, body)
    media = MediaInfo("synthetic-demo", "video", fps, 1280, 720, "synthetic")
    report = Engine().run(frames, media, frames_fps=args.frames_fps)
    _write(report, args.output)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="face-engine", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("analyze", help="analyze a photo, a video or a saved .npz of landmarks")
    a.add_argument("input")
    a.add_argument("-o", "--output", help="JSON report path (stdout if omitted)")
    a.add_argument("--neutral", help="photo/video (or .npz) of the same person at rest, used as baseline")
    a.add_argument("--segment", type=float, default=5.0, help="segment length in seconds")
    a.add_argument("--frames-fps", type=float, default=5.0,
                   help="per-frame rows written per second (0 = none)")
    a.add_argument("--sample-fps", type=float, help="analyze the video at this frame rate")
    a.add_argument("--max-seconds", type=float, help="only analyze the first N seconds")
    a.add_argument("--no-body", action="store_true", help="skip pose and hands")
    a.add_argument("--no-hands", action="store_true", help="skip hand landmarks")
    a.add_argument("--models", help="directory with MediaPipe .task models")
    a.add_argument("--save-landmarks", help="also save detector output to this .npz")
    a.set_defaults(func=cmd_analyze)

    m = sub.add_parser("models", help="download the MediaPipe landmark models")
    m.add_argument("--dir")
    m.add_argument("--force", action="store_true")
    m.set_defaults(func=cmd_models)

    d = sub.add_parser("demo", help="run on a synthetic clip (no detector needed)")
    d.add_argument("-o", "--output")
    d.add_argument("--frames-fps", type=float, default=0.0)
    d.set_defaults(func=cmd_demo)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
