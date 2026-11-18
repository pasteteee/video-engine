"""Episode folder layout, stage detection and owner approvals (gates)."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Stage:
    key: str
    agent: str
    output: str  # main output, relative to the episode folder
    schema: str | None
    gate: str | None = None  # owner approval needed after this stage


STAGES: list[Stage] = [
    Stage("topic", "rs-topics", "01_topic/topic_card.json", "topic_card", gate="topic"),
    Stage("research", "rs-researcher", "02_research/findings.json", "findings"),
    Stage("script", "rs-writer", "03_script/script.json", "script", gate="script"),
    Stage("shots", "rs-director", "04_shots/shotlist.json", "shotlist"),
    Stage("voice", "rs-voice", "05_voice/words.json", "words"),
    Stage("render", "rs-render", "06_render/main.mp4", None),
    Stage("qa", "rs-qa", "07_qa/qa_report.json", "qa_report", gate="final"),
    Stage("publish", "rs-publisher", "08_publish/publish.json", "publish"),
]
# A build short (amigurumi channel): no narration. The toy is crocheted stitch by stitch on screen, captions and
# music come from the knit plan. See vengine/build/ and channels/amigurumi/.
BUILD_STAGES: list[Stage] = [
    Stage("topic", "rs-topics", "01_topic/topic_card.json", "topic_card", gate="topic"),
    Stage("storyboard", "rs-build", "04_shots/storyboard.json", "storyboard", gate="script"),
    Stage("knit", "rs-build", "06_render/knit/plan.json", "knit_plan"),
    Stage("render", "rs-build", "06_render/main.mp4", None),
    Stage("qa", "rs-qa", "07_qa/qa_report.json", "qa_report", gate="final"),
    Stage("publish", "rs-publisher", "08_publish/publish.json", "publish"),
]
FORMATS: dict[str, list[Stage]] = {"documentary": STAGES, "build_short": BUILD_STAGES}

STAGE_BY_KEY = {s.key: s for s in STAGES + BUILD_STAGES}
GATES = list(dict.fromkeys(s.gate for st in FORMATS.values() for s in st if s.gate))

# Secondary files each stage also writes (checked by `validate`, not by `status`).
EXTRA = {
    "02_research/media.json": "media",
    "06_render/shorts/shorts.json": "shorts",
}

SUBDIRS = [
    "01_topic", "02_research/raw", "02_research/media", "03_script", "04_shots",
    "05_voice/lines", "06_render/shorts", "06_render/thumb", "07_qa/frames", "08_publish",
]
BUILD_SUBDIRS = ["01_topic", "02_research/media", "04_shots", "06_render/knit", "06_render/upload", "07_qa/frames",
                 "08_publish"]


def stages_for(fmt: str | None) -> list[Stage]:
    return FORMATS.get(fmt or "documentary", STAGES)


def load_channel(channel_id: str, channels_dir: Path | None = None) -> dict:
    path = (channels_dir or ROOT / "channels") / channel_id / "channel.json"
    if not path.exists():
        raise FileNotFoundError(f"no channel profile at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


class Episode:
    def __init__(self, folder: Path):
        self.folder = Path(folder)
        self.state_path = self.folder / "state.json"

    # ---- state -------------------------------------------------------
    @property
    def state(self) -> dict:
        if self.state_path.exists():
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        return {"approvals": {}}

    def save_state(self, st: dict) -> None:
        self.state_path.write_text(json.dumps(st, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    @property
    def channel(self) -> dict | None:
        cid = self.state.get("channel")
        try:
            return load_channel(cid) if cid else None
        except FileNotFoundError:
            return None

    @property
    def format(self) -> str:
        return self.state.get("format") or (self.channel or {}).get("format", "documentary")

    @property
    def stages(self) -> list[Stage]:
        return stages_for(self.format)

    @classmethod
    def init(cls, folder: Path, channel_id: str, slug: str, fmt: str = "documentary") -> "Episode":
        ep = cls(folder)
        for d in (BUILD_SUBDIRS if fmt == "build_short" else SUBDIRS):
            (ep.folder / d).mkdir(parents=True, exist_ok=True)
        if not ep.state_path.exists():
            ep.save_state({"channel": channel_id, "slug": slug, "format": fmt, "created": _now(), "approvals": {}})
        return ep

    def approve(self, gate: str, note: str = "") -> None:
        if gate not in GATES:
            raise ValueError(f"unknown gate '{gate}', expected one of {GATES}")
        st = self.state
        st.setdefault("approvals", {})[gate] = {"at": _now(), "note": note}
        self.save_state(st)

    def revoke(self, gate: str) -> None:
        st = self.state
        st.get("approvals", {}).pop(gate, None)
        self.save_state(st)

    # ---- stages ------------------------------------------------------
    def path(self, rel: str) -> Path:
        return self.folder / rel

    def stage_done(self, stage: Stage) -> bool:
        p = self.path(stage.output)
        if not p.exists() or p.stat().st_size == 0:
            return False
        if stage.key == "qa":
            return json.loads(p.read_text(encoding="utf-8")).get("verdict") == "ready"
        if stage.key == "publish":
            return bool(json.loads(p.read_text(encoding="utf-8")).get("video_id"))
        return True

    def status(self) -> dict:
        """Where the episode is: last finished stage, next stage, and whether the owner must act."""
        approvals = self.state.get("approvals", {})
        rows = []
        next_stage, waiting_gate = None, None
        for s in self.stages:
            done = self.stage_done(s)
            rows.append({"stage": s.key, "agent": s.agent, "done": done,
                         "gate": s.gate, "approved": bool(s.gate and s.gate in approvals)})
            if next_stage is None and waiting_gate is None:
                if not done:
                    next_stage = s.key
                elif s.gate and s.gate not in approvals:
                    waiting_gate = s.gate
        return {"folder": str(self.folder), "stages": rows,
                "next": next_stage, "waiting_for_owner": waiting_gate}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")
