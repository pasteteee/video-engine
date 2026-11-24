"""Assemble the 3D film: rendered frames on twos -> 1080x1920 at 24 fps with the story's captions and a light post
(bloom, vignette, grain), muxed with the track.  Usage: python3 post3d.py FRAMES_DIR OUT.mp4 AUDIO"""
import sys, os, math, subprocess
sys.path.insert(0, '/home/user/work/story')
import numpy as np
from PIL import Image, ImageFilter
import run
import snack as S

frames, out, audio = sys.argv[1], sys.argv[2], sys.argv[3]
F = object.__new__(run.Film)
F.S = S
LOOK = dict(bloom=0.12, vignette=0.18, grain=0.02)
tmp = out + '.frames'
os.makedirs(tmp, exist_ok=True)
n = int(math.ceil(S.DUR * 24))
for i in range(n):
    t = i / 24
    j = min(int(t * 12 + 1e-6), len(os.listdir(frames)) - 1)
    src = os.path.join(frames, f'f{j:04d}.png')
    im = Image.open(src).convert('RGB').resize((1080, 1920), Image.LANCZOS).filter(ImageFilter.UnsharpMask(1.2, 40, 2))
    im = F.post(im, t, LOOK)
    F.captions(im, t)
    im.save(os.path.join(tmp, f'{i:05d}.jpg'), quality=94)
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', '24', '-i', os.path.join(tmp, '%05d.jpg'),
                '-i', audio, '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'slow', '-crf', '19',
                '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out], check=True)
print('wrote', out)
