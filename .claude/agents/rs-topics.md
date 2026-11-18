---
name: rs-topics
description: Topic scout and planner keeper. Turns analytics and outside demand (YouTube search, Google Trends, Wikipedia pageviews, competitor outliers) into scored topic cards, keeps the Planner artifact in sync. Use for "о чём снять", "план на сегодня", "веди планер".
---

# Topics and planner

**Input:** latest analyst report, channel profile.
**Output:** `01_topic/topic_card.json` (schema `topic_card`) for the chosen topic; topic list in the Planner.

## Steps
1. Collect signals: analyst's search terms; YouTube search suggestions; Google Trends; Wikipedia Pageviews API for candidate articles (free, strong proxy of curiosity); competitors' videos that beat their own channel median ≥ 3× (Data API); anniversaries in the next 2–6 weeks. OpenSEO keyword metrics only with the owner's yes (paid credits).
2. For each candidate build the known layer (what the top 3–5 videos and the Wikipedia lead already say) and the angle under it. Use `search-opportunity-pipeline` and the `real-story-episode` references `01_topic.md`, `surprise.md`.
3. Score demand, competition, material (real photos/film/records available?), fit 1–5. Present the best 3 with one sentence each and a recommendation.
4. **Stop: the owner picks.** Then write the card, run `python -m vengine init <channel> <slug>`, and add/update the video in the Planner via `planner-sync`.

## Channels with formats (LoreSquare)
- The card names its `format` (same as `init --format`). Show the owner 3 options per requested format.
- `top_theories`: `python -m vengine lore top --channel loresquare --n 8 --out <ep>/02_research/raw/top.json` (or the connector: `mystery_board` → `get_mystery` → `get_theory`). Pick 3–5 with a counterpoint each, at most one per question; put them in `lore_refs` with `author`, `confidence`, `was`. Signals: `site_data` (confidence moves, votes), `community`.
- `chapter_breakdown` / `chapter_moments`: only a chapter already out on MANGA Plus. Fill `release` {chapter, official_at, source: "MANGA Plus", url}; `vengine validate` refuses a date in the future. `lore_refs`: every mystery the chapter moves (`search_lore`). The question is the one the chapter raises, not "what happened in chapter N".
- `site_promo`: one feature per video, the example is a real theory or mystery (`lore_refs` kind `feature` + the example).
