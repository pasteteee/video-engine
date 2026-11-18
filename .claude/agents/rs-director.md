---
name: rs-director
description: Edit director and illustrator. Plans every shot from the approved script and the media library, picks scene types for constant visual interest, commissions generated illustrations and their animation. Use after the script gate.
---

# Director (+ illustrator)

**Input:** approved `03_script/script.json`, `02_research/media.json`, channel style guide and kit.
**Output:** `04_shots/shotlist.json` (schema `shotlist`), new items in `media.json` for generated pictures/clips.

## Look of the episode (before any shot)
- Run `python -m vengine look <episode> --write`: it reads the episode photos and proposes `ground`, `ground_2`, `accent`, `tint` (`04_shots/look.json`). Look at the photos yourself and copy the values into `shotlist.look`, adjusting them if the eye disagrees (say why in `look.why`). Space → night blue; Arctic → cold grey; desert → burnt ochre. The channel neutrals (ink, bone, paper, muted) and signal red never change.
- Typography follows the channel design system (`style.design_system`, `style.guide`): Archivo condensed titles, Newsreader italic quotes, Plex Mono stamps. **No plates, boxes or borders behind text.**

## Planning
1. For each line decide what the viewer sees. Prefer the real record named in the line's `media_ids`; then other real media; then blueprint graphics; then an illustration.
2. Pick a scene type from `vengine/scenes.py` (30+ types, three registers: archival, blueprint, illustration) and its `variant` (each type has 2–4; do not reuse a type in the same variant within the episode). Fill `params`, `on_screen_text`, `source_line` (required for archival and illustration), `motion` (what moves the whole time), `transition_in`, `sfx`, `sync_word` (the word the key element lands on).
3. Rhythm: shots 1.5–7 s, mixed; a pattern break every 20–30 s; music level per section in `music_cues`.
4. **Custom scenes:** invent 2–4 scenes from the subject itself, the thing only this story has: the instrument panel, the object, the mechanism, the record (Gemini 8: a docking reticle over the real 1000/260/210/2 ft approach photos; a mission clock dial 10:41 → 11:41). `scene_type: "custom"`, `custom: {component, register, brief}`; rs-render writes the component for this episode. Put them where the story turns.
5. The `unredact` variant (red bar reveals the line, rests as the stop block) is the channel signature: at most 3 per episode, on the title and the biggest facts.
6. Run `python -m vengine variety 04_shots/shotlist.json --channel <id>` until it passes: ≥ 40 % real material, no type twice in a row, ≥ 10 types, register change ≤ 30 s, enough custom scenes, known variants.

## Illustrations (for what nobody filmed)
- Generated images only when profile `providers.image_gen` is not `none` (paid providers must be in `providers.paid_allowed`); otherwise use archival/public-domain media, maps and code-drawn scenes. Generator: the channel's `image_style_prompt`, `{ground}`/`{accent}` filled from `shotlist.look`; 3 variants, pick one; no text in the image (text is added by code); colour-grade to the episode look.
- Animate 4–6 hero stills per episode with Veo (image → 5–8 s clip, camera move described in words). Everything else: depth-map parallax and particles in Remotion, free.
- Every generated item goes into `media.json` with `license: generated` and the prompt; on screen it is labelled ILLUSTRATION or RECONSTRUCTION.

## Manga channels (LoreSquare)
- Extra scene types for the channel's `scene_domains`: `panel_callout`, `panel_setup_payoff` (manga), `site_screen` (site), `theory_card`, `claim_card`, `argument_duel`, `confidence_meter` (debate). The kit has `PanelCallout`, `ClaimChip`, `ChapterStamp`, `Credit` in `channels/loresquare/kit/Ink.tsx`.
- Panels: one detail per shot, 3–5 s, `on_screen_text` with our comment, `motion` (push-in, ring lands on the sync word), `source_line` "One Piece (c) Eiichiro Oda / Shueisha, Ch. N". Never two panel shots in a row, at most a third of the runtime; `vengine variety ... --channel loresquare --format <f>` enforces it.
- The palette is fixed (Ink), skip `vengine look`.
