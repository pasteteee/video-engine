"""A channel's model catalog: find a toy, look at its 3D model and facts, pull it into an episode.

The amigurumi channel's catalog is amigurumi.ai (channel.json `catalog`):
  - the card list   GET {api}?locale=en          -> {"total", "toys": [card...]}  (name, href, thumb, heightCm, hours…)
  - the package     {storage}/{id}/model.json    -> amikit-model/1 manifest (title, size_cm, yarn, colours with metres,
                                                    images, files: spec, glb, pattern_en, pattern_ru, pattern_data)
                    {storage}/{id}/<files.*>     -> the files themselves

    python -m vengine catalog search CHANNEL [QUERY] [--n 12]
    python -m vengine catalog info CHANNEL ID [--json]
    python -m vengine catalog view CHANNEL ID [--out model.html]   3D viewer page (rotate, zoom) + the facts
    python -m vengine catalog pull EPISODE ID                       spec, GLB, photo, facts and a draft storyboard

In the cloud container the catalog hosts may be blocked; the amigurumi_ai MCP tools (search_toys, get_toy) show the
same cards there. The CLI is for the owner's PC and any machine whose network allows the hosts.
"""
from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable

Getter = Callable[[str], bytes]


def http_get(url: str, timeout: float = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "vengine-catalog/1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


class Catalog:
    def __init__(self, cfg: dict, get: Getter | None = None):
        if not cfg or not cfg.get("api"):
            raise ValueError("this channel has no catalog (channel.json `catalog`)")
        self.cfg = cfg
        self.get = get or http_get
        self._cards: list[dict] | None = None

    # ---------------------------------------------------------- cards
    def cards(self) -> list[dict]:
        if self._cards is None:
            url = self.cfg["api"] + ("&" if "?" in self.cfg["api"] else "?") + "locale=" + self.cfg.get("locale", "en")
            self._cards = json.loads(self.get(url))["toys"]
        return self._cards

    def search(self, query: str = "", n: int = 12, category: str | None = None) -> list[dict]:
        words = [w for w in re.split(r"\W+", query.lower()) if w]
        out = []
        for c in self.cards():
            if category and c.get("category") != category:
                continue
            hay = " ".join(str(c.get(k) or "") for k in ("id", "name", "keywords", "category")).lower()
            score = sum((3 if w in (c.get("name") or "").lower() else 1) for w in words if w in hay)
            if words and not score:
                continue
            out.append((score, c.get("likes", 0) or 0, c))
        out.sort(key=lambda x: (-x[0], -x[1]))
        return [c for _, _, c in out[:n]]

    def card(self, toy_id: str) -> dict | None:
        try:
            return next((c for c in self.cards() if c.get("id") == toy_id), None)
        except Exception:
            return None

    # ---------------------------------------------------------- one toy
    def file_url(self, toy_id: str, rel: str) -> str:
        if re.match(r"^https?://", rel):
            return rel
        return f"{self.cfg['storage'].rstrip('/')}/{urllib.parse.quote(toy_id)}/{rel.lstrip('/')}"

    def manifest(self, toy_id: str) -> dict | None:
        try:
            return json.loads(self.get(self.file_url(toy_id, "model.json")))
        except Exception:
            return None

    def info(self, toy_id: str) -> dict:
        """Everything the storyboard and the owner need about one toy, from the card and the package."""
        card, man = self.card(toy_id), self.manifest(toy_id)
        if card is None and man is None:
            raise LookupError(f"toy '{toy_id}' not found in the catalog")
        card, man = card or {}, man or {}
        size = man.get("size_cm") or {}
        files = man.get("files") or {}
        colours = man.get("colours") or [{"hex": h, "name": h} for h in card.get("swatches", [])]
        metres = sum(c.get("metres") or 0 for c in colours) or None
        images = {k: self.file_url(toy_id, v) for k, v in (man.get("images") or {}).items()}
        photo = card.get("thumb") or next((v for k, v in images.items() if "studio" in k), None) or \
            next(iter(images.values()), None)
        yarn = man.get("yarn") or {}
        site = self.cfg.get("page", "").format(id=toy_id) or card.get("href")
        return {
            "id": toy_id,
            "title": man.get("title") or card.get("name") or toy_id,
            "title_ru": man.get("title_ru"),
            "url": site,
            "crochet_url": (site + "/crochet") if site else None,
            "category": card.get("category"),
            "difficulty": card.get("difficulty"),
            "construction": man.get("construction") or ("nosew" if card.get("noSew") else None),
            "height_cm": size.get("height_cm") or card.get("heightCm"),
            "width_cm": size.get("width_cm"), "depth_cm": size.get("depth_cm"),
            "hours": card.get("hours"),
            "hook_mm": yarn.get("hook_mm") or card.get("hookMm"),
            "yarn_weight": yarn.get("weight") or card.get("yarnWeight"),
            "yarn_m": round(metres) if metres else card.get("yarnMetres"),
            "colours": [{"name": c.get("name"), "hex": c.get("hex"), "metres": c.get("metres")} for c in colours],
            "photo": photo,
            "images": images,
            "glb": self.file_url(toy_id, files["glb"]) if files.get("glb") else None,
            "spec": self.file_url(toy_id, files["spec"]) if files.get("spec") else None,
            "pattern_en": self.file_url(toy_id, files["pattern_en"]) if files.get("pattern_en") else None,
            "likes": card.get("likes"), "made": card.get("made"),
        }

    # ---------------------------------------------------------- into an episode
    def pull(self, toy_id: str, folder: Path) -> dict:
        """spec → 02_research/toy.json, GLB → 02_research/model.glb, photo → 02_research/media/, facts →
        02_research/toy_info.json, and 04_shots/storyboard.json drafted from the facts (kept if it exists)."""
        info = self.info(toy_id)
        res = folder / "02_research"
        (res / "media").mkdir(parents=True, exist_ok=True)
        got = {}
        if info["spec"]:
            (res / "toy.json").write_bytes(self.get(info["spec"])); got["spec"] = "02_research/toy.json"
        if info["glb"]:
            (res / "model.glb").write_bytes(self.get(info["glb"])); got["glb"] = "02_research/model.glb"
        if info["photo"]:
            ext = Path(urllib.parse.urlparse(info["photo"]).path).suffix or ".jpg"
            (res / "media" / f"studio{ext}").write_bytes(self.get(info["photo"]))
            got["photo"] = f"02_research/media/studio{ext}"
        info["local"] = got
        (res / "toy_info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        sb_path = folder / "04_shots/storyboard.json"
        if not sb_path.exists():
            sb_path.parent.mkdir(parents=True, exist_ok=True)
            sb_path.write_text(json.dumps(draft_storyboard(info), ensure_ascii=False, indent=2), encoding="utf-8")
            got["storyboard"] = "04_shots/storyboard.json (draft)"
        return info


def draft_storyboard(info: dict) -> dict:
    """A storyboard to edit, not to ship: the title as the hook, the facts as the stats chip."""
    stats = {k: v for k, v in (("size_cm", info.get("height_cm")), ("hours", info.get("hours")),
                                 ("yarn_m", info.get("yarn_m")), ("yarn_weight", info.get("yarn_weight"))) if v}
    if stats.get("size_cm"):
        stats["size_cm"] = round(float(stats["size_cm"]))
    title = info["title"]
    sb = {"toy": {"spec": info.get("local", {}).get("spec", "02_research/toy.json"), "title": title,
                  "url": info.get("url") or "", "stats": stats},
          "hook": {"lines": [{"text": title[:28], "size": 120 if len(title) <= 12 else 96, "accent": True},
                             {"text": "from one strand of yarn", "size": 54}]}}
    photo = info.get("local", {}).get("photo")
    if photo:
        sb["photos"] = {"hook": photo, "real": photo}
    return sb


def format_info(i: dict) -> str:
    def v(x, unit=""):
        return f"{x:g}{unit}" if isinstance(x, (int, float)) else (x or "—")
    lines = [f"{i['title']}  ({i['id']})" + (f" · {i['title_ru']}" if i.get("title_ru") else ""),
             f"  page        {i.get('url') or '—'}",
             f"  size        {v(i.get('height_cm'), ' cm')} tall"
             + (f", {v(i.get('width_cm'), ' cm')} wide" if i.get("width_cm") else ""),
             f"  time        {v(i.get('hours'), ' h')}   difficulty {v(i.get('difficulty'))}   "
             f"{i.get('construction') or ''}",
             f"  yarn        {i.get('yarn_weight') or '—'}, hook {v(i.get('hook_mm'), ' mm')}, "
             f"{v(i.get('yarn_m'), ' m')} in all",
             "  colours     " + ", ".join(f"{c.get('name') or c.get('hex')} {c.get('hex') or ''}"
                                         + (f" {c['metres']:g} m" if c.get("metres") else "") for c in i["colours"]),
             f"  3D model    {i.get('glb') or '—'}",
             f"  spec        {i.get('spec') or '—'}",
             f"  photo       {i.get('photo') or '—'}"]
    return "\n".join(lines)


VIEWER = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<script type="module" src="https://cdn.jsdelivr.net/npm/@google/model-viewer@3.5.0/dist/model-viewer.min.js"></script>
<style>
:root{{--ink:#1b2454;--bg:#f9f3e8;--card:#fffbf4;--muted:#6b6f86;--accent:#ffd23f}}
@media (prefers-color-scheme:dark){{:root{{--ink:#f3eee6;--bg:#141726;--card:#1d2136;--muted:#a3a7bd}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.45 system-ui,sans-serif}}
main{{max-width:1100px;margin:0 auto;padding:16px;display:grid;gap:16px;grid-template-columns:minmax(0,3fr) minmax(0,2fr)}}
@media (max-width:760px){{main{{grid-template-columns:1fr}}}}
model-viewer{{width:100%;height:min(78vh,720px);background:var(--card);border-radius:16px}}
section{{background:var(--card);border-radius:16px;padding:18px}}h1{{margin:0 0 4px;font-size:24px}}
.sub{{color:var(--muted);margin:0 0 14px}}dl{{display:grid;grid-template-columns:auto 1fr;gap:6px 14px;margin:0}}
dt{{color:var(--muted)}}dd{{margin:0}}.sw{{display:inline-block;width:14px;height:14px;border-radius:50%;vertical-align:-2px;
margin-right:6px;border:1px solid #0002}}ul{{list-style:none;padding:0;margin:0}}li{{margin:3px 0}}a{{color:inherit}}
img{{width:100%;border-radius:12px;margin-top:14px}}
</style></head><body><main>
{viewer}
<section><h1>{title}</h1><p class="sub">{sub}</p><dl>{rows}</dl>{photo}</section>
</main></body></html>
"""


def viewer_html(i: dict, glb: str | None = None) -> str:
    e = html.escape
    glb = glb or i.get("glb")
    viewer = (f'<model-viewer src="{e(glb)}" camera-controls auto-rotate shadow-intensity="0.8" exposure="1.05" '
              f'alt="{e(i["title"])} 3D model" poster="{e(i.get("photo") or "")}"></model-viewer>') if glb else \
        "<section>No 3D model in this package.</section>"
    rows = []

    def row(k, val):
        if val not in (None, "", []):
            rows.append(f"<dt>{e(k)}</dt><dd>{val}</dd>")
    row("Height", f"{i['height_cm']:g} cm" if i.get("height_cm") else None)
    row("Time", f"{i['hours']:g} h" if i.get("hours") else None)
    row("Difficulty", e(str(i["difficulty"])) if i.get("difficulty") else None)
    row("Yarn", e(" · ".join(str(x) for x in (i.get("yarn_weight"), f"{i['yarn_m']} m" if i.get("yarn_m") else None) if x)))
    row("Hook", f"{i['hook_mm']:g} mm" if i.get("hook_mm") else None)
    row("Build", e(i.get("construction") or ""))
    row("Colours", "<ul>" + "".join(
        f'<li><span class="sw" style="background:{e(c.get("hex") or "#ccc")}"></span>{e(c.get("name") or c.get("hex") or "")}'
        + (f' · {c["metres"]:g} m' if c.get("metres") else "") + "</li>" for c in i["colours"]) + "</ul>")
    row("Pattern", f'<a href="{e(i["url"])}">{e(i["url"])}</a>' if i.get("url") else None)
    sub = " · ".join(x for x in (i["id"], i.get("title_ru"), i.get("category")) if x)
    photo = f'<img src="{e(i["photo"])}" alt="{e(i["title"])} photo">' if i.get("photo") else ""
    return VIEWER.format(title=e(i["title"]), sub=e(sub), rows="".join(rows), viewer=viewer, photo=photo)
