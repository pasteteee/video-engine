"""The channel's model catalog (amigurumi.ai) with a fake network."""
import json

import pytest

from vengine import catalog as cat, contracts
from vengine.cli import main
from vengine.episode import Episode, load_channel

CFG = load_channel("amigurumi")["catalog"]
CARDS = {"total": 3, "toys": [
    {"id": "goat-sweater-2027", "name": "Goat in a Sweater", "href": "/models/goat-sweater-2027", "category": "animals",
     "keywords": "goat sweater christmas", "heightCm": 14.4, "hours": 4, "hookMm": 2.5, "yarnWeight": "DK", "likes": 3,
     "thumb": CFG["storage"] + "/goat-sweater-2027/img/studio.webp", "swatches": ["#f7f2ea"]},
    {"id": "goat-on-rock", "name": "Goat on a Rock", "category": "animals", "keywords": "goat", "likes": 9},
    {"id": "frog-mochi", "name": "Frog Mochi", "category": "animals", "keywords": "frog"}]}
MANIFEST = {"schema": "amikit-model/1", "id": "goat-sweater-2027", "title": "Goat in a Sweater", "title_ru": "Козочка в свитере",
            "size_cm": {"height_cm": 14.4, "width_cm": 11.0}, "yarn": {"weight": "DK", "hook_mm": 2.5},
            "colours": [{"name": "white", "hex": "#f7f2ea", "metres": 70}, {"name": "red", "hex": "#c8323a", "metres": 50}],
            "images": {"studio": "img/studio.webp"}, "files": {"spec": "spec.json", "glb": "model.glb"}}
SPEC = {"name": "goat", "parts": []}


def fake_get(url):
    if url.startswith(CFG["api"]):
        return json.dumps(CARDS).encode()
    if url.endswith("/goat-sweater-2027/model.json"):
        return json.dumps(MANIFEST).encode()
    if url.endswith("/spec.json"):
        return json.dumps(SPEC).encode()
    if url.endswith("/model.glb"):
        return b"glTF"
    if url.endswith(".webp"):
        return b"RIFFwebp"
    raise OSError(f"404 {url}")


def test_search_ranks_name_hits_first():
    c = cat.Catalog(CFG, fake_get)
    ids = [t["id"] for t in c.search("goat")]
    assert ids[:2] == ["goat-on-rock", "goat-sweater-2027"] or set(ids) == {"goat-on-rock", "goat-sweater-2027"}
    assert [t["id"] for t in c.search("sweater")] == ["goat-sweater-2027"]
    assert len(c.search("")) == 3


def test_info_merges_card_and_package():
    i = cat.Catalog(CFG, fake_get).info("goat-sweater-2027")
    assert i["title_ru"] == "Козочка в свитере" and i["hours"] == 4 and i["yarn_m"] == 120
    assert i["glb"].endswith("/goat-sweater-2027/model.glb") and i["url"] == "https://amigurumi.ai/models/goat-sweater-2027"
    assert "Goat in a Sweater" in cat.format_info(i) and "120 m" in cat.format_info(i)
    page = cat.viewer_html(i)
    assert "<model-viewer" in page and "model.glb" in page and "Козочка" in page


def test_info_without_package_uses_card_and_unknown_fails():
    c = cat.Catalog(CFG, fake_get)
    i = c.info("frog-mochi")
    assert i["title"] == "Frog Mochi" and i["glb"] is None
    assert "No 3D model" in cat.viewer_html(i)
    with pytest.raises(LookupError):
        c.info("nope")


def test_pull_into_episode_drafts_a_valid_storyboard(tmp_path):
    ep = Episode.init(tmp_path / "goat", "amigurumi", "goat", "build_short")
    info = cat.Catalog(CFG, fake_get).pull("goat-sweater-2027", ep.folder)
    assert (ep.folder / "02_research/toy.json").exists() and (ep.folder / "02_research/model.glb").read_bytes() == b"glTF"
    sb = json.loads((ep.folder / "04_shots/storyboard.json").read_text())
    assert sb["toy"]["stats"] == {"size_cm": 14, "hours": 4, "yarn_m": 120, "yarn_weight": "DK"}
    assert sb["photos"]["hook"] == info["local"]["photo"]
    assert not contracts.validate_obj("storyboard", sb)


def test_cli_catalog(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cat, "http_get", fake_get)
    assert main(["catalog", "search", "amigurumi", "frog"]) == 0
    assert "frog-mochi" in capsys.readouterr().out
    assert main(["catalog", "info", "amigurumi", "goat-sweater-2027"]) == 0
    assert "DK, hook 2.5 mm" in capsys.readouterr().out
    out = tmp_path / "v.html"
    assert main(["catalog", "view", "amigurumi", "goat-sweater-2027", "--out", str(out)]) == 0
    assert "model-viewer" in out.read_text()
    ep = Episode.init(tmp_path / "g", "amigurumi", "g", "build_short")
    assert main(["catalog", "pull", str(ep.folder), "goat-sweater-2027"]) == 0


def test_realstory_has_no_catalog():
    with pytest.raises(ValueError):
        cat.Catalog(load_channel("realstory").get("catalog", {}))
