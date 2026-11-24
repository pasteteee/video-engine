# face-engine: every measured value (core engine)

This file documents every value the core engine (`src/face_engine`) writes into its JSON report.
It was written from the code in this repository (commit `57230ba` plus the feature bank), not from
the README. Where the README and the code differ, the code wins and the difference is noted.

The second layer, the **feature bank** (~30,000 derived numbers plus voice and transcript), is
documented separately in [FEATUREBANK.md](FEATUREBANK.md). How to run and test everything is in
[../TESTING.md](../TESTING.md).

> **What these values are not.** Every value describes visible geometry (landmark positions)
> relative to the same person's own neutral baseline. None of them detects lies, intent or felt
> emotion. `expr.anger = 0.7` means "the face configuration is 70% similar to the prototype anger
> display", nothing more (Barrett et al. 2019: facial configurations are not reliably diagnostic of
> emotion). Thresholds and "full scales" are heuristics from FACS ranges and have **not** been
> calibrated on labelled data (DISFA, BP4D and others). See `audit/` in the project for the evidence review.

---

## 1. Pipeline in one picture

```
photo / video
  └─ LandmarkSource  (sources/mediapipe_source.py; MediaPipe Tasks face 478 pts, pose 33, hands 21)
       maps detector indices → named points (topology.py): 35 face, 15 body, 21 per hand
  └─ FrameObservation per frame (observations.py), internal frame: x→image right, y→UP, z→toward camera, pixels
  └─ FaceAnalyzer (analyzers/face.py)  and  BodyAnalyzer (analyzers/body.py)
       raw measurements → smoothing → personal baseline → features (0..1, degrees, SW) → events
  └─ Engine (engine.py) → report.json: meta, glossary, baseline, summary, segments, events, frames
```

**Sides.** `_l` / `_r` always mean the **subject's own** left/right. The subject's left appears on the
**image right** (x>0) when they face the camera.

**Units.**
* Face lengths: **IOD** = distance between the two eye centres (eye centre = midpoint of the inner and outer
  eye corners). IOD is about 6.3 cm on an adult. The aligned face has its origin at the nose bridge (MediaPipe pt 168), with y up.
* Body lengths: **SW** = shoulder width in pixels for that frame (2D distance between the pose shoulders).
* Angles: degrees.
* Intensities: 0..1 after `clip01`.

**Missing data.** When no face (or no visible pair of shoulders) is found in a frame, every feature of
that analyzer except `face.present` / `body.present` is NaN, and NaN values are **omitted** from the
per-frame rows in the JSON (a key is simply absent). Summary statistics ignore NaN.

---

## 2. Face: raw measurements (internal, appear in `baseline.face.measurements`)

Computed per frame in `face_measurements()` on the **aligned** face (see 2.1). Units: IOD, y up.
These raw values never appear per frame in the report; the features in section 3 are built from
their deviation from the baseline. Per side `s ∈ {l, r}`; eye centre `C_s` = midpoint of the eye corners.

| measurement | formula (aligned coords) | grows when |
|---|---|---|
| `brow_inner_h_s` | y(`s_brow_inner`) − y(C_s) | inner brow rises |
| `brow_outer_h_s` | mean y(`s_brow_mid`, `s_brow_outer`) − y(C_s) | outer brow rises |
| `eye_open_s` | mean of y(up1−lo1), y(up2−lo2) over two lid point pairs | eye opens |
| `lower_lid_h_s` | mean y(lo1, lo2) − y(C_s) | lower lid pushed up (cheek raise) |
| `nose_eye_s` | 3D distance `s_alar` ↔ `s_eye_inner` | **shrinks** on nose wrinkle |
| `corner_h_s` | y(`s_mouth_corner`) − mean y(inner lips) | lip corner goes up |
| `gaze_h_s` | (iris − C_s) projected on the eye axis (pointing to image right), in half eye-widths | iris moves to image right |
| `gaze_v_s` | y(iris − C_s) / half eye-width | iris moves up |
| `brow_gap` | x(`l_brow_inner`) − x(`r_brow_inner`) | brows move apart |
| `sub_lip` | y(subnasale) − y(upper_lip_top) | **shrinks** when the upper lip rises |
| `lip_thick` | (upper_lip_top − upper_lip_inner).y + (lower_lip_inner − lower_lip_bottom).y | **shrinks** when lips press/thin |
| `lip_gap` | y(upper_lip_inner) − y(lower_lip_inner) | lips part |
| `mouth_width` | 3D distance between mouth corners | mouth stretches |
| `jaw_open` | 3D distance nose_tip ↔ chin | jaw drops |
| `lip_chin` | y(lower_lip_bottom) − y(chin) | **shrinks** when the chin boss pushes up |

### 2.1 Alignment and head pose (`align_face`, `geometry.py`)
1. Nine rigid **anchor** points (4 eye corners, nose bridge, nose tip, 2 face sides, forehead) are fitted
   to the canonical neutral face (`topology.CANONICAL_FACE`, from MediaPipe's `canonical_face_model.obj`, IOD = 1)
   with the **Umeyama** least-squares similarity (scale + rotation + translation, reflections excluded).
2. The whole face is transformed with that similarity, then re-centred on the nose bridge and **re-scaled
   by the measured eye-centre distance**. Reason: under strong roll the detector distorts the outer face and the
   fitted scale drifts 10–15%, which used to create fake "disgust".
3. The rotation gives the head pose (section 3.1). `iod_px` (IOD in pixels) is computed but only used internally.

### 2.2 Personal baseline (`baseline.face`)
`baseline.face.method` tells which one was used:

| method | when | how |
|---|---|---|
| `neutral_reference` | `--neutral` file given and a face found in it | median of every measurement over the neutral frames (sampled at 5 fps, ≤60 s) |
| `auto_calm_frames` | ≥2 frames with a face | "calmness score" per frame = Σ \|m − clip median\| / scale over 18 measurements (brows, lids, nose, lip corners, lips, jaw; gaze excluded; scale = the full-scale constants). Only frames within 20° of the median yaw count. The calmest 30% (`baseline_quantile`) → median |
| `population_canonical` | single photo, or <2 face frames | the canonical average face (not the person!). AU values on one photo therefore include the person's **morphology** (for example naturally low brows read as AU04) |

`baseline.face.head_pose` = median yaw/pitch/roll of the same frames (0/0/0 for `population_canonical`).
`baseline.face.frames_used` = number of frames used.

### 2.3 Pose compensation (`baseline.face.pose_compensation`: true/false)
A 2D detector foreshortens the face when the head turns or pitches. When the clip is ≥3 s long and the
std of yaw or pitch is ≥3°, frames are grouped into 8°×8° yaw/pitch bins (a bin needs ≥max(3, 0.4 s) frames).
The per-bin medians are fitted with a linear model (3–7 bins) or a quadratic one (≥8 bins) in (yaw, pitch).
That pose-dependent part is subtracted from every measurement of the clip and of the neutral reference.
It is off for photos, static or short clips.

### 2.4 Smoothing
All measurements are smoothed by a centred moving average over `smoothing_s = 0.10 s`
(window = odd number of frames, ≥1). NaN-aware. Then `d_x = smoothed_x − baseline_x`.

---

## 3. Face features (per-frame rows in `frames[]`; also feed `summary` and `segments`)

Default constants are from `config.FaceConfig`; the formula shows them inline.

### 3.1 Presence, reliability, head pose

| key | meaning | how computed | units / range | caveats |
|---|---|---|---|---|
| `face.present` | a face was found | 1 if all 9 anchor points are finite | 0/1 | the only face key present on frames without a face |
| `face.reliability` | how readable the face is at this head turn | `clip01(1 − (|head.yaw_rel| − 20)/40)`: 1 up to 20° off the neutral yaw, 0 at 60° | 0..1 | AU and expression **events** are suppressed while reliability < 0.5 (± one smoothing window) |
| `head.yaw` | head turn | from the Umeyama rotation: atan2 of the face-forward vector | degrees, >0 = turned to the subject's left (image right) | absolute to the camera axis |
| `head.pitch` | head nod up/down | same | degrees, >0 = chin up | camera height biases it; use `_rel` |
| `head.roll` | head tilt in the image plane | residual rotation about z | degrees, >0 = the subject's left eye is higher | |
| `head.yaw_rel`, `head.pitch_rel`, `head.roll_rel` | the same angles minus the baseline head pose | `head.x − baseline.head_pose.x` | degrees | head-nod/shake events use these |

### 3.2 Eyes

| key | meaning | how computed | range | caveats |
|---|---|---|---|---|
| `eye.closure_l`, `eye.closure_r` | how closed each eye is vs the neutral face | `clip01(1 − eye_open_s / baseline eye_open_s)` | 0 = as open as neutral, 1 = shut | widening gives 0 (see AU05). Glasses and low resolution add noise |
| `eye.closure` | both eyes | mean of l and r | 0..1 | blink events: ≥0.5 |

### 3.3 Action units (FACS proxies)
`au.AUxx`: geometric proxy of a FACS action unit, intensity 0..1, relative to the baseline.
"Full scale" = the deviation that maps to 1.0. Lateral AUs also have `_l` and `_r` (subject sides);
the plain key is the mean of the two sides.

| key | FACS name | formula (per side, then mean) | full scale | side keys | caveats |
|---|---|---|---|---|---|
| `au.AU01` | inner brow raiser | `d brow_inner_h / 0.10` | 0.10 IOD | yes | |
| `au.AU02` | outer brow raiser | `d brow_outer_h / 0.10` | 0.10 IOD | yes | |
| `au.AU04` | brow lowerer | `max(−d brow_inner_h / 0.07, −d brow_gap / 0.07)` | 0.07 IOD | yes | pulling the brows together alone is enough (key cue in the sad brow AU1+AU4) |
| `au.AU05` | upper lid raiser (eyes widen) | `(d eye_open / base_open) / 0.35` | +35% opening | no | |
| `au.AU06` | cheek raiser | `d lower_lid_h / 0.03`; forced to 0 near a blink | 0.03 IOD | yes | proxy is "lower lid pushed up", not the cheek itself |
| `au.AU07` | lid tightener (squint) | `−(d eye_open + d lower_lid_h)/base_open / 0.40`; 0 near a blink | 40% narrowing | no | the part explained by AU6 is removed |
| `au.AU09` | nose wrinkler | `−d nose_eye / 0.05` | 0.05 IOD | no | |
| `au.AU10` | upper lip raiser | `−d sub_lip / 0.06` | 0.06 IOD | no | noisy during speech |
| `au.AU12` | lip corner puller (smile) | `d corner_h / 0.08` | 0.08 IOD | yes | speech mouth shapes can look like AU12 on low-quality video |
| `au.AU15` | lip corner depressor | `−d corner_h / 0.06` | 0.06 IOD | yes | |
| `au.AU17` | chin raiser | `−d lip_chin / 0.06` | 0.06 IOD | no | |
| `au.AU20` | lip stretcher | `(d mouth_width / 0.15) × (1 − AU12)` | 0.15 IOD | no | suppressed by a smile, because smiling also widens the mouth |
| `au.AU23` | lip tightener / presser | `−d lip_thick / 0.08` | 0.08 IOD | no | noisy during speech |
| `au.AU25` | lips part | `d lip_gap / 0.10` | 0.10 IOD | no | fires constantly in speech: no AU25 events, excluded from expressivity |
| `au.AU26` | jaw drop | `d jaw_open / 0.35` | 0.35 IOD | no | |

Every AU is clipped to 0..1, so movement in the opposite direction gives 0 (for example AU01 gives 0 when the brow is lowered).
"Near a blink" means within one smoothing window of a frame with closure ≥0.5 on that side.

### 3.4 Expression prototypes (EMFACS-style)

`expr.<name>` = **mean of the component AUs × share of components that are ≥0.2** (a soft "AND").
For `sadness`, `anger` and `disgust` the score is then multiplied by `1 − max(AU12, expr.happiness)`,
because a broad smile also moves the AU9/10/23 proxies.

| key | components | range | caveat |
|---|---|---|---|
| `expr.happiness` | AU06, AU12 | 0..1 | |
| `expr.sadness` | AU01, AU04, AU15 | 0..1 | smile-inhibited |
| `expr.surprise` | AU01, AU02, AU05, AU26 | 0..1 | |
| `expr.fear` | AU01, AU02, AU04, AU05, AU20 | 0..1 | |
| `expr.anger` | AU04, AU07, AU23 | 0..1 | smile-inhibited |
| `expr.disgust` | AU09, AU10 | 0..1 | smile-inhibited |
| `expr.contempt` | one-sided AU12 | `|AU12_l − AU12_r| × (1 − min(AU12_l, AU12_r))` | high when only one corner rises |

Psychological meaning: resemblance to a prototype display only (EMFACS). Evidence that these displays
map to felt emotion is weak and context-dependent (Barrett 2019). The feature bank tags `expr.*` as
"facial expressivity", grade B (Antonakis charismatic tactics). The intended tag for contempt is grade C,
negative for warmth (see FEATUREBANK.md, known issues).

### 3.5 Composite face values

| key | meaning | formula | range | evidence / caveats |
|---|---|---|---|---|
| `face.expressivity` | how far the face is from its neutral | RMS of the 14 AUs (all except AU25) | 0..1 (typical 0.03–0.4 on real video) | animated face is a charisma cue (B). Sensitive to detector jitter |
| `smile.duchenne` | eye-involving smile | `min(AU06, AU12)` | 0..1 | rated more genuine (Gunnery & Ruben 2016 meta, B), but it **can be posed** |
| `smile.social` | lip-only smile | `AU12 × (1 − AU06)` | 0..1 | smiling raises warmth and liking (A) |
| `asym.mouth` | lip-corner asymmetry | `clip((d corner_h_l − d corner_h_r)/0.08, −1, 1)` | −1..1, >0 = subject's left corner higher | one-sided expressions read as less genuine (C). Head yaw >20° makes it unreliable |
| `asym.brow` | brow asymmetry | `clip(((d inner_l + d outer_l) − (d inner_r + d outer_r)) / 0.20, −1, 1)` | −1..1, >0 = left brow higher | |
| `asym.eye` | eye-closure asymmetry | `clip(closure_r − closure_l, −1, 1)` | −1..1, >0 = **right** eye more closed (wink with the right eye) | note the opposite sign convention from mouth/brow |

### 3.6 Gaze

| key | meaning | formula | units | caveats |
|---|---|---|---|---|
| `gaze.h` | iris offset in the eye, horizontal | mean over eyes of `d gaze_h_s`; 0 while `eye.closure ≥ 0.5` | half eye-widths vs neutral, >0 = toward image right | needs the 478-point mesh with iris points; NaN otherwise. MediaPipe iris is weak at low resolution |
| `gaze.v` | same, vertical | mean of `d gaze_v_s` | half eye-widths, >0 = up | lids move with vertical gaze, so this is noisy |
| `gaze.dir_h_deg` | approximate gaze direction (head + eyes) | `head.yaw_rel + 35 × gaze.h` | degrees vs the neutral direction | 35° = assumed eye rotation at \|gaze.h\| = 1 (`eye_rotation_deg`), not calibrated |
| `gaze.dir_v_deg` | same, vertical | `head.pitch_rel + 35 × gaze.v` | degrees | |
| `gaze.averted` | gaze away from neutral | 1 if `hypot(dir_h, dir_v) > 15°` | 0/1 | "neutral direction" = the person's typical direction, usually the camera or the interviewer; that is **not** verified eye contact. Grade B for eye contact and liking, inverted-U |

### 3.7 Mouth activity

| key | meaning | formula | units | caveats |
|---|---|---|---|---|
| `mouth.activity` | how much the lip opening fluctuates | rolling std of the smoothed `lip_gap` over 0.5 s | IOD (typical 0.001–0.02) | |
| `mouth.speaking` | looks like speech | `mouth.activity > 0.015` | 0/1 | a visual guess, no audio. While it is 1, mouth AUs (10, 23, 25, 26) are less reliable. Chewing and laughing also trigger it |

---

## 4. Body: raw measurements (`analyzers/body.py::measure_frame`)

Uses MediaPipe Pose points with visibility ≥ 0.5 (`min_visibility`); 2D only (x, y).
If either shoulder is not visible, the whole body row is NaN. Origin = shoulder midpoint, unit = SW.

| measurement | formula |
|---|---|
| `sw_px` | shoulder width in pixels |
| `shoulder_roll` | atan2(y_l − y_r, x_l − x_r) of the shoulders, degrees |
| `lateral_lean` | atan2 of (shoulder midpoint − hip midpoint), degrees; needs both hips |
| `head_x`, `head_y` | nose position in SW (internal only) |
| `neck` | mean ear height above the shoulder line in SW |
| `wrist_x_s`, `wrist_y_s` | wrist position in SW (y>0 above the shoulders) |
| `touch_face_s` | min 2D distance from the hand points (21 hand landmarks, or the pose wrist + index if no hand was detected) to the nose, mouth corners and ears, in SW |
| `hands_dist` | min distance between the two hands' points, SW |
| `palm_s` | `palm_facing()`: normalised 2D cross product of (index MCP − wrist) × (pinky MCP − wrist), sign flipped for the left hand; +1 palm to camera, −1 back of hand |

Hands without a side label are assigned to the nearest visible pose wrist.

**Body baseline (`baseline.body`).** The method is `neutral_reference` if the `--neutral` file has a body, else `clip_median`, else `none`.
It is the median of `sw_px`, `shoulder_roll`, `lateral_lean`, `neck` and `arm_span` (= |wrist_x_l − wrist_x_r|).
`sw_px` always comes from the clip itself (resolution can differ between files). Smoothing: 0.15 s.

## 5. Body features

| key | meaning | formula | units / range | evidence and caveats |
|---|---|---|---|---|
| `body.present` | shoulders visible | 1 if both shoulders are visible | 0/1 | |
| `body.lean_in` | apparent torso size vs typical | `sw_px / baseline sw_px − 1` | ratio, >0 = closer to the camera | camera zoom and cuts fake it. Always 0 on a single photo. Forward lean: B, depends on context (good in conversation, bad for lecturers) |
| `body.shoulder_roll_rel` | shoulder-line tilt vs typical | `shoulder_roll − base` | degrees, >0 = subject's left shoulder higher | |
| `body.lateral_lean_rel` | sideways torso lean vs typical | `lateral_lean − base` (base NaN → 0) | degrees | needs the hips in view |
| `body.shrug` | shoulders raised toward the ears | `clip01(−(neck − base neck)/0.15)` | 0..1 | head pitch also changes ear height, so it can fire falsely. Shrugs mark uncertainty (C) |
| `body.hand_height_l`, `_r` | wrist height | smoothed `wrist_y_s` | SW, >0 above the shoulder line | NaN if the wrist is not visible |
| `body.gesture_speed` | fastest wrist speed relative to the torso | max over hands of \|d(wrist x,y)/dt\| | SW/s | detector jitter adds a floor. Illustrative gesturing raises persuasion and competence (B) |
| `body.gesture_activity` | normalised gesture speed | `clip01(speed / 1.5)` | 0..1 | |
| `body.gesturing` | a hand is moving | `speed > 0.6 SW/s` | 0/1 | |
| `body.hands_visible` | number of visible pose wrists | sum over sides | 0, 1, 2 | counts **pose** wrists, not hand-landmark detections. Hidden hands (podium, crop) mean no gesture conclusions |
| `body.arm_openness` | horizontal distance between the wrists | \|wrist_x_l − wrist_x_r\| | SW | |
| `body.arm_openness_rel` | same vs the person's typical | `arm_openness − base arm_span` | SW | expansive posture: grade D (power posing did not replicate) |
| `body.arms_crossed` | arms crossed | wrists swapped across the midline (`x_l < x_r`), both wrists more than 0.2 SW below the shoulders, both within 1 SW of the centre | 0/1 | "crossed arms = defensive" is folk psychology (D) |
| `body.hands_joined` | hands touching each other | `hands_dist < 0.25` and not crossed | 0/1 | clasping, steepling, wringing are not told apart. D |
| `body.face_touch` | hand near the face | min(`touch_face_l`, `touch_face_r`) < 0.30 SW | 0/1 | self-touch/adaptors are negative for observer ratings (B, Ambady & Rosenthal 1993). Proximity only, no actual contact check; a hand in front of the face in 2D counts |
| `body.palm_to_camera` | palm orientation | max(`palm_l`, `palm_r`) | −1..1 | needs hand landmarks. Unreliable when the hands overlap |
| `body.open_palms` | a palm clearly shown | `palm_to_camera > 0.5` and not crossed and not joined | 0/1 | the "open palms = honesty" claim is D |

---

## 6. Events (`events[]`)

Every event has: `source` (face/body), `type`, `start_s`, `end_s`, `duration_s`, `frame_start`, `frame_end`
(video frame numbers, inclusive). Most also have `peak` (max of the signal) and `peak_s`.
Events are sorted by `start_s`.

| type | source | trigger | extra fields | notes |
|---|---|---|---|---|
| `blink` | face | run of `eye.closure ≥ 0.5` lasting ≤ 0.5 s | peak | conversational norm about 8–26/min. A high rate reads as nervous (C) |
| `eye_closure` | face | same run, > 0.5 s | peak | |
| `action_unit` | face | `au.AUxx ≥ 0.35` (all AUs except AU25), only while the face is readable | `au`, `label`, `brief` (duration < 0.5 s) | "brief" is **not** a micro-expression claim |
| `expression` | face | `expr.<name> ≥ 0.35`, readable frames only | `expression`, `brief` | |
| `smile` | face | `au.AU12 ≥ 0.35` | `duchenne` (max AU06 in the span ≥ 0.3), `asymmetry` (mean `asym.mouth`) | not gated by reliability, unlike AU events |
| `gaze_averted` | face | `gaze.averted` for ≥ 0.3 s, gaps ≤ 0.2 s merged | peak | |
| `head_nod` | face | `head.pitch_rel` oscillation: ≥ 2 consecutive zigzag legs of ≥ 6°, each leg ≤ 0.8 s | – | nodding is a rapport cue (B) |
| `head_shake` | face | same on `head.yaw_rel` | – | |
| `gesture` | body | `body.gesturing` for ≥ 0.2 s, gaps ≤ 0.4 s merged | `peak_speed_sw_s` | |
| `face_touch`, `arms_crossed`, `hands_joined`, `open_palms` | body | flag ≥ 0.5 for ≥ 0.2 s, gaps ≤ 0.4 s merged | peak | |
| `shrug` | body | `body.shrug ≥ 0.5` | peak | no minimum duration |
| `posture_shift` | body | zigzag on `body.lean_in` with legs ≥ 0.08 | `direction` (toward_camera/away_from_camera), `delta` | camera zoom fakes it |

---

## 7. Report blocks

| key | content |
|---|---|
| `schema_version` | "1.0" |
| `generator`, `disclaimer` | engine version and the reading rules |
| `meta` | `path`, `kind` (image/video), `fps` (1.0 for a photo), `width`, `height`, `detector`, `frames`, `duration_s`, `analyzers` |
| `glossary` | short text for each feature family (the one-line version of this file) |
| `baseline.face` | `method`, `frames_used`, `measurements` (section 2), `head_pose`, `pose_compensation` |
| `baseline.body` | `method`, `frames_used`, `measurements` (`sw_px`, `shoulder_roll`, `lateral_lean`, `neck`, `arm_span`) |
| `summary.face` | see the table below |
| `summary.body` | `body_visible`, `hands_visible_mean`, `gesturing_share`, `gesture_activity_mean`, `face_touch_share`, `arms_crossed_share`, `hands_joined_share`, `open_palms_share`, `arm_openness_mean`, `arm_openness_rel_mean`, `lean_in_mean`, `shoulder_roll_rel_mean`, `shrug_peak` (shares = fraction of finite observations of the corresponding feature where the flag > 0.5; null without observations) |
| `summary.event_counts` | number of events per type |
| `summary.highlights` | ready-made English sentences (dominant expression, blink rate vs 8–26/min only if the clip is ≥ 10 s, smile counts with Duchenne / one-sided (\|asymmetry\| ≥ 0.4), brief AU movements, nods/shakes, gaze-averted share, body shares, face touches, posture shifts) |
| `segments[]` | the same summary over windows of `--segment` seconds (default 5) plus `event_counts` (by the event's first frame) and `notable_vs_clip` |
| `frames[]` | per-frame rows `{i: frame index, t: seconds, <feature>: value}`; values rounded to 3 decimals; NaN omitted. Row density is set by `--frames-fps` (default **5** for `analyze`, **0 = none** for `demo`) |

`summary.face` fields:

| field | meaning |
|---|---|
| `face_visible` | share of frames with a face |
| `action_units` | `{AUxx: {mean, peak}}`, **only AUs whose peak ≥ 0.2** |
| `expressions_mean` | mean of every `expr.*` |
| `dominant_expression` | the expression with the highest mean if that mean is ≥ 0.15, else `"neutral"` |
| `expressivity_mean` | mean `face.expressivity` |
| `smile.duchenne_mean`, `smile.social_mean` | means |
| `asymmetry_mean` | means of `asym.mouth`, `asym.brow`, `asym.eye` |
| `blinks`, `blink_rate_per_min` | blink events starting in the range; rate = blinks / (frames / fps / 60) |
| `head.{yaw,pitch,roll}_mean` | means of the `_rel` angles |
| `head.movement_std_deg` | mean of std(yaw_rel) and std(pitch_rel) |
| `gaze_averted_share`, `speaking_share` | shares of face frames |
| `reliability_mean` | mean `face.reliability` |

`notable_vs_clip` compares 7 segment metrics with the whole clip (expressivity, blink rate, gaze averted,
gesturing, face touch, arms crossed, open palms) and lists those where
`|segment − clip| ≥ max(0.1, 0.5 × |clip|)`.

---

## 8. Reference ranges seen on real video

From `visual-tests/male-report.json` (MediaPipe, 768×432, 12 fps, 134 s, head-pose test clip, no hands
visible). Use these as sanity ranges, not norms.

| key | p5 | median | p95 | max |
|---|---|---|---|---|
| `head.yaw_rel` | −10.5 | 0.0 | 7.2 | 68.6 |
| `head.roll_rel` | −23.8 | 0.1 | 11.5 | 43.0 |
| `eye.closure` | 0 | 0.02 | 0.49 | 0.97 |
| `au.AU12` | 0 | 0.003 | 0.31 | 1.0 |
| `au.AU07` | 0 | 0.02 | 0.60 | 1.0 |
| `face.expressivity` | 0.03 | 0.10 | 0.42 | 0.60 |
| `mouth.activity` | 0.001 | 0.004 | 0.021 | 0.09 |
| `face.reliability` | 0.21 | 1.0 | 1.0 | 1.0 |
| `gaze.h` | −0.13 | −0.006 | 0.07 | 0.31 |

Male clip events: 31 blinks (13.9/min), 138 AU events (95 brief), 12 expression events, 1 nod, 1 shake, 9 gaze-averted.
Female clip: 30 blinks (13.4/min), 269 AU events, 35 smiles (7 Duchenne), 11 posture shifts.
Mostly brief AU06/AU07/AU09 events on a calm face are typical **detector noise** at this resolution.


## Additions verified on 2026-11-24

`meta.engine_config` records the effective Engine/Face/Body configuration.
`eye.closed80` is bilateral relative geometric closure >=0.8, excluding unreliable observations.
Face summaries include observed eye seconds, closed80 share, share of closures >=0.5 s,
longest closure, and mean/p90 head angle-derivative norm. `head.angular_speed_deg_s`
uses wrapped Euler differences; `head.angular_accel_deg_s2` is its absolute derivative.
These are geometric quantities; closed80 is not calibrated pupil occlusion/PERCLOS.
No derivatives cross missing frames. First-frame velocity is unavailable.

Hidden wrists/palms produce missing behavior flags. Shares use each channel's finite
observations, with null for zero coverage. A missing gesture is not recorded as a negative.
`blink_release_closure=None` preserves default blink boundaries. Explicit 0.25 expands
boundaries around high-threshold samples; evaluation found higher precision but lower recall/F1.
See BENCHMARKS.md for the measured tradeoff and TEST_RESULTS.md for verification.
