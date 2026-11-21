"""Named landmark topology shared by every detector backend.

The engine never works with raw detector indices. A detector adapter maps its
output to these named points, so any backend (MediaPipe, dlib, OpenFace, ...)
can feed the same math.

Coordinate convention used everywhere inside the engine ("internal frame"):
    x -> image right (the subject's LEFT when they face the camera)
    y -> up
    z -> toward the camera
Prefix ``r_`` / ``l_`` always means the subject's own right / left side.
"""

from __future__ import annotations

import numpy as np

# name -> (MediaPipe FaceMesh index, canonical neutral position)
# Canonical positions come from MediaPipe's canonical_face_model.obj,
# re-centred on the nose bridge and scaled so the inter-ocular distance
# (between eye centres) is 1.0. They serve as the alignment target and as the
# population-level neutral face when no personal baseline is available.
_FACE: dict[str, tuple[int, tuple[float, float, float]]] = {
    "r_eye_outer": (33, (-0.7054, -0.0963, -0.3273)),
    "r_eye_inner": (133, (-0.2946, -0.1088, -0.2345)),
    "l_eye_inner": (362, (0.2946, -0.1088, -0.2345)),
    "l_eye_outer": (263, (0.7054, -0.0963, -0.3273)),
    "r_lid_up1": (159, (-0.5041, -0.0487, -0.2156)),
    "r_lid_lo1": (145, (-0.5041, -0.1550, -0.2317)),
    "r_lid_up2": (158, (-0.4322, -0.0491, -0.2165)),
    "r_lid_lo2": (153, (-0.4322, -0.1516, -0.2315)),
    "l_lid_up1": (386, (0.5041, -0.0487, -0.2156)),
    "l_lid_lo1": (374, (0.5041, -0.1550, -0.2317)),
    "l_lid_up2": (385, (0.4322, -0.0491, -0.2165)),
    "l_lid_lo2": (380, (0.4322, -0.1516, -0.2315)),
    "r_brow_inner": (55, (-0.1937, 0.1382, -0.0206)),
    "r_brow_mid": (105, (-0.6326, 0.2917, -0.1221)),
    "r_brow_outer": (70, (-0.9078, 0.1561, -0.3816)),
    "l_brow_inner": (285, (0.1937, 0.1382, -0.0206)),
    "l_brow_mid": (334, (0.6326, 0.2917, -0.1221)),
    "l_brow_outer": (300, (0.9078, 0.1561, -0.3816)),
    "nose_bridge": (168, (0.0, 0.0, 0.0)),
    "nose_tip": (1, (0.0, -0.6978, 0.3554)),
    "subnasale": (2, (0.0, -0.8505, 0.1305)),
    "r_alar": (98, (-0.2230, -0.7910, 0.0008)),
    "l_alar": (327, (0.2230, -0.7910, 0.0008)),
    "upper_lip_top": (0, (0.0, -1.0595, 0.1180)),
    "upper_lip_inner": (13, (0.0, -1.1528, -0.0026)),
    "lower_lip_inner": (14, (0.0, -1.2398, 0.0268)),
    "lower_lip_bottom": (17, (0.0, -1.3703, 0.0475)),
    "r_mouth_corner": (61, (-0.3897, -1.2081, -0.1511)),
    "l_mouth_corner": (291, (0.3897, -1.2081, -0.1511)),
    "chin": (152, (0.0, -2.0111, -0.1542)),
    "forehead": (10, (0.0, 0.7919, -0.1197)),
    "r_face_side": (234, (-1.2161, -0.4122, -1.2173)),
    "l_face_side": (454, (1.2161, -0.4122, -1.2173)),
    # Iris centres exist only in the 478-point mesh; canonical = eye centre.
    "r_iris": (468, (-0.5000, -0.1026, -0.2809)),
    "l_iris": (473, (0.5000, -0.1026, -0.2809)),
}

FACE_POINTS: tuple[str, ...] = tuple(_FACE)
FACE_INDEX: dict[str, int] = {name: i for i, name in enumerate(FACE_POINTS)}
MEDIAPIPE_FACE_IDS: tuple[int, ...] = tuple(v[0] for v in _FACE.values())
CANONICAL_FACE: np.ndarray = np.array([v[1] for v in _FACE.values()], dtype=float)

# Points treated as (nearly) rigid with the skull; used to estimate head pose.
FACE_ANCHORS: tuple[str, ...] = (
    "r_eye_outer",
    "r_eye_inner",
    "l_eye_inner",
    "l_eye_outer",
    "nose_bridge",
    "nose_tip",
    "r_face_side",
    "l_face_side",
    "forehead",
)

# Body: MediaPipe Pose (BlazePose, 33 points) subset, named per subject side.
_BODY: dict[str, int] = {
    "nose": 0,
    "l_ear": 7,
    "r_ear": 8,
    "mouth_l": 9,
    "mouth_r": 10,
    "l_shoulder": 11,
    "r_shoulder": 12,
    "l_elbow": 13,
    "r_elbow": 14,
    "l_wrist": 15,
    "r_wrist": 16,
    "l_index": 19,
    "r_index": 20,
    "l_hip": 23,
    "r_hip": 24,
}
BODY_POINTS: tuple[str, ...] = tuple(_BODY)
BODY_INDEX: dict[str, int] = {name: i for i, name in enumerate(BODY_POINTS)}
MEDIAPIPE_BODY_IDS: tuple[int, ...] = tuple(_BODY.values())

# Hand: the 21-point MediaPipe hand model is used as-is (it is the de facto
# standard layout). Only a few indices are used by the analyzers.
HAND_WRIST, HAND_INDEX_MCP, HAND_PINKY_MCP = 0, 5, 17
HAND_NUM_POINTS = 21

# Subject sides, in the order used everywhere (also the on-disk hand-side code).
SIDES: tuple[str, str] = ("l", "r")
