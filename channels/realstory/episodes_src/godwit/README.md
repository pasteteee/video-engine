# S1E03 Godwit (Kokoro rebuild) — episode source

The project-folder copy of the v4 contracts was empty (storage full), so the episode contracts and renderer live here.
- `Godwit.tsx` — data-driven episode renderer (scene types: film_clip, stock_broll, film_freeze_annotate, photo_parallax, photo_detail_zoom, photo_lighttable, photo_compare, satellite_reveal, kinetic_type, chapter_card, question_card, big_number, counter_ticker, chart_bar_race, diagram_build, timeline_scroll, split_screen, globe_route, map_zoom, map_compare_scale + customs TagPing, WindBelts, TurnWind). Globe/maps use the episode palette instead of the kit's fixed navy.
- `plan.py` + `build_shots.py` — shot plan per script line, re-timed from `05_voice/words.json`.
- `build_shorts.py` — vertical plans for the kit `Short.tsx`; `../../kit/custom_examples/GodwitV.tsx` holds the 9:16 customs.
- `srt.py` — subtitles from line/word timings.
Media are public domain (USGS, USFWS, NASA); see media.json.
