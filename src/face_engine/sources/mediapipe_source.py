"""MediaPipe Tasks adapter: the only place that knows MediaPipe's formats.

MediaPipe is used purely as a landmark detector (face mesh, pose, hands).
Its blendshape classifier is deliberately not used: interpretation is done by
the engine's own analyzers.
"""

from __future__ import annotations

import os
import urllib.request
from pathlib import Path
from typing import Any, Iterator

import numpy as np

from face_engine.observations import FrameObservation, Hand, MediaInfo
from face_engine.topology import MEDIAPIPE_BODY_IDS, MEDIAPIPE_FACE_IDS

_BASE = "https://storage.googleapis.com/mediapipe-models"
MODEL_URLS = {
    "face_landmarker.task": f"{_BASE}/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
    "pose_landmarker.task": f"{_BASE}/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task",
    "hand_landmarker.task": f"{_BASE}/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def default_models_dir() -> Path:
    env = os.environ.get("FACE_ENGINE_MODELS")
    return Path(env) if env else Path.home() / ".cache" / "face-engine" / "models"


def download_models(models_dir: Path | None = None, force: bool = False) -> list[Path]:
    models_dir = models_dir or default_models_dir()
    models_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, url in MODEL_URLS.items():
        path = models_dir / name
        if force or not path.exists():
            tmp = path.with_suffix(".part")
            urllib.request.urlretrieve(url, tmp)
            tmp.replace(path)
        paths.append(path)
    return paths


def _to_internal(points: np.ndarray, width: int, height: int) -> np.ndarray:
    """Normalised MediaPipe (x right, y down, z away) -> internal pixels (x right, y up, z toward)."""
    out = np.empty_like(points, dtype=float)
    out[:, 0] = points[:, 0] * width
    out[:, 1] = -points[:, 1] * height
    out[:, 2] = -points[:, 2] * width
    return out


def _array(landmarks: Any) -> np.ndarray:
    return np.array([(p.x, p.y, p.z) for p in landmarks], dtype=float)


class MediaPipeSource:
    """Reads an image or a video and yields :class:`FrameObservation` objects."""

    name = "mediapipe-tasks"

    def __init__(
        self,
        models_dir: Path | None = None,
        use_face: bool = True,
        use_body: bool = True,
        use_hands: bool = True,
    ) -> None:
        self.models_dir = models_dir or default_models_dir()
        self.use = {"face": use_face, "pose": use_body, "hand": use_hands and use_body}

    # ---------------------------------------------------------------- public
    def read(
        self, path: str | Path, sample_fps: float | None = None, max_seconds: float | None = None
    ) -> tuple[MediaInfo, list[FrameObservation]]:
        path = Path(path)
        if path.suffix.lower() in IMAGE_SUFFIXES:
            return self._read_image(path)
        return self._read_video(path, sample_fps, max_seconds)

    # --------------------------------------------------------------- internal
    def _landmarkers(self, video: bool) -> dict[str, Any]:
        from mediapipe.tasks.python import BaseOptions, vision

        mode = vision.RunningMode.VIDEO if video else vision.RunningMode.IMAGE
        specs = {
            "face": (vision.FaceLandmarker, vision.FaceLandmarkerOptions, {"num_faces": 1}),
            "pose": (vision.PoseLandmarker, vision.PoseLandmarkerOptions, {"num_poses": 1}),
            "hand": (vision.HandLandmarker, vision.HandLandmarkerOptions, {"num_hands": 2}),
        }
        out = {}
        for key, (cls, opts_cls, extra) in specs.items():
            if not self.use[key]:
                continue
            model = self.models_dir / f"{key}_landmarker.task"
            if not model.exists():
                raise FileNotFoundError(
                    f"model {model} not found; run `face-engine models` to download it"
                )
            opts = opts_cls(
                base_options=BaseOptions(model_asset_path=str(model)), running_mode=mode, **extra
            )
            out[key] = cls.create_from_options(opts)
        return out

    def _observe(
        self, detectors: dict[str, Any], rgb: np.ndarray, index: int, time_s: float, video: bool
    ) -> FrameObservation:
        import mediapipe as mp

        h, w = rgb.shape[:2]
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))

        def detect(key: str) -> Any:
            det = detectors[key]
            return det.detect_for_video(image, int(round(time_s * 1000))) if video else det.detect(image)

        obs = FrameObservation(index=index, time_s=time_s)
        if "face" in detectors:
            res = detect("face")
            if res.face_landmarks:
                mesh = _array(res.face_landmarks[0])
                face = np.full((len(MEDIAPIPE_FACE_IDS), 3), np.nan)
                ids = np.array(MEDIAPIPE_FACE_IDS)
                ok = ids < len(mesh)  # iris points exist only in the 478-point mesh
                face[ok] = _to_internal(mesh[ids[ok]], w, h)
                obs.face = face
        if "pose" in detectors:
            res = detect("pose")
            if res.pose_landmarks:
                lms = res.pose_landmarks[0]
                ids = list(MEDIAPIPE_BODY_IDS)
                obs.body = _to_internal(_array([lms[i] for i in ids]), w, h)
                obs.body_visibility = np.array([lms[i].visibility or 0.0 for i in ids])
        if "hand" in detectors:
            res = detect("hand")
            # Side is assigned later from the pose wrists, which is more reliable
            # than MediaPipe's handedness label (it assumes a mirrored selfie image).
            obs.hands = [Hand(_to_internal(_array(lms), w, h)) for lms in res.hand_landmarks]
        return obs

    def _read_image(self, path: Path) -> tuple[MediaInfo, list[FrameObservation]]:
        import cv2

        bgr = cv2.imread(str(path))
        if bgr is None:
            raise ValueError(f"cannot read image {path}")
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        detectors = self._landmarkers(video=False)
        try:
            obs = self._observe(detectors, rgb, 0, 0.0, video=False)
        finally:
            for d in detectors.values():
                d.close()
        h, w = rgb.shape[:2]
        return MediaInfo(str(path), "image", 1.0, w, h, self.name), [obs]

    def _read_video(
        self, path: Path, sample_fps: float | None, max_seconds: float | None
    ) -> tuple[MediaInfo, list[FrameObservation]]:
        import cv2

        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            raise ValueError(f"cannot open video {path}")
        src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        step = max(1, int(round(src_fps / sample_fps))) if sample_fps else 1
        fps = src_fps / step
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        detectors = self._landmarkers(video=True)
        frames: list[FrameObservation] = []
        try:
            for i, rgb in _iter_frames(cap, step, cv2):
                t = i / src_fps
                if max_seconds is not None and t > max_seconds:
                    break
                frames.append(self._observe(detectors, rgb, i, t, video=True))
        finally:
            cap.release()
            for d in detectors.values():
                d.close()
        return MediaInfo(str(path), "video", fps, w, h, self.name), frames


def _iter_frames(cap: Any, step: int, cv2: Any) -> Iterator[tuple[int, np.ndarray]]:
    i = 0
    while True:
        ok = cap.grab()
        if not ok:
            return
        if i % step == 0:
            ok, bgr = cap.retrieve()
            if not ok:
                return
            yield i, cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        i += 1
