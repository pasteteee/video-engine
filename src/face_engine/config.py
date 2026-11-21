"""Tunable constants. Every heuristic threshold of the engine lives here.

Distances on the face are in IOD units (inter-ocular distance = 1, about 6.3 cm
on an adult). Distances on the body are in shoulder widths (SW).
"Full scale" means the deviation from the person's neutral that maps to an
intensity of 1.0; values come from typical FACS amplitude ranges and should be
re-fitted once labelled data is available.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FaceConfig:
    # Full-scale deviations (IOD units unless noted).
    brow_raise_full: float = 0.10
    brow_lower_full: float = 0.07
    brow_gap_full: float = 0.07
    eye_widen_full_rel: float = 0.35  # relative to neutral eye opening
    lid_tighten_full_rel: float = 0.40
    lower_lid_raise_full: float = 0.03
    nose_wrinkle_full: float = 0.05
    upper_lip_raise_full: float = 0.06
    corner_raise_full: float = 0.08
    corner_depress_full: float = 0.06
    mouth_stretch_full: float = 0.15
    lip_press_full: float = 0.08
    lip_part_full: float = 0.10
    jaw_drop_full: float = 0.35
    chin_raise_full: float = 0.06

    smoothing_s: float = 0.10
    blink_closure: float = 0.5  # eye closure (0..1) that counts as "closed"
    blink_max_s: float = 0.5  # closures longer than this are "eye_closure" events
    event_threshold: float = 0.35  # AU / emotion intensity that starts an event
    brief_event_s: float = 0.5  # events shorter than this are flagged "brief"
    gaze_averted_deg: float = 15.0
    eye_rotation_deg: float = 35.0  # approx. eye-in-head rotation at |gaze_h| = 1
    nod_amplitude_deg: float = 6.0
    speaking_lip_std: float = 0.015
    reliable_yaw_deg: float = 20.0  # beyond this, asymmetry/AU values degrade
    baseline_quantile: float = 0.3  # share of calmest frames used for the baseline


@dataclass(frozen=True)
class BodyConfig:
    min_visibility: float = 0.5
    smoothing_s: float = 0.15
    gesture_speed: float = 0.6  # SW per second
    gesture_speed_full: float = 1.5
    face_touch_dist: float = 0.30
    hands_joined_dist: float = 0.25
    palm_facing: float = 0.5
    shrug_full: float = 0.15
    posture_shift: float = 0.08  # change of lean_in (relative scale)
    min_event_s: float = 0.2
    merge_gap_s: float = 0.4  # e.g. the pause at the turning point of a gesture


@dataclass(frozen=True)
class EngineConfig:
    face: FaceConfig = field(default_factory=FaceConfig)
    body: BodyConfig = field(default_factory=BodyConfig)
    segment_s: float = 5.0
