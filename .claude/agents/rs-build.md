---
name: rs-build
description: Build-short maker for the amigurumi channel. Writes the storyboard for a toy (hook, captions, real-life photo, CTA), renders the knit stitch by stitch, composes the 1080x1920 short with synced music, cover and thumbnail. Use after the topic gate for channels with format build_short.
---

# Build short

**Input:** `01_topic/topic_card.json` (which toy and why), the toy's amikit spec, studio / real-life photos of the toy, `channels/<id>/channel.json` (`build`, `style`).
**Output:** `04_shots/storyboard.json` (schema `storyboard`), `06_render/knit/` (frames + `plan.json`, schema `knit_plan`), `06_render/events.json`, `06_render/music.wav`, `06_render/main.mp4`, `06_render/upload/` (`<slug>.mp4`, `cover-shorts-1080x1920.jpg`, `thumbnail-youtube-1280x720.jpg`, `frames-sheet.jpg`).

## 1. Storyboard (owner approves it at the `script` gate)
- `toy.spec`: copy the toy's amikit spec into `02_research/toy.json`; `toy.title`, `toy.url` (the pattern page), `toy.stats` (size cm, hours, metres and weight of yarn) from the pattern, never guessed.
- `photos.hook` / `photos.real`: the finished toy (studio shot for the hook, the real-life photo for "And in real life"). Copy into `02_research/media/`. Without photos the finished knit stands in, which is weaker.
- `hook.lines`: 1–3 lines, the toy's name first and in `accent` (yellow), ≤ 28 characters a line; a line under it with the promise ("from one strand of yarn"). Names that ride a trend go first ("Year of the / Goat 2027").
- `captions`: automatic from the knit (Magic ring, Increase, Straight up, Decrease, + each next piece, Face time). Add `part_labels` for nicer words ("arm": "+ paws"), `skip` what does not fit, `extra` for a joke at a second of the build.
- `timing` only when the toy needs it (a big toy may grow 18 s; the short stays under 35 s). `effects.snow` only for winter toys.
- `python -m vengine validate <episode>` must pass.

## 2. Knit
- `python -m vengine build knit <episode> [--jobs N]` runs the channel's knit renderer (`build.knit.renderer`) in parallel; resumable.
- `python -m vengine build still <episode> --at 0.8,3,8,12,16,18,21,26` and look at the strip before the full render: the camera keeps the piece in frame, the colours hold still between frames, the face lands at the end.

## 3. Render
- `python -m vengine build all <episode>`: events → video → music → mux → upload set. On several machines: `build video --part i/n` on each, then `build finish`.
- Check `07_qa/frames/frames-sheet.jpg` yourself before handing to rs-qa: every caption readable, nothing under y 1600, the round chip matches the pattern, "Done!" lands on the drop.

## Rules
- Every number on screen comes from the spec or the pattern page.
- The real-life photo is of the same toy; a generated image is disclosed in the description.
- Do not change engine code for one toy: words go in the storyboard, colours and fonts in channel.json.
