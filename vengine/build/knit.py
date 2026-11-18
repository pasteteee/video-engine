"""The knit hook: run the channel's knit renderer and read what it wrote.

Contract (schema `knit_plan`): the renderer writes OUTDIR/0000.png, 0001.png … (one per plan entry, the size of
the short) and OUTDIR/plan.json. The compositor never cares which renderer made them, so a better yarn renderer
plugs in by changing `build.knit.renderer` in channel.json:

    "auto"        "yarn" when vengine/yarn is in this checkout, else "crochetsim" (the default)
    "crochetsim"  vengine/build/knit_crochetsim.py (the yg4 code of the goat short; stopgap)
    "yarn"        `python -m vengine yarn grow SPEC OUT --size --dur --reveal --frames a:b` (the new yarn package:
                  flicker-free, motion blur; flags --ss --mblur --core go in build.knit.params.yarn)
    "command"     any argv in build.knit.command with {spec} {out} {dur} {reveal} {size} {a} {b} {i} {n}

Each runs as N parallel processes over frame ranges; existing frames are skipped, so a render can be resumed.

The yarn renderer can end on the studio photo's angle: `view` is a match.json of `vengine yarn match` (azimuth,
elevation, lens and the photo's backdrop colours) and `rest` the knit second when the final turn stops, so the
compositor can dissolve the still last frame into the photo (comp.py).  The backdrop colours are passed through the
inverse of the montage `lift`, so the knit backdrop reaches the screen in the photo's colour.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from .. import contracts


def renderer(knit_cfg: dict) -> str:
    """'auto' = the yarn package when it is installed in this checkout, else the crochetsim stopgap."""
    r = knit_cfg.get("renderer", "auto")
    if r == "auto":
        import importlib.util
        r = "yarn" if importlib.util.find_spec("vengine.yarn") is not None else "crochetsim"
    return r


def smooth_for(knit_cfg: dict):
    """Temporal blend of neighbour frames: a list, or a map renderer -> list. The yarn renderer removes flicker
    itself (and adds motion blur), so it gets none by default."""
    sm = knit_cfg.get("smooth", {})
    if isinstance(sm, dict):
        sm = sm.get(renderer(knit_cfg), [0.0, 1.0, 0.0])
    return sm


LIFT = 1.3


def lift_of(knit_cfg: dict) -> float:
    """The montage's tone lift of the knit frames (`build.knit.lift`, 1 = none)."""
    return float(knit_cfg.get("lift", LIFT))


def unlift_hex(rgb, lift: float) -> str:
    """The hex colour that `KnitFrames.frame` lifts to `rgb` (sRGB 0..1)."""
    v = [1 - (1 - min(1.0, max(0.0, float(c)))) ** (1 / lift) for c in rgb]
    return "#" + "".join(f"{round(c * 255):02x}" for c in v)


def _nframes(dur: float, reveal: float, fps: int) -> int:
    return int(round((dur + reveal) * fps))


def commands(knit_cfg: dict, spec: Path, out: Path, dur: float, reveal: float, size: str, fps: int, n: int,
             still: str | None = None, view: Path | None = None, rest: float | None = None) -> list[list[str]]:
    r = renderer(knit_cfg)
    params = knit_cfg.get("params", {})
    if isinstance(params.get(r), dict) or any(isinstance(v, dict) for v in params.values()):
        params = params.get(r, {})
    nf = _nframes(dur, reveal, fps)
    cmds = []
    for i in range(n):
        a, b = nf * i // n, nf * (i + 1) // n
        if r == "crochetsim":
            cmd = [sys.executable, "-m", "vengine.build.knit_crochetsim", str(spec), str(out), f"{i}/{n}",
                   "--dur", str(dur), "--reveal", str(reveal), "--size", size]
            src = os.environ.get("CROCHETSIM_SRC") or knit_cfg.get("src")
            if src:
                cmd += ["--src", src]
            for k, v in params.items():
                cmd += [f"--{k.replace('_', '-')}", str(v)]
            if still:
                cmd += ["--still", still]
        elif r == "yarn":
            cmd = [sys.executable, "-m", "vengine", "yarn", "grow", str(spec), str(out), "--size", size,
                   "--dur", str(dur), "--reveal", str(reveal)]
            for k, v in params.items():
                cmd += [f"--{k.replace('_', '-')}", str(v)]
            if view:
                cmd += ["--view", str(view)]
                m = json.loads(Path(view).read_text(encoding="utf-8"))
                if m.get("bg_top") and m.get("bg_bot") and "bg" not in params:
                    lf = lift_of(knit_cfg)
                    cmd += ["--bg", f"{unlift_hex(m['bg_top'], lf)},{unlift_hex(m['bg_bot'], lf)}"]
            if rest is not None:
                cmd += ["--rest", str(round(rest, 3))]
            cmd += ["--still", still] if still else ["--frames", f"{a}:{b}"]
        elif r == "command":
            fill = dict(spec=spec, out=out, dur=dur, reveal=reveal, size=size, a=a, b=b, i=i, n=n)
            cmd = [str(x).format(**fill) for x in knit_cfg["command"]]
        else:
            raise ValueError(f"unknown knit renderer '{r}'")
        cmds.append(cmd)
        if still:
            break
    return cmds


def run(knit_cfg: dict, spec: Path, out: Path, dur: float, reveal: float, size: str = "1080x1920", fps: int = 30,
        jobs: int | None = None, still: str | None = None, view: Path | None = None, rest: float | None = None) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    n = 1 if still else max(1, jobs or os.cpu_count() or 1)
    env = dict(os.environ)
    if knit_cfg.get("amikit") and "AMIKIT" not in env:
        env["AMIKIT"] = knit_cfg["amikit"]
    root = str(Path(__file__).resolve().parents[2])
    env["PYTHONPATH"] = root + os.pathsep + env.get("PYTHONPATH", "")
    procs = [subprocess.Popen(c, env=env) for c in commands(knit_cfg, spec, out, dur, reveal, size, fps, n, still,
                                                             view, rest)]
    bad = [p.args for p in procs if p.wait() != 0]
    if bad:
        raise RuntimeError(f"knit renderer failed: {bad[0]}")
    return out


def match(knit_cfg: dict, spec: Path, photo: Path, out: Path, sheet: Path | None = None) -> Path:
    """`vengine yarn match` once per episode: the studio photo's angle for the final view (cached in `out`)."""
    if out.exists():
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    if knit_cfg.get("amikit") and "AMIKIT" not in env:
        env["AMIKIT"] = knit_cfg["amikit"]
    root = str(Path(__file__).resolve().parents[2])
    env["PYTHONPATH"] = root + os.pathsep + env.get("PYTHONPATH", "")
    cmd = [sys.executable, "-m", "vengine", "yarn", "match", str(spec), str(photo), "--out", str(out)]
    if sheet:
        sheet.parent.mkdir(parents=True, exist_ok=True)
        cmd += ["--sheet", str(sheet)]
    subprocess.run(cmd, env=env, check=True, stdout=subprocess.DEVNULL)
    return out


def check(out: Path, schema: bool = True) -> list[dict]:
    p = out / "plan.json"
    if not p.exists():
        return [{"level": "error", "file": "knit_plan", "msg": f"{p} missing"}]
    plan = json.loads(p.read_text(encoding="utf-8"))
    probs = contracts.validate_obj("knit_plan", plan, "knit_plan") if schema else []
    pat = plan.get("frames", "%04d.png")
    missing = [k for k in range(len(plan.get("plan", []))) if not (out / (pat % k)).exists()]
    if missing:
        probs.append({"level": "error", "file": "knit_plan",
                      "msg": f"{len(missing)} knit frames missing (first {missing[0]})"})
    return probs


class KnitFrames:
    """Frames of a finished knit render, with the optional temporal blend of neighbours (`build.knit.smooth`)."""

    def __init__(self, folder: Path, smooth=(0.0, 1.0, 0.0), size: tuple[int, int] | None = None, lift: float = LIFT):
        self.folder = Path(folder)
        self.data = json.loads((self.folder / "plan.json").read_text(encoding="utf-8"))
        self.plan, self.pieces = self.data["plan"], self.data["pieces"]
        self.pat = self.data.get("frames", "%04d.png")
        self.smooth = [float(x) for x in smooth]
        self.size = size
        self.lift = float(lift)
        self.final = self.data.get("final") or {}
        self._cache: dict[int, np.ndarray] = {}

    def __len__(self):
        return len(self.plan)

    def raw(self, k: int) -> np.ndarray:
        k = max(0, min(len(self.plan) - 1, k))
        if k not in self._cache:
            if len(self._cache) > 8:
                self._cache.pop(next(iter(self._cache)))
            im = Image.open(self.folder / (self.pat % k)).convert("RGB")
            if self.size and im.size != self.size:
                im = im.resize(self.size, Image.LANCZOS)
            self._cache[k] = np.asarray(im, np.float32)
        return self._cache[k]

    def frame(self, k: int, lift: float | None = None) -> Image.Image:
        lift = self.lift if lift is None else lift
        a, b, c = self.smooth
        x = b * self.raw(k)
        if a:
            x = x + a * self.raw(k - 1)
        if c:
            x = x + c * self.raw(k + 1)
        x = np.clip(x / max(1e-6, a + b + c), 0, 255) / 255.0
        if lift != 1.0:
            x = 1 - (1 - x) ** lift          # lift the yarn: ivory reads white, no grey
        return Image.fromarray((x * 255).astype(np.uint8))
