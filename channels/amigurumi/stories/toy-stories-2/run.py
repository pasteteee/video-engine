"""python run.py STORY frames OUTDIR [--part i/n] [--step k] | stills OUT.jpg t1,t2,... | mux OUTDIR OUT.mp4"""
import importlib, math, os, sys, time, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from engine import LiveStage, make_cam, project, bg_crop, composite, OUTW, OUTH, clamp, ease, back_out

FPS = 24
FONT = '/home/user/video-engine/channels/amigurumi/brand/fonts/Unbounded-Bold.ttf'
_F = {}


def font(sz):
    if sz not in _F:
        _F[sz] = ImageFont.truetype(FONT, sz)
    return _F[sz]


class Film:
    def __init__(self, story):
        self.S = importlib.import_module(story)
        S = self.S
        self.A = S.build()
        self.st = LiveStage(self.A, OUTW, OUTH, ss=1, light=S.LIGHT, extent=S.EXTENT, center=S.CENTER)
        self.photo = Image.open(S.BG).convert('RGB')
        c = S.CAM0
        self.cam0 = make_cam(c['pos'], c['target'], c['fov'])

    def frame(self, t):
        S = self.S
        params = S.pose(t, self.A)
        tg, fov, shk = S.camera(t)
        tg = np.asarray(tg, float) + np.array([0, getattr(S, 'AIM_UP', 0.0), 0])
        # handheld drift
        pos = np.asarray(S.CAM0['pos'], float) + np.array([3 * math.sin(0.31 * t), 2 * math.sin(0.23 * t + 1), 0])
        tgh = tg + np.array([1.2 * math.sin(0.41 * t + 2), 0.8 * math.sin(0.37 * t), 0])
        cam = make_cam(pos, tgh, fov)
        rgb, a = self.st.render_frame(params, cam)
        cx, cy, _ = project(self.cam0, tgh)
        zoom = math.tan(math.radians(S.CAM0['fov']) / 2) / math.tan(math.radians(fov) / 2)
        bgim, _ = bg_crop(self.photo, cx, cy, zoom, blur=max(0.0, (zoom - 1.0) * 1.2))
        look = dict(S.LOOK)
        blobs = []
        for act, p in zip(self.A, params):
            if p['show'] < 0.5 or p['scale'] < 0.3:
                continue
            fx, fy, z1 = project(cam, (p['x'], 0, p['z']))
            ex, _, _ = project(cam, (p['x'] + act.width * 0.5 * p['scale'], 0, p['z']))
            rw = abs(ex - fx) * 0.85
            hgt = max(0.0, p['y'])
            k = 1.0 / (1.0 + hgt / 30.0)
            blobs.append((float(fx), float(fy), float(rw * (1 + 0.3 * (1 - k))), float(rw * 0.22), 0.9 * k))
        look['_blobs'] = blobs
        look['_wrap'] = np.asarray(bgim.filter(ImageFilter.GaussianBlur(30)), np.float32) / 255
        out = composite(np.asarray(bgim, np.float32) / 255, rgb, a, look)
        im = Image.fromarray((out * 255 + 0.5).astype(np.uint8))
        if hasattr(S, 'fx'):
            im = S.fx(im, t, cam, params, self.A, project)
        im = self.post(im, t, look)
        if shk:
            dx = shk * math.sin(t * 61.0)
            dy = shk * math.sin(t * 47.0 + 1)
            im = im.transform(im.size, Image.AFFINE, (1, 0, dx, 0, 1, dy), Image.BILINEAR)
            im = im.resize((int(OUTW * 1.01), int(OUTH * 1.01)), Image.BILINEAR).crop((5, 10, 5 + OUTW, 10 + OUTH))
        self.captions(im, t)
        return im

    def post(self, im, t, look):
        a = np.asarray(im, np.float32) / 255
        if look.get('bloom'):
            hi = np.clip((a - 0.72) / 0.28, 0, 1)
            bl = np.asarray(Image.fromarray((hi * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(28)), np.float32) / 255
            a = 1 - (1 - a) * (1 - bl * look['bloom'])
        if look.get('vignette'):
            yy, xx = np.mgrid[0:OUTH, 0:OUTW]
            r = ((xx / OUTW - 0.5) ** 2 + ((yy / OUTH - 0.5) * 1.0) ** 2) ** 0.5
            a = a * (1 - look['vignette'] * np.clip((r - 0.35) / 0.45, 0, 1) ** 1.5)[..., None]
        if look.get('grain'):
            rng = np.random.default_rng(int(t * 1000) % 2 ** 31)
            g = rng.normal(0, look['grain'], (OUTH // 2, OUTW // 2)).astype(np.float32)
            g = np.asarray(Image.fromarray(g).resize((OUTW, OUTH), Image.BILINEAR))
            a = a + g[..., None] * (0.6 + 0.4 * (1 - a))
        return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8))

    def captions(self, im, t):
        for t0, t1, rows, where in self.S.CAPS:
            if not (t0 <= t < t1):
                continue
            age = t - t0
            k = back_out(clamp(age / 0.18), 2.2) if age < 0.18 else 1.0
            k *= 1 - 0.15 * ease((t - (t1 - 0.12)) / 0.12)
            if age < 0:
                continue
            al = 1.0 if t < t1 - 0.1 else max(0.0, (t1 - t) / 0.1)
            big = max(len(r) for r in rows)
            sz = int(min(118, 900 / max(4, big) * 1.55))
            while sz > 40 and max(font(sz).getlength(r) for r in rows) > 940:
                sz -= 4
            y = 330 if where == 'top' else 860
            lay = Image.new('RGBA', (OUTW, 520), (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            yy = 40
            for j, r in enumerate(rows):
                fill = (255, 214, 64) if (j == len(rows) - 1 and len(rows) > 1) or r.isupper() and len(rows) == 1 else (255, 251, 244)
                if r.islower():
                    fill = (255, 251, 244)
                d.text((OUTW // 2, yy), r, font=font(sz), fill=fill + (255,), stroke_width=max(6, sz // 9),
                       stroke_fill=(27, 24, 52, 255), anchor='mt')
                yy += int(sz * 1.12)
            bb = lay.getbbox()
            if not bb:
                continue
            lay = lay.crop(bb)
            if k != 1.0:
                lay = lay.resize((max(1, int(lay.width * k)), max(1, int(lay.height * k))), Image.BILINEAR)
            if al < 1:
                lay.putalpha(lay.getchannel('A').point(lambda v: int(v * al)))
            rotd = -3 if (int(t0 * 10) % 2) else 3
            lay = lay.rotate(rotd * (1 if age > 0.18 else 2), resample=Image.BICUBIC, expand=True)
            im.paste(lay, (OUTW // 2 - lay.width // 2, y - lay.height // 2 + 120 * (where == 'top') // 2), lay)


def main():
    story, mode = sys.argv[1], sys.argv[2]
    F = Film(story)
    S = F.S
    if mode == 'stills':
        out, ts = sys.argv[3], [float(x) for x in sys.argv[4].split(',')]
        ims = []
        for t in ts:
            t1 = time.time()
            ims.append(F.frame(t))
            print(f't={t} {time.time() - t1:.1f}s', flush=True)
        cols = min(len(ims), 5)
        rows = (len(ims) + cols - 1) // cols
        sw, sh = 360, 640
        W = Image.new('RGB', (cols * sw, rows * (sh + 30)), (20, 20, 20))
        d = ImageDraw.Draw(W)
        for i, (t, im) in enumerate(zip(ts, ims)):
            x, y = (i % cols) * sw, (i // cols) * (sh + 30)
            W.paste(im.resize((sw, sh), Image.LANCZOS), (x, y))
            d.text((x + 8, y + sh + 6), f'{t:.2f}s', fill=(255, 255, 255))
        W.save(out, quality=88)
        if len(ims) == 1:
            ims[0].save(out.replace('.jpg', '_full.jpg'), quality=92)
    elif mode == 'frames':
        outdir = sys.argv[3]
        os.makedirs(outdir, exist_ok=True)
        part = [a for a in sys.argv if a.startswith('--part')]
        i, n = (1, 1)
        if part:
            i, n = map(int, sys.argv[sys.argv.index(part[0]) + 1].split('/'))
        N = int(round(S.DUR * FPS))
        for f in range(i - 1, N, n):
            fn = f'{outdir}/f{f:05d}.jpg'
            if os.path.exists(fn):
                continue
            t1 = time.time()
            F.frame(f / FPS).save(fn, quality=93)
            print(f'{f}/{N} {time.time() - t1:.1f}s', flush=True)


if __name__ == '__main__':
    main()
