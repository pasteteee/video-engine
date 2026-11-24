"""Crocheted props for the story Shorts (amikit spec v1). python make_props.py -> <id>/spec.json"""
import json, os
Y = {"weight": "DK", "hook_mm": 2.5, "stitch_mm": 4.0, "round_mm": 3.6, "thickness_mm": 1.9}
P = {}
P['tv-remote'] = {
  "name": "tv_remote", "title": "TV remote", "colours": {"charcoal": "#3a3d44", "red": "#e0393e", "grey": "#9aa0a8", "teal": "#3fb6b0"},
  "parts": [{"id": "body", "rounds": ["ch 7", "inc 4 to 22", "even 24", "dec 4 to 14", "dec 7 to 7"], "colour": "charcoal", "stuff": "medium", "flatten": 0.5}],
  "assembly": [{"part": "body", "axis": [0, 1, 0]}],
  "face": [{"type": "safety_nose", "on": "body", "at": {"round": 24, "az": 0}, "size_mm": [6, 6], "shape": "oval", "colour": "red", "id": "power"},
           {"type": "safety_nose", "on": "body", "at": {"round": 18, "az": 0}, "size_mm": [9, 9], "shape": "oval", "colour": "teal", "id": "ok"},
           {"type": "satin", "on": "body", "at": {"round": 12, "az": 14}, "width_mm": 3, "height_mm": 3, "shape": "oval", "colour": "grey", "thickness_mm": 1.2, "mirror": True, "id": "b1"},
           {"type": "satin", "on": "body", "at": {"round": 9, "az": 14}, "width_mm": 3, "height_mm": 3, "shape": "oval", "colour": "grey", "thickness_mm": 1.2, "mirror": True, "id": "b2"},
           {"type": "satin", "on": "body", "at": {"round": 6, "az": 14}, "width_mm": 3, "height_mm": 3, "shape": "oval", "colour": "grey", "thickness_mm": 1.2, "mirror": True, "id": "b3"}]}
P['striped-sock'] = {
  "name": "striped_sock", "title": "Striped sock", "colours": {"cream": "#f4ede0", "red": "#d8434b", "mustard": "#e9b53c"},
  "parts": [{"id": "body", "rounds": ["mr 6", "inc 6 to 18", "even 6", "even 14", "blo 18", "even 2"], "colour": "cream", "end": "open", "stuff": "light",
             "colours": [{"rounds": [1, 4], "colour": "red"}, {"rounds": [12, 13], "colour": "red"}, {"rounds": [16, 17], "colour": "mustard"}, {"rounds": [20, 21], "colour": "red"}, {"rounds": [24, 27], "colour": "red"}],
             "bend": {"deg": 85, "at": 7, "over": 3, "toward": [0, 0, 1]}}],
  "assembly": [{"part": "body", "axis": [0, 1, 0]}], "face": []}
P['popcorn'] = {
  "name": "popcorn", "title": "Popcorn", "colours": {"butter": "#fff4d6", "gold": "#f0c868"},
  "parts": [{"id": "body", "rounds": ["mr 6", "12", "popcorns every 2", "popcorns every 2 from 1", "dec 6 to 6"], "colour": "butter", "stuff": "firm",
             "colours": [{"rounds": [1, 1], "colour": "gold"}]}],
  "assembly": [{"part": "body", "axis": [0, 1, 0]}], "face": []}
P['retro-toaster'] = {
  "name": "retro_toaster", "title": "Retro toaster", "colours": {"mint": "#9fd8c9", "cream": "#fbf3e4", "charcoal": "#2c2c30", "chrome": "#c9ced6", "red": "#e2484c"},
  "parts": [{"id": "body", "rounds": ["ch 17", "inc 4 to 46", "blo 46", "even 13", "flo 46", "dec 6 to 34", "dec 10 to 24"], "colour": "mint", "stuff": "firm",
             "colours": [{"rounds": [1, 4], "colour": "cream"}, {"rounds": [11, 12], "colour": "cream"}]},
            {"id": "lever", "rounds": ["mr 6", "even 4"], "colour": "red", "end": "closed", "stuff": "firm", "flatten": 0.3},
            {"id": "knob", "rounds": ["mr 6", "even 1"], "colour": "chrome", "end": "open", "stuff": "light"},
            {"id": "foot", "rounds": ["mr 6", "even 2"], "colour": "charcoal", "end": "closed", "stuff": "firm"}],
  "assembly": [{"part": "body", "axis": [0, 1, 0]},
               {"part": "lever", "on": "body", "at": {"round": 14, "az": 90}, "dir": [1, 0, 0], "sink": 2},
               {"part": "knob", "on": "body", "at": {"round": 9, "az": 60}, "applique": True},
               {"part": "foot", "on": "body", "at": {"round": 2, "az": 45}, "dir": [0, -1, 0], "mirror": True, "sink": 2}],
  "face": [{"type": "satin", "on": "body", "at": {"round": 22.6, "az": 90}, "width_mm": 34, "height_mm": 5, "shape": "oval", "colour": "charcoal", "thickness_mm": 0.6, "mirror": True, "id": "slot"},
           {"type": "safety_eye", "on": "body", "at": {"round": 14, "az": 14}, "size_mm": 9, "mirror": True, "id": "eye"},
           {"type": "stitch", "on": "body", "points": [[11.5, -7], [10.8, -3.5], [10.6, 0], [10.8, 3.5], [11.5, 7]], "colour": "charcoal", "thickness_mm": 1.4, "id": "smile"}]}
P['toast'] = {
  "name": "toast", "title": "Toast slice", "colours": {"bread": "#f3d9a4", "crust": "#b86f2f", "dark brown": "#4b2722", "pink": "#ffa9b0"},
  "parts": [{"id": "body", "rounds": ["ch 8", "inc 4 to 24", "even 9", "inc 4 to 28", "28", "dec 4 to 20", "dec 10 to 10"], "colour": "bread", "stuff": "light", "flatten": 0.8,
             "colours": [{"rounds": [1, 1], "colour": "crust"}, {"rounds": [1, 20], "az": [72, 108], "colour": "crust"}, {"rounds": [1, 20], "az": [-108, -72], "colour": "crust"}, {"rounds": [15, 20], "colour": "crust"}]}],
  "assembly": [{"part": "body", "axis": [0, 1, 0]}],
  "face": [{"type": "safety_eye", "on": "body", "at": {"round": 9, "az": 18}, "size_mm": 6, "mirror": True, "id": "eye"},
           {"type": "stitch", "on": "body", "points": [[6.6, -7], [6.1, -3], [6.0, 0], [6.1, 3], [6.6, 7]], "colour": "dark brown", "thickness_mm": 1.2, "id": "smile"}]}
for k, v in P.items():
    v.setdefault("yarn", Y)
    os.makedirs(k, exist_ok=True)
    json.dump(v, open(f'{k}/spec.json', 'w'), indent=1)
print('ok', list(P))
