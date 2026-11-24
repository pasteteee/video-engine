"""Evaluate cached full-rate observations using independent annotation timestamps.

Run with --help. Download datasets separately under their author's terms.
"""
from dataclasses import replace
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from face_engine.engine import Engine
from face_engine.evaluation import evaluate_events, tag_intervals
from face_engine.sources import load_landmarks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('landmarks', type=Path)
    parser.add_argument('annotation', type=Path)
    parser.add_argument('timestamps', type=Path)
    parser.add_argument('-o', '--output', type=Path, required=True)
    args = parser.parse_args()
    media, frames = load_landmarks(args.landmarks)
    times = np.loadtxt(args.timestamps, ndmin=2)
    if times.shape != (len(frames), 2) or not np.isfinite(times).all():
        raise ValueError('need one finite frame_id/timestamp row per observation')
    if not np.array_equal(times[:, 0], [f.index for f in frames]):
        raise ValueError('timestamp frame IDs do not match observations')
    truth, ids = tag_intervals(args.annotation.read_text(encoding='utf-8-sig'))
    if ids != list(range(len(frames))):
        raise ValueError('need contiguous full zero-based annotation')
    differences = np.diff(times[:, 1])
    if not len(differences) or not (differences > 0).all() or not np.allclose(differences, np.median(differences), rtol=.001, atol=1e-6):
        raise ValueError('this benchmark requires uniform increasing timestamps')
    fps = 1 / float(np.median(differences))
    container_fps = media.fps
    media = replace(media, fps=fps)
    frames = [replace(f, time_s=float(t-times[0, 1])) for f, t in zip(frames, times[:, 1])]
    report = Engine().run(frames, media, frames_fps=0)
    predictions = [(e['frame_start'], e['frame_end']) for e in report['events'] if e['type'] == 'blink']
    result = evaluate_events(predictions, truth)
    result.update(protocol='pooled blink IDs; inclusive frames; one-to-one IoU > 0.2',
                  parameters_tuned=False, annotation_fps=fps, container_fps=container_fps,
                  n_frames=len(frames), annotation_sha256=hashlib.sha256(args.annotation.read_bytes()).hexdigest(),
                  timestamps_sha256=hashlib.sha256(args.timestamps.read_bytes()).hexdigest())
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k != 'matches'}))


if __name__ == '__main__':
    main()
