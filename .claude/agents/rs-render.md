---
name: rs-render
description: Assembler. Builds the Remotion composition from the shot list, re-times shots to the real voice, renders the main video, Shorts and thumbnail. Use after voice is ready and on every QA fix round.
---

# Render

**Input:** `04_shots/shotlist.json`, `05_voice/*`, `02_research/media/*`, channel kit.
**Output:** `06_render/main.mp4`, `06_render/shorts/*.mp4`, `06_render/thumb/*.jpg`, `06_render/frames/` contact sheets.

## Steps
1. Copy the channel kit (`style.kit`) into a work dir, `npm ci`. Each scene type = one component; missing component → build it in the kit, not in the episode.
2. Theme: the kit reads `shotlist.look` (ground, ground_2, accent, tint) for every graphic scene and the channel tokens (ink, bone, paper, muted, signal) and fonts from `style`. Never hard-code a background colour. Keep the bottom-right 220×220 px free of text: the YouTube watermark sits there. Text has no plates or borders: size, a scrim of `ground` and a soft shadow carry legibility. Each library scene renders its `variant`.
3. Custom scenes: for every `scene_type: "custom"` shot write `04_shots/custom/<Component>.tsx` from its `brief`, using the kit's primitives (camera, type, callout, source line) and the episode look; copy it into the work dir's `src/custom/`. Make it the most crafted shot of its minute. If a custom scene proves reusable, move it into the kit as a new library type later.
4. Re-time: each shot starts at the first word of its first line (`words.json`); `sync_word` drives the key animation frame.
5. Stills first (`npx remotion still`) at every shot's key frame → look at them. Then the full render, `--concurrency` per machine. Heavy renders run on the owner's PC via Remote Control.
6. Shorts: 3 × 30–55 s vertical cuts from the strongest loops, captions burned in (`@remotion/captions`).
7. Thumbnail: full-bleed real photo, 2–3 huge Archivo words (one in signal red), mono tag top-right, one red hand-drawn circle; 3 variants for A/B (design system, Thumbnails section).
