"""Observable temporal descriptors; no mental-state classifications."""

import numpy as np

from face_engine.analyzers.base import rnd
from face_engine.temporal import runs


def enrich(features, fps):
    valid = (features['face.reliability'] >= 0.5) & (features['face.present'] > 0)
    left, right = features['eye.closure_l'], features['eye.closure_r']
    eye_valid = valid & np.isfinite(left) & np.isfinite(right)
    features['eye.closed80'] = np.where(eye_valid, (left >= 0.8) & (right >= 0.8), np.nan)
    angles = np.vstack([features['head.' + k] for k in ('yaw', 'pitch', 'roll')])
    delta = (np.diff(angles, axis=1) + 180) % 360 - 180
    speed = np.full(len(valid), np.nan)
    speed[1:] = np.where(valid[1:] & valid[:-1], np.linalg.norm(delta, axis=0) * fps, np.nan)
    features['head.angular_speed_deg_s'] = speed
    accel = np.full(len(valid), np.nan)
    accel[1:] = np.abs(np.diff(speed)) * fps
    features['head.angular_accel_deg_s2'] = accel


def summarize_behavior(features, fps):
    closed = features['eye.closed80']
    good = np.isfinite(closed)
    spans = runs(good & (closed > 0))
    # Keep only slow closures, >= 0.5 s; missing frames break runs.
    slow = sum(b - a for a, b in spans if (b - a) / fps >= 0.5)
    speed = features['head.angular_speed_deg_s']
    speed = speed[np.isfinite(speed)]
    return {
        'eye_observed_s': rnd(good.sum() / fps),
        'eye_closed80_share': rnd(closed[good].mean()) if good.any() else None,
        'eye_slow_closed80_share': rnd(slow / good.sum()) if good.any() else None,
        'eye_longest_closed80_s': rnd(max((b-a for a, b in spans), default=0) / fps) if good.any() else None,
        'head_angular_speed_mean_deg_s': rnd(speed.mean()) if len(speed) else None,
        'head_angular_speed_p90_deg_s': rnd(np.quantile(speed, 0.9)) if len(speed) else None,
    }
