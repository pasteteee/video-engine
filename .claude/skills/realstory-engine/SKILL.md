---
name: video-engine
description: Orchestrates a channel's video pipeline end to end (analytics → topic → research → script → shots → voice → render → QA → publish) through the rs-* agents and file contracts. Use for "что сегодня", "сделай серию", "где мы по серии X", "продолжи серию", "опубликуй", for any channel profile in channels/.
---

# Video engine orchestrator

The engine is shared; everything channel-specific lives in `channels/<id>/channel.json` (style, rules, voice, YouTube secrets folder, planner, variety limits). A new channel = a new profile, no engine code changes.

Talk to the owner in the profile's `work_language` (Russian for realstory). First line of every reply: which skills/agents you take.

## The chain

| # | Agent | Writes | Owner stop |
|---|---|---|---|
| 1 | rs-analyst | `channels/<id>/analytics/<date>.md` | no |
| 2 | rs-topics | `01_topic/topic_card.json` | **topic** |
| 3 | rs-researcher | `02_research/findings.json`, `media.json` | no |
| 4 | rs-writer | `03_script/script.json` | **script** |
| 5 | rs-director | `04_shots/shotlist.json` | no |
| 6 | rs-voice | `05_voice/words.json` + audio | no |
| 7 | rs-render | `06_render/main.mp4`, shorts, thumb | no |
| 8 | rs-qa | `07_qa/qa_report.json` (loops back to 7) | **final** |
| 9 | rs-publisher | `08_publish/publish.json` | no |

## How to run
1. Find the episode: `python -m vengine status <episode_dir>` tells the next stage or the gate waiting for the owner. New episode: `python -m vengine init <channel> <slug>`.
2. Run the next agent (subagent if available, else follow its card in `.claude/agents/<agent>.md` yourself). Give it only the paths of its inputs and the channel profile.
3. After it finishes: `python -m vengine validate <episode_dir>`. Errors → back to the same agent with the error list. Never hand over a file with errors.
4. At a gate: show the owner the result (topic options / script / final video + QA report) and wait. Record the answer with `python -m vengine approve <episode_dir> <gate> --note "..."`. "Делай всё сразу" from the owner skips the topic and script stops, never the final one.
5. Update the Planner (`planner-sync`) when the stage changes.
6. Long session or switching agents → `handoff`.

## Morning flow ("что сегодня")
rs-analyst → one-paragraph answer: what took off and why (evidence), then rs-topics → 3 topics with a recommendation. Wait for the pick.

## Where things run
Cloud container: research, writing, planning, validation, stills. Owner's PC (Remote Control): OAuth and YouTube API calls, word alignment, heavy renders, uploads. Secrets never enter the repo, the chat or the shared project folder.
