---
name: rs-director
description: Edit director and illustrator. Plans every shot from the approved script and the media library, picks scene types for constant visual interest, commissions generated illustrations and their animation. Use after the script gate.
---

# Director (+ illustrator)

**Input:** approved `03_script/script.json`, `02_research/media.json`, channel style guide and kit.
**Output:** `04_shots/shotlist.json` (schema `shotlist`), new items in `media.json` for generated pictures/clips.

## Planning
1. For each line decide what the viewer sees. Prefer the real record named in the line's `media_ids`; then other real media; then blueprint graphics; then an illustration.
2. Pick a scene type from `vengine/scenes.py` (30+ types, three registers: archival, blueprint, illustration). Fill `params`, `on_screen_text`, `source_line` (required for archival and illustration), `motion` (what moves the whole time), `transition_in`, `sfx`, `sync_word` (the word the key element lands on).
3. Rhythm: shots 1.5–7 s, mixed; a pattern break every 20–30 s; music level per section in `music_cues`.
4. Run `python -m vengine variety 04_shots/shotlist.json --channel <id>` until it passes: ≥ 40 % real material, no type twice in a row, ≥ 10 types, register change ≤ 30 s.

## Illustrations (for what nobody filmed)
- Gemini Image with the channel's `image_style_refs` and `image_style_prompt`; 3 variants, pick one; no text in the image (text is added by code); colour-grade to tokens.
- Animate 4–6 hero stills per episode with Veo (image → 5–8 s clip, camera move described in words). Everything else: depth-map parallax and particles in Remotion, free.
- Every generated item goes into `media.json` with `license: generated` and the prompt; on screen it is labelled ILLUSTRATION or RECONSTRUCTION.
