# Toy stories in 3D (Blender/Cycles)

The toys as on the site's studio previews, acting in a modelled living room. Everything runs on our server.

- `export_toy.py tid:height`: rig (pieces, joints, arms) from the yarn Dancer, to `<tid>.npz`.
- `export_ami.py tid:height`: the site's amikit model (smooth pieces with stitch UVs, embroidery, eyes, felt) plus that rig, to `<tid>.ami.pkl`.
- `mouths.py`: replacement mouths (half/open, embroidered lining, tongue, teeth), stop-motion style.
- `ami3d.py`: AmiToy (posing with the story engine's rig, eye pops, crocheted eyelids, mouth swaps), tiled crochet stitch material.
- `set3d.py`: the room (table, sofa, knitted blanket, shelf, fairy lights, lamp, candle, window) and lights.
- `film3d.py OUT --frames A B`: a story module (snack.py) rendered on twos (12 poses/s). `post3d.py` adds captions and post at 24 fps and the track.
- Needs bpy 5 in a Python 3.11 venv (`pip install bpy`), the story engine in `../toy-stories-2`, and `stitch_h.png`/`stitch_ao.png` (made by the snippet in the thread; see `ami_materials`).

## Crochet look and model clean-up (v2)

- `stitch_tile.py` draws the single-crochet stitch tile (two plump V legs, twisted plies, fibres, grooves) used by
  `ami3d.ami_materials()`; run it once to make `stitch_h.png` / `stitch_ao.png`.
- `unfold.py` cleans amikit meshes on export (`export_ami.py`): relaxes folded stitches where an applique crowds onto
  a curved piece, overlaps the rounds of a patch, tucks under-layers, lines each applique with its own yarn and turns
  any inside-out triangle back out. These removed the dark specks around the shark's face patch.
- Parts the rig does not name follow the piece they are sewn on (`rig.alias` from the spec's assembly, `rig.pmap`
  by nearest rig piece): cheeks, muzzles, brows now move with the head.
- `lookdev.py PKL OUT --views front,q34,face [--hide head,trim]` renders studio stills of one toy to compare with its
  AI preview before animating.

## Santa's Stuck (Christmas)

`xmas_set.py` (coffee-table Christmas set), `xmas3d.py` (story, acting, camera, set events; renders on twos),
`xstory.py` (captions), `xpost.py` (24 fps assembly, post, amigurumi.ai end card, audio mux).
Music: Lyria prompt in `santas-stuck.music-prompt.txt`.
