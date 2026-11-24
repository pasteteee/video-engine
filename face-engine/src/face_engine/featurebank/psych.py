"""Research tags for feature names.

Each rule maps a feature-name pattern to the psychological dimensions it feeds, the direction
the literature reports for observer liking/trust, an evidence grade and a short source note.
Direction is a prior for the interpreting model, not a score: context can reverse it.

Grades: A = meta-analysis or well replicated; B = replicated or large single study;
C = single study / small sample; D = practitioner claim or contested.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Tag:
    factor: str
    dims: tuple[str, ...]
    direction: str  # "+", "-", "inverted-U", "context"
    grade: str
    note: str


RULES: list[tuple[str, Tag]] = [
    # ---------------- face
    (r"^(au\.AU12|smile\.social|geo\.lip_corner_lift)\|", Tag("smiling", ("warmth", "positivity"), "+", "A", "Smiling raises warmth/liking; Ambady & Rosenthal 1993 thin slices (r~.7 HS teachers); LaFrance 2003")),
    (r"^(au\.AU06|smile\.duchenne)\|", Tag("eye-involved (Duchenne) smile", ("warmth", "positivity"), "+", "B", "AU6+AU12 rated more genuine (Gunnery & Ruben 2016 meta); can be posed")),
    (r"^event\.smile\.(duration|interval)", Tag("smile timing", ("trust",), "+ slow onset/offset", "C", "Slow-onset/offset smiles look more trustworthy, more trust-game cooperation (Krumhuber 2007)")),
    (r"^(au\.AU04|geo\.brow_gap)\|", Tag("frowning / brow lowering", ("warmth",), "-", "B", "Frowning -.46 with teacher ratings (Ambady & Rosenthal 1993)")),
    (r"^(au\.AU01|au\.AU02|geo\.brow_height|geo\.brow_inner_height)\|", Tag("brow raising / eyebrow flash", ("expressiveness", "attentiveness"), "context", "C", "Brow raises mark emphasis and interest; inner-brow raise reads as sad/trustworthy in Todorov-type models")),
    (r"^(face\.expressivity|expr\.)", Tag("facial expressivity", ("charisma", "expressiveness"), "+", "B", "Animated facial expression is one of Antonakis's 12 charismatic tactics")),
    (r"^(expr\.contempt|au\.AU14)", Tag("contempt-like display", ("warmth",), "-", "C", "Unilateral lip-corner tightening read as contempt")),
    (r"^(au\.AU15|au\.AU17|au\.AU23|au\.AU24)\|", Tag("lip press / chin raise / corner depress", ("warmth", "composure"), "-", "C", "Tension displays; read as doubt or restraint")),
    (r"^asym\.", Tag("facial asymmetry", ("trust",), "-", "C", "Asymmetric (one-sided) expressions read as less genuine")),
    # ---------------- eyes
    (r"^(gaze\.averted|gaze\.dir|geo\.iris)", Tag("gaze toward listener / camera", ("attentiveness", "trust", "dominance"), "+ (moderate)", "B", "Eye contact raises liking up to a point; preferred mutual gaze ~3.3 s (Binetti 2016); averting while thinking is normal")),
    (r"^cross\.(gaze_on|visual_dominance)", Tag("visual dominance ratio", ("dominance",), "context", "B", "Looking more while speaking than while listening signals dominance (Exline/Dovidio 1988)")),
    (r"^(event\.blink|eye\.closure|geo\.eye_open)", Tag("blink rate / eye closure", ("composure",), "- if high", "C", "High blink rate read as nervousness (Omori 1997); long listener blinks act as feedback (Homke 2018)")),
    # ---------------- head
    (r"^(event\.head_nod|align\.head_nod)", Tag("nodding", ("attentiveness", "warmth", "coordination"), "+", "B", "Nodding +.38 (Ambady & Rosenthal 1993); rapport correlate (Tickle-Degnen & Rosenthal 1990)")),
    (r"^(kin\.head_|head\.(yaw|pitch|roll)|kin\.head_head)", Tag("head movement", ("expressiveness", "charisma"), "inverted-U", "C", "Head motion marks prosodic emphasis; freezing reads stiff, constant jitter reads restless")),
    (r"^(head\.pitch|geo\.head_over)", Tag("head tilt down/up", ("dominance",), "context", "B", "Head tilted down looks more dominant via apparent brow lowering (Witkower & Tracy 2019)")),
    (r"^(head\.roll|geo\.head_tilt_2d)", Tag("lateral head tilt", ("warmth",), "context", "D", "Popular warmth claim; weak evidence")),
    # ---------------- body
    (r"^(body\.gesture|event\.gesture|kin\.geo_wrist|geo\.wrist|geo\.hands_spread)", Tag("illustrative gesturing", ("competence", "charisma", "persuasion"), "+", "B", "Illustrative gestures raised persuasion and perceived competence in 2,184 TED talks (Zhou, Cascio Rizzo & Berger 2025); animated gestures in Antonakis CLTs")),
    (r"^align\.gesture", Tag("gesture-speech synchrony", ("fluency", "competence"), "+", "C", "Strokes landing on stressed syllables; decoupled movement reads as fidgeting")),
    (r"^(body\.face_touch|event\.face_touch|geo\.hands_to_face)", Tag("self-touch / adaptors", ("composure",), "-", "B", "Hand fidgeting -.70 with teacher ratings (Ambady & Rosenthal 1993)")),
    (r"^(body\.open_palms|body\.palm_to_camera|event\.open_palms)", Tag("open palms", ("warmth", "trust"), "+", "D", "Practitioner claim; no verified effect size")),
    (r"^(body\.arms_crossed|body\.hands_joined)", Tag("closed arms", ("warmth",), "-", "D", "Commonly claimed; weak evidence")),
    (r"^(body\.lean_in|geo\.face_scale|kin\.geo_face_scale)", Tag("forward lean / approach", ("attentiveness", "immediacy"), "context", "B", "Rapport correlate in conversation; negative for lecturers (Ambady & Rosenthal 1993); confounded by camera zoom")),
    (r"^(body\.arm_openness|geo\.elbow_spread|geo\.shoulder_width)", Tag("expansive posture", ("dominance",), "context", "D", "Power-posing effects on the poser failed to replicate (Ranehill 2015); observer effects small")),
    (r"^(body\.shrug|event\.shrug|body\.shoulder|geo\.shoulder_tilt)", Tag("shrugs / shoulder movement", ("composure",), "context", "C", "Shrugs mark uncertainty")),
    (r"^(event\.posture_shift|kin\.geo_torso|kin\.geo_face_c)", Tag("fidgeting / body sway", ("composure",), "-", "B", "Fidgeting negatively related to observer ratings")),
    # ---------------- voice
    (r"^voice\.pitch_(st|hz)\|.*\|(std|iqr|range_p95_p05|p95|p05|mean_abs_delta)", Tag("pitch variability", ("charisma", "expressiveness"), "+", "B", "Wider F0 range/variability raises perceived charisma (Niebuhr 2016; Rosenberg & Hirschberg 2005)")),
    (r"^voice\.pitch_hz\|.*\|(mean|median)", Tag("pitch level", ("dominance", "competence"), "- (lower = more dominant)", "B", "Lower pitch within sex -> perceived dominance/leadership (Klofstad 2012/2015)")),
    (r"^voice\.loudness_db", Tag("loudness and its variation", ("charisma", "dominance"), "+ variation", "C", "Animated voice is an Antonakis CLT; emphasis via intensity peaks")),
    (r"^voice\.(jitter|shimmer|spectral_flatness)", Tag("voice roughness / breathiness", ("composure",), "context", "C", "Perturbation measures; smooth voices rated more attractive (Bruckert)")),
    (r"^voice\.(spectral_tilt|spectral_centroid|mfcc)", Tag("voice timbre", ("warmth",), "context", "C", "Timbre feeds first impressions (McAleer 2014 'hello' study: trust/dominance from one word)")),
    (r"^timing\.(articulation_rate|speech_rate|wpm)|^lang\.words_per_min", Tag("speech rate", ("competence", "warmth"), "inverted-U", "B", "Faster -> more competent; very fast -> less benevolent (6 studies, N=3,958)")),
    (r"^timing\.(pause|pauses|long_pause|silence)", Tag("pausing", ("fluency", "charisma"), "context", "C", "Strategic pauses after key points; many short hesitations read as disfluency")),
    (r"^timing\.filled_pauses|^lang\.filler", Tag("filled pauses (um/uh)", ("competence",), "-", "B", "Fewer fillers predicted interview ratings (Naim et al., MIT); powerless speech (Hosman 2002)")),
    (r"^timing\.clause_terminal_rise", Tag("uptalk / rising terminals", ("competence",), "-", "C", "Rising terminals on statements read as less certain")),
    (r"^timing\.(clause_pitch_range|pitch_reset)", Tag("phrase-level melody", ("charisma",), "+", "C", "Pitch resets start new idea units")),
    # ---------------- language
    (r"^lang\.(pron_you|ratio\.you_vs_i|questions\.with_you)", Tag("listener focus ('you')", ("warmth", "attentiveness"), "+", "C", "Higher-status speakers use fewer 'I' and more 'you/we' (Kacewicz/Pennebaker 2014)")),
    (r"^lang\.(pron_we|ratio\.we_vs_i)", Tag("collective 'we'", ("warmth", "leadership"), "+", "B", "'We' over 'I' predicted interview ratings (Naim et al.); collective sentiment is an Antonakis CLT")),
    (r"^lang\.(pron_i|first_person_opening)", Tag("self-focus ('I')", ("status",), "- (high = lower status)", "B", "Kacewicz et al. 2014; also linked to distress")),
    (r"^(lang\.questions|timing\.pause_after_question)", Tag("question asking", ("warmth", "attentiveness"), "+ (in conversation)", "B", "More (follow-up) questions -> more liking, d=.35/.27 (Huang 2017); in speeches = rhetorical questions (CLT)")),
    (r"^lang\.(hedge|tentative|ratio\.certainty)", Tag("hedges / powerless speech", ("competence",), "-", "B", "Hedges and hesitations lower perceived control (eta2~.25) but not sociability (Hosman 2002)")),
    (r"^lang\.(certainty|absolutist)", Tag("certainty / absolutist words", ("competence", "warmth"), "context", "C", "Certainty reads confident; absolutist words track anxiety (Al-Mosaiwi 2018)")),
    (r"^lang\.(posemo|ratio\.posemo|gratitude|politeness|affiliation)", Tag("positive / affiliative language", ("warmth", "positivity"), "+", "B", "Gratitude roughly doubled further helping (Grant & Gino 2010)")),
    (r"^lang\.(negemo|anxiety|negation)", Tag("negative language", ("positivity",), "-", "C", "Attack/negativity lowers warmth (Benoit functional theory: winners acclaim more)")),
    (r"^lang\.(anaphora|repeated_|and_lists|contrast_pairs|superlative|moral)", Tag("rhetorical devices (lists, contrasts, repetition, moral conviction)", ("charisma",), "+", "B", "Antonakis charismatic leadership tactics; trainable")),
    (r"^lang\.(numbers|number_word|money|quantifier)", Tag("specificity / numbers", ("competence",), "+", "C", "Concrete, specific language signals listening/competence (Packard & Berger)")),
    (r"^lang\.(flesch|fk_grade|syllables|mean_word_len|long_words|clause_len)", Tag("processing fluency", ("fluency",), "+ simpler", "B", "Easier-to-process language is liked and believed more (Reber 2004; Oppenheimer 2006)")),
    (r"^lang\.(type_token|mattr|hapax)", Tag("lexical diversity", ("competence",), "+", "C", "More unique words predicted interview ratings (Naim et al.)")),
    (r"^lang\.(future|past|ratio\.future)", Tag("future orientation", ("leadership",), "+", "C", "Vision/high expectations are CLTs")),
    (r"^lang\.because", Tag("'because' justifications", ("persuasion",), "+ (weak)", "D", "Langer 1978; recent critiques")),
    (r"^lang\.self_repairs", Tag("self-repairs / repetitions", ("fluency",), "-", "C", "Disfluency")),
    # ---------------- cross-modal / alignment
    (r"^cross\.xcorr\.kin\.head|^cross\.corr\.kin\.head.*voice", Tag("head-voice coupling", ("coordination", "charisma"), "+", "C", "Head movement aligned with prosodic peaks")),
    (r"^cross\.(xcorr|corr)\.au\.AU0[12]", Tag("brow-voice coupling", ("expressiveness",), "+", "C", "Brow raises on emphasised words")),
    (r"^align\.blink", Tag("blink placement", ("composure", "fluency"), "context", "C", "Blinks at pauses/clause ends are normal punctuation; mid-word blink bursts read nervous")),
    (r"^align\.smile", Tag("smile placement", ("warmth",), "context", "C", "Smiles at clause ends/punchlines vs mid-attack")),
    (r"^align\.gaze_averted", Tag("gaze aversion placement", ("fluency",), "context", "B", "Averting at clause start = planning (normal); at clause end = avoids feedback")),
    (r"^cross\.corr\.", Tag("multimodal coupling", ("coordination",), "context", "C", "Within-person coherence of face, body and voice")),
    (r"^meta\.", Tag("reliability", ("meta",), "context", "A", "Coverage and quality; use to discount features")),
]

_COMPILED = [(re.compile(p), t) for p, t in RULES]


def tag(name: str) -> Tag | None:
    for rx, t in _COMPILED:
        if rx.search(name):
            return t
    return None


DIMENSIONS = {
    "warmth": "Is this person on my side? (Fiske/Cuddy SCM: judged first, drives liking)",
    "competence": "Can they act on it? (SCM second axis)",
    "dominance": "Influence by force; separate from liking, mildly disliked (Cheng 2013)",
    "status": "Prestige/standing signals in language",
    "trust": "Trustworthiness (Todorov face model axis 1)",
    "attentiveness": "Rapport triad 1 (Tickle-Degnen & Rosenthal)",
    "positivity": "Rapport triad 2 (matters most early)",
    "coordination": "Rapport triad 3 (matters most later); synchrony, mimicry",
    "charisma": "Antonakis CLTs: animated voice/face/gesture, rhetorical devices",
    "expressiveness": "Overall animation",
    "composure": "Calm vs nervous-looking behaviour",
    "fluency": "Ease of processing (Reber 2004)",
    "persuasion": "Attitude change",
    "leadership": "Collective vision signals",
    "immediacy": "Approach/closeness cues (Mehrabian)",
}
