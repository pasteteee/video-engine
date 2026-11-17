---
name: rs-shorts
description: Shorts editor. Finds the episode's most clickable 15–55 s moments, writes a vertical-native plan (hook text, title, 9:16 layouts, captions, loop) and renders the Shorts at 1080x1920. Use after the main render passes QA, or when the owner asks for shorts.
---

# Shorts

**Input:** `03_script/script.json`, `04_shots/shotlist.json` (with `look`), `05_voice/words.json`, `05_voice/voice.wav`, media, channel kit.
**Output:** `06_render/shorts/candidates.json`, `06_render/shorts/shorts.json` (schema `shorts`), `06_render/shorts/<id>.mp4`, `06_render/shorts/<id>_cover.jpg`.

## 1. Pick the moments
- `python -m vengine shorts <episode> --n 3 --write` scores every window of lines: the first second (cold open, question, twist, a number), a payoff inside the window, density of numbers and hard words (first, never, wrong, only), custom scenes and real records on screen, length near 35 s, and a penalty for openings that need context ("And…", "Their…", "In the same…").
- Read the top 12, not only the 3 picked. Prefer windows a stranger understands with no episode. Ask: would I stop scrolling in the first second? Does it end on something I want to repeat or share?
- Never cut inside a line; voice audio is the episode take from `start_s` to `end_s`.

## 2. Make it bait, honestly
- `hook_text`: 1–6 words on screen from frame 0, before the voice. The sharpest true claim of the window ("THEY CAME BACK THE SAME DAY", "2 FEET FROM THE TARGET"). It may tease, it may not lie or claim what the sources do not support.
- `title`: ≤ 70 chars, the curiosity gap in plain words, no ALL CAPS, at most one emoji, no "you won't believe".
- `loop_end`: the last 0.5 s leads back into the first frame (same image, the question again, or a cut on the hook word), so replays feel seamless.
- The first cut by 1.2 s; then a cut every 1.5–4 s. A 40 s short has 12–20 shots.

## 3. Compose for 9:16 (never a landscape frame in a vertical box)
Every shot has a `layout` that starts with `v_`; `vengine shorts --check` rejects `letterbox`, `pillarbox`, `blur_fill` and anything not vertical-native.
- `v_photo_pan`: the 9:16 crop travels across the photo along `focus` points (tall photos tilt, wide photos pan across the subject); the detail fills the frame.
- `v_photo_stack`: two or three photos stacked top to bottom, each its own crop, cut in on the beat.
- `v_film_crop`: the film clip cropped to 9:16 on its subject, the crop follows the action.
- `v_type`: kinetic words / unredact stacked one or two words a line, 160–230 px, centred in the upper half.
- `v_number`: odometer number, full width.
- `v_quote`: Newsreader quote, words with the voice.
- `v_map`: the map re-projected for a tall frame (route runs top to bottom).
- `v_custom`: the episode's custom scene re-laid for 9:16 (the HUD readout under the target, the dial on top and the number below).
Safe zones: keep text out of the bottom 420 px (Shorts UI and captions) and the right 160 px (buttons); the top 220 px is the hook line.

## 4. Captions
Big word-by-word captions from `words.json`: Archivo wdth 75, 84 px, bone with a soft ground-colour shadow, the current word in `ep-accent`, 1–3 words at a time, centred at y≈1260. No boxes behind them (channel rule).

## 5. Render and check
- Kit composition `Short` (props: the short id) in `style.kit`; render `npx remotion render src/index.ts Short-<id> 06_render/shorts/<id>.mp4`, loudness −14 LUFS.
- Check stills at 0.0 s, the first cut and the last frame: hook readable on a phone at arm's length, nothing under the UI zones, no letterbox bars.
- Cover frame `<id>_cover.jpg`: the hook frame.
- Report to rs-publisher: title, description (one line + link to the full episode), the timestamps used.

## Type on a vertical frame
- One text layer at a time. Picture shots carry a bottom-left block: mono kicker (what we see) over the spoken phrase, built word by word. Type, number, quote, doc and custom shots carry their own words; captions step aside there.
- One left edge (x 80) for hook, kicker, captions and type scenes. Type is fitted to the 900 px column, never centred in empty space.
- Captions break on phrases (≤ 22 chars, ≤ 4 words), never end on a weak word (the, of, in, and, was...), no karaoke colour.
- The hook owns the first two seconds: balanced lines, stop block glued to the last word; a big number on the first shot waits until the hook leaves.
