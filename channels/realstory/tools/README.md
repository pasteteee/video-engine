# Real Story voice tools (Gemini Batch API)

Used when live TTS quotas are spent. Plain line text only: any style prefix in the prompt gets read aloud.

1. `python tts_batch.py EPISODE MODEL` submits 2 takes per script line, prints the batch name.
2. `python batch_fetch.py BATCH_NAME TAKES_DIR` polls and writes `<line>_<a|b>.wav` (24 kHz mono).
3. `python pick_takes.py EPISODE TAKES_DIR` keeps the take with pace nearest 150 wpm, writes `05_voice/voice_qa.json`.
4. `python assemble_voice.py EPISODE` writes `05_voice/voice.wav` (−16 LUFS, 48 kHz) and `words.json`.

`GEMINI_API_KEY` comes from the environment; never commit it.

## Re-voicing an episode that already has a cut (Kokoro)
1. `python tts_kokoro.py EPISODE` (per-line wavs).
2. `python assemble_inserts.py EPISODE OLD_words.json MEDIA_DIR`: keeps the old gaps, re-inserts the real archive audio
   (`inserts` in the old words.json) at the new times, writes `voice.wav`, `words.json` and `05_voice/timemap.json`.
3. `python retime_from_map.py EPISODE OLD_shotlist.json [OLD_shorts.json]`: moves every shot and Short to the new voice.
