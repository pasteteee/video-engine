"""CLI: python -m face_engine.featurebank.run clip.mp4 words.json out.json"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from face_engine.engine import Engine
from face_engine.featurebank import FeatureBank
from face_engine.sources.mediapipe_source import MediaPipeSource
from face_engine.sources import load_landmarks, save_landmarks


def main(argv=None) -> None:
    clip, words_path, out = (argv or sys.argv[1:])[:3]
    t0 = time.time()
    cache = clip + ".fbcache.npz"
    if os.path.exists(cache) and os.path.getmtime(cache) > os.path.getmtime(clip):
        media, frames = load_landmarks(cache)
    else:
        media, frames = MediaPipeSource(None).read(clip)
        save_landmarks(cache, media, frames)
    report = Engine().run(frames, media, frames_fps=media.fps)
    words = json.loads(Path(words_path).read_text(encoding="utf-8")) if words_path != "-" else []
    dur = len(frames) / media.fps
    res = FeatureBank(media.fps, dur).run(report, frames, clip, words)
    res["source"] = {"clip": clip, "words": words_path}
    Path(out).write_text(json.dumps(res, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    print(f"{res['n_features']} features ({res['n_valid']} valid) in {time.time() - t0:.0f}s -> {out}")


if __name__ == "__main__":
    main()
