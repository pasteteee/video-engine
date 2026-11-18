# Real Story voice tools (Gemini Batch API)

Used when live TTS quotas are spent. Plain line text only: any style prefix in the prompt gets read aloud.

1. `python tts_batch.py EPISODE MODEL` submits 2 takes per script line, prints the batch name.
2. `python batch_fetch.py BATCH_NAME TAKES_DIR` polls and writes `<line>_<a|b>.wav` (24 kHz mono).
3. `python pick_takes.py EPISODE TAKES_DIR` keeps the take with pace nearest 150 wpm, writes `05_voice/voice_qa.json`.
4. `python assemble_voice.py EPISODE` writes `05_voice/voice.wav` (−16 LUFS, 48 kHz) and `words.json`.

`GEMINI_API_KEY` comes from the environment; never commit it.

## Archival listening slots (Kokoro episodes)

`python assemble_voice_records.py EPISODE` places Kokoro line WAVs (0.25 s gaps, +0.45 s at chapter changes) and, for every
script line with `sound_after: {media_id, seconds, from_s}`, leaves a slot of 0.35 s + clip + 0.35 s. It writes
`voice.wav` (narration stem only, −16 LUFS), `voice_with_records.wav` (preview), `words.json` with `sounds[]`
(`media_id, at, from_s, dur, gain`) for the renderer to play the record itself, and `cues.json` archive spans so
`music_bed.py` is silent under every record.

## Episode kit (`kit/episode/`, `kit/Extra.tsx`)

Reference copies of the renderer used for S1E02 Bloop (Kokoro rebuild): `Episode.tsx` plays `words.sounds` through
`<Audio startFrom volume=gain>`, counts chapters from unique chapter numbers, applies a slow push to diagrams and data plots
so no shot sits still for more than 4 s, and keeps the highlight dot in the episode accent. `Geo.tsx` takes globe and flat
map colours from `GROUND/GROUND2/TINT`. `Extra.tsx` adds Title, MapPin, GlobeRoute (night_side, terminator_line,
flat_unroll), MapPins (map_zoom with pins, map_compare_scale), StockBroll, DataPlotReal (line_draw, scope_trace),
EvidenceBoard, ScaleStack (scale_compare stack_up) and DayCounter (counter_ticker flip_digits).
