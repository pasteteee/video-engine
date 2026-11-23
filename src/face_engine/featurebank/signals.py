"""Builds the per-frame signal table: engine outputs + landmark geometry + audio."""

from __future__ import annotations

import subprocess
from typing import Any, Sequence

import numpy as np

from face_engine.observations import FrameObservation
from face_engine.topology import BODY_POINTS, FACE_POINTS

F = {n: i for i, n in enumerate(FACE_POINTS)}
B = {n: i for i, n in enumerate(BODY_POINTS)}


def _dist(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a[:2] - b[:2]))


def _speed(x: np.ndarray, fps: float) -> np.ndarray:
    s = np.full_like(x, np.nan)
    s[1:] = np.abs(np.diff(x)) * fps
    return s


def engine_signals(report: dict[str, Any], n: int) -> dict[str, np.ndarray]:
    rf = {r["i"]: r for r in report["frames"]}
    keys = sorted({k for r in report["frames"] for k, v in r.items()
                   if k not in ("i", "t") and isinstance(v, (int, float))})
    out = {}
    for k in keys:
        out[k] = np.array([np.nan if rf.get(i, {}).get(k) is None else float(rf[i][k])
                           for i in range(n)], float)
    return out


def geometry_signals(frames: Sequence[FrameObservation], fps: float) -> dict[str, np.ndarray]:
    """Scale-free geometry from the 35 face points and 15 body points."""
    n = len(frames)
    names = ("geo.face_scale geo.face_cx geo.face_cy geo.mouth_open geo.mouth_width "
             "geo.lip_corner_lift geo.brow_height geo.brow_inner_height geo.brow_gap geo.eye_open "
             "geo.nose_wrinkle geo.chin_raise geo.iris_offset_x geo.iris_offset_y "
             "geo.head_tilt_2d geo.shoulder_width geo.shoulder_tilt geo.torso_cx geo.head_over_shoulders "
             "geo.wrist_l_height geo.wrist_r_height geo.hands_spread geo.hands_to_face "
             "geo.elbow_spread geo.body_scale_ratio").split()
    t = {k: np.full(n, np.nan) for k in names}
    for i, f in enumerate(frames):
        p = f.face
        if p is not None and len(p) >= len(FACE_POINTS):
            io = _dist(p[F["r_eye_outer"]], p[F["l_eye_outer"]])
            if io > 1:
                t["geo.face_scale"][i] = io
                c = p[:, :2].mean(0)
                t["geo.face_cx"][i], t["geo.face_cy"][i] = c[0] / io, c[1] / io
                t["geo.mouth_open"][i] = _dist(p[F["upper_lip_inner"]], p[F["lower_lip_inner"]]) / io
                t["geo.mouth_width"][i] = _dist(p[F["r_mouth_corner"]], p[F["l_mouth_corner"]]) / io
                mid_lip = (p[F["upper_lip_inner"]][1] + p[F["lower_lip_inner"]][1]) / 2
                corners = (p[F["r_mouth_corner"]][1] + p[F["l_mouth_corner"]][1]) / 2
                t["geo.lip_corner_lift"][i] = (corners - mid_lip) / io
                eyes_y = (p[F["r_eye_inner"]][1] + p[F["l_eye_inner"]][1]) / 2
                brow = np.mean([p[F[k]][1] for k in ("r_brow_mid", "l_brow_mid", "r_brow_outer", "l_brow_outer")])
                t["geo.brow_height"][i] = (brow - eyes_y) / io
                t["geo.brow_inner_height"][i] = ((p[F["r_brow_inner"]][1] + p[F["l_brow_inner"]][1]) / 2 - eyes_y) / io
                t["geo.brow_gap"][i] = _dist(p[F["r_brow_inner"]], p[F["l_brow_inner"]]) / io
                eo = (_dist(p[F["r_lid_up1"]], p[F["r_lid_lo1"]]) + _dist(p[F["l_lid_up1"]], p[F["l_lid_lo1"]])) / 2
                t["geo.eye_open"][i] = eo / io
                t["geo.nose_wrinkle"][i] = _dist(p[F["nose_bridge"]], p[F["subnasale"]]) / io
                t["geo.chin_raise"][i] = _dist(p[F["lower_lip_bottom"]], p[F["chin"]]) / io
                ex = np.mean([(p[F["r_iris"]][0] - (p[F["r_eye_outer"]][0] + p[F["r_eye_inner"]][0]) / 2),
                              (p[F["l_iris"]][0] - (p[F["l_eye_outer"]][0] + p[F["l_eye_inner"]][0]) / 2)]) / io
                ey = np.mean([p[F["r_iris"]][1] - (p[F["r_eye_outer"]][1] + p[F["r_eye_inner"]][1]) / 2,
                              p[F["l_iris"]][1] - (p[F["l_eye_outer"]][1] + p[F["l_eye_inner"]][1]) / 2]) / io
                t["geo.iris_offset_x"][i], t["geo.iris_offset_y"][i] = ex, ey
                v = p[F["l_eye_outer"]][:2] - p[F["r_eye_outer"]][:2]
                t["geo.head_tilt_2d"][i] = float(np.degrees(np.arctan2(v[1], v[0])))
        b, vis = f.body, f.body_visibility
        if b is not None and vis is not None:
            ok = lambda k: vis[B[k]] > 0.5  # noqa: E731
            if ok("l_shoulder") and ok("r_shoulder"):
                sw = _dist(b[B["l_shoulder"]], b[B["r_shoulder"]])
                if sw > 1:
                    t["geo.shoulder_width"][i] = sw
                    v = b[B["l_shoulder"]][:2] - b[B["r_shoulder"]][:2]
                    t["geo.shoulder_tilt"][i] = float(np.degrees(np.arctan2(v[1], abs(v[0]) + 1e-9)))
                    sc = (b[B["l_shoulder"]][:2] + b[B["r_shoulder"]][:2]) / 2
                    t["geo.torso_cx"][i] = sc[0] / sw
                    t["geo.head_over_shoulders"][i] = (b[B["nose"]][1] - sc[1]) / sw
                    for side in ("l", "r"):
                        if ok(f"{side}_wrist"):
                            t[f"geo.wrist_{side}_height"][i] = (b[B[f"{side}_wrist"]][1] - sc[1]) / sw
                    if ok("l_wrist") and ok("r_wrist"):
                        t["geo.hands_spread"][i] = _dist(b[B["l_wrist"]], b[B["r_wrist"]]) / sw
                        hw = (b[B["l_wrist"]][:2] + b[B["r_wrist"]][:2]) / 2
                        t["geo.hands_to_face"][i] = float(np.linalg.norm(hw - b[B["nose"]][:2])) / sw
                    if ok("l_elbow") and ok("r_elbow"):
                        t["geo.elbow_spread"][i] = _dist(b[B["l_elbow"]], b[B["r_elbow"]]) / sw
                    if not np.isnan(t["geo.face_scale"][i]):
                        t["geo.body_scale_ratio"][i] = t["geo.face_scale"][i] / sw
    # normalise absolute pixel scale by the person's own median (distance to camera proxy)
    for k in ("geo.face_scale", "geo.shoulder_width"):
        m = np.nanmedian(t[k]) if np.isfinite(t[k]).any() else np.nan
        t[k] = t[k] / m
    return t


def kinematic_signals(sig: dict[str, np.ndarray], fps: float) -> dict[str, np.ndarray]:
    out = {}
    for k in ("head.yaw", "head.pitch", "head.roll", "gaze.h", "gaze.v", "geo.face_cx", "geo.face_cy",
              "geo.torso_cx", "geo.wrist_l_height", "geo.wrist_r_height", "geo.hands_spread", "geo.face_scale"):
        if k in sig:
            out[f"kin.{k.replace('.', '_')}_speed"] = _speed(sig[k], fps)
    if all(k in sig for k in ("head.yaw", "head.pitch", "head.roll")):
        d = np.vstack([np.diff(sig[k], prepend=np.nan) for k in ("head.yaw", "head.pitch", "head.roll")])
        av = np.sqrt((d**2).sum(0)) * fps
        out["kin.head_angular_speed"] = av
        acc = np.full_like(av, np.nan)
        acc[1:] = np.abs(np.diff(av)) * fps
        out["kin.head_angular_accel"] = acc
    return out


def audio_signals(clip: str, n: int, fps: float) -> dict[str, np.ndarray]:
    import librosa

    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", clip, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    a = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
    sr, hop = 16000, 160
    tf = lambda m: np.arange(m) * hop / sr  # noqa: E731
    tv = np.arange(n) / fps

    def to_video(x: np.ndarray) -> np.ndarray:
        good = np.isfinite(x)
        if not good.any():
            return np.full(n, np.nan)
        return np.interp(tv, tf(len(x))[good], x[good], left=np.nan, right=np.nan)

    out: dict[str, np.ndarray] = {}
    rms = librosa.feature.rms(y=a, frame_length=640, hop_length=hop)[0]
    out["voice.loudness_db"] = to_video(20 * np.log10(rms + 1e-6))
    f0, vflag, vprob = librosa.pyin(a, fmin=65, fmax=450, sr=sr, frame_length=1024, hop_length=hop)
    med = np.nanmedian(f0) if np.isfinite(f0).any() else np.nan
    st = 12 * np.log2(f0 / med)
    out["voice.pitch_st"] = to_video(st)
    out["voice.pitch_hz"] = to_video(f0)
    voiced = to_video(vflag.astype(float))
    out["voice.voiced"] = voiced
    out["voice.voicing_prob"] = to_video(vprob)
    out["voice.pitch_st"][~(voiced > 0.5)] = np.nan
    out["voice.pitch_hz"][~(voiced > 0.5)] = np.nan
    S = np.abs(librosa.stft(a, n_fft=512, hop_length=hop))
    out["voice.spectral_centroid"] = to_video(librosa.feature.spectral_centroid(S=S, sr=sr)[0])
    out["voice.spectral_flatness"] = to_video(librosa.feature.spectral_flatness(S=S)[0])
    out["voice.spectral_rolloff"] = to_video(librosa.feature.spectral_rolloff(S=S, sr=sr)[0])
    out["voice.spectral_bandwidth"] = to_video(librosa.feature.spectral_bandwidth(S=S, sr=sr)[0])
    out["voice.zcr"] = to_video(librosa.feature.zero_crossing_rate(a, frame_length=640, hop_length=hop)[0])
    # spectral tilt: low (0-1k) vs high (1-4k) band energy, dB  (breathy/soft vs pressed/bright)
    freqs = librosa.fft_frequencies(sr=sr, n_fft=512)
    lo = S[(freqs > 50) & (freqs < 1000)].sum(0)
    hi = S[(freqs >= 1000) & (freqs < 4000)].sum(0)
    out["voice.spectral_tilt_db"] = to_video(20 * np.log10((hi + 1e-6) / (lo + 1e-6)))
    out["voice.onset_strength"] = to_video(librosa.onset.onset_strength(y=a, sr=sr, hop_length=hop))
    mf = librosa.feature.mfcc(y=a, sr=sr, n_mfcc=13, hop_length=hop)
    for j in range(13):
        out[f"voice.mfcc{j + 1:02d}"] = to_video(mf[j])
    # jitter/shimmer-like local perturbations from frame-level pitch and loudness
    hz = out["voice.pitch_hz"]
    jit = np.full(n, np.nan)
    jit[1:] = np.abs(np.diff(hz)) / hz[1:]
    out["voice.jitter_like"] = jit
    ld = out["voice.loudness_db"]
    shim = np.full(n, np.nan)
    shim[1:] = np.abs(np.diff(ld))
    shim[~(voiced > 0.5)] = np.nan
    out["voice.shimmer_like_db"] = shim
    out["_audio_raw"] = a  # type: ignore[assignment]
    return out
