# face-engine feature bank

Turns one person's clip into ~30,000 plain numeric quantities (about 19 families), tags each one with what psychology research says about it, and builds an LLM brief. The LLM (with `SKILL.md`) then decides what actually makes the person likeable, trusted or persuasive.

## Pipeline
1. `run.py clip.mp4 words.json out.json`: MediaPipe → engine report → feature bank. The engine pass is cached in `clip.fbcache.pkl`, so a rerun takes about 10 s.
   - `words.json` is a list of `[start_s, end_s, "word"]` (faster-whisper word timestamps).
2. `digest.py A=a.json B=b.json -o digest.md`: per-dimension tables of the largest differences, with research tags and coverage filters.
3. The LLM reads `digest.md` (and queries the full JSON) using `SKILL.md`. See `examples/interpretation_carter_vs_reagan.md`.

## What gets measured
`<signal>|<condition>|<functional>` grid plus event, language, timing and cross-modal families.

- **Signals (~150):**
  - All engine outputs: action units, smiles, expressions, head pose, gaze, eye closure, asymmetry, posture and gesture.
  - 25 landmark geometries: mouth opening, brow height and gap, iris offset, shoulder tilt, wrists, hands spread, distance proxies.
  - 14 kinematics: speeds and accelerations.
  - 30 voice descriptors: loudness, pitch in semitones and Hz, voicing, spectral centroid, flatness, rolloff, bandwidth and tilt, ZCR, onset strength, MFCC 1–13, jitter-like and shimmer-like perturbation.
- **Conditions (13):** all, speaking, silent, thirds 1/2/3, emphasis (loudest 20% of words), around I-words, around you/we-words, questions, clause start, clause end, long pauses ≥ 1 s. Contrasts: speaking−silent, third3−third1, other−self reference, emphasis−all.
- **Functionals (29):**
  - Distribution: mean, sd, percentiles, iqr, cv, skew, kurtosis.
  - Change: delta stats, slope.
  - Person-relative: z vs own baseline, share above/below baseline, peaks/min, longest high run.
  - Rhythm: 1 s autocorrelation.
- **Events:** rate, durations, peaks, intervals, and placement by third, emphasis, question, clause end and long pause.
- **Language (~310):**
  - 46 word categories (pronouns, hedges, certainty, absolutist words, emotion, gratitude, affiliation, power, moral, future/past, numbers, money and others), each per 100 words, per minute and by third.
  - Ratios, lexical diversity, readability.
  - Question onsets found without punctuation.
  - Anaphora, repetition, contrasts, self-repairs.
- **Timing:** pause distributions; pauses ≥ 0.25–2 s per minute; articulation and speech rate; rate variability; pause after questions; pause before you/we; filled pauses; clause-final pitch rise/fall; pitch reset.
- **Cross-modal and alignment:**
  - 272 correlations between channels.
  - Lagged face/voice coupling (peak and lag).
  - Whether nods, blinks, smiles, gaze aversion and gestures land on stressed words, clause starts/ends or long pauses.
  - Visual dominance ratio.
- **Meta:** coverage of face, body, hands, transcript and audio.

`feature_catalogue.csv` lists every feature with its research tag (about 65% are tagged).

## Limits
- One person per clip. Two-person features (mimicry, style matching, response latency, shared laughter) need diarisation and two tracks; that is the next step.
- Research directions are priors, not scores. About a third of the catalogue rests on unverified classic sources (see the research report).
- Behaviour only: no lie detection, intent or traits.
