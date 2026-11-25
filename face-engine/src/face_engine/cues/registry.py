"""The behaviour cues tracked by the deviation layer, with their research notes.

Every cue is a plain, observable quantity measured in sliding windows and compared
with the same person's own baseline. ``direction`` says which way of moving away from
the baseline the literature links to load, arousal or tension:

* ``up``   - more than usual is the reported change (e.g. pitch, lip press)
* ``down`` - less than usual is the reported change (e.g. illustrator gestures)
* ``both`` - either way is worth flagging (e.g. head movement: freezing or agitation)

Grades follow ``featurebank/psych.py``: A = meta-analytic or well replicated,
B = replicated or large single study, C = single study / small sample,
D = practitioner claim or contested. No cue is a lie cue on its own: meta-analyses
find small, heterogeneous effects (DePaulo et al. 2003; Sporer & Schwandt 2006/2007;
Luke 2019), so the output is a map of deviations, never a verdict.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Cue:
    id: str
    channel: str  # face | eyes | head | body | hands | voice | speech | mismatch
    label: str  # short caption, safe to put on screen
    unit: str
    direction: str  # up | down | both
    zone: str  # overlay zone: brow | eyes | mouth | face | head | shoulders | hands | torso | voice
    grade: str
    note: str
    needs: str = "video"  # video | audio | words


CHANNELS = ("face", "eyes", "head", "body", "hands", "voice", "speech", "mismatch")

CUES: tuple[Cue, ...] = (
    # ---------------------------------------------------------------- face (FACS proxies)
    Cue("lip_press", "face", "lip press", "0..1", "up", "mouth", "B",
        "AU23/24 with lips closed. Lip pressing d~0.16 in DePaulo 2003; read as restraint."),
    Cue("chin_raise", "face", "chin raise", "0..1", "up", "mouth", "B",
        "AU17. Chin raise d~0.25 in DePaulo 2003; suppressing an expression."),
    Cue("lip_corner_depress", "face", "mouth corners down", "0..1", "up", "mouth", "C",
        "AU15, part of the sadness prototype; often with AU17 as a 'doubt' face."),
    Cue("brow_lower", "face", "brow lowered", "0..1", "up", "brow", "C",
        "AU4: effort, concentration or disagreement (Ekman & Friesen 1978)."),
    Cue("inner_brow_raise", "face", "inner brows up", "0..1", "up", "brow", "C",
        "AU1 without AU2: distress / sadness brow (Ekman 2003)."),
    Cue("eyes_widen", "face", "eyes widened", "0..1", "up", "eyes", "C",
        "AU5, part of fear and surprise prototypes."),
    Cue("lid_tighten", "face", "lids tightened", "0..1", "up", "eyes", "C",
        "AU7, anger prototype and concentration."),
    Cue("lip_stretch", "face", "lips stretched", "0..1", "up", "mouth", "C",
        "AU20, fear prototype; rare in calm speech."),
    Cue("disgust_face", "face", "nose/upper lip raised", "0..1", "up", "mouth", "C",
        "AU9/AU10 disgust prototype."),
    Cue("social_smile", "face", "lip-only smile", "0..1", "up", "mouth", "B",
        "AU12 without AU6. Duchenne vs lip-only smile (Gunnery & Ruben 2016); can be posed."),
    Cue("one_sided_mouth", "face", "one-sided mouth", "0..1", "up", "mouth", "C",
        "Unilateral lip-corner movement (contempt prototype) and mouth asymmetry."),
    Cue("lip_suck", "face", "lips pulled in", "0..1", "up", "mouth", "C",
        "Red lip disappearing with the mouth closed: lips sucked in or bitten (AU28/AU32 "
        "proxy) or a hard press. Read as holding back / discomfort (Ekman 2003; Navarro)."),
    Cue("micro_twitch", "face", "micro twitches", "per min", "up", "face", "C",
        "Any AU rising above the person's own 95th percentile and falling back within 0.5 s. "
        "Porter & ten Brinke 2008: true micro-expressions are rare (~2%) and occur in truthful "
        "people too."),
    Cue("expressivity", "face", "facial movement", "0..1", "both", "face", "C",
        "Overall facial activity. A drop can be masking or control, a rise arousal."),
    # ---------------------------------------------------------------- eyes
    Cue("blink_rate", "eyes", "blink rate", "per min", "both", "eyes", "B",
        "Cognitive load suppresses blinking, followed by a rebound (Leal & Vrij 2008); "
        "arousal raises it. Blinks alone: d~0.07 in DePaulo 2003."),
    Cue("long_closures", "eyes", "long eye closures", "share", "up", "eyes", "C",
        "Eye closures over 0.5 s: eye blocking / disengagement (Navarro, practitioner)."),
    Cue("gaze_aversion", "eyes", "gaze averted", "share", "up", "eyes", "B",
        "Looking away reduces cognitive load (Glenberg 1998; Doherty-Sneddon 2005). Not a lie "
        "cue: gaze aversion d~0.03 in DePaulo 2003."),
    Cue("gaze_shifts", "eyes", "gaze shifts", "per min", "up", "eyes", "C",
        "How often gaze leaves and returns; restlessness."),
    # ---------------------------------------------------------------- head
    Cue("head_motion", "head", "head movement", "deg/s", "both", "head", "C",
        "Freezing (Vrij 2008 'behavioural control') or agitation, relative to the person."),
    Cue("head_nods", "head", "nods", "per min", "both", "head", "C",
        "Nodding d~-0.01 overall in DePaulo 2003; useful mainly against what is said."),
    Cue("head_shakes", "head", "head shakes", "per min", "up", "head", "C",
        "Head shakes; meaningful when they contradict the words."),
    Cue("head_down", "head", "head lowered", "deg", "up", "head", "C",
        "Head pitched down vs own baseline: shame / submission displays (Tracy & Matsumoto 2008)."),
    # ---------------------------------------------------------------- body
    Cue("lean_back", "body", "leans back", "rel. size", "up", "torso", "C",
        "Torso moving away from the camera (withdrawal); camera zoom confounds it."),
    Cue("posture_shifts", "body", "posture shifts", "per min", "up", "torso", "C",
        "Shifts toward/away from camera. DePaulo 2003: posture shifts d~0.05 (weak)."),
    Cue("shrugs", "body", "shrugs", "per min", "up", "shoulders", "C",
        "Shoulder shrugs mark uncertainty (Ekman & Friesen 1969 emblems)."),
    Cue("arms_crossed", "body", "arms crossed", "share", "up", "hands", "D",
        "Closed arms; popular claim, weak evidence. Also comfort or habit."),
    Cue("body_motion", "body", "body movement", "SW/s", "both", "torso", "C",
        "Torso sway. Liars often move less (behavioural control, Vrij 2008); "
        "fidgeting reads nervous."),
    # ---------------------------------------------------------------- hands
    Cue("illustrators", "hands", "speech gestures", "share", "down", "hands", "B",
        "Gestures that illustrate speech. Fewer illustrators d~-0.14 (DePaulo 2003); "
        "drop under cognitive load (Vrij 2008)."),
    Cue("self_touch_face", "hands", "touches face", "share", "up", "face", "C",
        "Hand to face/mouth/nose. Self-adaptors rise with anxiety (Ekman & Friesen 1972; "
        "Harrigan 1985); no reliable link to lying."),
    Cue("self_touch_neck", "hands", "touches neck", "share", "up", "head", "D",
        "Hand to neck/throat; pacifying behaviour (Navarro, practitioner)."),
    Cue("self_touch_head", "hands", "touches head/hair", "share", "up", "head", "D",
        "Hand above the eyes / on the head or hair."),
    Cue("hand_wringing", "hands", "hands together", "share", "up", "hands", "C",
        "Hands touching each other (clasping, rubbing, wringing): object-free adaptor."),
    # ---------------------------------------------------------------- voice
    Cue("pitch", "voice", "voice pitch", "semitones", "up", "voice", "B",
        "Higher F0 under arousal; pitch d~0.21 in DePaulo 2003, positive in Sporer & "
        "Schwandt 2006."),
    Cue("pitch_variability", "voice", "pitch range", "semitones", "both", "voice", "C",
        "Flattened or exaggerated melody vs own speech."),
    Cue("loudness", "voice", "loudness", "dB", "both", "voice", "C",
        "Level vs own speech; bursts or swallowing the voice."),
    Cue("voice_tension", "voice", "voice tension", "rel.", "up", "voice", "C",
        "Frame-to-frame pitch/level perturbation (jitter/shimmer-like) and brighter "
        "spectrum. Vocal tension d~0.26 in DePaulo 2003 (rated, not acoustic)."),
    Cue("silence", "voice", "silence in answers", "share", "up", "voice", "B",
        "Unfilled pauses: hesitation under load (Goldman-Eisler 1968; Vrij 2008)."),
    # ---------------------------------------------------------------- speech (needs words)
    Cue("speech_rate", "speech", "speech rate", "words/min", "both", "voice", "C",
        "No reliable rate difference in Sporer & Schwandt 2006; still a load marker "
        "relative to the same person.", "words"),
    Cue("fillers", "speech", "um / uh", "per min", "up", "voice", "B",
        "Filled pauses: disfluency, planning (Clark & Fox Tree 2002).", "words"),
    Cue("hedges", "speech", "hedges", "per min", "up", "voice", "B",
        "'I think', 'maybe', 'to be honest', 'I believe': tentative / qualifying language "
        "(Hosman 2002; Newman et al. 2003 for qualifiers).", "words"),
    Cue("non_recall", "speech", "can't recall", "per min", "up", "voice", "C",
        "'I don't know / recall / remember'. Count only: honest people forget too.", "words"),
    Cue("repairs", "speech", "self-repairs", "per min", "up", "voice", "C",
        "Repeated words and restarts. Speech errors positive in Sporer & Schwandt 2006.",
        "words"),
    Cue("response_latency", "speech", "answer delay", "s", "up", "voice", "B",
        "Time from end of the question to first word. Longer latency positive in Sporer & "
        "Schwandt 2006 (small, heterogeneous).", "words"),
    # ---------------------------------------------------------------- mismatches
    Cue("yes_no_mismatch", "mismatch", "word vs head", "count", "up", "head", "C",
        "'Yes' with a head shake or 'no' with a nod within 1 s: emblematic slip "
        "(Ekman & Friesen 1969 leakage).", "words"),
    Cue("certainty_shrug", "mismatch", "sure + shrug", "count", "up", "shoulders", "D",
        "Certainty words with a shrug within 1 s (practitioner claim).", "words"),
)

CUE_BY_ID = {c.id: c for c in CUES}

DISCLAIMER = (
    "Behaviour map, not a lie detector. Each value is this person's deviation from their own "
    "baseline in the same recording. Meta-analyses find no single reliable cue to deception "
    "(DePaulo et al. 2003; Bond & DePaulo 2006: people detect lies ~54% of the time), and every "
    "cue here also rises with stress, fatigue, cognitive effort, illness, camera angle or simply "
    "the topic. A hotspot means 'several channels changed at once', which is a reason to look "
    "closer at that moment, nothing more. Word any on-screen read as opinion."
)
