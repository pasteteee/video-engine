# Feature bank: the ~30,000 derived values

Code: `src/face_engine/featurebank/` (added to the package so `python -m face_engine.featurebank.run` works).
Docs and data: `featurebank/README.md`, `featurebank/SKILL.md` (how an LLM should interpret the bank),
`featurebank/feature_catalogue.csv` (30,938 feature names with research tags), `featurebank/examples/`
(Carter vs Reagan 1980 debate: banks, word timestamps, digest, interpretation).

The core engine values it builds on are in [METRICS.md](METRICS.md).

## 1. Inputs and outputs

```
python -m face_engine.featurebank.run clip.mp4 words.json out.json
python -m face_engine.featurebank.digest A=a.json B=b.json -o digest.md
```

* `words.json`: list of `[start_s, end_s, "word"]` (for example faster-whisper word timestamps). Pass `-` for no transcript.
* `run.py` runs MediaPipe and the engine with **`frames_fps = media.fps` (every frame)**, because the bank needs dense
  per-frame rows. The result is cached in `clip.mp4.fbcache.pkl`; the cache is reused if it is newer than the clip.
* Audio needs `ffmpeg` on PATH and `librosa` (`pip install -e ".[featurebank]"`). Voice features are computed
  whenever a clip path is given.
* Output JSON: `schema` ("featurebank/1"), `duration_s`, `fps`, `n_frames`, `n_features`, `n_valid`,
  `conditions` (share of frames in each condition), `features` (`name → number or null`, rounded to 5 decimals).
  Example: Carter clip, 189.5 s at 30 fps → 28,950 features, 28,917 valid.

## 2. Naming

* Time-series features: `<signal>|<condition>|<functional>`, for example `au.AU12|speaking|p90`.
* Contrasts: `<signal>|<a>_minus_<b>|mean_z`.
* Other families: `<family>.<name>[.<stat>]`, for example `event.blink.per_min`, `lang.pron_we.per_100w`.

Families and their share of the catalogue: au 5,967 · voice 5,963 · geo 5,161 · body 3,129 · kin 2,855 · expr 1,547 ·
head 1,326 · gaze 1,105 · asym 663 · eye 663 · face 654 · mouth 442 · smile 442 · lang 313 · event 284 ·
cross 283 · align 72 · timing 61 · meta 8.

## 3. Signals (~140 per-frame series)

### 3.1 Engine signals (`engine_signals`)
Every numeric key of `report.frames[]` (all features in METRICS.md sections 3 and 5: `au.*`, `expr.*`, `smile.*`,
`asym.*`, `eye.*`, `gaze.*`, `head.*`, `mouth.*`, `face.*`, `body.*`). Frames missing from the report are NaN.
Values arrive rounded to 3 decimals.

### 3.2 Landmark geometry (`geometry_signals`, prefix `geo.`)
**Important:** these are computed in **image coordinates (2D, x/y only), not on the pose-aligned face**, so they
change with head turn and tilt. The face unit `io` here = distance between the **outer** eye corners (≈ 1.4 IOD),
not the eye-centre IOD used by the engine.

| signal | formula | unit | meaning / caveat |
|---|---|---|---|
| `geo.face_scale` | `io` in px ÷ the clip median | ratio (1 = typical) | distance-to-camera proxy; zoom fakes it |
| `geo.face_cx`, `geo.face_cy` | mean of the face points ÷ io | face widths from the image origin | only useful through its speed (`kin.*`) |
| `geo.mouth_open` | inner-lip distance / io | io | |
| `geo.mouth_width` | corner distance / io | io | |
| `geo.lip_corner_lift` | mean corner y − mean inner-lip y, / io | io, >0 corners up | raw smile proxy, not baseline-relative |
| `geo.brow_height` | mean y of the brow mid/outer points − inner-eye-corner y, / io | io | |
| `geo.brow_inner_height` | inner brow y − inner-eye-corner y, / io | io | |
| `geo.brow_gap` | inner-brow distance / io | io | smaller = brows drawn together (AU04) |
| `geo.eye_open` | mean lid distance (up1–lo1) of both eyes / io | io | |
| `geo.nose_wrinkle` | nose bridge ↔ subnasale distance / io | io | **smaller = more wrinkle**, despite the name |
| `geo.chin_raise` | lower lip bottom ↔ chin / io | io | **smaller = more chin raise** |
| `geo.iris_offset_x`, `_y` | mean iris − eye centre / io | io | |
| `geo.head_tilt_2d` | angle of the outer-eye-corner line | degrees | 2D roll |
| `geo.shoulder_width` | shoulder distance ÷ clip median | ratio | |
| `geo.shoulder_tilt` | shoulder-line angle | degrees | |
| `geo.torso_cx` | shoulder midpoint x / SW | SW | sway via its speed |
| `geo.head_over_shoulders` | nose y − shoulder mid y, / SW | SW | |
| `geo.wrist_l_height`, `_r` | wrist y − shoulder mid y, / SW | SW | |
| `geo.hands_spread` | wrist-to-wrist distance / SW | SW | |
| `geo.hands_to_face` | (wrist midpoint ↔ nose) / SW | SW | |
| `geo.elbow_spread` | elbow distance / SW | SW | |
| `geo.body_scale_ratio` | face io / SW in px | ratio | |

Body geometry needs both shoulders with visibility > 0.5.

### 3.3 Kinematics (`kin.`)
`kin.<signal>_speed` = |Δ per frame| × fps for `head.yaw`, `head.pitch`, `head.roll`, `gaze.h`, `gaze.v`, `geo.face_cx`,
`geo.face_cy`, `geo.torso_cx`, `geo.wrist_l_height`, `geo.wrist_r_height`, `geo.hands_spread`, `geo.face_scale`
(units per second). `kin.head_angular_speed` = √(Δyaw² + Δpitch² + Δroll²) × fps (deg/s);
`kin.head_angular_accel` = |Δ angular speed| × fps (deg/s²).

### 3.4 Voice (`voice.`, librosa; 16 kHz mono, hop 10 ms, interpolated to video frames)

| signal | meaning | unit |
|---|---|---|
| `voice.loudness_db` | RMS level, 40 ms frames | dBFS |
| `voice.pitch_hz` | F0 by pYIN, 65–450 Hz, voiced frames only | Hz |
| `voice.pitch_st` | F0 in semitones vs the clip median F0 | st |
| `voice.voiced`, `voice.voicing_prob` | pYIN voicing flag / probability | 0..1 |
| `voice.spectral_centroid`, `_rolloff`, `_bandwidth` | spectral shape | Hz |
| `voice.spectral_flatness` | noisiness | 0..1 |
| `voice.spectral_tilt_db` | energy 1–4 kHz vs 50–1000 Hz | dB (higher = brighter/pressed) |
| `voice.zcr` | zero-crossing rate | 0..1 |
| `voice.onset_strength` | onset envelope (syllable attacks) | arbitrary |
| `voice.mfcc01..13` | MFCCs (timbre) | arbitrary |
| `voice.jitter_like` | \|ΔF0\| / F0 between **video frames** | ratio |
| `voice.shimmer_like_db` | \|Δloudness\| between video frames, voiced only | dB |

Caveat: jitter-like and shimmer-like values are frame-level proxies (33 ms at 30 fps), **not** clinical cycle-to-cycle
jitter/shimmer. Room, microphone and broadcast compression dominate the timbre features.

## 4. Conditions (frame masks)

| condition | definition |
|---|---|
| `all` | every frame |
| `speaking` / `silent` | inside a word ±0.05 s (with a transcript), else `mouth.speaking`, else none |
| `third1..3` | first, middle, last third of the clip |
| `emphasis` | ±0.15 s around the loudest 20% of words (mean loudness over the word); needs audio + words |
| `self_ref` | ±0.3 s around I-words |
| `other_ref` | ±0.3 s around you/we-words |
| `question` | a clause detected as a question, up to 1 s after its end |
| `clause_start` | −0.3 to +0.7 s around a clause's first word |
| `clause_end` | ±0.5 s around a clause's last word |
| `long_pause` | gaps between words ≥ 1 s |

Clauses: a new clause starts after a gap ≥ 0.3 s or after a word ending in `.?!`.
A condition is skipped if it covers fewer than max(5, 0.5 × fps) frames.

## 5. Functionals (`functionals.compute`, applied to each signal × condition)

`valid_share` (finite share; computed always). If fewer than max(5, 0.5 s) valid values, nothing else.

| functional | definition |
|---|---|
| `mean`, `std`, `min`, `max`, `median`, `p05`, `p10`, `p25`, `p75`, `p90`, `p95` | distribution |
| `iqr` | p75 − p25 |
| `range_p95_p05` | p95 − p05 |
| `cv` | std / \|mean\| (NaN if mean ≈ 0) |
| `skew`, `kurtosis` | standardised 3rd moment; excess 4th moment |
| `mean_abs_delta_per_s`, `std_delta_per_s`, `max_abs_delta_per_s` | frame-to-frame change × fps; deltas across NaN gaps are dropped |
| `slope_per_min` | linear trend vs time in minutes |
| `share_above_baseline_1sd`, `share_below_baseline_1sd` | share of valid frames above mean+1sd / below mean−1sd, where mean and sd are the **person's whole-clip** values for this signal |
| `z_mean_vs_person` | (condition mean − whole-clip mean) / whole-clip sd |
| `longest_high_run_s` | longest run above mean+1sd, seconds |
| `high_episodes_per_min` | runs ≥ 2 frames above mean+1sd, per minute |
| `peaks_per_min` | local maxima above mean+1sd, ≥ 0.25 s apart, per minute |
| `autocorr_1s` | lag-1 s autocorrelation (rhythmicity) |

The full set is computed for `all`, `speaking`, `silent`, `third1..3`. The focus conditions (`emphasis`, `self_ref`, `other_ref`,
`question`, `clause_start`, `clause_end`, `long_pause`) keep only `mean`, `std`, `p90`, `share_above_baseline_1sd`, `peaks_per_min`,
`z_mean_vs_person`, `mean_abs_delta_per_s`.

Contrasts: `speaking_minus_silent`, `third3_minus_third1`, `other_ref_minus_self_ref`, `emphasis_minus_all`, as
`(mean_a − mean_b) / whole-clip sd` (`|mean_z`).

## 6. Event features (`event.<type>.*`)
For every engine event type (always including blink, smile, head_nod, head_shake, gaze_averted, gesture, posture_shift, shrug,
face_touch, open_palms, eye_closure, expression, action_unit):
`count`, `per_min`; if there are events: `duration_s.{n,mean,median,std,max,p90}`, `peak.{…}`, `interval_mean_s` and
`interval_cv` (if more than 2 events), `share_while_speaking` (by the event's peak frame), `per_min_in_<third1|third2|third3|emphasis|question|clause_end|long_pause>`
(events whose peak falls in the condition ÷ condition minutes), and `kind.<au|label|direction>.per_min` (for example `event.action_unit.kind.AU12.per_min`).

## 7. Language (`lang.`, English only; needs words)

* `lang.words`, `lang.words_per_min`.
* 46 word categories (`lexicon.CATEGORIES`: pron_i, pron_we, pron_you, pron_they, pron_he_she, pron_impersonal, article,
  negation, hedge, certainty, absolutist, filler, discourse_marker, posemo, negemo, anxiety, gratitude, affiliation,
  achievement, power, moral, future, past, insight, cause, discrepancy, tentative, contrast, inclusive, exclusive,
  number_word, quantifier, time, money, social, perception, body_words, action_verbs, address_audience, superlative,
  intensifier, politeness, agreement, apology, humor_markers, question_words). Each has `count`, `per_100w`, `per_min`,
  `per_100w_third1..3`. They are small hand-made lists in the LIWC style, not LIWC itself. Some words are in several lists
  ("like" is both posemo and discourse marker, "never" is in negation, certainty and absolutist).
* Ratios: `ratio.you_vs_i`, `we_vs_i`, `posemo_vs_negemo`, `certainty_vs_hedge`, `future_vs_past` = a/(a+b).
* Diversity: `type_token_ratio`, `mattr_50` (moving-window TTR, needs ≥ 50 words), `hapax_share`.
* Complexity: `mean_word_len`, `long_words_share` (≥ 7 letters), `syllables_per_word` (vowel-group heuristic),
  `clause_len_words.*`, `clauses_per_min`, `flesch_reading_ease`, `fk_grade` (clauses stand in for sentences).
* Questions (found by word order when there is no "?"): `questions.count`, `per_min`, `share_of_clauses`, `with_you_share`.
* Rhetoric: `repeated_bigram_share`, `repeated_trigram_types`, `anaphora_max_same_opening`, `anaphora_share`,
  `and_lists.per_min` (loose heuristic), `contrast_pairs.per_min` (but/not/instead/rather), `because_justifications.per_min`,
  `direct_address_names.per_min` (governor/president/senator/friends/folks/americans: tuned to political debates),
  `self_repairs.per_min` (immediately repeated word), `first_person_opening_share`, `numbers.per_100w`.

## 8. Timing (`timing.`, needs ≥ 3 words)
`pause_s.*` (gaps ≥ 0.25 s), `pauses_ge_{0.25,0.5,1.0,1.5,2.0}s.per_min`, `long_pause_share_of_time`, `silence_share`
(1 − word time / duration), `word_duration_s.*`, `articulation_rate_syl_s` (syllables / word time), `speech_rate_syl_s`
(syllables / clip duration), `wpm_10s_window.*` and `.cv`, `pause_after_question_s.*`, `pause_before_you_we_s.*`,
`filled_pauses.per_min` (um/uh/er/ah/erm; ASR usually drops them, so this is a lower bound).
With audio: `clause_terminal_slope_st_s.*` (pitch slope over the last 0.6 s of each clause), `clause_terminal_rise_share`
(slope > 2 st/s), `clause_terminal_fall_share` (< −2 st/s), `clause_pitch_range_st.*` (p90 − p10 per clause), `pitch_reset_st.*`.

## 9. Cross-modal (`cross.`) and alignment (`align.`)
* `cross.corr.<a>~<b>|all` and `|speaking`: Pearson r between 17 key signals (head speed, AU12/06/01/02/04, gaze averted,
  eye closure, expressivity, gesture activity, mouth open, brow height, loudness, pitch, onset strength, face scale, lean in).
* `cross.xcorr.<a>~<b>.peak` and `.lag_ms`: best correlation within ±1 s lag between movement (head speed, AU01, AU02,
  gesture activity, AU12, eye closure) and voice (loudness, onset strength, pitch); lag > 0 = movement leads the voice.
* `cross.gaze_on_speaking`, `cross.gaze_on_silent`, `cross.visual_dominance_ratio` (on-gaze while speaking / while silent;
  Exline/Dovidio, B). "On" = not `gaze.averted`, which is the neutral direction, not verified eye contact.
* `align.<event>.near_<stressed_word|clause_end|clause_start|word_onset>_share` and `.to_<…>_median_ms`, `align.<event>.in_long_pause_share`
  for head_nod, head_shake, blink, smile, gaze_averted, gesture, shrug, posture_shift. Windows: stressed word 0.3 s, clause start/end 0.6 s, word onset 0.2 s.

## 10. Reliability (`meta.`)
`meta.face.present`, `meta.body.present`, `meta.body.hands_visible`, `meta.face.reliability` (means), `meta.duration_s`,
`meta.has_transcript`, `meta.has_audio`, `meta.face_px_scale_var` (std of `geo.face_scale`; high = zoom/cuts).
Rule from SKILL.md: drop a family when its coverage is below ~0.5.

## 11. Psychological meaning and evidence grades (`psych.py`, catalogue columns)

Each name is tagged by the **first** matching regex in `psych.RULES`: `factor`, `dimensions`, `literature_direction`
(+, −, inverted-U, context) and `grade`. Grades: **A** = meta-analysis / well replicated; **B** = replicated or a large study;
**C** = single study; **D** = practitioner claim or contested. The direction is a prior for observers' liking/trust, not a score.
In the catalogue: A 671, B 6,971, C 10,844, D 1,489, untagged 10,963.

| pattern (signal) | factor | dims | dir | grade |
|---|---|---|---|---|
| au.AU12, smile.social, geo.lip_corner_lift | smiling | warmth, positivity | + | A |
| au.AU06, smile.duchenne | Duchenne smile | warmth, positivity | + | B |
| event.smile.duration/interval | smile timing | trust | + slow | C |
| au.AU04, geo.brow_gap | frowning | warmth | − | B |
| au.AU01/02, geo.brow_height | brow raising | expressiveness, attentiveness | context | C |
| face.expressivity, expr.* | facial expressivity | charisma | + | B |
| au.AU15/17/23 | lip press, chin raise | warmth, composure | − | C |
| asym.* | asymmetry | trust | − | C |
| gaze.averted, gaze.dir, geo.iris | gaze toward listener | attentiveness, trust, dominance | + moderate | B |
| cross.gaze_on, visual_dominance | visual dominance ratio | dominance | context | B |
| event.blink, eye.closure, geo.eye_open | blink rate | composure | − if high | C |
| event/align.head_nod | nodding | attentiveness, warmth, coordination | + | B |
| kin.head_*, head.yaw/pitch/roll | head movement | expressiveness, charisma | inverted-U | C |
| geo.head_tilt_2d | lateral head tilt | warmth | context | D |
| body.gesture, event.gesture, geo.wrist, geo.hands_spread | illustrative gesturing | competence, charisma, persuasion | + | B |
| align.gesture | gesture-speech sync | fluency, competence | + | C |
| body.face_touch, geo.hands_to_face | self-touch | composure | − | B |
| body.open_palms, palm_to_camera | open palms | warmth, trust | + | D |
| body.arms_crossed, hands_joined | closed arms | warmth | − | D |
| body.lean_in, geo.face_scale | forward lean | attentiveness, immediacy | context | B |
| body.arm_openness, geo.elbow_spread, geo.shoulder_width | expansive posture | dominance | context | D |
| body.shrug, body.shoulder, geo.shoulder_tilt | shrugs | composure | context | C |
| event.posture_shift, kin.geo_torso, kin.geo_face_c | fidgeting / sway | composure | − | B |
| voice.pitch variability functionals | pitch variability | charisma | + | B |
| voice.pitch_hz mean/median | pitch level | dominance, competence | lower = more dominant | B |
| voice.loudness_db | loudness | charisma, dominance | + variation | C |
| voice.jitter/shimmer/flatness | roughness | composure | context | C |
| voice.tilt/centroid/mfcc | timbre | warmth | context | C |
| speech rate | speech rate | competence, warmth | inverted-U | B |
| pauses | pausing | fluency, charisma | context | C |
| filled pauses | um/uh | competence | − | B |
| clause terminal rise | uptalk | competence | − | C |
| lang.pron_you, you_vs_i | listener focus | warmth, attentiveness | + | C |
| lang.pron_we, we_vs_i | collective we | warmth, leadership | + | B |
| lang.pron_i | self-focus | status | − | B |
| lang.questions, pause_after_question | question asking | warmth, attentiveness | + in conversation | B |
| hedges / tentative | powerless speech | competence | − | B |
| certainty / absolutist | certainty | competence, warmth | context | C |
| posemo, gratitude, politeness, affiliation | positive language | warmth, positivity | + | B |
| negemo, anxiety, negation | negative language | positivity | − | C |
| anaphora, repetition, lists, contrasts, superlatives, moral | rhetorical devices | charisma | + | B |
| numbers, money, quantifiers | specificity | competence | + | C |
| readability, word length | processing fluency | fluency | + simpler | B |
| lexical diversity | diversity | competence | + | C |
| future / past | future orientation | leadership | + | C |
| because | justifications | persuasion | + weak | D |
| self repairs | disfluency | fluency | − | C |
| cross.xcorr head~voice, brow~voice, align.blink/smile/gaze_averted, cross.corr | coupling and placement | coordination etc. | context/+ | B–C |
| meta.* | reliability | – | – | A |

Not tagged at all: `au.AU05`, `AU07`, `AU09`, `AU10`, `AU20`, `AU25`, `AU26`, `mouth.*`, most `geo.*` mouth/eye
measures, MFCC-like untagged items and so on (they are "exploratory" in the digest).

### Known tagging issues (found while reading the code; worth a test)
Because the first matching rule wins:
1. `expr.contempt|…` matches the earlier `expr.` rule, so it is tagged "facial expressivity, +, B" instead of the intended
   "contempt-like display, −, C".
2. `head.pitch|…` and `head.roll|…` match the "head movement, inverted-U, C" rule first, so the "head tilt down = dominance (B)"
   and "lateral head tilt (D)" rules never apply to them (they do apply to `geo.head_over_shoulders` and `geo.head_tilt_2d`).
3. `gaze.averted` is tagged "+ (moderate)" as eye contact, but the signal is 1 when gaze is **away**. The direction is inverted
   for this signal (the note text is right, the sign is not).
4. `lang.filler.*` matches the "filled pauses" rule only through `^lang\.filler`. That is fine, but ASR transcripts drop fillers.

## 12. Digest (`digest.py`)
* Per person: coverage line and the `NORMS` check (blink 8–26/min, 140–170 wpm, 4.0–5.5 syl/s articulation, I-words 3–7/100,
  you-words 1–4/100, fillers 0–4/min).
* With 2 banks: d = (B − A) / scale for every common rankable feature (means use the pooled whole-clip std; rates and
  shares use their mean magnitude with a floor of 0.1; z-type values use 0.5). d is clipped to ±10. Features whose
  `valid_share` < 0.3 in either bank are skipped. At most 2 features per signal, top 12 per dimension, grouped by the tag's dimensions,
  plus a list of untagged large differences.
