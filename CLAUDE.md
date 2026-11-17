# video-engine

Multi-channel YouTube production engine: 9 agents (`.claude/agents/rs-*.md`) passing JSON contracts (`vengine/schemas/`) inside an episode folder, orchestrated by the `video-engine` skill (`.claude/skills/realstory-engine/SKILL.md`).

- Channel-specific things only in `channels/<id>/channel.json`. Do not hard-code a channel in `vengine/`.
- Every handoff file must pass `python -m vengine validate <episode>`; shot lists must pass `python -m vengine variety`.
- Scene types are defined once in `vengine/scenes.py`; the renderer kit implements one component per type.
- Tests: `python -m pytest -q`.
- Secrets (OAuth client, tokens, API keys) live on the owner's PC in the profile's `youtube.secrets_dir` or env vars; never commit them.
- Owner talks Russian; code, comments and video text are English.
