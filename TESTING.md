# TESTING.md: how to set up, run and test face-engine

Written for the next model or engineer who has to test this engine. Read it together with
[docs/METRICS.md](docs/METRICS.md) (every value of the core report: meaning, formula, units, caveats) and
[docs/FEATUREBANK.md](docs/FEATUREBANK.md) (the ~30k derived features, voice, transcript, research grades).

## 0. What is in this folder

| path | what | in git |
|---|---|---|
| `src/face_engine/` | core engine: detector adapter, face and body analyzers, engine, CLI, visualisation | yes |
| `src/face_engine/featurebank/` | feature bank (signals, functionals, lexicon, psych tags, digest, `run.py`) | yes (added in the last commit) |
| `tests/` | pytest suite (119 tests) | yes |
| `docs/METRICS.md`, `docs/FEATUREBANK.md`, `TESTING.md` | this documentation | yes |
| `featurebank/README.md`, `SKILL.md`, `feature_catalogue.csv` | feature-bank overview, LLM interpretation skill, 30,938 tagged feature names | yes |
| `featurebank/examples/` | Carter vs Reagan 1980 debate: feature banks (`*_fb.json`), word timestamps, `digest.md`, interpretation | no (data) |
| `examples/` | sample reports: `demo_synthetic.json`, `photo_smile_crossed_arms.json` | no (data) |
| `visual-tests/` | reports, overlay videos, timelines and key-moment sheets from two real test videos (Intel sample videos, CC BY 4.0) | no (data) |

Git history: 7 commits (5 original + 2 for the feature bank, docs and this restore script). The remote copy tool cannot write a `.git` folder,
so the history ships as `face-engine-history.bundle`. Run `restore-git-history.cmd` once (or: `git init`,
`git fetch face-engine-history.bundle master`, `git reset FETCH_HEAD`); then `git log --oneline` shows the 7 commits and
`git status` lists only the untracked data folders.

## 1. Setup (Windows, PowerShell)

Python 3.10 or newer (tested here with 3.13).

```powershell
cd $HOME\Downloads\face-engine
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"                      # core + pytest (numpy only)
pip install -e ".[mediapipe,viz]"            # real photos/videos + overlay/timeline
pip install -e ".[featurebank]"              # voice features (also needs ffmpeg on PATH)
face-engine models                           # downloads 3 MediaPipe .task models (~21 MB) to ~/.cache/face-engine/models
```

On Linux without a GPU, MediaPipe also needs `libegl1` and `libgles2` (`apt-get install libegl1 libgles2`). Without them the
error is `OSError: libEGL.so.1`. Use `FACE_ENGINE_MODELS=<dir>` to keep the models elsewhere.

## 2. Running

```powershell
face-engine demo -o demo.json --frames-fps 30          # synthetic 12 s clip, no detector needed
face-engine analyze photo.jpg -o photo.json
face-engine analyze clip.mp4 -o clip.json --segment 10 --sample-fps 15 --frames-fps 5
face-engine analyze clip.mp4 --neutral calm.jpg -o clip.json   # personal neutral from another file
face-engine analyze clip.mp4 --save-landmarks lm.npz -o a.json  # cache detector output
face-engine analyze lm.npz -o b.json                            # re-run analysis without MediaPipe
face-engine visualize clip.mp4 -o viz\                          # overlay.mp4, timeline.png, moments.png, report.json
python -m face_engine.featurebank.run clip.mp4 words.json bank.json   # words.json = [[start, end, "word"], ...] or "-"
python -m face_engine.featurebank.digest A=a.json B=b.json -o digest.md
```

Flags: `--frames-fps 0` writes no per-frame rows; `--max-seconds N`; `--no-body`; `--no-hands`; `--models DIR`.

## 3. Existing tests

```powershell
pytest                                                   # 118 pass, 1 skipped (the real-photo test)
$env:FACE_ENGINE_SAMPLES="C:\path\to\folder_with_portrait.jpg"; pytest tests/test_mediapipe_integration.py
```

The real-photo test needs `portrait.jpg` from `https://storage.googleapis.com/mediapipe-assets/portrait.jpg`
(a smiling person with crossed arms) plus the models.

**Last verified run (Linux, Python 3.13, mediapipe + opencv + matplotlib installed, sample set): 119 passed in 3.7 s.**
Without mediapipe/opencv: 117 passed, 2 skipped.

| file | tests | what it checks |
|---|---|---|
| `test_geometry.py` | 10 | Umeyama recovers a similarity, never a reflection, rejects degenerate input; yaw/pitch/roll round trip and sign conventions |
| `test_face.py` | 61 | neutral face → no AUs at 3 poses; head pose recovered within 0.5°; each of 10 primitives activates its AUs (>0.7) and not others (<0.2) at 3 poses; intensity is monotonic; expression prototypes; Duchenne vs social smile; asymmetry sign; gaze; population vs personal baseline; robustness when an expression fills part of the clip; blink vs squint; long closure ≠ blink; brief flag; nod/shake events; missing faces; NaN anchors; missing iris only disables gaze; blink counts per segment; distorted outer face does not change scale; pose compensation; broad smile ≠ disgust; no expression events while turned away |
| `test_body.py` | 24 | posture flags for 6 postures with and without hand landmarks; openness ordering; palm sign per side; open palms needs a shown palm; hand-side assignment; scale invariance; gesture events merge turning points; posture shift; shrug; invisible shoulders → no body; low-visibility wrist ignored; lean_in ignores the neutral file's resolution |
| `test_temporal.py` | 9 | runs/merging, NaN-aware smoothing, dilation, oscillation detector, threshold events, event spans |
| `test_engine.py` | 9 | report structure and JSON safety, notable segments, single photo, empty input, plug-in analyzer, `.npz` round trip, CLI demo and npz analyze, neutral loader, segment event counts |
| `test_featurebank.py` | 4 | >1000 named features from a fake clip, word counts, questions without punctuation, baseline-relative functionals, research tags, digest render |
| `test_viz.py` | 1 | overlay video and timeline are written (needs opencv + matplotlib) |
| `test_mediapipe_integration.py` | 1 | real portrait: happiness > 0.5, Duchenne > 0.5, \|yaw\| < 10, arms crossed |

The synthetic generator (`src/face_engine/sources/synthetic.py`) is the main test tool. It moves canonical face points by known
amounts (IOD units) at any head pose, noise level and personal morphology:

* face primitives: `brow_raise`, `brow_inner_raise`, `brow_lower`, `eye_widen`, `blink`, `wink_l`, `wink_r`, `cheek_raise`,
  `smile`, `smile_l`, `smile_r`, `frown`, `jaw_drop`, `lip_press`, `nose_wrinkle`, `upper_lip_raise`, `gaze_h`, `gaze_v`
  (amount 1.0 = the AU full scale, so expect an intensity of about 1);
* `synthetic_face(expr, yaw, pitch, roll, iod_px, identity, noise_px, rng)`; `random_identity(rng)` for morphology;
* body postures: `rest`, `open`, `crossed`, `face_touch`, `hands_joined`, `raised`, or a dict of wrist positions in SW;
  `synthetic_body(posture, sw_px, scale, with_hands, palms_to_camera)`;
* `synthetic_clip(n_frames, fps, face_fn, body_fn)` builds a sequence of `FrameObservation`.

Minimal pattern:

```python
import numpy as np
from face_engine.analyzers.face import FaceAnalyzer
from face_engine.sources.synthetic import synthetic_clip, synthetic_face
fps = 30
rng = np.random.default_rng(0)
frames = synthetic_clip(180, fps, lambda i: synthetic_face({"smile": 1.0} if 60 <= i < 90 else None, rng=rng, noise_px=0.2))
r = FaceAnalyzer().analyze(frames, fps)
assert r.features["au.AU12"][75] > 0.7 and r.features["au.AU12"][10] < 0.1
assert any(e["type"] == "smile" for e in r.events)
```

## 4. Suggested new test cases

Grouped by what they protect. "Expect" is what the code is supposed to do according to docs/METRICS.md;
items marked **(likely fails today)** were found while reading the code and confirmed by a quick probe or by reading.

### 4.1 Known issues to confirm or fix first
1. **Smile events ignore reliability (likely fails today).** A smile at yaw 55° produces a `smile` event although `action_unit`
   and `expression` events are suppressed (confirmed: synthetic smile at yaw=55 → events `smile`, `gaze_averted`). Decide whether
   `smile` should use the same `readable` mask as AU events.
2. **Research tag shadowing (likely fails today).** `psych.tag("expr.contempt|all|mean")` returns "facial expressivity, +, B" instead of
   "contempt-like display, −, C"; `head.pitch|…` and `head.roll|…` never get their own dominance/tilt tags. Cause: the first regex wins.
3. **Inverted direction for `gaze.averted` (likely fails today).** It is tagged "+" as eye contact, but the value is 1 when gaze is away.
4. **Feature bank needs dense frames.** `engine_signals` reads `report.frames`. With a report made by `face-engine analyze` (default
   `--frames-fps 5`), 5 of 6 frames are NaN. Test: bank built from a 5 fps report has `valid_share` ≈ 1/6; `run.py` avoids this by using full fps.
5. **README test count is stale:** it says 100 tests; the suite has 119.

### 4.2 Face accuracy and invariance
6. Monotonic intensity for **every** AU (not only AU12): amounts 0.25/0.5/0.75/1.0 give strictly increasing values with each step ≈ 0.25 ± 0.07.
7. Pose sweep: neutral face at yaw −40..40° and pitch −25..25° in 5° steps. Expect max AU < 0.05 up to 20°; record where it breaks (reliability should drop there).
8. Scale and position invariance: the same expression at `iod_px` 30, 60, 120, 400 and different `center` → identical AUs (±0.02).
9. Noise robustness: `noise_px` 0.5, 1, 2 at iod 60 → false AU events per minute on a neutral clip (a regression number to track).
10. Laterality: `smile_l` only → `au.AU12_l` > 0.7, `_r` < 0.1, `asym.mouth` > 0, `expr.contempt` > 0.5; mirror for `smile_r`. `wink_l` → `asym.eye` < 0 (note the opposite sign convention).
11. AU20 suppression: `smile` 1.0 → `au.AU20` < 0.1 even though the mouth widens.
12. AU6/AU7 blanking: blink at the same time as `cheek_raise` → AU06 = 0 during the blink frames only.
13. Baseline with `--neutral`: a person with `random_identity` (e.g. low brows) → AU04 ≈ 0 with a neutral reference, > 0 with `population_canonical`.
14. Baseline trap: a clip that is a smile 70% of the time → auto baseline absorbs the smile (documented limitation). Test that
    `baseline.face.method == "auto_calm_frames"` and that AU12 is low; then that `--neutral` fixes it.
15. Pose compensation on/off: clip ≥ 3 s with yaw std ≥ 3° → `pose_compensation: true`; 2 s or static → false.
16. Gaze: `gaze_h` 1.0 with a frontal head → `gaze.dir_h_deg` ≈ 35, `gaze.averted` = 1; `gaze_h` 0.3 → ≈ 10.5°, not averted.
17. Missing iris (NaN rows 33–34) → `gaze.*` NaN, all AUs still valid.
18. Speech: lip gap oscillating ±0.05 IOD at 4 Hz → `mouth.speaking` = 1, no AU25 events, `mouth.activity` > 0.015.

### 4.3 Events and timing
19. Blink duration boundary: closures of 0.47 s and 0.53 s at 30 fps → `blink` vs `eye_closure`.
20. Brief flag boundary: an AU held 0.43 s vs 0.57 s → `brief` true / false.
21. Nod: pitch sinusoid amplitude 5° vs 8° at 2 Hz → no nod vs nod; a slow 0.3 Hz tilt of 10° → no nod (legs > 0.8 s).
22. Event frame numbers: with `--sample-fps` lower than the video fps, `frame_start`/`frame_end` are video frame indices, not positions.
23. Segment sums: Σ `segments[].event_counts[type]` == `summary.event_counts[type]` for every type.
24. Blink rate: 10 blinks in 30 s → `blink_rate_per_min` = 20.0 and a highlight "within" the range; a 9 s clip → no blink highlight.

### 4.4 Body
25. `lean_in`: scale the body by 1.2 for 2 s in the middle → `body.lean_in` ≈ 0.2 there and one `posture_shift` toward then away.
26. Arms crossed with wrists above −0.2 SW (high cross) → not crossed (documented geometry rule).
27. Face touch threshold: hand distance 0.29 vs 0.31 SW from the nose.
28. Hands hidden (visibility 0.3) → `hands_visible` = 0, no gesture events, `gesture_speed` NaN.
29. Shrug false positive: pitch the head down (ears drop toward the shoulders) without moving the shoulders → `body.shrug` rises. Document the size of the effect.

### 4.5 Real media (needs MediaPipe)
30. Re-run `face-engine visualize` on the Intel sample videos (`head-pose-face-detection-male.mp4` / `-female.mp4`
    from github.com/intel-iot-devkit/sample-videos) and compare with `visual-tests/*-report.json`: event counts within ±10%
    (male: 31 blinks, 138 AU events, 1 nod, 1 shake; female: 30 blinks, 269 AU events, 35 smiles). This is a regression test, not ground truth.
31. Determinism: two runs on the same `.npz` give byte-identical JSON.
32. Photo vs video: the same portrait as a 1-frame image and as a 3 s still video (`ffmpeg -loop 1 -t 3`) → similar AUs;
    the video uses `auto_calm_frames` (so AUs ≈ 0, because the smile becomes the neutral). This is a good demo of the baseline limitation.
33. Accuracy against labels: if a labelled set is available (DISFA, BP4D, or self-recorded posed AUs), compute per-AU correlation
    and F1 at threshold 0.35. No calibration has been done yet; this is the most valuable missing test.

### 4.6 Feature bank
34. With a real clip and transcript: `n_features` > 20,000, `meta.has_audio` = 1, `voice.pitch_hz|all|median` within 80–300 Hz.
35. `lexicon.question_onsets` on 20 hand-made sentences (statements with "do you", embedded questions such as "what you said") → precision/recall.
36. Conditions: with no words, only `all`, `speaking` (from `mouth.speaking`), `silent`, `third1..3` exist.
37. Digest: two identical banks → every d = 0 and an empty "largest differences" table.
38. Catalogue consistency: every name in a fresh bank either appears in `feature_catalogue.csv` or is a new name, and `psych.tag` gives the same grade as the CSV row.

## 5. How to read results when testing
* Look at `baseline.face.method` first: `population_canonical` (single photo) mixes the person's anatomy into the AUs.
* `face.reliability` < 0.5 → ignore AU/asymmetry values for those frames.
* Mouth AUs during `mouth.speaking` = 1 are mostly speech shapes.
* Many brief AU06/AU07/AU09 events on a calm low-resolution face are detector noise (see `visual-tests`).
* Never report lies, intent or felt emotion from any value (see the `disclaimer` field and `featurebank/SKILL.md`).
