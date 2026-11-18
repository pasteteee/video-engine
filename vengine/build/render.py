"""Build-short steps behind `python -m vengine build ...`.

    knit    run the knit renderer into 06_render/knit/ (frames + plan.json)
    still   a strip of composed frames at given seconds, for a quick look
    events  06_render/events.json: section times, captions, stitch ticks (what the music follows)
    video   06_render/video.mp4 (no sound); --part i/n renders a slice to 06_render/parts/ for parallel machines
    audio   06_render/music.wav from events.json
    finish  joins parts if any, muxes the sound into 06_render/main.mp4, writes the upload set and the frame sheet
    all     knit (if missing) → video → audio → finish
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

from ..episode import Episode
from . import audio, knit as K
from . import storyboard as SB
from .comp import Compositor

KNIT_DIR = "06_render/knit"
MATCH = "06_render/match.json"


def _load(ep: Episode):
    sb = json.loads(ep.path("04_shots/storyboard.json").read_text(encoding="utf-8"))
    ch = ep.channel or {}
    return sb, ch


def spec_path(ep: Episode, sb: dict) -> Path:
    p = Path(sb["toy"]["spec"])
    return p if p.is_absolute() else ep.folder / p


def photo_path(ep: Episode, sb: dict) -> Path | None:
    """The studio photo the knit dissolves into (photos.real, else photos.hook), if there is one."""
    ph = sb.get("photos", {})
    rel = ph.get("real") or ph.get("hook")
    if not rel:
        return None
    p = Path(rel)
    p = p if p.is_absolute() else ep.folder / p
    return p if p.exists() else None


def run_knit(ep: Episode, jobs: int | None = None, still: str | None = None) -> Path:
    sb, ch = _load(ep)
    b = ch.get("build", {})
    tm = SB.timing(sb, ch)
    ka = tm.knit_args()
    out = ep.path(KNIT_DIR if not still else "06_render/knit_still")
    view, rest = None, None
    photo = photo_path(ep, sb)
    if K.renderer(b["knit"]) == "yarn" and photo and b["knit"].get("match", True):
        # end the knit on the studio photo's angle, at rest just before the photo comes in
        view = K.match(b["knit"], spec_path(ep, sb), photo, ep.path(MATCH), ep.path("07_qa/frames/match.jpg"))
        rest = tm.grow + tm.done - 0.2
    # the episode may add renderer flags (storyboard `knit`: hook, ss, mblur ...) and render the knit smaller than
    # the short (`size`; the compositor scales the frames up)
    knit_cfg = dict(b["knit"])
    extra = dict(sb.get("knit") or {})
    size = extra.pop("size", None) or b.get("size", "1080x1920")
    if extra:
        r = K.renderer(knit_cfg)
        params = dict(knit_cfg.get("params") or {})
        if isinstance(params.get(r), dict) or any(isinstance(v, dict) for v in params.values()):
            params[r] = {**(params.get(r) or {}), **extra}
        else:
            params.update(extra)
        knit_cfg["params"] = params
    return K.run(knit_cfg, spec_path(ep, sb), out, ka["dur"], ka["reveal"], size, int(b.get("fps", 30)), jobs, still,
                 view, rest)


def compositor(ep: Episode) -> Compositor:
    sb, ch = _load(ep)
    b = ch.get("build", {})
    from .comp import DESIGN
    frames = K.KnitFrames(ep.path(KNIT_DIR), K.smooth_for(b.get("knit", {})), DESIGN, K.lift_of(b.get("knit", {})))
    return Compositor(ep.folder, sb, ch, frames)


def still(ep: Episode, times: list[float], out: Path | None = None) -> Path:
    c = compositor(ep)
    tw, th = c.out_size[0] // 3, c.out_size[1] // 3
    ims = [c.frame(int(round(t * c.fps))).resize((tw, th), Image.LANCZOS) for t in times]
    sh = Image.new("RGB", (tw * len(ims), th))
    for k, im in enumerate(ims):
        sh.paste(im, (tw * k, 0))
    out = out or ep.path("07_qa/frames/still.jpg")
    out.parent.mkdir(parents=True, exist_ok=True)
    sh.save(out, quality=88)
    return out


def write_events(ep: Episode) -> Path:
    c = compositor(ep)
    E = SB.events(c.knit.data, c.sb, c.tm, c.fps)
    p = ep.path("06_render/events.json")
    p.write_text(json.dumps(E, ensure_ascii=False), encoding="utf-8")
    return p


def _ffmpeg_writer(out: Path, W: int, H: int, fps: int):
    out.parent.mkdir(parents=True, exist_ok=True)
    return subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                             "-pix_fmt", "yuv420p", "-crf", "17", str(out)], stdin=subprocess.PIPE)


def video(ep: Episode, part: str | None = None) -> Path:
    c = compositor(ep)
    nf = c.nframes
    if part:
        i, n = (int(v) for v in part.split("/"))
        rng = range(nf * i // n, nf * (i + 1) // n)
        out = ep.path(f"06_render/parts/{i:02d}-of-{n:02d}.mp4")
    else:
        rng = range(nf)
        out = ep.path("06_render/video.mp4")
    p = _ffmpeg_writer(out, *c.out_size, c.fps)
    for k in rng:
        p.stdin.write(np.asarray(c.frame(k).convert("RGB")).tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError("ffmpeg failed")
    return out


def music(ep: Episode) -> Path:
    sb, ch = _load(ep)
    m = SB.resolve(sb, ch).get("music", {})
    ev = ep.path("06_render/events.json")
    if not ev.exists():
        write_events(ep)
    E = json.loads(ev.read_text(encoding="utf-8"))
    x = audio.render(E, bpm=float(m.get("bpm", 60.0 / E["BEAT"])), key=m.get("key", "F"), seed=int(m.get("seed", 1)))
    return audio.write_wav(ep.path("06_render/music.wav"), x)


def finish(ep: Episode) -> dict:
    sb, ch = _load(ep)
    slug = ep.state.get("slug", ep.folder.name)
    parts = sorted(ep.path("06_render/parts").glob("*.mp4")) if ep.path("06_render/parts").exists() else []
    vid = ep.path("06_render/video.mp4")
    if parts:
        lst = ep.path("06_render/parts/list.txt")
        lst.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
                        str(vid)], check=True)
    wav = ep.path("06_render/music.wav")
    if not wav.exists():
        music(ep)
    main = ep.path("06_render/main.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(vid), "-i", str(wav), "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(main)],
                   check=True)
    c = compositor(ep)
    up = ep.path("06_render/upload"); up.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(main, up / f"{slug}.mp4")
    c.shorts_cover().save(up / "cover-shorts-1080x1920.jpg", quality=92)
    c.thumbnail().save(up / "thumbnail-youtube-1280x720.jpg", quality=92)
    tm = c.tm
    times = [0.5, tm.t_grow + 0.3] + [tm.t_grow + tm.grow * k / 7 for k in range(1, 7)] + \
            [tm.t_done + 0.6, tm.t_done + tm.done * 0.8, tm.t_real + 0.6, tm.t_real + tm.real * 0.8,
             tm.t_cta + 0.4, tm.t_cta + 1.5, tm.t_cta + tm.cta * 0.6, tm.t_end - 0.2]
    sheet = ep.path("07_qa/frames/frames-sheet.jpg"); sheet.parent.mkdir(parents=True, exist_ok=True)
    c.sheet(times, cols=8).save(sheet, quality=85)
    shutil.copyfile(sheet, up / "frames-sheet.jpg")
    return {"main": str(main), "upload": str(up), "sheet": str(sheet), "duration_s": tm.t_end}


def run_all(ep: Episode, jobs: int | None = None) -> dict:
    if K.check(ep.path(KNIT_DIR)):
        run_knit(ep, jobs)
    write_events(ep)
    video(ep)
    music(ep)
    return finish(ep)
