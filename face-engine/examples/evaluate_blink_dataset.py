"""Aggregate all .tag/report.json pairs; fail if any report is missing."""
import argparse
import hashlib
import json
from pathlib import Path

from face_engine.evaluation import evaluate_events, restrict_to_annotation, tag_intervals


def evaluate_dataset(root, report_name="report.json"):
    annotations = sorted(Path(root).rglob('*.tag'))
    if not annotations:
        raise ValueError('no annotation files found')
    clips = []
    for annotation in annotations:
        path = annotation.parent / report_name
        report = json.loads(path.read_text(encoding='utf-8'))
        truth, frames = tag_intervals(annotation.read_text(encoding='utf-8-sig'))
        if not frames or frames[-1] >= report['meta']['frames']:
            raise ValueError(f'annotation exceeds report: {annotation}')
        predicted = [(e['frame_start'], e['frame_end']) for e in report['events']
                     if e['type'] == 'blink']
        predicted = restrict_to_annotation(predicted, frames)
        result = evaluate_events(predicted, truth)
        result.pop('matches')
        result.update(clip=annotation.relative_to(root).as_posix(),
                      annotated_frames=len(frames), total_frames=report['meta']['frames'],
                      fps=report['meta']['fps'],
                      annotation_sha256=hashlib.sha256(annotation.read_bytes()).hexdigest(),
                      report_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        clips.append(result)
    tp, fp, fn = (sum(c[k] for c in clips) for k in ('tp', 'fp', 'fn'))
    return {'protocol': 'pooled blink IDs; inclusive frames; one-to-one IoU > 0.2; '
                        'predictions clipped/split to annotated regions; container FPS',
            'clips': clips, 'n_clips': len(clips), 'tp': tp, 'fp': fp, 'fn': fn,
            'precision': tp / (tp + fp) if tp + fp else None,
            'recall': tp / (tp + fn) if tp + fn else None,
            'f1': 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
            'annotated_frames': sum(c['annotated_frames'] for c in clips),
            'total_frames': sum(c['total_frames'] for c in clips)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('-o', '--output', required=True, type=Path)
    parser.add_argument('--report-name', default='report.json')
    args = parser.parse_args()
    result = evaluate_dataset(args.root, args.report_name)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'clips'}))


if __name__ == '__main__':
    main()
