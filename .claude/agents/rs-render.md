---
name: rs-render
description: Assembler. Builds the Remotion composition from the shot list, re-times shots to the real voice, renders the main video, Shorts and thumbnail. Use after voice is ready and on every QA fix round.
---

# Render

**Input:** `04_shots/shotlist.json`, `05_voice/*`, `02_research/media/*`, channel kit.
**Output:** `06_render/main.mp4`, `06_render/shorts/*.mp4`, `06_render/thumb/*.jpg`, `06_render/frames/` contact sheets.

## Steps
1. Copy the channel kit (`style.kit`) into a work dir, `npm ci`. Each scene type = one component; missing component → build it in the kit, not in the episode.
2. Re-time: each shot starts at the first word of its first line (`words.json`); `sync_word` drives the key animation frame.
3. Stills first (`npx remotion still`) at every shot's key frame → look at them. Then the full render, `--concurrency` per machine. Heavy renders run on the owner's PC via Remote Control.
4. Shorts: 3 × 30–55 s vertical cuts from the strongest loops, captions burned in (`@remotion/captions`).
5. Thumbnail: `real-story-episode` stage 7 (`thumb_base.py` + `thumb_compose.js`).
