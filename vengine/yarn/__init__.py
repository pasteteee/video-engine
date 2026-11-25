"""Crochet yarn rendering for growth shots: a toy made stitch by stitch from its amikit pattern.

    render.py  the renderer (numba): soft plied yarn, temporally stable shading
    toy.py     pattern -> yarn centreline per piece, colour per node (colour zones included)
    grow.py    the growth shot: clock, camera, motion blur, frames + plan.json
    details.py face, felt, embroidery, appliques (cheeks, motifs) and ribbing
    stable.py  frame-to-frame stability probe (the flicker number used to compare renderer versions)

Needs numba and scipy (requirements-yarn.txt) and the amikit package (folder in $AMIKIT, default /home/user).
"""
