# amigurumi.ai Shorts: brand book

A 30 s vertical short: the toy is crocheted stitch by stitch from one strand of yarn, faster and faster, then the
finished toy in real life and the free pattern. No narration; music and stitch ticks come from the same plan as the
picture, so every caption lands on a beat.

## The cut (default timing, `build.timing` in channel.json, overridable per short in `storyboard.json`)

| s | Section | What is on screen |
|---|---|---|
| 0–2 | hook | studio photo of the finished toy, slow push-in, the toy's name in yellow word by word on the beat |
| 2–17 | grow | the knit: magic ring → increases → straight → decreases → each next piece; captions at the moments, a round chip ("Rnd 5: (3 sc, inc) x 6 (30)") for the first piece, then a stitch counter; speed chip x10…x1000 |
| 17–20 | done | "Done!", the camera turns the finished knit, "16 pieces. 3,398 stitches." |
| 20–24 | real | the real-life photo, "And in real life", stats chip (size · hours · yarn) |
| 24–30 | cta | the toy in a circle, "Free pattern + 3D model", navy button amigurumi.ai, PDF chip |

## Look
- Ground: warm cream gradient (GROUND_TOP → GROUND_BOTTOM); the knit renders on the same cream.
- Text: Unbounded Bold, cream fill, navy stroke 11% of the size, soft navy shadow. Words pop in with a small overshoot.
- Accent: yellow (#ffd23f) for names and the finish; pink (#f4a9c0) only for the speed chip at x300 and above.
- Progress bar: thin white rail near the top, yellow fill = share of all stitches made.
- Seasonal: `effects.snow` in the storyboard for winter toys only.
- Phone-safe area: captions at y 330–620 and 1380–1530; nothing under y 1600 (Shorts buttons and title).

## Upload set (06_render/upload/)
`<slug>.mp4` 1080x1920, `cover-shorts-1080x1920.jpg` (the hook frame), `thumbnail-youtube-1280x720.jpg`
(name left in big type, toy photo right, "Free crochet pattern" pill), `frames-sheet.jpg` for QA.
