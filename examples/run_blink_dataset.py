"""Run blink benchmark clips, reusing landmark caches for parameter comparisons."""
import argparse
import json
from pathlib import Path
from face_engine.config import EngineConfig, FaceConfig
from face_engine.engine import Engine
from face_engine.sources import load_landmarks, save_landmarks
from face_engine.sources.mediapipe_source import MediaPipeSource


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--release', type=float, default=None)
    parser.add_argument('--report-name', default=None)
    parser.add_argument('--models', type=Path)
    args = parser.parse_args()
    report_name = args.report_name or ('report.json' if args.release is None else 'report-hysteresis.json')
    config = EngineConfig(face=FaceConfig(blink_release_closure=args.release))
    annotations = sorted(args.root.rglob('*.tag'))
    if not annotations:
        raise ValueError('no .tag annotations found')
    for annotation in annotations:
        cache = annotation.parent/'landmarks.npz'
        if cache.exists():
            media, frames = load_landmarks(cache)
        else:
            video = annotation.with_suffix('.avi')
            media, frames = MediaPipeSource(args.models, use_body=False, use_hands=False).read(video)
            save_landmarks(cache, media, frames)
        report = Engine(config=config).run(frames,media,frames_fps=0)
        (annotation.parent/report_name).write_text(json.dumps(report,allow_nan=False),encoding='utf-8')
        print(json.dumps({'clip':str(annotation.relative_to(args.root)), 'frames':len(frames),
                          'report':report_name,'blinks':report['summary']['face'].get('blinks')}),flush=True)


if __name__ == '__main__':
    main()
