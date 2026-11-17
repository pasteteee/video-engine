import json
from pathlib import Path

import pytest

from vengine import ailint, contracts, scenes, variety
from vengine.cli import main
from vengine.episode import ROOT, Episode, load_channel

CH = load_channel("realstory")


def write(ep, rel, obj):
    p = ep.path(rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj), encoding="utf-8")


TOPIC = {
    "slug": "bloop", "working_title": "The Bloop", "question": "What made the loudest sound NOAA ever recorded?",
    "signals": [{"kind": "wiki_pageviews", "detail": "Bloop article 40k views/month", "value": 40000}],
    "known_layer": ["It was a sea monster theory", "NOAA said icequake"],
    "angle": "Replay the real hydrophone data and compare with an icequake",
    "scores": {"demand": 4, "competition": 3, "material": 4, "fit": 5},
}
FINDINGS = {
    "sources": [
        {"id": "s1", "title": "NOAA PMEL acoustics", "url": "https://www.pmel.noaa.gov/acoustics/", "kind": "primary"},
        {"id": "s2", "title": "Wikipedia: Bloop", "url": "https://en.wikipedia.org/wiki/Bloop", "kind": "encyclopedia"},
        {"id": "s3", "title": "Dziak 2012", "url": "https://example.org/dziak", "kind": "data"},
    ],
    "facts": [
        {"id": "f1", "text": "Recorded in 1997", "source_ids": ["s1"], "status": "verified"},
        {"id": "f2", "text": "Heard 5000 km apart", "source_ids": ["s1", "s3"], "status": "likely"},
        {"id": "f3", "text": "Giant animal", "source_ids": ["s2"], "status": "rejected"},
    ],
    "calculations": [{"id": "c1", "question": "How far apart?", "inputs": ["f2"], "result": "~5000 km"}],
    "conclusions": [{"id": "k1", "statement": "Icequake fits best", "based_on": ["f1", "c1"], "confidence": "high"}],
}
SCRIPT = {
    "meta": {"slug": "bloop", "language": "en", "title_options": ["a", "b", "c"]},
    "lines": [
        {"id": "l1", "chapter": "cold", "text": "In 1997 the ocean made a sound.", "emotion": "tense", "hook": "cold_open",
         "fact_ids": ["f1"]},
        {"id": "l2", "chapter": "cold", "text": "Two stations heard it.", "emotion": "curious", "hook": "open_loop",
         "fact_ids": ["f2"]},
        {"id": "l3", "chapter": "end", "text": "It was ice.", "emotion": "somber", "closes_loop": "l2"},
    ],
}
MEDIA = {"items": [{"id": "m1", "path": "media/x.jpg", "kind": "photo", "license": "public-domain",
                    "source_url": "https://noaa.gov/x", "shows": "hydrophone"}]}


def shot(i, st, d, line="l1", **kw):
    s = {"id": f"s{i}", "line_ids": [line], "scene_type": st, "duration_s": d}
    if scenes.LIBRARY[st].needs_media:
        s["media_ids"] = ["m1"]
    if scenes.LIBRARY[st].register != scenes.BLUEPRINT:
        s["source_line"] = "PHOTO: NOAA"
    s.update(kw)
    return s


def test_channel_profile_is_valid():
    assert contracts.validate_obj("channel", CH) == []


def test_status_and_gates(tmp_path):
    ep = Episode.init(tmp_path / "bloop", "realstory", "bloop")
    assert ep.status()["next"] == "topic"
    write(ep, "01_topic/topic_card.json", TOPIC)
    st = ep.status()
    assert st["waiting_for_owner"] == "topic" and st["next"] is None
    ep.approve("topic")
    assert ep.status()["next"] == "research"


def test_valid_episode_has_no_errors(tmp_path):
    ep = Episode.init(tmp_path / "bloop", "realstory", "bloop")
    write(ep, "01_topic/topic_card.json", TOPIC)
    write(ep, "02_research/findings.json", FINDINGS)
    write(ep, "02_research/media.json", MEDIA)
    write(ep, "03_script/script.json", SCRIPT)
    write(ep, "04_shots/shotlist.json", {"fps": 30, "width": 1920, "height": 1080, "shots": [
        shot(1, "photo_parallax", 3, "l1"), shot(2, "globe_route", 4, "l2"), shot(3, "film_clip", 3, "l3")]})
    probs = contracts.validate_episode(ep, CH)
    assert [p for p in probs if p["level"] == "error"] == []
    # the 'likely' fact must produce a hedge warning
    assert any("likely" in p["msg"] for p in probs)


def test_cross_check_catches_bad_refs():
    bad = json.loads(json.dumps(SCRIPT))
    bad["lines"][0]["fact_ids"] = ["f3", "nope"]
    probs = contracts.cross_check({"findings": FINDINGS, "script": bad, "media": MEDIA})
    msgs = " ".join(p["msg"] for p in probs)
    assert "rejected" in msgs and "unknown fact nope" in msgs


def test_shotlist_needs_source_line_and_coverage():
    sl = {"fps": 30, "width": 1920, "height": 1080, "shots": [
        {"id": "s1", "line_ids": ["l1"], "scene_type": "photo_parallax", "duration_s": 3, "media_ids": ["m1"]}]}
    probs = contracts.cross_check({"script": SCRIPT, "media": MEDIA, "shotlist": sl}, channel=CH)
    msgs = " ".join(p["msg"] for p in probs)
    assert "without source_line" in msgs and "line l2 has no shot" in msgs


def test_schema_rejects_generated_media_without_prompt():
    m = {"items": [{"id": "g", "path": "a.png", "kind": "illustration", "license": "generated", "shows": "x"}]}
    assert contracts.validate_obj("media", m)


def test_variety_flags_monotone_navy_edit():
    # the old look: blueprint only, same lengths, repeats
    sl = {"shots": [shot(i, t, 4.5) for i, t in enumerate(
        ["chapter_card", "globe_route", "globe_route", "big_number", "map_zoom", "big_number",
         "map_zoom", "chart_line_draw", "big_number", "map_zoom"])]}
    res = variety.check(sl, CH)
    msgs = " ".join(p["msg"] for p in res["problems"])
    assert not res["ok"]
    assert "real material is 0%" in msgs and "both globe_route" in msgs and "barely vary" in msgs


def test_variety_passes_mixed_edit():
    seq = [("photo_parallax", 3), ("kinetic_type", 2), ("film_clip", 5), ("globe_route", 6),
           ("document_highlight", 4), ("big_number", 2), ("illus_animated", 5), ("photo_detail_zoom", 3),
           ("chart_line_draw", 6), ("transcript_waveform", 5), ("map_zoom", 3), ("satellite_reveal", 4),
           ("question_card", 2), ("film_freeze_annotate", 5)]
    shots = [shot(i, t, d) for i, (t, d) in enumerate(seq)]
    shots.insert(7, {**shot(99, "custom", 4), "custom": {"component": "DockingHud", "brief": "Reticle over the approach photos"}})
    res = variety.check({"shots": shots}, CH)
    assert res["ok"], res["problems"]


def test_variety_needs_custom_scenes_and_known_variants():
    seq = [("photo_parallax", 5), ("kinetic_type", 4), ("film_clip", 5), ("globe_route", 6)] * 6
    shots = [shot(i, t, d) for i, (t, d) in enumerate(seq)]
    shots[1]["variant"] = "no_such_variant"
    res = variety.check({"shots": shots}, CH)
    msgs = " ".join(p["msg"] for p in res["problems"])
    assert "made for this episode" in msgs and "no variant 'no_such_variant'" in msgs


def test_look_picks_dark_ground_and_vivid_accent(tmp_path):
    from PIL import Image
    from vengine import look
    im = Image.new("RGB", (200, 200), (10, 25, 60))           # night blue
    im.paste((235, 190, 40), (80, 80, 110, 110))               # a yellow collar
    im.save(tmp_path / "a.png")
    res = look.pick([tmp_path / "a.png"])
    L, C, h = look.hex_to_oklch(res["ground"])
    assert L < 0.22 and 220 < h < 290
    assert 60 < res["accent_hue"] < 110 and res["contrast_accent"] >= 4.5


@pytest.mark.parametrize("text,rule", [
    ("This discovery stands as a testament to human curiosity.", "significance"),
    ("Let's delve into the intricate details.", "ai-vocab"),
    ("The crew landed safely, highlighting the importance of training.", "participle-tail"),
    ("Experts say it was an icequake.", "vague-attribution"),
    ("It's important to note that the tape was damaged.", "editorial"),
    ("It wasn't just a storm, it was a monster.", "negative-parallel"),
    ("Buckle up, because the answer may surprise you.", "youtube-cliche"),
])
def test_ailint_catches(text, rule):
    assert rule in {h["rule"] for h in ailint.lint_text(text)}


def test_ailint_leaves_plain_narration_alone():
    text = ("At 11:22 the lightning hit. The needles on the panel dropped to zero. "
            "Pete Conrad laughed. Then he read the numbers back to Houston, one by one.")
    assert ailint.lint_text(text) == []


def test_cli_status_and_validate(tmp_path, capsys):
    ep = Episode.init(tmp_path / "bloop", "realstory", "bloop")
    write(ep, "01_topic/topic_card.json", TOPIC)
    assert main(["status", str(ep.folder)]) == 0
    assert "waiting for the owner" in capsys.readouterr().out
    assert main(["validate", str(ep.folder)]) == 0


def test_every_agent_has_a_definition():
    from vengine.episode import STAGES
    agents = {s.agent for s in STAGES} | {"rs-analyst"}
    for a in agents:
        assert (ROOT / ".claude" / "agents" / f"{a}.md").exists(), a


def test_shorts_pick_prefers_hooks_and_rejects_landscape_layouts():
    from vengine import shorts as sh
    lines = [{"id": f"l{i}", "chapter": "a", "text": t, **({"hook": h} if h else {})} for i, (t, h) in enumerate([
        ("Nobody had done this before, 1966.", "cold_open"), ("They flew for ten hours.", None), ("And then it went on.", None),
        ("It was quiet for a long time after that and nothing much happened at all.", None), ("Two feet.", "reveal")])]
    words = {"lines": [{"id": l["id"], "start": i * 9.0, "end": i * 9.0 + 8.5} for i, l in enumerate(lines)]}
    c = sh.candidates({"lines": lines}, {"shots": []}, words)
    assert c[0]["line_ids"][0] == "l0"
    plan = {"width": 1080, "height": 1920, "shorts": [{"id": "s1", "start_s": 0, "end_s": 30, "hook_text": "TWO FEET AWAY",
             "shots": [{"id": "a", "layout": "letterbox", "duration_s": 2}, {"id": "b", "layout": "v_type", "duration_s": 2}]}]}
    msgs = " ".join(p["msg"] for p in sh.check_plan(plan))
    assert "not vertical-native" in msgs and "'v_type'" not in msgs
