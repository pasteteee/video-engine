"""Scene library: every scene type the director may put in a shot list.

A scene type is data, not code: the renderer (Remotion kit of the channel) has
one component per type and builds it from `shot.params` and `shot.media_ids`.
Registers say what kind of picture the viewer sees:

- archival: a real record (photo, film, document, audio, data plot of real data)
- blueprint: drawn graphics in the channel style (maps, charts, diagrams, type)
- illustration: generated picture of what nobody filmed, always labelled
"""
from __future__ import annotations

from dataclasses import dataclass

ARCHIVAL, BLUEPRINT, ILLUSTRATION = "archival", "blueprint", "illustration"
REGISTERS = (ARCHIVAL, BLUEPRINT, ILLUSTRATION)


@dataclass(frozen=True)
class SceneType:
    name: str
    register: str
    what: str
    needs_media: bool = False
    static_risk: bool = False  # tends to look frozen; must declare `motion`
    variants: tuple[str, ...] = ()  # composition/motion variants the kit implements


_LIB = [
    # archival
    SceneType("photo_parallax", ARCHIVAL, "Real photo split into depth layers, slow 2.5D camera move", True),
    SceneType("photo_lighttable", ARCHIVAL, "Photo on the light table with amber brackets and credit line", True, True),
    SceneType("photo_detail_zoom", ARCHIVAL, "Push from the whole photo into one detail, circle or underline lands", True),
    SceneType("photo_compare", ARCHIVAL, "Two photos side by side or before/after wipe", True),
    SceneType("film_clip", ARCHIVAL, "Archival film or video clip, graded and framed", True),
    SceneType("film_freeze_annotate", ARCHIVAL, "Clip plays, freezes, annotation draws on the frame", True),
    SceneType("document_highlight", ARCHIVAL, "Scanned page, camera glides to a line, highlighter sweeps it", True),
    SceneType("transcript_waveform", ARCHIVAL, "Real audio with waveform and typed transcript in sync", True),
    SceneType("quote_card", ARCHIVAL, "Verbatim quote of a real person with portrait and source", True, True),
    SceneType("data_plot_real", ARCHIVAL, "Plot of real measured data (sensor, recorder, survey) drawing itself", True),
    SceneType("satellite_reveal", ARCHIVAL, "Satellite or space image, slow zoom from orbit to the place", True),
    SceneType("stock_broll", ARCHIVAL, "Licensed stock footage for context (sea, sky, city)", True),
    # blueprint
    SceneType("globe_route", BLUEPRINT, "3D globe, route draws with glowing core, subject marker travels"),
    SceneType("map_zoom", BLUEPRINT, "Flat map, zoom from region to point, labels type on"),
    SceneType("map_compare_scale", BLUEPRINT, "Outline of A laid over B to show size"),
    SceneType("chart_line_draw", BLUEPRINT, "Line chart drawing left to right, key point flagged"),
    SceneType("chart_bar_race", BLUEPRINT, "Bars grow or race, the hero bar in accent"),
    SceneType("big_number", BLUEPRINT, "One number counts up in brackets, unit and meaning under it"),
    SceneType("counter_ticker", BLUEPRINT, "Running counter or clock while narration moves on"),
    SceneType("timeline_scroll", BLUEPRINT, "Horizontal timeline, camera travels to the date"),
    SceneType("diagram_build", BLUEPRINT, "Schematic builds part by part (machine, process, cause chain)"),
    SceneType("cutaway_section", BLUEPRINT, "Cross-section of an object or the ground/ocean with depth labels"),
    SceneType("scale_compare", BLUEPRINT, "Objects lined up by size or distance, camera dollies along"),
    SceneType("kinetic_type", BLUEPRINT, "Words of the line land one by one in sync with the voice"),
    SceneType("chapter_card", BLUEPRINT, "Chapter number and title, short, with sound hit"),
    SceneType("split_screen", BLUEPRINT, "Two or three panels that run at once (then vs now, A vs B)"),
    SceneType("question_card", BLUEPRINT, "The episode question or the viewer's choice, held on screen"),
    SceneType("formula_card", BLUEPRINT, "The one formula of the episode, terms light up as they are named"),
    SceneType("evidence_board", BLUEPRINT, "Pinned cards and photos linked by strings, camera drifts"),
    # illustration
    SceneType("illus_animated", ILLUSTRATION, "Generated still animated by an image-to-video model", True),
    SceneType("illus_parallax", ILLUSTRATION, "Generated still split in layers, 2.5D move and particles", True),
    SceneType("illus_reconstruction", ILLUSTRATION, "Reconstruction of a moment nobody filmed, marked RECONSTRUCTION", True),
]

# Variants: each library scene has 2+ ways to look, so two episodes never cut the same.
VARIANTS: dict[str, tuple[str, ...]] = {
    "photo_parallax": ("push_in", "lateral_drift", "rack_focus"),
    "photo_lighttable": ("single_print", "contact_strip", "stack_shuffle"),
    "photo_detail_zoom": ("circle_lands", "crop_marks", "magnifier"),
    "photo_compare": ("side_by_side", "wipe", "flip"),
    "film_clip": ("full_frame", "projector_flicker", "split_reel"),
    "film_freeze_annotate": ("freeze_trace", "freeze_callouts"),
    "document_highlight": ("glide_marker", "redaction_lift", "typewriter_overlay"),
    "transcript_waveform": ("waveform_wide", "reel_to_reel"),
    "quote_card": ("words_with_voice", "portrait_side", "handwritten_source"),
    "data_plot_real": ("line_draw", "scope_trace"),
    "satellite_reveal": ("orbit_dive", "tile_assemble"),
    "stock_broll": ("graded", "split_tone"),
    "globe_route": ("night_side", "terminator_line", "flat_unroll"),
    "map_zoom": ("dive", "pan_along", "topo_lines"),
    "map_compare_scale": ("overlay_drop", "outline_morph"),
    "chart_line_draw": ("draw_flag", "scrub_cursor"),
    "chart_bar_race": ("race", "stack_build"),
    "big_number": ("odometer", "unredact", "fill_count"),
    "counter_ticker": ("clock_dial", "flip_digits", "mission_clock"),
    "timeline_scroll": ("rail_travel", "calendar_tear", "vertical_drop"),
    "diagram_build": ("part_by_part", "exploded", "trace_flow"),
    "cutaway_section": ("slice_reveal", "depth_drop"),
    "scale_compare": ("dolly_line", "stack_up"),
    "kinetic_type": ("rise_narrow", "unredact", "stagger_weight", "type_on"),
    "chapter_card": ("hairline_index", "unredact", "big_index"),
    "split_screen": ("two_up", "three_up"),
    "question_card": ("unredact", "rise_narrow", "hold_cursor"),
    "formula_card": ("terms_light", "derive"),
    "evidence_board": ("strings", "folder_spread"),
    "illus_animated": ("veo",),
    "illus_parallax": ("layers_drift", "light_sweep"),
    "illus_reconstruction": ("marked", "split_with_record"),
}
_LIB = [SceneType(s.name, s.register, s.what, s.needs_media, s.static_risk, VARIANTS.get(s.name, ())) for s in _LIB]

# A scene made for one episode: its component lives in the episode
# (`04_shots/custom/<Component>.tsx`), not in the kit. The shot declares
# `custom: {component, register, brief}`; the register counts like a library scene.
CUSTOM = SceneType("custom", BLUEPRINT, "Scene built for this episode's subject (HUD, instrument, object, mechanism)")
_LIB.append(CUSTOM)

LIBRARY: dict[str, SceneType] = {s.name: s for s in _LIB}


def register_of(shot: dict) -> str | None:
    """Register of a shot; custom scenes say their own."""
    if shot.get("scene_type") == "custom":
        reg = (shot.get("custom") or {}).get("register", BLUEPRINT)
        return reg if reg in REGISTERS else BLUEPRINT
    st = LIBRARY.get(shot.get("scene_type"))
    return st.register if st else None


def get(name: str) -> SceneType:
    try:
        return LIBRARY[name]
    except KeyError as e:
        raise KeyError(f"unknown scene type '{name}'. Known: {', '.join(sorted(LIBRARY))}") from e


def allowed_for(channel: dict) -> set[str]:
    st = channel.get("scene_types", "all")
    return set(LIBRARY) if st == "all" else set(st)
