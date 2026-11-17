---
name: rs-voice
description: Voice and sound. Records the narration line by line with emotion directions, aligns words to time, builds music and SFX beds. Use after the shot list is ready.
---

# Voice and sound

**Input:** `03_script/script.json`, `04_shots/shotlist.json`, channel `voice` block.
**Output:** `05_voice/lines/<line>.wav`, `05_voice/voice.wav`, `05_voice/words.json` (schema `words`), `05_voice/music.wav`, `05_voice/sfx.json`.

## Steps
1. TTS per line (Gemini TTS, voice from the profile). Prompt = profile `base_direction` + the line's `emotion` and `delivery`. Existing tool: `/mnt/project-files/tools/gemini_tts_batch.py`.
2. Listen-check by numbers: clipped words, wrong stress on names and numbers, too fast (> profile wpm + 15 %). Re-take the line with a corrected direction; max 3 takes.
3. Assemble with the pauses from `delivery`; loudness to −16 LUFS for the voice stem.
4. Word timing: stable-ts or WhisperX on the owner's PC (HuggingFace is blocked in the cloud) → `words.json` with `line_id`.
5. Music: Lyria cues by tension level (`music_cues`), `music_bed.py`; ducking under the voice. SFX from the kit library at shot transitions and `sync_word` hits.
