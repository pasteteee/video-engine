# LoreSquare channel: style "Ink"

Chosen by the owner on 2026-11-15 for the theory Shorts. Reference frames: the six
Shorts in `/mnt/project-files/shorts/series/<slug>/` (8 key frames each, EN and RU)
and their generator in `/mnt/project-files/shorts/series/source/`.

## Look (Shorts, 1080x1920, updated 2026-11-18)
All four formats are vertical Shorts. Kit: `channels/loresquare/kit/` (Remotion,
`LoreShort` composition, one component per scene type in `scenes.tsx`).

- **Type.** Slams in Dela Gothic One (also covers katakana), UI and captions in
  Inter 900, labels in JetBrains Mono 700. Load all three from `public/fonts/fonts.css`
  before the first frame (`useFonts` in `Short.tsx`).
- **Slam words.** 1-3 lines, each lands with a spring (scale 2.6 -> 1), slight
  rotation, 10 px ink stroke and an 8 px hard shadow; the key word sits on a yellow
  slab. Every landing shakes the camera and gets a hit sfx.
- **Art under type** (`art_backdrop`). Official art only: volume covers, chapter
  title pages and colour spreads (One Piece Wiki CDN, credited). Variants:
  `ken_burns`, `halftone_duotone` (grayscale + tint + dots), `speed_burst` (zoom punch
  + radial speed lines + flash), `parallax_cut` (diagonal slab slides over the art).
  Small images become a framed card over their own blurred fill. Always carries
  on-screen text, 6 s max, no share cap.
- **Katakana SFX.** ドン for a hit, ゴゴゴ for menace: huge outlined yellow glyphs
  behind the slam, one per shot at most.
- **Raw manga panels** (`panel_callout`). Tilted white-bordered card, zoom into the
  detail, red ring or box draws in, yellow note chip. 3-5 s, never two in a row,
  at most a third of the runtime.
- **Claim chip.** Above the captions on every shot whose line has a claim:
  CANON green `#2f9e44` (+ chapters), INFERENCE `#f0b400`, THEORY `#e64980`,
  COMMUNITY `#1f6feb`.
- **Captions.** Word by word from whisper-aligned timings, 3 words max per chunk,
  Inter 900 uppercase 78 px at y 1250, active word yellow. Nothing important below
  y 1500 (Shorts UI).
- **Site screens.** Real screenshots inside a phone frame over blurred art; scroll,
  device rise or cursor click; a yellow highlight chip names what to look at.
- **Chrome.** Red progress bar on top, LORESQUARE mark top-left, the credit line
  `One Piece © Eiichiro Oda / Shueisha · CH. N / VOL. N` under it on every frame.

## Formats on screen
| Format | Frames |
|---|---|
| top_theories | countdown cards (big number), art slams with author tag, claim stamp, FOR/VS/AGAINST duel, confidence meter, crown for No. 1, vote card |
| chapter_breakdown | question card, art slams, panel callouts, setup/payoff, claim cards, prediction |
| chapter_moments | panel callouts + art slams, "watch for" stamp |
| site_promo | phone screens (40%+ of runtime) between art slams, PromoEnd card |

## Sound
Voice ducks a quiet bgm (sidechain); whoosh on every cut, hits on slam landings,
paper + stamp on claim cards, shutter on panels, swipe on screens; loudnorm -14 LUFS.
`kit/tools/mix.py`.

## Fan art
Not used by default. Only with the artist's credit and written permission, stored
in `media.json` (`license`, `credit`, `source_url`).

## Thumbnail
Own graphics: one slam word (2-4 words max) + one stamp + a duotone crop.
No bare panel, no main twist of a fresh chapter.

## Voice
Kokoro `am_michael` (EN); Silero `eugene` for RU versions. One direction for all
lines (see channel.json `voice`). Transcribe the result and re-record wrong names.
