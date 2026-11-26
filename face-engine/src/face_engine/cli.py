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
    text = json.dumps(report, ensure_ascii=False, indent=1, allow_nan=False)
    if out:
        Path(out).write_text(text, encoding="utf-8")
        print(f"wrote {out}", file=sys.stderr)
    else:
        print(text)


def cmd_analyze(args: argparse.Namespace) -> int:
    from face_engine.sources import load_landmarks, save_landmarks

    source = None

    def read(path: str, **kw):
        nonlocal source
        if Path(path).suffix.lower() == ".npz":
            return load_landmarks(path)
        if source is None:
            from face_engine.sources.mediapipe_source import MediaPipeSource

            models = Path(args.models) if args.models else None
            source = MediaPipeSource(models, use_body=not args.no_body, use_hands=not args.no_hands)
        return source.read(path, **kw)

    media, frames = read(args.input, sample_fps=args.sample_fps, max_seconds=args.max_seconds)
    # The neutral only feeds a median baseline: a few frames per second are plenty.
    neutral = read(args.neutral, sample_fps=5.0, max_seconds=60.0)[1] if args.neutral else []
    if args.save_landmarks and Path(args.input).suffix != ".npz":
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
    from face_engine.sources.synthetic import (
        random_identity,
        synthetic_body,
        synthetic_clip,
        synthetic_face,
    )

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
        return synthetic_body(
            {"l_wrist": (1.1 + swing, -0.5), "r_wrist": (-0.6, -1.5)}, palms_to_camera=t < 2.0
        )

    frames = synthetic_clip(int(12 * fps), fps, face, body)
    media = MediaInfo("synthetic-demo", "video", fps, 1280, 720, "synthetic")
    report = Engine().run(frames, media, frames_fps=args.frames_fps)
    _write(report, args.output)
    return 0


def cmd_visualize(args: argparse.Namespace) -> int:
    """Overlay video/photo + timeline plot + contact sheet for visual checking."""
    import cv2

    from face_engine import viz
    from face_engine.sources import load_landmarks, save_landmarks
    from face_engine.sources.mediapipe_source import IMAGE_SUFFIXES, MediaPipeSource

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    stem = Path(args.input).stem
    lm_path = out / f"{stem}.landmarks.npz"
    if args.landmarks:
        media, frames = load_landmarks(args.landmarks)
    else:
        models = Path(args.models) if args.models else None
        media, frames = MediaPipeSource(models).read(args.input, max_seconds=args.max_seconds)
        save_landmarks(lm_path, media, frames)
    report = Engine().run(frames, media, frames_fps=None)
    _write(report, str(out / f"{stem}.report.json"))

    if Path(args.input).suffix.lower() in IMAGE_SUFFIXES:
        img = cv2.imread(args.input)
        viz.draw_landmarks(img, frames[0], cv2)
        panel = np.zeros((max(img.shape[0], 330), 260, 3), np.uint8)
        viz.draw_panel(panel, report["frames"][0], [], cv2)
        canvas = np.zeros((panel.shape[0], img.shape[1] + 260, 3), np.uint8)
        canvas[: img.shape[0], : img.shape[1]] = img
        canvas[:, img.shape[1] :] = panel
        cv2.imwrite(str(out / f"{stem}.overlay.png"), canvas)
        return 0

    video = viz.render_overlay(args.input, frames, report, out / f"{stem}.overlay.mp4")
    viz.plot_timeline(report, out / f"{stem}.timeline.png")
    # Contact sheet: the frames where the strongest events peak.
    peaks = sorted(
        (e for e in report["events"] if "peak_s" in e and e["type"] in ("expression", "smile")),
        key=lambda e: -e.get("peak", 0),
    )
    times = sorted({round(e["peak_s"], 1) for e in peaks[:30]})[:9] or [0.0]
    cap = cv2.VideoCapture(str(video))
    shots = []
    for t in times:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, img = cap.read()
        if ok:
            shots.append(img)
    cap.release()
    if shots:
        viz.contact_sheet(shots, out / f"{stem}.moments.png")
    return 0


def _spans(items):
    out = []
    for it in items or []:
        a, b = it.split(":")
        out.append((float(a), float(b)))
    return out or None


def cmd_behavior(args: argparse.Namespace) -> int:
    """Multi-channel behaviour map vs the person's own baseline (face, eyes, head, body,
    hands, voice, speech) -> <stem>.behavior.json, <stem>.overlay.json, <stem>.behavior.png."""
    from face_engine import cues
    from face_engine.cues.deviation import DeviationConfig
    from face_engine.cues.signals import parse_words
    from face_engine.sources import load_landmarks, save_landmarks

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    stem = Path(args.input).stem
    if Path(args.input).suffix.lower() == ".npz":
        media, frames = load_landmarks(args.input)
        clip = args.audio or (media.path if Path(media.path).exists() else None)
    else:
        lm = out / f"{stem}.landmarks.npz"
        if lm.exists() and not args.redetect:
            media, frames = load_landmarks(lm)
        else:
            from face_engine.sources.mediapipe_source import MediaPipeSource

            models = Path(args.models) if args.models else None
            media, frames = MediaPipeSource(models).read(
                args.input, sample_fps=args.sample_fps, max_seconds=args.max_seconds)
            save_landmarks(lm, media, frames)
        clip = args.audio or args.input
    report = Engine().run(frames, media, frames_fps=None)
    audio = None
    if clip and not args.no_audio:
        from face_engine.featurebank.signals import audio_signals

        audio = audio_signals(str(clip), len(frames), media.fps)
        audio.pop("_audio_raw", None)
    words = None
    if args.words:
        words = parse_words(json.loads(Path(args.words).read_text(encoding="utf-8")))
    elif args.transcribe and clip:
        words = _transcribe(str(clip), args.transcribe, out / f"{stem}.words.json")
    questions = json.loads(Path(args.questions).read_text(encoding="utf-8")) if args.questions else ()
    override = state_override = None
    if args.baseline_from:
        prev = json.loads(Path(args.baseline_from).read_text(encoding="utf-8"))
        override = {k: v for k, v in prev["baseline"].items() if isinstance(v, dict) and "median" in v and "scale" in v}
        state_override = {g: v for g, v in prev.get("states", {}).get("groups", {}).items() if v.get("used")}
    states = json.loads(Path(args.states).read_text(encoding="utf-8")) if args.states else ()
    cfg = DeviationConfig(z=args.z, min_channels=args.min_channels, cluster_s=args.cluster)
    behavior, overlay, moments = cues.run(
        report, frames, media, audio, words, args.subject, questions, _spans(args.baseline), override, cfg,
        overlay_fps=args.overlay_fps, states=states, state_override=state_override)
    video = None if Path(args.input).suffix.lower() == ".npz" else args.input
    stills = {}
    if video:
        offset = frames[0].time_s
        for st, t in behavior["states"]["baseline_frame_s"].items():
            jpg = out / f"{stem}.baseline_{st}.jpg"
            if _still(video, t + offset, jpg):
                stills[st] = jpg.name
        for m in moments["moments"]:
            if m.get("baseline_frame"):
                m["baseline_frame"]["path"] = stills.get(m["baseline_frame"]["state"])
                m["baseline_frame"]["t"] = round(m["baseline_frame"]["t"] + offset, 3)
    _write(behavior, str(out / f"{stem}.behavior.json"))
    _write(overlay, str(out / f"{stem}.overlay.json"))
    _write(moments, str(out / f"{stem}.moments.json"))
    if not args.no_plot:
        try:
            from face_engine.cues.plot import plot

            plot(behavior, out / f"{stem}.behavior.png")
        except ImportError:
            print("matplotlib missing: no plot", file=sys.stderr)
    for line in behavior["summary"]["notes"]:
        print(line, file=sys.stderr)
    return 0


def _still(video: str, t: float, path: Path) -> bool:
    import os
    import subprocess

    r = subprocess.run([os.environ.get("FACE_ENGINE_FFMPEG", "ffmpeg"), "-v", "error", "-y", "-ss", f"{t:.3f}",
                        "-i", video, "-frames:v", "1", "-q:v", "2", str(path)], capture_output=True)
    return r.returncode == 0 and path.exists()


def _transcribe(clip: str, model: str, path: Path):
    from faster_whisper import WhisperModel

    from face_engine.cues.signals import parse_words

    import os
    import subprocess

    pcm = subprocess.run([os.environ.get("FACE_ENGINE_FFMPEG", "ffmpeg"), "-v", "error", "-i", clip, "-ac", "1",
                          "-ar", "16000", "-f", "s16le", "-"], capture_output=True, check=True).stdout
    audio = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768
    segs, _ = WhisperModel(model, device="cpu", compute_type="int8").transcribe(audio, word_timestamps=True)
    rows = [[w.start, w.end, w.word.strip()] for s in segs for w in (s.words or [])]
    path.write_text(json.dumps(rows), encoding="utf-8")
    return parse_words(rows)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="face-engine", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("analyze", help="analyze a photo, a video or a saved .npz of landmarks")
    a.add_argument("input")
    a.add_argument("-o", "--output", help="JSON report path (stdout if omitted)")
    a.add_argument(
        "--neutral", help="photo/video (or .npz) of the same person at rest, used as baseline"
    )
    a.add_argument("--segment", type=float, default=5.0, help="segment length in seconds")
    a.add_argument(
        "--frames-fps", type=float, default=5.0, help="per-frame rows written per second (0 = none)"
    )
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

    v = sub.add_parser("visualize", help="overlay video, timeline plot and key-moment sheet")
    v.add_argument("input", help="photo or video")
    v.add_argument("-o", "--output", required=True, help="output directory")
    v.add_argument("--landmarks", help="reuse a saved .npz instead of running the detector")
    v.add_argument("--max-seconds", type=float)
    v.add_argument("--models")
    v.set_defaults(func=cmd_visualize)

    b = sub.add_parser("behavior", help="multi-channel behaviour map, hotspots and overlay data")
    b.add_argument("input", help="video, or a saved .npz of landmarks")
    b.add_argument("-o", "--output", required=True, help="output directory")
    b.add_argument("--words", help="word timings JSON: [[start, end, text(, speaker)], ...]")
    b.add_argument("--subject", help="speaker label of the person on camera (with labelled words)")
    b.add_argument("--questions", help="JSON list of question end times or [start, end, text] rows")
    b.add_argument("--transcribe", metavar="MODEL", help="make word timings with faster-whisper (e.g. small.en)")
    b.add_argument("--baseline", action="append", metavar="A:B",
                   help="baseline span in seconds (repeatable); default: the whole clip")
    b.add_argument("--baseline-from", help="reuse the baseline of another .behavior.json (same person)")
    b.add_argument("--states", help="JSON [[start, end, label], ...] e.g. positive / negative_safe spans; "
                   "speak/listen are found automatically")
    b.add_argument("--audio", help="audio source when the input is .npz or the audio is separate")
    b.add_argument("--no-audio", action="store_true")
    b.add_argument("--z", type=float, default=2.0, help="SD from baseline that counts as a deviation")
    b.add_argument("--min-channels", type=int, default=3, help="channels needed for a hotspot")
    b.add_argument("--cluster", type=float, default=5.0, help="hotspot window, seconds")
    b.add_argument("--overlay-fps", type=float, default=10.0)
    b.add_argument("--sample-fps", type=float)
    b.add_argument("--max-seconds", type=float)
    b.add_argument("--models")
    b.add_argument("--redetect", action="store_true", help="ignore the cached landmarks")
    b.add_argument("--no-plot", action="store_true")
    b.set_defaults(func=cmd_behavior)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
