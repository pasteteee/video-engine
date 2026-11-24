# Toy stories 2: Snack Attack, The Toaster

Story Shorts: yarn toys and crocheted props (`../../props`) acting in a photographed set.

- `engine.py`: actors (Dancer + rig with elbow bends, eye pop/blink, held props, hidden pieces), LiveStage, camera
  that matches the background photo crop, compositing with real cast shadows from the renderer's floor.
- `acting.py`: life (breathing, sway, blinks), hops, shakes, beat-synced dance moves.
- `snack.py`, `toaster.py`: the two stories, timed to their tracks.
- `run.py STORY stills OUT.jpg t1,t2` / `run.py STORY frames DIR --part i/n`.
- Music: `lyria.py` (Google Lyria 3 Pro, prompts `snack2.txt`, `toaster2.txt`), `transcribe.py` gets the lyric timeline.
- Backgrounds: `gen.py` (Gemini 3 Pro Image, 4K 9:16), prompts `movie.txt`, `kitchen.txt`.
