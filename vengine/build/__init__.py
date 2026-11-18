"""Build shorts: a toy crocheted stitch by stitch on screen (the amigurumi channel's format).

    storyboard.py      the storyboard contract, timing, automatic captions and music events from the knit plan
    knit.py            the knit renderer hook: runs the channel's renderer, reads its frames (knit_plan contract)
    knit_crochetsim.py the default renderer adapter (crochetsim toy yarn, accelerating clock, moving camera)
    comp.py            the compositor: hook, grow, done, real life, CTA over the knit frames
    audio.py           music and stitch ticks synthesised from the same events as the picture
    render.py          mp4, audio mux, Shorts cover, YouTube thumbnail, frame sheet
"""
