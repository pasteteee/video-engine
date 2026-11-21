"""Visual checks: landmark/feature overlay video and timeline plots.

Needs the optional dependencies (opencv, matplotlib). Works from detector
output (FrameObservation list) plus the engine report computed with every
frame kept (``frames_fps=None``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

import numpy as np

from face_engine.analyzers.face import AU_NAMES, EXPRESSIONS
from face_engine.observations import FrameObservation
from face_engine.topology import BODY_INDEX, FACE_INDEX

EXPR_NAMES = (*EXPRESSIONS, "contempt")
BODY_FLAGS = ("gesturing", "face_touch", "arms_crossed", "hands_joined", "open_palms")
_BONES = [
    ("l_shoulder", "r_shoulder"),
    ("l_shoulder", "l_elbow"),
    ("l_elbow", "l_wrist"),
    ("r_shoulder", "r_elbow"),
    ("r_elbow", "r_wrist"),
    ("l_shoulder", "l_hip"),
    ("r_shoulder", "r_hip"),
    ("l_hip", "r_hip"),
]
_HAND_CHAINS = [
    (0, 1, 2, 3, 4),
    (0, 5, 6, 7, 8),
    (0, 9, 10, 11, 12),
    (0, 13, 14, 15, 16),
    (0, 17, 18, 19, 20),
    (5, 9, 13, 17),
]
_FACE_CHAINS = [
    ("r_brow_outer", "r_brow_mid", "r_brow_inner"),
    ("l_brow_inner", "l_brow_mid", "l_brow_outer"),
    (
        "r_eye_outer",
        "r_lid_up1",
        "r_lid_up2",
        "r_eye_inner",
        "r_lid_lo2",
        "r_lid_lo1",
        "r_eye_outer",
    ),
    (
        "l_eye_inner",
        "l_lid_up2",
        "l_lid_up1",
        "l_eye_outer",
        "l_lid_lo1",
        "l_lid_lo2",
        "l_eye_inner",
    ),
    ("r_mouth_corner", "upper_lip_top", "l_mouth_corner", "lower_lip_bottom", "r_mouth_corner"),
    ("r_mouth_corner", "upper_lip_inner", "l_mouth_corner", "lower_lip_inner", "r_mouth_corner"),
    ("nose_bridge", "nose_tip", "subnasale"),
    ("r_alar", "subnasale", "l_alar"),
]

# BGR colours
WHITE, GREY, CYAN, ORANGE, GREEN, RED, YELLOW = (
    (255, 255, 255),
    (150, 150, 150),
    (255, 220, 0),
    (0, 160, 255),
    (80, 220, 80),
    (60, 60, 255),
    (0, 230, 255),
)


def _px(p: np.ndarray) -> tuple[int, int]:
    """Internal frame (y up) -> image pixel."""
    return int(round(p[0])), int(round(-p[1]))


def draw_landmarks(img: np.ndarray, obs: FrameObservation, cv2: Any) -> None:
    if obs.face is not None:
        for chain in _FACE_CHAINS:
            pts = [obs.face[FACE_INDEX[n]] for n in chain]
            if not np.isnan(pts).any():
                cv2.polylines(img, [np.array([_px(p) for p in pts])], False, CYAN, 1, cv2.LINE_AA)
        for p in obs.face:
            if not np.isnan(p).any():
                cv2.circle(img, _px(p), 2, YELLOW, -1, cv2.LINE_AA)
    if obs.body is not None:
        vis = obs.body_visibility if obs.body_visibility is not None else np.ones(len(obs.body))
        for a, b in _BONES:
            ia, ib = BODY_INDEX[a], BODY_INDEX[b]
            if min(vis[ia], vis[ib]) >= 0.5:
                cv2.line(img, _px(obs.body[ia]), _px(obs.body[ib]), ORANGE, 2, cv2.LINE_AA)
    for hand in obs.hands:
        colour = GREEN if hand.side != "r" else RED
        for chain in _HAND_CHAINS:
            pts = np.array([_px(hand.points[i]) for i in chain])
            cv2.polylines(img, [pts], False, colour, 1, cv2.LINE_AA)


def _bar(img, cv2, x, y, label, value, colour, width=150):
    cv2.putText(img, label, (x, y + 9), cv2.FONT_HERSHEY_SIMPLEX, 0.36, WHITE, 1, cv2.LINE_AA)
    x0 = x + 70
    cv2.rectangle(img, (x0, y), (x0 + width, y + 10), (60, 60, 60), -1)
    if value is not None and not np.isnan(value):
        cv2.rectangle(
            img, (x0, y), (x0 + int(width * float(np.clip(value, 0, 1))), y + 10), colour, -1
        )


def draw_panel(panel: np.ndarray, row: dict[str, Any], active: list[str], cv2: Any) -> None:
    """Right-hand side panel with AU bars, expression bars, head pose and active events."""
    y = 14
    t = row.get("t", 0.0)
    cv2.putText(
        panel, f"t={t:6.2f}s", (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, WHITE, 1, cv2.LINE_AA
    )
    y += 14
    if row.get("face.present") == 1.0:
        cv2.putText(panel, "Action units", (10, y + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.4, GREY, 1)
        y += 14
        for au in AU_NAMES:
            _bar(panel, cv2, 10, y, au, row.get(f"au.{au}"), CYAN)
            y += 12
        y += 4
        cv2.putText(panel, "Expressions", (10, y + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.4, GREY, 1)
        y += 14
        for e in EXPR_NAMES:
            _bar(panel, cv2, 10, y, e[:9], row.get(f"expr.{e}"), ORANGE)
            y += 12
        y += 4
        head = " ".join(
            f"{a[0]}{row.get(f'head.{a}_rel', 0):+4.0f}" for a in ("yaw", "pitch", "roll")
        )
        cv2.putText(panel, f"head {head}", (10, y + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.38, WHITE, 1)
        y += 14
        eyes = f"eyes closed {row.get('eye.closure', 0):.2f}  gaze {'AWAY' if row.get('gaze.averted') else 'on'}"
        cv2.putText(panel, eyes, (10, y + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.38, WHITE, 1)
        y += 14
    else:
        cv2.putText(panel, "no face", (10, y + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, RED, 1)
        y += 16
    if row.get("body.present") == 1.0:
        flags = [f for f in BODY_FLAGS if row.get(f"body.{f}") == 1.0]
        cv2.putText(
            panel,
            "body: " + (", ".join(flags) or "-"),
            (10, y + 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.38,
            GREEN,
            1,
        )
        y += 14
        _bar(panel, cv2, 10, y, "gesture", row.get("body.gesture_activity"), GREEN)
        y += 14
    y += 4
    for label in active[:6]:
        cv2.putText(
            panel, label, (10, y + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.38, YELLOW, 1, cv2.LINE_AA
        )
        y += 13


def _event_label(e: dict[str, Any]) -> str:
    what = e.get("au") or e.get("expression") or e.get("direction") or ""
    return f"> {e['type']} {what}".strip()


def render_overlay(
    video: str | Path,
    frames: Sequence[FrameObservation],
    report: dict[str, Any],
    out: str | Path,
    panel_width: int = 260,
) -> Path:
    """Write an MP4 with landmarks on the video and a feature panel beside it."""
    import cv2

    rows = {r["i"]: r for r in report["frames"]}
    by_index = {f.index: f for f in frames}
    events = report["events"]
    cap = cv2.VideoCapture(str(video))
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out_h = max(h, 330)
    fps = report["meta"]["fps"]
    writer = cv2.VideoWriter(
        str(out), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w + panel_width, out_h)
    )
    i = 0
    try:
        while True:
            ok, img = cap.read()
            if not ok:
                break
            if i in by_index:
                obs, row = by_index[i], rows.get(i, {})
                draw_landmarks(img, obs, cv2)
                canvas = np.zeros((out_h, w + panel_width, 3), np.uint8)
                canvas[:h, :w] = img
                active = [
                    _event_label(e)
                    for e in events
                    if e["frame_start"] <= i <= e["frame_end"] and e["type"] != "posture_shift"
                ]
                draw_panel(canvas[:, w:], row, active, cv2)
                writer.write(canvas)
            i += 1
    finally:
        cap.release()
        writer.release()
    return Path(out)


def plot_timeline(report: dict[str, Any], out: str | Path, title: str = "") -> Path:
    """PNG with AU heatmap, expressions, head pose, eyes and body flags over time."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = report["frames"]
    t = np.array([r["t"] for r in rows])

    def col(key: str) -> np.ndarray:
        return np.array([r.get(key, np.nan) for r in rows], dtype=float)

    fig, axes = plt.subplots(
        5, 1, figsize=(14, 13), sharex=True, gridspec_kw={"height_ratios": [3.2, 2, 1.4, 1.2, 1.4]}
    )
    ax = axes[0]
    aus = list(AU_NAMES)
    heat = np.array([col(f"au.{a}") for a in aus])
    ax.imshow(
        np.nan_to_num(heat),
        aspect="auto",
        cmap="magma",
        vmin=0,
        vmax=1,
        extent=(t[0], t[-1], len(aus) - 0.5, -0.5),
        interpolation="nearest",
    )
    ax.set_yticks(range(len(aus)), [f"{a} {AU_NAMES[a][:22]}" for a in aus], fontsize=7)
    ax.set_title("Action units (0..1 vs personal neutral)", fontsize=10, loc="left")

    ax = axes[1]
    for e in EXPR_NAMES:
        ax.plot(t, col(f"expr.{e}"), label=e, lw=1)
    ax.set_ylim(0, 1)
    ax.legend(ncol=7, fontsize=7, loc="upper right")
    ax.set_title("Expression prototype similarity", fontsize=10, loc="left")

    ax = axes[2]
    for a in ("yaw", "pitch", "roll"):
        ax.plot(t, col(f"head.{a}_rel"), label=f"{a} (deg)", lw=1)
    ax.axhline(0, color="grey", lw=0.5)
    for e in report["events"]:
        if e["type"] in ("head_nod", "head_shake"):
            ax.axvspan(
                e["start_s"],
                e["end_s"],
                color="C3" if e["type"] == "head_shake" else "C2",
                alpha=0.2,
            )
    ax.legend(ncol=3, fontsize=7, loc="upper right")
    ax.set_title("Head pose vs neutral (green band = nod, red = shake)", fontsize=10, loc="left")

    ax = axes[3]
    ax.plot(t, col("eye.closure"), color="k", lw=0.8, label="eye closure")
    ax.plot(t, col("gaze.averted") * 0.5, color="C1", lw=0.8, label="gaze averted")
    for e in report["events"]:
        if e["type"] == "blink":
            ax.axvline(e["peak_s"], color="C0", lw=0.6, alpha=0.6)
    ax.set_ylim(0, 1.05)
    ax.legend(ncol=2, fontsize=7, loc="upper right")
    ax.set_title("Eyes (blue lines = detected blinks)", fontsize=10, loc="left")

    ax = axes[4]
    for k, flag in enumerate(BODY_FLAGS):
        on = np.nan_to_num(col(f"body.{flag}")) > 0.5
        ax.fill_between(t, k, k + np.where(on, 0.8, 0), step="mid", color=f"C{k}")
    ax.plot(t, len(BODY_FLAGS) + np.nan_to_num(col("body.gesture_activity")), color="k", lw=0.8)
    ax.set_yticks(
        [k + 0.4 for k in range(len(BODY_FLAGS))] + [len(BODY_FLAGS) + 0.5],
        [*BODY_FLAGS, "gesture activity"],
        fontsize=7,
    )
    ax.set_title("Body and hands", fontsize=10, loc="left")
    ax.set_xlabel("time, s")

    fig.suptitle(title or Path(report["meta"]["path"]).name, fontsize=12)
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    plt.close(fig)
    return Path(out)


def contact_sheet(video_png: Sequence[np.ndarray], out: str | Path, cols: int = 3) -> Path:
    """Tile several rendered frames into one PNG."""
    import cv2

    h, w = video_png[0].shape[:2]
    rows = (len(video_png) + cols - 1) // cols
    sheet = np.zeros((rows * h, cols * w, 3), np.uint8)
    for k, img in enumerate(video_png):
        r, c = divmod(k, cols)
        sheet[r * h : (r + 1) * h, c * w : (c + 1) * w] = img
    cv2.imwrite(str(out), sheet)
    return Path(out)
