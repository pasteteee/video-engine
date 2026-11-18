"""LoreSquare channel: formats, manga safety rules, site data."""
import datetime as dt
import json

import pytest

from vengine import contracts, formats, lore, scenes, variety
from vengine.cli import main
from vengine.episode import ROOT, Episode, load_channel

LS = load_channel("loresquare")
TODAY = dt.date(2026, 11, 18)


def write(ep, rel, obj):
    p = ep.path(rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj), encoding="utf-8")


def line(i, beat, text, claim=None, ch=None, hook=None):
    l = {"id": f"l{i}", "chapter": "c1", "text": text, "emotion": "neutral", "beat": beat}
    if claim:
        l["claim"] = claim
    if ch:
        l["chapter_refs"] = ch
    if hook:
        l["hook"] = hook
    return l


TOPIC = {
    "slug": "mother_flame", "format": "chapter_breakdown", "working_title": "Who paid for the artificial sun?",
    "question": "Why did Vegapunk build a sun that erased a kingdom?",
    "signals": [{"kind": "site_data", "detail": "theory confidence 61%", "value": 61}],
    "known_layer": ["Mother Flame powers the weapon"], "angle": "Mirror of the Void Century",
    "scores": {"demand": 4, "competition": 3, "material": 4, "fit": 5},
    "release": {"chapter": 1116, "official_at": "2024-05-26", "source": "MANGA Plus"},
    "lore_refs": [{"kind": "theory", "ref": "mother-flame", "author": "someone", "confidence": 61, "was": 50}],
}
WORDS = "one two three four five six seven eight nine ten"
SCRIPT = {"meta": {"slug": "mother_flame", "language": "en", "title_options": ["a", "b", "c"]}, "lines": [
    line(1, "hook", WORDS, hook="cold_open"),
    line(2, "question", WORDS),
    line(3, "recap", WORDS),
    line(4, "motive", WORDS, "canon", [1116]),
    line(5, "author_intent", WORDS, "inference"),
    line(6, "setup_payoff", WORDS, "canon", [1067, 1116]),
    line(7, "theory", WORDS, "speculation"),
    line(8, "counter", WORDS, "community"),
    line(9, "community", WORDS),
    line(10, "prediction", WORDS, "speculation"),
    line(11, "viewer_question", WORDS),
    line(12, "cta", WORDS),
]}
MEDIA = {"items": [
    {"id": "p1", "path": "media/p1.png", "kind": "panel", "license": "fair-use-review", "chapter": 1116, "page": 7,
     "credit": "One Piece (c) Eiichiro Oda / Shueisha", "shows": "Vegapunk's broadcast"},
    {"id": "p2", "path": "media/p2.png", "kind": "panel", "license": "fair-use-review", "chapter": 1067, "page": 3,
     "credit": "One Piece (c) Eiichiro Oda / Shueisha", "shows": "Lulusia before"},
]}
SRC = "One Piece (c) Eiichiro Oda / Shueisha"
SHOTS = {"fps": 30, "width": 1920, "height": 1080, "shots": [
    {"id": "s1", "line_ids": ["l1"], "scene_type": "question_card", "variant": "rise_narrow", "duration_s": 5},
    {"id": "s2", "line_ids": ["l2"], "scene_type": "panel_callout", "variant": "circle_note", "duration_s": 4, "media_ids": ["p1"],
     "on_screen_text": ["He chose the sun"], "motion": "push in", "source_line": SRC + ", Ch. 1116"},
    {"id": "s3", "line_ids": ["l3"], "scene_type": "timeline_scroll", "variant": "rail_travel", "duration_s": 6},
    {"id": "s4", "line_ids": ["l4"], "scene_type": "claim_card", "variant": "stamp", "duration_s": 5},
    {"id": "s5", "line_ids": ["l5"], "scene_type": "custom", "duration_s": 6, "custom": {"component": "SunDial", "brief": "dial"}},
    {"id": "s6", "line_ids": ["l6"], "scene_type": "panel_setup_payoff", "variant": "split", "duration_s": 5, "media_ids": ["p1", "p2"],
     "on_screen_text": ["Ch. 1067 -> Ch. 1116"], "source_line": SRC},
    {"id": "s7", "line_ids": ["l7"], "scene_type": "theory_card", "variant": "wanted_poster", "duration_s": 6},
    {"id": "s8", "line_ids": ["l8"], "scene_type": "argument_duel", "variant": "two_column", "duration_s": 6},
    {"id": "s9", "line_ids": ["l9"], "scene_type": "confidence_meter", "variant": "gauge", "duration_s": 5},
    {"id": "s10", "line_ids": ["l10"], "scene_type": "kinetic_type", "variant": "type_on", "duration_s": 5},
    {"id": "s11", "line_ids": ["l11", "l12"], "scene_type": "question_card", "variant": "hold_cursor", "duration_s": 6},
]}


def episode(tmp_path, **over):
    ep = Episode.init(tmp_path / "ep", "loresquare", "mother_flame", "chapter_breakdown")
    docs = {"01_topic/topic_card.json": TOPIC, "03_script/script.json": SCRIPT,
            "02_research/media.json": MEDIA, "04_shots/shotlist.json": SHOTS}
    for rel, obj in {**docs, **over}.items():
        write(ep, rel, obj)
    return ep


def errors(probs):
    return [p["msg"] for p in probs if p["level"] == "error"]


def test_every_channel_profile_matches_its_schema():
    for d in sorted((ROOT / "channels").glob("*/channel.json")):
        assert contracts.validate_obj("channel", json.loads(d.read_text(encoding="utf-8")), d.parent.name) == []


def test_formats_are_the_four_video_kinds():
    assert formats.names(LS) == ["chapter_breakdown", "chapter_moments", "site_promo", "top_theories"]
    promo = formats.effective(LS, "site_promo")
    assert promo["aspect"] == "9:16"
    g = promo["variety"]["groups"]
    assert g["manga_panels"]["max_share"] == 0.15 and g["manga_panels"]["shot_max_s"] == 5  # merged, not replaced
    assert g["site_screens"]["min_share"] == 0.4
    with pytest.raises(KeyError):
        formats.get(LS, "nope")


def test_domain_scenes_only_for_channels_that_ask():
    assert "panel_callout" in scenes.allowed_for(LS)
    assert "panel_callout" not in scenes.allowed_for(load_channel("realstory"))
    assert "photo_parallax" in scenes.allowed_for(LS)


def test_valid_breakdown_has_no_errors(tmp_path):
    ep = episode(tmp_path)
    assert errors(contracts.validate_episode(ep, ep.channel())) == []
    res = variety.check(SHOTS, ep.channel())
    assert res["ok"], res["problems"]
    assert res["stats"]["groups"]["manga_panels"]["shots"] == 2


def test_panels_capped_short_commented_and_never_back_to_back():
    shots = json.loads(json.dumps(SHOTS))
    shots["shots"][1]["duration_s"] = 9
    shots["shots"][1]["on_screen_text"] = []
    shots["shots"][2] = {**shots["shots"][5], "id": "s3", "line_ids": ["l3"]}
    shots["shots"][7] = {**shots["shots"][5], "id": "s8", "line_ids": ["l8"], "variant": "wipe"}
    msgs = " | ".join(p["msg"] for p in variety.check(shots, formats.effective(LS, "chapter_breakdown"))["problems"])
    assert "s2 holds 9s, at most 5s" in msgs
    assert "s2 has no on_screen_text" in msgs
    assert "s3 makes 2 in a row" in msgs
    assert "of screen time, at most 33%" in msgs


def test_release_gate_blocks_leaks():
    ch = formats.effective(LS, "chapter_breakdown")
    topic = {**TOPIC, "release": {"chapter": 1200, "official_at": "2026-12-01", "source": "MANGA Plus"}}
    msgs = errors(contracts.format_check({"topic_card": topic}, None, ch, TODAY))
    assert any("not officially out" in m for m in msgs)
    msgs = errors(contracts.format_check({"topic_card": {k: v for k, v in TOPIC.items() if k != "release"}}, None, ch, TODAY))
    assert any("release missing" in m for m in msgs)
    media = {"items": [{**MEDIA["items"][0], "chapter": 1117}]}
    script = {**SCRIPT, "lines": SCRIPT["lines"][:3] + [line(4, "motive", WORDS, "canon", [1117])]}
    msgs = errors(contracts.format_check({"topic_card": TOPIC, "media": media, "script": script}, None, ch, TODAY))
    assert any("panel from chapter 1117" in m for m in msgs)
    assert any("cites chapter 1117" in m for m in msgs)


def test_script_rules_of_the_format():
    ch = formats.effective(LS, "chapter_breakdown")
    lines = [line(1, "hook", WORDS), line(2, "recap", " ".join([WORDS] * 3)), line(3, "theory", WORDS)]
    msgs = errors(contracts.format_check({"script": {"meta": SCRIPT["meta"], "lines": lines}}, None, ch, TODAY))
    assert any("needs a 'prediction' line" in m for m in msgs)
    assert any("recap is 60%" in m for m in msgs)
    assert any("l3 (theory) has no claim tag" in m for m in msgs)


def test_panel_media_needs_chapter_credit_and_review_license(tmp_path):
    bad = {"items": [{"id": "p", "path": "x.png", "kind": "panel", "license": "CC0", "source_url": "u", "shows": "x"}]}
    msgs = " ".join(m["msg"] for m in contracts.validate_obj("media", bad))
    assert "chapter" in msgs and "credit" in msgs and "fair-use-review" in msgs


def test_status_stops_before_publish(tmp_path):
    ep = episode(tmp_path)
    st = ep.status()
    assert st["format"] == "chapter_breakdown" and st["skipped"] == ["publish"]
    assert [r["stage"] for r in st["stages"] if r.get("skipped")] == ["publish"]
    write(ep, "07_qa/qa_report.json", {"verdict": "ready"})
    for s in ("02_research/findings.json", "05_voice/words.json", "06_render/main.mp4"):
        write(ep, s, {"x": 1})
    for g in ("topic", "script", "final"):
        ep.approve(g)
    st = ep.status()
    assert st["next"] is None and st["waiting_for_owner"] is None


def test_cli_init_needs_a_format(tmp_path, capsys):
    with pytest.raises(SystemExit):
        main(["init", "loresquare", "x", "--root", str(tmp_path)])
    assert main(["init", "loresquare", "x", "--root", str(tmp_path), "--format", "top_theories"]) == 0
    assert json.loads((tmp_path / "x/state.json").read_text())["format"] == "top_theories"
    assert main(["formats", "loresquare"]) == 0
    assert "site_promo" in capsys.readouterr().out


def fake_site():
    board = {"items": [{"ref": "m1"}, {"ref": "m2"}]}
    mysteries = {
        "m1": {"mystery": {"ref": "m1", "question": "Blackbeard's fruit?"},
               "theories": [{"ref": "t1", "confidence": 84}, {"ref": "t2", "confidence": 40}]},
        "m2": {"mystery": {"ref": "m2", "question": "Imu?"}, "theories": [{"ref": "t3", "confidence": 59}]},
    }

    def theory(ref, conf, hist, args):
        return {"theory": {"ref": ref, "title": ref.upper(), "author": "a_" + ref, "confidence": conf, "votes": 30,
                           "url": f"https://loresquare.com/t/{ref}?utm_source=claude"},
                "history": hist, "arguments": args}
    theories = {
        "t1": theory("t1", 84, [54, 70, 84], [{"stance": "for", "text": "Dark water", "source": "Ch. 441", "votes": 12},
                                             {"stance": "against", "text": "Imu", "source": "Ch. 1086", "votes": 5}]),
        "t2": theory("t2", 40, [40], [{"stance": "for", "text": "x", "source": "", "votes": 1}]),
        "t3": theory("t3", 59, [59], [{"stance": "for", "text": "Nerona", "source": "Ch. 1086 p. 3", "votes": 9},
                                     {"stance": "against", "text": "Ch. 1198 says no", "source": "Ch. 1198", "votes": 4}]),
    }
    calls = []

    def transport(url, msg):
        name, args = msg["params"]["name"], msg["params"]["arguments"]
        calls.append(name)
        sc = {"mystery_board": lambda: board, "get_mystery": lambda: mysteries[args["ref"]],
              "get_theory": lambda: theories[args["ref"]]}[name]()
        return {"jsonrpc": "2.0", "id": 1, "result": {"structuredContent": sc, "content": []}}
    return transport, calls


def test_top_theories_ranks_and_spreads_over_questions():
    transport, calls = fake_site()
    top = lore.top_theories(2, url="x", transport=transport)
    assert [t["ref"] for t in top] == ["t1", "t3"]  # one per question first, t2 has no counterpoint
    assert top[0]["was"] == 54 and top[0]["moved"] == 30 and top[0]["chapters"] == [441, 1086]
    assert calls[0] == "mystery_board"
    assert len(lore.top_theories(3, url="x", transport=transport)) == 3


def test_tool_errors_surface():
    with pytest.raises(RuntimeError):
        lore.call("get_theory", {}, "x", lambda u, m: {"result": {"isError": True, "content": [{"type": "text", "text": "no"}]}})


def test_utm_replaces_connector_tags():
    u = lore.with_utm("https://loresquare.com/t/x?utm_source=claude&ref=1", "zaza")
    assert "utm_source=youtube" in u and "utm_campaign=zaza" in u and "ref=1" in u and "claude" not in u
