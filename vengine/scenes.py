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

LIBRARY: dict[str, SceneType] = {s.name: s for s in _LIB}


def get(name: str) -> SceneType:
    try:
        return LIBRARY[name]
    except KeyError as e:
        raise KeyError(f"unknown scene type '{name}'. Known: {', '.join(sorted(LIBRARY))}") from e


def allowed_for(channel: dict) -> set[str]:
    st = channel.get("scene_types", "all")
    return set(LIBRARY) if st == "all" else set(st)
