"""Assemble SANTA'S STUCK: frames on twos -> 1080x1920 at 24 fps, captions, a light post and the amigurumi.ai end
card, muxed with the track.  Usage: python3 xpost.py FRAMES OUT.mp4 AUDIO [--from T0 --to T1]"""
import sys, os, math, subprocess, argparse
sys.path.insert(0, '/home/user/work/story')
import numpy as np
from PIL import Image, ImageFilter, ImageDraw
import run
from run import font
from engine import ease, clamp, back_out
import xstory as S

ap = argparse.ArgumentParser()
ap.add_argument('frames'); ap.add_argument('out'); ap.add_argument('audio')
ap.add_argument('--from', dest='t0', type=float, default=0.0)
ap.add_argument('--to', dest='t1', type=float, default=S.DUR)
a = ap.parse_args()
F = object.__new__(run.Film)
F.S = S
LOOK = dict(bloom=0.14, vignette=0.2, grain=0.018)
W, Hh = 1080, 1920


def end_card(im, t):
    """'Crochet them all on amigurumi.ai': a cream card slides up from the bottom, then the question on top."""
    d = t - S.T_END
    if d < 0:
        return
    k = back_out(clamp(d / 0.45), 1.6)
    lay = Image.new('RGBA', (W, Hh), (0, 0, 0, 0))
    dr = ImageDraw.Draw(lay)
    y0 = int(1480 + (1 - k) * 520)
    dr.rounded_rectangle((70, y0, W - 70, y0 + 330), radius=48, fill=(255, 248, 236, 240), outline=(200, 40, 60, 255), width=8)
    dr.text((W // 2, y0 + 48), 'CROCHET THEM ALL', font=font(62), fill=(200, 40, 60, 255), anchor='mt')
    dr.text((W // 2, y0 + 128), 'amigurumi.ai', font=font(118), fill=(36, 30, 60, 255), anchor='mt')
    dr.text((W // 2, y0 + 262), 'free patterns  •  3D models', font=font(40), fill=(110, 100, 120, 255), anchor='mt')
    im.paste(lay, (0, 0), lay)
    if d > 1.6:
        k2 = back_out(clamp((d - 1.6) / 0.3), 2.0)
        cap = Image.new('RGBA', (W, 420), (0, 0, 0, 0))
        c = ImageDraw.Draw(cap)
        for j, r in enumerate(["WHO'S NEXT DOWN", 'THE CHIMNEY?']):
            c.text((W // 2, 30 + 104 * j), r, font=font(92), fill=(255, 214, 64, 255) if j else (255, 251, 244, 255),
                   stroke_width=10, stroke_fill=(27, 24, 52, 255), anchor='mt')
        bb = cap.getbbox()
        cap = cap.crop(bb)
        cap = cap.resize((max(1, int(cap.width * k2)), max(1, int(cap.height * k2))), Image.BILINEAR)
        im.paste(cap, (W // 2 - cap.width // 2, 300 - cap.height // 2), cap)


tmp = a.out + '.frames'
os.makedirs(tmp, exist_ok=True)
n0, n1 = int(round(a.t0 * 24)), int(math.ceil(a.t1 * 24))
for i in range(n0, n1):
    t = i / 24
    j = int(t * 12 + 1e-6)
    src = os.path.join(a.frames, f'f{j:04d}.png')
    while not os.path.exists(src) and j > 0:
        j -= 1; src = os.path.join(a.frames, f'f{j:04d}.png')
    im = Image.open(src).convert('RGB').resize((W, Hh), Image.LANCZOS).filter(ImageFilter.UnsharpMask(1.2, 40, 2))
    if t < 0.6:                                   # fade in from black
        im = Image.blend(Image.new('RGB', im.size), im, ease(t / 0.6))
    im = F.post(im, t, LOOK)
    F.captions(im, t)
    end_card(im, t)
    im.save(os.path.join(tmp, f'{i - n0:05d}.jpg'), quality=94)
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', '24', '-i', os.path.join(tmp, '%05d.jpg'),
                '-ss', f'{a.t0:.3f}', '-t', f'{a.t1 - a.t0:.3f}', '-i', a.audio, '-map', '0:v', '-map', '1:a',
                '-c:v', 'libx264', '-preset', 'slow', '-crf', '19', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
                '-af', f'afade=t=out:st={max(0.0, a.t1 - a.t0 - 0.8):.2f}:d=0.8', '-shortest', '-movflags', '+faststart', a.out], check=True)
print('wrote', a.out)
