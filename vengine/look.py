"""Episode look: background and accent colours picked from the episode's own photos.

The channel keeps its neutrals and signal colour (channel.json `style.tokens`);
every episode gets its own ground and accent so that a space story is night blue
with the yellow of the float collar and an Arctic story is cold grey with the
orange of a survival suit.

    python -m vengine look <episode> [--write]

Output `04_shots/look.json`:
    {"ground": "#0a1424", "ground_2": "#13233a", "accent": "#e8b430",
     "tint": "#8fa6c2", "hue": 255.0, "from": ["m_launch_photo", ...], "notes": [...]}

The director may override any value in the shot list's `look` (a human eye
beats k-means); the renderer reads `shotlist.look` first, then look.json.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

# ---- colour maths (OKLab / OKLCH, Björn Ottosson) -------------------------

def _srgb_to_lin(c):
    c = np.asarray(c, dtype=float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _lin_to_srgb(c):
    c = np.clip(np.asarray(c, dtype=float), 0, 1)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055)


def rgb_to_oklab(rgb):
    """rgb: (..., 3) floats 0..1 → (..., 3) OKLab."""
    r, g, b = np.moveaxis(_srgb_to_lin(rgb), -1, 0)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l, m, s = np.cbrt(l), np.cbrt(m), np.cbrt(s)
    return np.stack([
        0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
        1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
        0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s,
    ], axis=-1)


def oklab_to_rgb(lab):
    L, a, b = np.moveaxis(np.asarray(lab, dtype=float), -1, 0)
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return _lin_to_srgb(np.stack([
        4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    ], axis=-1))


def oklch_to_hex(L: float, C: float, h: float) -> str:
    """OKLCH → hex, reducing chroma until the colour is inside sRGB."""
    for _ in range(40):
        lab = np.array([L, C * math.cos(math.radians(h)), C * math.sin(math.radians(h))])
        r, g, b = np.moveaxis(np.asarray(lab), -1, 0)
        l_ = (r + 0.3963377774 * g + 0.2158037573 * b) ** 3
        m_ = (r - 0.1055613458 * g - 0.0638541728 * b) ** 3
        s_ = (r - 0.0894841775 * g - 1.2914855480 * b) ** 3
        lin = np.array([
            4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
            -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
            -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_,
        ])
        if lin.min() >= -1e-4 and lin.max() <= 1 + 1e-4:
            break
        C *= 0.92
    rgb = _lin_to_srgb(lin)
    return "#" + "".join(f"{int(round(v * 255)):02x}" for v in rgb)


def hex_to_oklch(hx: str) -> tuple[float, float, float]:
    hx = hx.lstrip("#")
    rgb = np.array([int(hx[i:i + 2], 16) / 255 for i in (0, 2, 4)])
    L, a, b = rgb_to_oklab(rgb)
    return float(L), float(math.hypot(a, b)), float(math.degrees(math.atan2(b, a)) % 360)


def contrast(hex1: str, hex2: str) -> float:
    def lum(hx):
        hx = hx.lstrip("#")
        r, g, b = _srgb_to_lin([int(hx[i:i + 2], 16) / 255 for i in (0, 2, 4)])
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    a, b = sorted((lum(hex1), lum(hex2)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def hue_dist(a: float, b: float) -> float:
    d = abs(a - b) % 360
    return min(d, 360 - d)


# ---- clustering --------------------------------------------------------

def _kmeans(x: np.ndarray, k: int, iters: int = 25, seed: int = 7):
    rng = np.random.default_rng(seed)
    cent = x[rng.choice(len(x), size=min(k, len(x)), replace=False)]
    for _ in range(iters):
        d = ((x[:, None, :] - cent[None]) ** 2).sum(-1)
        lab = d.argmin(1)
        new = np.array([x[lab == i].mean(0) if (lab == i).any() else cent[i] for i in range(len(cent))])
        if np.allclose(new, cent, atol=1e-5):
            break
        cent = new
    counts = np.bincount(lab, minlength=len(cent))
    return cent, counts


def _pixels(paths: list[Path], side: int = 96) -> np.ndarray:
    from PIL import Image
    out = []
    for p in paths:
        im = Image.open(p).convert("RGB")
        im.thumbnail((side, side))
        out.append(np.asarray(im, dtype=float).reshape(-1, 3) / 255)
    return np.concatenate(out) if out else np.zeros((0, 3))


# ---- the look ----------------------------------------------------------

SIGNAL_HUE = 29.0  # channel red (#e2231a); the accent must not look like it


def pick(paths: list[Path], k: int = 10) -> dict:
    """Pick ground / accent / tint from photos. Pure function of the pixels."""
    notes: list[str] = []
    lab = rgb_to_oklab(_pixels(paths))
    if len(lab) == 0:
        raise ValueError("no photos to read")
    cent, counts = _kmeans(lab, k)
    share = counts / counts.sum()
    L = cent[:, 0]
    C = np.hypot(cent[:, 1], cent[:, 2])
    H = np.degrees(np.arctan2(cent[:, 2], cent[:, 1])) % 360

    # ground hue: weighted circular mean over tinted clusters, dark ones count more
    tinted = C > 0.018
    if tinted.any():
        w = share * tinted * (1.2 - L) * np.minimum(C, 0.08)
        hx = (w * np.cos(np.radians(H))).sum()
        hy = (w * np.sin(np.radians(H))).sum()
        hue = math.degrees(math.atan2(hy, hx)) % 360
        g_chroma = float(np.clip((w * C).sum() / max(w.sum(), 1e-9) * 0.7, 0.02, 0.05))
    else:  # black-and-white archive: warm graphite
        hue, g_chroma = 75.0, 0.012
        notes.append("photos are monochrome: neutral warm ground")

    ground = oklch_to_hex(0.18, g_chroma, hue)
    ground_2 = oklch_to_hex(0.26, g_chroma * 1.1, hue)
    tint = oklch_to_hex(0.72, min(g_chroma * 1.3, 0.05), hue)

    # accent: the hue that the vivid pixels share most (an orange suit, a yellow collar),
    # read from pixels, not centroids, because k-means averages small vivid areas away
    Cp = np.hypot(lab[:, 1], lab[:, 2])
    Hp = np.degrees(np.arctan2(lab[:, 2], lab[:, 1])) % 360
    vivid = (Cp > 0.07) & (lab[:, 0] > 0.40) & (lab[:, 0] < 0.95)
    a_h = None
    if vivid.mean() > 0.003:
        bins = (Hp[vivid] // 15).astype(int)
        w = np.bincount(bins, weights=Cp[vivid] ** 2, minlength=24)
        for b in range(24):  # damp hues that look like the ground or the channel red
            c = b * 15 + 7.5
            if hue_dist(c, hue) < 40:
                w[b] *= 0.12
            if hue_dist(c, SIGNAL_HUE) < 18:
                w[b] *= 0.35
        b = int(w.argmax())
        sel = vivid & ((Hp // 15).astype(int) == b)
        a_h = float(np.degrees(np.arctan2(lab[sel, 2].mean(), lab[sel, 1].mean())) % 360)
        a_c = float(np.percentile(Cp[sel], 75))
    if a_h is None:
        a_h, a_c = (hue + 180) % 360, 0.13
        notes.append("no saturated colour in the photos: accent is the ground's complement")
    a_L, a_C = 0.80, float(np.clip(a_c, 0.11, 0.17))
    accent = oklch_to_hex(a_L, a_C, a_h)
    while contrast(accent, ground) < 4.5 and a_L < 0.95:
        a_L += 0.02
        accent = oklch_to_hex(a_L, a_C, a_h)
    if hue_dist(a_h, SIGNAL_HUE) < 20:
        notes.append("accent is close to the channel red: keep signal for the stop block only")
    return {"ground": ground, "ground_2": ground_2, "accent": accent, "tint": tint,
            "hue": round(hue, 1), "accent_hue": round(a_h, 1),
            "contrast_accent": round(float(contrast(accent, ground)), 2),
            "contrast_text": round(float(contrast("#f2efe8", ground)), 2), "notes": notes}


def for_episode(folder: Path, max_photos: int = 12) -> dict:
    """Read 02_research/media.json, use real photos (archival first)."""
    folder = Path(folder)
    media = json.loads((folder / "02_research/media.json").read_text(encoding="utf-8"))
    items = [m for m in media.get("items", []) if m.get("kind") == "photo" and m.get("license") != "generated"]
    paths, ids = [], []
    for m in items[:max_photos]:
        p = folder / "02_research" / m["path"]
        if p.exists():
            paths.append(p)
            ids.append(m["id"])
    if not paths:
        raise FileNotFoundError("no photo files found from 02_research/media.json")
    out = pick(paths)
    out["from"] = ids
    return out
