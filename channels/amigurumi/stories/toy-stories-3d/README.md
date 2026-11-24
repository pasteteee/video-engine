# Toy stories in 3D (Blender/Cycles)

The toys as on the site's studio previews, acting in a modelled living room. Everything runs on our server.

- `export_toy.py tid:height`: rig (pieces, joints, arms) from the yarn Dancer, to `<tid>.npz`.
- `export_ami.py tid:height`: the site's amikit model (smooth pieces with stitch UVs, embroidery, eyes, felt) plus that rig, to `<tid>.ami.pkl`.
- `mouths.py`: replacement mouths (half/open, embroidered lining, tongue, teeth), stop-motion style.
- `ami3d.py`: AmiToy (posing with the story engine's rig, eye pops, crocheted eyelids, mouth swaps), tiled crochet stitch material.
- `set3d.py`: the room (table, sofa, knitted blanket, shelf, fairy lights, lamp, candle, window) and lights.
- `film3d.py OUT --frames A B`: a story module (snack.py) rendered on twos (12 poses/s). `post3d.py` adds captions and post at 24 fps and the track.
- Needs bpy 5 in a Python 3.11 venv (`pip install bpy`), the story engine in `../toy-stories-2`, and `stitch_h.png`/`stitch_ao.png` (made by the snippet in the thread; see `ami_materials`).
