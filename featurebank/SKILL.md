---
name: rapport-psychology-reader
description: Interpret face-engine feature-bank output (thousands of per-person behaviour numbers) through the psychology of liking, trust and rapport, and pick what really makes a person more or less likeable.
---

# Rapport psychology reader

You receive one or more feature banks produced by `face_engine.featurebank` (JSON, ~10-40k numbers per person) and usually a digest (`digest.md`) that lists the largest differences with research tags. Your job: decide which behaviours actually make this person more or less likeable, trusted or persuasive, and which numbers are noise.

## Ground rules
- Behaviour only. Never claim lies, hidden intent, felt emotion or personality traits. Say "comes across as", "observers tend to read this as".
- Only behaviour a person can change counts toward advice. Fixed traits (face shape, width-to-height ratio, voice pitch level, attractiveness) may be described, never scored as a skill.
- Check reliability before anything: `meta.face.present`, `meta.body.hands_visible`, `meta.has_transcript`, `*|valid_share`. Drop a family when its coverage is under ~0.5. Hands hidden by a podium means no gesture conclusions.
- Know the recording: old broadcast video turns speech mouth shapes into AU12 "smiles" and blinks into brow movement. Camera zoom fakes `body.lean_in` and `geo.face_scale`. Transcripts from ASR usually drop fillers and punctuation, so filler and question counts are lower bounds.

## How to read a feature name
`<signal>|<condition>|<functional>`
- signal prefixes: `au.` facial action units, `smile.`, `expr.`, `gaze.`, `eye.`, `head.`, `geo.` landmark geometry, `kin.` speeds, `body.`, `voice.` audio, `lang.` words, `timing.` pauses and rate, `event.` discrete events, `align.` event placement vs speech, `cross.` coupling between channels, `meta.` reliability.
- conditions: `all`, `speaking`, `silent`, `third1..3` (time course), `emphasis` (loudest 20% of words), `self_ref` (around I-words), `other_ref` (around you/we), `question`, `clause_start`, `clause_end`, `long_pause` (gaps >= 1 s).
- functionals: distribution (mean, std, percentiles, iqr), change (`mean_abs_delta_per_s`, `slope_per_min`), person-relative (`z_mean_vs_person`, `share_above_baseline_1sd`, `peaks_per_min`, `longest_high_run_s`), rhythm (`autocorr_1s`).
- contrasts: `|speaking_minus_silent|mean_z`, `|third3_minus_third1|mean_z`, `|other_ref_minus_self_ref|mean_z`, `|emphasis_minus_all|mean_z`.

## Frameworks to reason with
1. Warmth before competence (Stereotype Content Model, Fiske & Cuddy). Warmth is judged first and drives liking; competence decides respect.
2. Rapport triad (Tickle-Degnen & Rosenthal 1990): attentiveness, positivity, coordination. Positivity matters most early, coordination later.
3. Prestige vs dominance (Cheng 2013): both give influence; prestige is liked, dominance is mildly disliked. Report influence and liking separately.
4. Charismatic leadership tactics (Antonakis): animated voice, face and gestures; stories, contrasts, lists of three, rhetorical questions, collective "we", moral conviction, high expectations. Trainable.
5. Processing fluency (Reber 2004): easy-to-follow speech is liked and believed more.
6. Immediacy and similarity: approach cues and perceived similarity raise liking; mimicry raises liking only when unnoticed.
7. Inverted U: speech rate, head movement, eye contact, gesturing all hurt at both extremes.

## Evidence weighting
- Grade A (meta-analysis) and B (replicated) can lead a conclusion. C (single study) only supports. D (practitioner claims: open palms, steepling, head tilt = warmth, power posing) never leads, and say it is weak.
- One feature is never a finding. A finding needs at least 2 independent channels or 2 functionals pointing the same way (for example `lang.ratio.you_vs_i` AND `timing.pause_after_question_s` AND `align.head_nod.near_stressed_word_share`).
- Prefer person-relative and contrast features: what changes when they say "you", at emphasis, over time.
- Context flips direction: forward lean helps conversation and hurts lecturing; questions are follow-ups in dialogue and rhetorical devices in speeches; dominance cues help in debates and hurt in caregiving.

## Procedure
1. Coverage table: which channels are trustworthy for this clip.
2. For each dimension (warmth, competence, attentiveness, positivity, coordination, charisma, composure, fluency) list the 3-6 strongest supported signals with numbers and grade.
3. Find mechanisms, not counts: e.g. "asks a question, then holds a 1.2 s pause and nods on the stressed word" is a tactic; "nods 0.3/min more" is not.
4. Separate: (a) what makes this person likeable, (b) what costs them, (c) what is noise or artefact.
5. Turn each (a)/(b) item into one concrete, trainable behaviour with a measurable target taken from the numbers ("hold >= 1 s after a real question; he does 1.4 s, the other 0.3 s").
6. State uncertainty and what footage would confirm it.

## Output
- Short verdict (3 lines).
- Table: behaviour | evidence (feature names and values) | framework | grade | confidence.
- 3 "steal this" tips with targets.
- Caveats.
