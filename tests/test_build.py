"""Build shorts (amigurumi channel): format, contracts, captions from the knit plan, compositor and music."""
import json
import shutil

import numpy as np
import pytest
from PIL import Image

from vengine import contracts
from vengine.build import audio, knit as K, storyboard as SB
from vengine.build.comp import Compositor
from vengine.cli import main
from vengine.episode import Episode, load_channel

CH = load_channel("amigurumi")
FPS = 30


def fake_knit(folder, size=(108, 192), dur=4.0, reveal=1.5):
    """A knit render without crochetsim: body (inc, straight, dec), head, two arms, then the face."""
    pieces = [dict(name="body", part="body", start=0, end=600, counts=[6, 12, 18, 24, 24, 24, 18, 12]),
              dict(name="head", part="head", start=600, end=1000, counts=[6, 12, 18, 18, 12, 6]),
              dict(name="arm_L", part="arm", start=1000, end=1100, counts=[6, 6, 6]),
              dict(name="arm_R", part="arm", start=1100, end=1200, counts=[6, 6, 6]),
              dict(name="ear_L", part="ear", start=1200, end=1260, counts=[6, 9]),
              dict(name="ear_R", part="ear", start=1260, end=1320, counts=[6, 9])]
    NY = pieces[-1]["end"]
    plan = []
    nf = int(round((dur + reveal) * FPS))
    for i in range(nf):
        t = i / FPS
        x = t / dur
        s = min(1.0, 0.06 * x + 0.94 * x ** 2.2) if x < 0.94 else 1.0
        n = int(s * NY)
        pi = next((k for k, p in enumerate(pieces) if n < p["end"]), len(pieces) - 1)
        p = pieces[pi]
        q = (n - p["start"]) / (p["end"] - p["start"]) * sum(p["counts"])
        cum = np.concatenate([[0], np.cumsum(p["counts"])])
        rnd = int(np.clip(np.searchsorted(cum, q, side="right"), 1, len(p["counts"])))
        plan.append(dict(t=t, n=n, piece=p["part"], name=p["name"], pi=pi, round=rnd, rounds=len(p["counts"]), st=q,
                         count=p["counts"][rnd - 1], face=min(1.0, max(0.0, (x - 0.88) / 0.1)), s=s))
    folder.mkdir(parents=True, exist_ok=True)
    for i in range(nf):
        v = int(120 + 120 * plan[i]["s"])
        Image.new("RGB", size, (v, 200, 230)).save(folder / f"{i:04d}.png")
    data = dict(renderer="fake", fps=FPS, size=list(size), dur=dur, reveal=reveal, plan=plan, pieces=pieces)
    (folder / "plan.json").write_text(json.dumps(data), encoding="utf-8")
    return data


SB_MIN = {"toy": {"spec": "02_research/toy.json", "title": "Little bear", "stats": {"size_cm": 9, "hours": 2, "yarn_m": 40, "yarn_weight": "DK"}},
          "hook": {"lines": [{"text": "Little bear", "size": 120, "accent": True}, {"text": "from one strand of yarn", "size": 54}]},
          "timing": {"hook": 1.0, "grow": 3.76, "done": 1.0, "real": 0.6, "cta": 1.2},
          "captions": {"part_labels": {"arm": "+ paws"}}}


def make_ep(tmp_path):
    ep = Episode.init(tmp_path / "bear", "amigurumi", "bear", "build_short")
    (ep.folder / "02_research/toy.json").write_text("{}", encoding="utf-8")
    (ep.folder / "04_shots/storyboard.json").write_text(json.dumps(SB_MIN), encoding="utf-8")
    knit = fake_knit(ep.folder / "06_render/knit")
    return ep, knit


def small_channel():
    ch = json.loads(json.dumps(CH))
    ch["build"]["size"] = "108x192"
    return ch


def test_channel_profile_is_valid_and_build_format():
    assert not contracts.validate_obj("channel", CH)
    assert CH["format"] == "build_short"
    bad = {k: v for k, v in CH.items() if k != "build"}
    assert contracts.validate_obj("channel", bad), "build_short channel without build must fail"
    rs = load_channel("realstory")
    assert not contracts.validate_obj("channel", rs)
    assert contracts.validate_obj("channel", {k: v for k, v in rs.items() if k != "voice"})


def test_build_episode_stages(tmp_path):
    ep, _ = make_ep(tmp_path)
    assert [s.key for s in ep.stages] == ["topic", "storyboard", "knit", "render", "qa", "publish"]
    st = ep.status()
    assert st["next"] == "topic"
    (ep.folder / "01_topic/topic_card.json").write_text("{}", encoding="utf-8")
    ep.approve("topic")
    st = ep.status()
    assert st["waiting_for_owner"] == "script"            # the storyboard is approved at the script gate
    ep.approve("script")
    assert ep.status()["next"] == "render"                 # knit plan exists already


def test_validate_build_episode(tmp_path):
    ep, _ = make_ep(tmp_path)
    probs = contracts.validate_episode(ep, ep.channel)
    assert not [p for p in probs if p["level"] == "error"], probs
    assert not K.check(ep.folder / "06_render/knit")
    sb = dict(SB_MIN, toy=dict(SB_MIN["toy"], spec="missing.json"), photos={"hook": "nope.jpg"})
    (ep.folder / "04_shots/storyboard.json").write_text(json.dumps(sb), encoding="utf-8")
    msgs = " ".join(p["msg"] for p in contracts.validate_episode(ep, ep.channel))
    assert "missing.json not found" in msgs and "photos.hook" in msgs


def test_knit_too_short_for_storyboard(tmp_path):
    ep, _ = make_ep(tmp_path)
    sb = dict(SB_MIN, timing=dict(SB_MIN["timing"], grow=12))
    (ep.folder / "04_shots/storyboard.json").write_text(json.dumps(sb), encoding="utf-8")
    assert any("re-run" in p["msg"] for p in contracts.validate_episode(ep, ep.channel))


@pytest.mark.parametrize("counts,k,text", [
    ([6, 12, 18], 0, "6 sc in a magic ring"), ([6, 12], 1, "inc in every st"), ([6, 12, 18], 2, "(1 sc, inc) x 6"),
    ([24, 30], 1, "(3 sc, inc) x 6"), ([54, 54], 1, "sc around"), ([54, 48], 1, "(7 sc, dec) x 6"),
    ([12, 6], 1, "dec all around"), ([10, 13], 1, "3 inc evenly (13)")])
def test_round_text(counts, k, text):
    assert SB.round_text(counts, k) == text


def test_captions_follow_the_knit(tmp_path):
    knit = fake_knit(tmp_path / "k")
    tm = SB.timing(SB_MIN, CH)
    caps = SB.captions(knit, SB_MIN, tm)
    texts = [c[1] for c in caps]
    assert texts[0] == "Magic ring" and caps[0][0] == tm.t_grow
    assert "Increase" in texts and "Straight up" in texts and "+ head" in texts
    sb = dict(SB_MIN, captions={"part_labels": {"head": "+ big head"}, "skip": ["Straight up"], "extra": [[0.2, "Go!"]]})
    texts = [c[1] for c in SB.captions(knit, sb, tm)]
    assert "+ big head" in texts and "Straight up" not in texts and "Go!" not in texts   # Go! is too close to the start
    # small pieces worked together share one caption
    late = dict(knit, plan=[dict(f, t=f["t"] * 0.5) if f["piece"] in ("arm", "ear") else f for f in knit["plan"]])
    assert any("&" in c[1] for c in SB.captions(late, SB_MIN, SB.timing(dict(SB_MIN, timing={"grow": 9}), CH)))
    times = [c[0] for c in caps]
    assert times == sorted(times) and all(b - a >= SB.MIN_CAPTION_GAP for a, b in zip(times, times[1:]))
    assert all(t < tm.breath for t in times)


def test_events_ticks_and_sections(tmp_path):
    knit = fake_knit(tmp_path / "k")
    tm = SB.timing(SB_MIN, CH)
    E = SB.events(knit, SB_MIN, tm)
    assert E["T_END"] == pytest.approx(tm.t_end) and E["T_DONE"] == pytest.approx(tm.t_done)
    assert E["ticks"] and all(tm.t_grow <= t < tm.breath for t, _, _ in E["ticks"])
    assert [t for t, _, _ in E["ticks"]] == sorted(t for t, _, _ in E["ticks"])
    assert len(E["hook_words"]) == 2


def test_knit_args_finish_yarn_on_done():
    tm = SB.Timing(2, 15, 3, 4, 6)
    ka = tm.knit_args()
    assert ka["dur"] * SB.YARN_DONE_AT == pytest.approx(15, abs=0.01)
    assert ka["reveal"] >= tm.done


def test_compositor_sections_and_stills(tmp_path):
    ep, knit = make_ep(tmp_path)
    ch = small_channel()
    frames = K.KnitFrames(ep.folder / "06_render/knit", K.smooth_for(CH["build"]["knit"]), (1080, 1920))
    c = Compositor(ep.folder, SB_MIN, ch, frames)
    assert c.nframes == int(round(c.tm.t_end * FPS))
    for t in (0.3, c.tm.t_grow + 0.5, c.tm.t_done + 0.3, c.tm.t_real + 0.3, c.tm.t_cta + 0.9):
        im = c.frame(int(t * FPS))
        assert im.size == (108, 192) and im.mode == "RGB"
    assert c.thumbnail().size == (1280, 720)
    assert c.shorts_cover().size == (108, 192)


def test_knit_frames_smoothing(tmp_path):
    fake_knit(tmp_path / "k", size=(8, 8))
    f0 = K.KnitFrames(tmp_path / "k", (0, 1, 0))
    f1 = K.KnitFrames(tmp_path / "k", (0.15, 0.7, 0.15))
    a, b = np.asarray(f0.frame(40, lift=1.0), float), np.asarray(f1.frame(40, lift=1.0), float)
    assert np.abs(a - b).max() <= 3      # a smooth ramp barely changes; flicker would be averaged away


def test_knit_commands_for_each_renderer(tmp_path):
    spec, out = tmp_path / "s.json", tmp_path / "o"
    cs = K.commands({"renderer": "crochetsim", "src": "/x", "params": {"soft": 1.2}}, spec, out, 16, 3.5, "1080x1920", 30, 4)
    assert len(cs) == 4 and cs[1][3:6] == [str(spec), str(out), "1/4"] and "--src" in cs[0] and "--soft" in cs[0]
    ys = K.commands({"renderer": "yarn"}, spec, out, 16, 3.5, "1080x1920", 30, 2)
    assert ys[0][-1] == "0:292" and ys[1][-1] == "292:585" and ys[0][3:5] == ["yarn", "grow"]
    ys = K.commands({"renderer": "yarn", "params": {"yarn": {"mblur": 4}, "crochetsim": {"soft": 1}}}, spec, out, 1, 1, "1x1", 30, 1)
    assert "--mblur" in ys[0] and "--soft" not in ys[0]
    assert K.renderer({"renderer": "auto"}) in ("yarn", "crochetsim")
    assert K.smooth_for({"renderer": "yarn", "smooth": {"crochetsim": [0.2, 0.6, 0.2]}}) == [0.0, 1.0, 0.0]
    cm = K.commands({"renderer": "command", "command": ["r", "{spec}", "{out}", "{a}-{b}"]}, spec, out, 1, 1, "1x1", 30, 2)
    assert cm[1] == ["r", str(spec), str(out), "30-60"]
    view = tmp_path / "match.json"
    view.write_text(json.dumps({"az": 35, "el": 8, "fov": 18, "iou": 0.92, "bg_top": [0.95, 0.9, 0.84],
                                "bg_bot": [0.98, 0.94, 0.89]}))
    ys = K.commands({"renderer": "yarn"}, spec, out, 16, 3.5, "1080x1920", 30, 1, None, view, 17.8)
    c = ys[0]
    assert c[c.index("--view") + 1] == str(view) and c[c.index("--rest") + 1] == "17.8"
    top, bot = c[c.index("--bg") + 1].split(",")
    lifted = 1 - (1 - int(top[1:3], 16) / 255) ** K.LIFT                 # through the montage lift: the photo's colour
    assert lifted == pytest.approx(0.95, abs=0.006)


def _photo_like_knit(size, box):
    """An image with a red rounded toy in `box` on a cream backdrop (stands in for a knit frame or the photo)."""
    from PIL import ImageDraw
    im = Image.new("RGB", size, (246, 232, 217))
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = box
    d.ellipse((x0, y0 + (y1 - y0) * 0.35, x1, y1), fill=(190, 30, 34))
    d.ellipse((x0 + (x1 - x0) * 0.2, y0, x1 - (x1 - x0) * 0.2, y0 + (y1 - y0) * 0.55), fill=(180, 40, 40))
    a = np.asarray(im, np.int16)
    a = a + (np.random.default_rng(2).normal(0, 9, a.shape[:2])[..., None] * (a[..., 1:2] < 100))
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))


def test_matched_knit_dissolves_into_the_photo(tmp_path):
    """The real-life section opens on the knit frame and dissolves into the photo laid over it: no jump in position,
    size or backdrop colour from frame to frame."""
    ep, knit = make_ep(tmp_path)
    W, H = 216, 384
    box = (40, 120, 176, 270)
    kd = ep.folder / "06_render/knit"
    data = json.loads((kd / "plan.json").read_text())
    data["final"] = {"az": 35, "el": 8, "fov": 18, "matched": True, "box": list(box)}
    (kd / "plan.json").write_text(json.dumps(data))
    for i in range(len(data["plan"])):
        _photo_like_knit((W, H), box).save(kd / f"{i:04d}.png")
    _photo_like_knit((400, 400), (110, 60, 330, 300)).save(ep.folder / "02_research/photo.png")
    sb = dict(SB_MIN, photos={"hook": "02_research/photo.png", "real": "02_research/photo.png"},
              timing=dict(SB_MIN["timing"], real=2.0))
    ch = json.loads(json.dumps(CH))
    ch["build"]["size"] = f"{W}x{H}"
    c = Compositor(ep.folder, sb, ch, K.KnitFrames(kd, (0, 1, 0), (1080, 1920), lift=1.0))
    assert c.matched
    s, tx, ty, fit = c.placement()
    assert fit > 0.9 and s == pytest.approx(5 * 136 / 220, rel=0.06)       # knit frames are scaled 5x to the design
    k0 = int(round(c.tm.t_real * FPS))
    fr = [np.asarray(c.frame(k).resize((W, H)), float) for k in range(k0 - 2, k0 + int(0.7 * FPS))]
    steps = [np.abs(b - a).mean() for a, b in zip(fr, fr[1:])]
    assert max(steps) < 6                                                  # a dissolve, not a cut or a flash
    top = [f[: H // 10].reshape(-1, 3).mean(0) for f in fr]
    assert max(np.abs(b - a).max() for a, b in zip(top, top[1:])) < 4       # the backdrop colour glides


def test_music_render_short():
    E = {"T_GROW": 0.5, "T_DONE": 1.5, "BREATH": 1.25, "T_REAL": 2.0, "T_CTA": 2.5, "T_END": 3.0, "BEAT": 0.5,
         "caps": [[0.5, "Magic ring"]], "ticks": [[0.6, 0.1, 0], [1.0, 0.5, 1]], "button": 2.75, "hook_words": [0, 0.5]}
    x = audio.render(E)
    assert x.shape[1] == 2 and x.shape[0] == int((3.0 + 0.8) * audio.SR)
    assert 0.5 < np.abs(x).max() <= 0.9 and np.isfinite(x).all()


def test_cli_build_still_and_events(tmp_path, capsys, monkeypatch):
    ep, _ = make_ep(tmp_path)
    import vengine.build.render as R
    monkeypatch.setattr(Episode, "channel", property(lambda self: small_channel()))
    assert main(["build", "events", str(ep.folder)]) == 0
    E = json.loads((ep.folder / "06_render/events.json").read_text())
    assert E["caps"][0][1] == "Magic ring"
    assert main(["build", "still", str(ep.folder), "--at", "0.3,2,5"]) == 0
    assert (ep.folder / "07_qa/frames/still.jpg").exists()
    assert main(["build", "check", str(ep.folder)]) == 0


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_full_render_tiny(tmp_path, monkeypatch):
    ep, _ = make_ep(tmp_path)
    monkeypatch.setattr(Episode, "channel", property(lambda self: small_channel()))
    assert main(["build", "all", str(ep.folder)]) == 0
    up = ep.folder / "06_render/upload"
    assert (ep.folder / "06_render/main.mp4").stat().st_size > 0
    for f in ("bear.mp4", "cover-shorts-1080x1920.jpg", "thumbnail-youtube-1280x720.jpg", "frames-sheet.jpg"):
        assert (up / f).exists(), f
