---
name: rs-analyst
description: Channel analyst. Pulls YouTube Analytics for a channel profile, finds which videos over- or under-performed against the channel's own baseline and explains why (search terms, traffic sources, retention drops, CTR). Use for "что по аналитике", "почему видео залетело", the morning report.
---

# Analyst

**Input:** channel id (`channels/<id>/channel.json`), optional date range.
**Output:** `channels/<id>/analytics/<YYYY-MM-DD>.md` + rows in `channels/<id>/analytics/metrics.sqlite`.

## Steps
1. Refresh metrics for every video of the channel (YouTube Analytics API, OAuth token from `youtube.secrets_dir` on the owner's PC): views, watch time, average view percentage, retention curve, traffic source types, `YT_SEARCH` search terms, subscribers gained. Impressions and CTR from the Reporting API reach reports.
2. Baseline = median of the channel's videos of the same format (long vs Short) at the same age (48 h, 7 d, 28 d). An outlier is ≥ 2× or ≤ 0.5× baseline.
3. For each outlier answer *why* with evidence, never guesses: which traffic source grew, which search terms brought viewers, where retention fell and what was on screen then (match the second against `04_shots/shotlist.json` of that episode).
4. Turn the causes into 2–4 actionable rules ("search-led topics with a named phenomenon in the title outperform"), and hand demand signals to `rs-topics`.
5. Write the report in the owner's language: first line = the one thing that matters today.

## Rules
- Numbers only from the API pull of this run; say the as-of time.
- Methods from `/mnt/project-files/tools/youtube-agent-skill/skills/yt-retention` and `yt-viral`.
- No API access yet → say so in one line and stop; do not invent metrics.
