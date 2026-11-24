"""Independent event evaluation with inclusive original-frame intervals.

This is a pooled blink-ID protocol, not the per-eye Fogelton benchmark.
No dataset, annotation code, or detector threshold is bundled here.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def tag_intervals(text: str) -> tuple[list[tuple[int, int]], list[int]]:
    """Read Fogelton .tag blink IDs, keeping adjacent different IDs separate."""
    intervals = []
    frames = []
    current = None
    last_id = None
    for line in text.splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        fields = line.split(':')
        if len(fields) != 19:
            raise ValueError('annotation row must contain 19 colon-separated fields')
        frame, blink = int(fields[0]), int(fields[1])
        if frame < 0 or (frames and frame <= frames[-1]):
            raise ValueError('annotation frames must be nonnegative and increasing')
        if current is not None and (blink != last_id or frame != current[1] + 1):
            intervals.append(tuple(current))
            current = None
        if blink >= 0:
            if current is None:
                current = [frame, frame]
            else:
                current[1] = frame
        frames.append(frame)
        last_id = blink
    if current is not None:
        intervals.append(tuple(current))
    return intervals, frames


def interval_iou(a, b):
    intersection = max(0, min(a[1], b[1]) - max(a[0], b[0]) + 1)
    union = (a[1] - a[0] + 1) + (b[1] - b[0] + 1) - intersection
    return intersection / union


def restrict_to_annotation(intervals, frames):
    """Clip/split predictions to contiguous annotated regions; never score unknown frames."""
    regions = []
    for frame in frames:
        if regions and frame == regions[-1][1] + 1:
            regions[-1][1] = frame
        else:
            regions.append([frame, frame])
    return [(max(start, a), min(end, b)) for start, end in intervals
            for a, b in regions if max(start, a) <= min(end, b)]


def evaluate_events(predicted, truth, threshold=0.2):
    """Maximum-cardinality one-to-one matching at IoU > threshold."""
    if not 0 <= threshold < 1:
        raise ValueError('threshold must be in [0, 1)')
    for start, end in [*predicted, *truth]:
        if start < 0 or end < start:
            raise ValueError('invalid inclusive frame interval')
    edges = [sorted((j for j, gt in enumerate(truth) if interval_iou(p, gt) > threshold),
                    key=lambda j: (-interval_iou(p, truth[j]), j)) for p in predicted]
    matched = {}

    def assign(i, visited):
        for j in edges[i]:
            if j in visited:
                continue
            visited.add(j)
            if j not in matched or assign(matched[j], visited):
                matched[j] = i
                return True
        return False

    for i in range(len(predicted)):
        assign(i, set())
    tp = len(matched)
    fp, fn = len(predicted) - tp, len(truth) - tp
    precision = tp / len(predicted) if predicted else None
    recall = tp / len(truth) if truth else None
    f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None
    return {'tp': tp, 'fp': fp, 'fn': fn, 'precision': precision, 'recall': recall,
            'f1': f1, 'predicted': len(predicted), 'ground_truth': len(truth),
            'iou_threshold_strict': threshold,
            'matches': [{'prediction': i, 'truth': j, 'iou': interval_iou(predicted[i], truth[j])}
                        for j, i in sorted(matched.items())]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('annotation', type=Path)
    parser.add_argument('-o', '--output', type=Path, required=True)
    parser.add_argument('--allow-partial-annotation', action='store_true',
                        help='clip/split predictions to annotated regions; unknown frames are excluded')
    args = parser.parse_args(argv)
    report = json.loads(args.report.read_text(encoding='utf-8'))
    truth, frames = tag_intervals(args.annotation.read_text(encoding='utf-8-sig'))
    if not frames or frames[-1] >= report['meta']['frames']:
        raise ValueError('annotation is empty or exceeds the report frame count')
    if not args.allow_partial_annotation and frames != list(range(report['meta']['frames'])):
        raise ValueError('evaluation requires a full unsampled report and contiguous zero-based annotation')
    predicted = [(e['frame_start'], e['frame_end']) for e in report['events'] if e['type'] == 'blink']
    if args.allow_partial_annotation:
        predicted = restrict_to_annotation(predicted, frames)
    result = evaluate_events(predicted, truth)
    result.update(protocol='pooled blink IDs; inclusive frames; one-to-one IoU > 0.2',
                  annotation=str(args.annotation), report=str(args.report),
                  annotated_frames=len(frames), total_frames=report['meta']['frames'],
                  partial_annotation=args.allow_partial_annotation)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'matches'}))


if __name__ == '__main__':
    main()
