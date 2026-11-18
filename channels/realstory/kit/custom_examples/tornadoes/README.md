# S1E04 Tornadoes: custom scenes and Episode.tsx changes

Data scenes over the NOAA SPC tornado database (1950–2022). Data files (tracks.json, geo.json, stats.json, days.json) go in `public/data/`; `tdata.ts` loads them.

- `TrackMap`: every track on one map. Modes: grow, rating, decades, regions, place. Camera `cam`, `zoom`, `bare` (no text, used for the thumbnail).
- `YearBars` (all, split, jump, strong), `DayStrips`, `DamageRuler` (scale, elreno), `DeathShift`, `RadarSweep`.
- `TornadoV.tsx`: `VTrackMap` for Shorts.

`Episode.tsx` here is the Apollo 12 base with these improvements, worth folding into the shared base:
- Chapter list read from `ep/chapters.json` instead of hard-coded.
- `film_clip` takes `zoom` and `snd` (unmute the clip's own sound).
- `counter_ticker` has a `count` mode (`decimals`, `unit`) for plain counts, not only mission time.
- `timeline_scroll` never pans the first event off screen, and when it fits it drifts 60 px so it is never a static hold over 4 s.
- Signal red is kept for the stop block only: timeline highlight and map pins use the episode accent.

`Short.tsx` (kit root): the bottom shade now starts at 45 % so captions over bright sky stay above 4.5 contrast.
