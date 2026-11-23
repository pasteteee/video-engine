"""CLI: python -m face_engine.featurebank.run clip.mp4 words.json out.json"""

from __future__ import annotations

import json
import os
import pickle
import sys
import time

from face_engine.engine import Engine
from face_engine.featurebank import FeatureBank
from face_engine.sources.mediapipe_source import MediaPipeSource


def main(argv=None) -> None:
    clip, words_path, out = (argv or sys.argv[1:])[:3]
    t0 = time.time()
    cache = clip + ".fbcache.pkl"
    if os.path.exists(cache) and os.path.getmtime(cache) > os.path.getmtime(clip):
        media, frames, report = pickle.load(open(cache, "rb"))
    else:
        media, frames = MediaPipeSource(None).read(clip)
        report = Engine().run(frames, media, frames_fps=media.fps)
        pickle.dump((media, frames, report), open(cache, "wb"))
    words = json.load(open(words_path)) if words_path != "-" else []
    dur = len(frames) / media.fps
    res = FeatureBank(media.fps, dur).run(report, frames, clip, words)
    res["source"] = {"clip": clip, "words": words_path}
    json.dump(res, open(out, "w"))
    print(f"{res['n_features']} features ({res['n_valid']} valid) in {time.time() - t0:.0f}s -> {out}")


if __name__ == "__main__":
    main()
