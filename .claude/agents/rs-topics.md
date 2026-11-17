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
