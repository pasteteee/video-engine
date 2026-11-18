"""Music and sound for a build short, synthesised from the same events as the picture (numpy only).

Sections follow the storyboard: a soft pad and a bell per hook word; the groove enters with the knit and tightens
as the stitches speed up (kick 1 & 3 → four on the floor + 16th hats, a snare roll into the held breath); every
stitch is a tick (pitch rises with progress, locked to the grid when fast); a whoosh on each caption; the drop with
a crash on "Done!"; lighter for the real-life photo; the groove and a bell on the CTA button; a soft tail.

    wav = render(events, bpm=120, key="F", seed=1)  ->  float32 (N, 2) at SR
"""
from __future__ import annotations

import math
import wave
from pathlib import Path

import numpy as np

SR = 44100
NOTE = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
        "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
# I - IV - V - I - vi - IV - V - V7 in the key, as semitones of the root and chord quality
PROG = [(0, "maj"), (0, "maj"), (5, "maj"), (7, "maj"), (0, "maj"), (9, "min"), (5, "maj"), (7, "dom")]
QUAL = {"maj": [0, 4, 7, 12], "min": [0, 3, 7, 12], "dom": [0, 4, 7, 10]}


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def env(n, a=0.005, d=0.2, s=0.0, r=0.05, hold=None):
    """ADSR as samples; hold = seconds at sustain before release (default: until the end)."""
    t = np.arange(n) / SR
    e = np.minimum(1.0, t / max(a, 1e-4))
    dec = s + (1 - s) * np.exp(-(t - a) / max(d, 1e-4))
    e = np.where(t < a, e, dec)
    if hold is not None:
        tr = t - (a + hold)
        e = np.where(tr > 0, e * np.exp(-tr / max(r, 1e-4)), e)
    return e


def _lp_fast(x, cut):
    """Cheap smoothing low-pass (moving average), enough for noise colouring."""
    k = max(1, int(SR / cut / 2))
    return np.convolve(x, np.ones(k) / k, mode="same")


class Bus:
    def __init__(self, n):
        self.x = np.zeros((n, 2), np.float32)

    def add(self, sig, t, gain=1.0, pan=0.0):
        i = int(t * SR)
        if i >= len(self.x) or i < 0:
            return
        sig = sig[: len(self.x) - i] * gain
        l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
        self.x[i:i + len(sig), 0] += sig * l * 1.414
        self.x[i:i + len(sig), 1] += sig * r * 1.414


class Kit:
    def __init__(self, seed=1):
        rng = np.random.default_rng(seed)
        self.noise = rng.standard_normal(SR * 3).astype(np.float32)
        n = int(0.45 * SR); t = np.arange(n) / SR
        f = 48 + 110 * np.exp(-t * 28)
        self.kick = (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7.5) +
                     0.25 * self.noise[:n] * np.exp(-t * 300)).astype(np.float32)
        n = int(0.25 * SR); t = np.arange(n) / SR
        e = sum(np.exp(-np.maximum(0, t - d) * 60) * (t >= d) for d in (0, 0.009, 0.019)) / 3 + np.exp(-t * 18) * 0.4
        c = self.noise[:n] - _lp_fast(self.noise[:n], 900)
        self.clap = (c * e * 0.7).astype(np.float32)
        n = int(0.06 * SR); t = np.arange(n) / SR
        h = self.noise[1000:1000 + n] - _lp_fast(self.noise[1000:1000 + n], 6000)
        self.hat = (h * np.exp(-t * 80) * 0.5).astype(np.float32)
        n = int(0.3 * SR); t = np.arange(n) / SR
        h = self.noise[3000:3000 + n] - _lp_fast(self.noise[3000:3000 + n], 5000)
        self.ohat = (h * np.exp(-t * 14) * 0.35).astype(np.float32)
        n = int(0.2 * SR); t = np.arange(n) / SR
        self.snare = ((self.noise[5000:5000 + n] * 0.6 + np.sin(2 * np.pi * 190 * t) * 0.5) * np.exp(-t * 22)).astype(np.float32)
        n = int(2.2 * SR); t = np.arange(n) / SR
        cr = self.noise[:n] - _lp_fast(self.noise[:n], 4000)
        self.crash = (cr * np.exp(-t * 2.2) * 0.4).astype(np.float32)
        n = int(0.6 * SR); t = np.arange(n) / SR
        w = self.noise[2000:2000 + n] * np.sin(np.pi * t / t[-1]) ** 2
        self.whoosh = (_lp_fast(w, 2500) * 0.9).astype(np.float32)

    def tick(self, s):
        """One stitch: a short wooden click that rises in pitch as the toy fills in."""
        n = int(0.05 * SR); t = np.arange(n) / SR
        f = 1400 + 1600 * s
        return ((np.sin(2 * np.pi * f * t) * 0.6 + self.noise[:n] * 0.25) * np.exp(-t * 140)).astype(np.float32)


def tone(midi, dur, kind="pluck"):
    n = int((dur + 0.6) * SR); t = np.arange(n) / SR; f = hz(midi)
    if kind == "pluck":
        x = sum(np.sin(2 * np.pi * f * h * t) / h ** 1.6 for h in range(1, 6)) * np.exp(-t * (3.5 + f / 400))
        return (x * env(n, 0.003, 0.4, 0.0) * 0.6).astype(np.float32)
    if kind == "bell":
        x = np.sin(2 * np.pi * f * t + 1.8 * np.sin(2 * np.pi * f * 3.5 * t) * np.exp(-t * 4))
        return (x * np.exp(-t * 2.6) * 0.5).astype(np.float32)
    if kind == "pad":
        x = sum(np.sin(2 * np.pi * f * d * t + d) for d in (0.995, 1.0, 1.006)) / 3
        x += 0.25 * np.sin(2 * np.pi * f * 2 * t)
        return (x * env(n, 0.35, 1.0, 0.8, 0.5, hold=dur) * 0.35).astype(np.float32)
    if kind == "bass":
        x = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 2 * t)
        return (x * env(n, 0.005, 0.25, 0.6, 0.08, hold=dur) * 0.6).astype(np.float32)
    raise ValueError(kind)


def reverb(x, seconds=1.6, seed=3):
    """Convolution with a decaying noise tail (FFT), stereo-decorrelated."""
    rng = np.random.default_rng(seed)
    n = int(seconds * SR); t = np.arange(n) / SR
    out = np.zeros_like(x)
    for ch in range(2):
        ir = rng.standard_normal(n) * np.exp(-t * 6.9 / seconds)
        ir = _lp_fast(ir, 5000); ir /= np.sqrt((ir ** 2).sum()) + 1e-9
        L = len(x[:, ch]) + n - 1; N = 1 << (L - 1).bit_length()
        y = np.fft.irfft(np.fft.rfft(x[:, ch], N) * np.fft.rfft(ir, N), N)[: len(x)]
        out[:, ch] = y
    return out


def render(E: dict, bpm: float = 120.0, key: str = "F", seed: int = 1) -> np.ndarray:
    """Stereo float32 (N, 2): the whole soundtrack of the short."""
    B = 60.0 / bpm                     # one beat; the picture's beat is E['BEAT']
    dur = E["T_END"] + 0.8
    N = int(dur * SR)
    kit = Kit(seed)
    drums, music, fx, wet = Bus(N), Bus(N), Bus(N), Bus(N)
    root = 48 + NOTE.get(key, 5)       # the key's root around C3
    bar = 4 * B

    def chord(t):
        r, q = PROG[int(t // (2 * B)) % len(PROG)]
        return [root + r + i for i in QUAL[q]]

    G, D, Br, R, C, END = E["T_GROW"], E["T_DONE"], E["BREATH"], E["T_REAL"], E["T_CTA"], E["T_END"]
    # pad under everything but the breath, one chord per half bar
    t = 0.0
    while t < END:
        if not (Br <= t < D):
            c = chord(t)
            for m in c[:3]:
                wet.add(tone(m + 12, 2 * B, "pad"), t, 0.16 if t < G else 0.12)
            music.add(tone(c[0] - 12, 2 * B * 0.9, "bass"), t, 0.0 if t < G else 0.42)
        t += 2 * B
    # hook: a bell for each word line
    for k, tw in enumerate(E.get("hook_words", [])):
        music.add(tone(root + 24 + [0, 4, 7, 12][k % 4], 0.6, "bell"), tw, 0.35, pan=-0.2 + 0.2 * k)
        wet.add(tone(root + 24 + [0, 4, 7, 12][k % 4], 0.6, "bell"), tw, 0.2)

    def steps(t0, t1, fn):
        t = t0; i = 0
        while t < t1 - 1e-6:
            fn(t, i % 16); t += B / 4; i += 1

    mid = G + (D - G) * 0.6

    def groove_a(t, s):
        if s % 8 == 0:
            drums.add(kit.kick, t, 0.8)
        if s % 8 == 4:
            drums.add(kit.clap, t, 0.45); wet.add(kit.clap, t, 0.2)
        if s % 4 == 2:
            drums.add(kit.hat, t, 0.12, -0.3)

    def groove_b(t, s):
        if s % 4 == 0:
            drums.add(kit.kick, t, 0.9)
        if s % 8 == 4:
            drums.add(kit.clap, t, 0.55); wet.add(kit.clap, t, 0.2)
        drums.add(kit.hat, t, 0.16 if s % 2 else 0.09, -0.3)
        if s % 4 == 2:
            drums.add(kit.ohat, t, 0.08, 0.3)

    steps(G, mid, groove_a)
    steps(mid, Br, groove_b)
    # snare roll into the breath
    t, n = max(G, Br - 4 * B), 0
    for dv in (4, 4, 8, 8, 8, 8, 16, 16, 16, 16, 16, 16, 16, 16):
        if t >= Br - 1e-6:
            break
        drums.add(kit.snare, t, 0.12 + n * 0.02, 0.05); t += 4 * B / dv; n += 1
    fx.add(kit.whoosh[::-1].copy(), max(0, Br - 0.6), 0.5)       # a riser into the breath
    # the drop on Done!
    drums.add(kit.kick, D, 1.1); drums.add(kit.crash, D, 0.5, -0.2); drums.add(kit.crash, D, 0.35, 0.25)

    def drop(t, s):
        if s % 4 == 0:
            drums.add(kit.kick, t, 0.95)
        if s % 8 == 4:
            drums.add(kit.clap, t, 0.6); drums.add(kit.snare, t, 0.2); wet.add(kit.clap, t, 0.25)
        drums.add(kit.hat, t, 0.2 if s % 2 else 0.11, -0.3)
        if s % 4 == 2:
            drums.add(kit.ohat, t, 0.08, 0.3)

    steps(D + B / 4, R, drop)
    steps(R, C, lambda t, s: (drums.add(kit.kick, t, 0.6) if s % 8 == 0 else None,
                             drums.add(kit.hat, t, 0.1, -0.3) if s % 4 == 2 else None))
    steps(C, END - B, groove_a)
    # an arpeggio over the drop, the real-life photo and the CTA
    t = D
    while t < END - B:
        c = chord(t)
        k = int(round((t - D) / (B / 2)))
        m = c[[0, 1, 2, 3, 2, 1][k % 6]] + 24
        music.add(tone(m, B / 2, "pluck"), t, 0.22 if t < R else 0.16, pan=0.25 * math.sin(k))
        wet.add(tone(m, B / 2, "pluck"), t, 0.08)
        t += B / 2
    # the button
    for k, m in enumerate((0, 7, 12)):
        music.add(tone(root + 24 + m, 0.8, "bell"), E.get("button", C + 1) + k * 0.06, 0.3)
        wet.add(tone(root + 24 + m, 0.8, "bell"), E.get("button", C + 1) + k * 0.06, 0.25)
    # stitch ticks and caption whooshes
    for tt, s, fast in E.get("ticks", []):
        fx.add(kit.tick(s), tt, 0.12 if fast else 0.22, pan=0.4 * math.sin(tt * 7))
    for tt, _ in E.get("caps", []):
        fx.add(kit.whoosh, max(0, tt - 0.25), 0.35)
    mix = drums.x * 0.9 + music.x + fx.x + reverb(wet.x + 0.25 * music.x) * 0.9
    # soft clip, fade out
    t = np.arange(N) / SR
    fade = np.clip((END + 0.6 - t) / 1.2, 0, 1)[:, None]
    fade_in = np.clip(t / 0.02, 0, 1)[:, None]
    mix = np.tanh(mix * 1.1) * fade * fade_in
    peak = np.abs(mix).max() + 1e-9
    return (mix / peak * 0.89).astype(np.float32)


def write_wav(path: Path, x: np.ndarray) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return path
