"""Voice for an episode with Kokoro (am_michael): python3 vo.py <episode_dir>
-> 05_voice/voice.wav, 05_voice/lines/<id>.wav, 05_voice/words.json (line + estimated word timings)."""
import json, os, re, sys
from pathlib import Path
import numpy as np, soundfile as sf, scipy.signal as ss

TTS = Path(os.environ.get("KOKORO_DIR", "tts"))  # kokoro-v1.0.onnx + voices-v1.0.bin
SR = 48000
GAP = {"countdown": 0.55, "hook": 0.35, "question": 0.4}
LEX = {"LoreSquare": "Lore Square", "LoreSquare's": "Lore Square's", "Imu": "Eemoo", "Imu's": "Eemoo's", "Poneglyph": "Pony-glyph",
       "hiraeth": "Heer-eyeth", "skadoosh": "ska-doosh", "marroka": "ma-rocka", "Zaza": "Zah-zah", "Nika": "Nee-kah",
       "Churchward's": "Church-ward's", "Mu": "Moo", "Mu,": "Moo,", "Mu?": "Moo?", "Mu.": "Moo.", "Oda": "Oh-da", "Haki": "Hah-kee",
       "Zoan": "Zo-an", "Davy": "Davy", "1933": "nineteen thirty-three"}


def prep(t):
    out = []
    for w in t.split(" "):
        core = w.strip(".,?:!")
        out.append(w.replace(core, LEX[core]) if core in LEX else (LEX.get(w, w)))
    return " ".join(out)


_k = None


def say(text):
    global _k
    if _k is None:
        from kokoro_onnx import Kokoro
        _k = Kokoro(str(TTS / "kokoro-v1.0.onnx"), str(TTS / "voices-v1.0.bin"))
    a, sr = _k.create(text, voice="am_michael", speed=1.05, lang="en-us")
    a = ss.resample_poly(a, SR, sr).astype(np.float32)
    nz = np.where(np.abs(a) > 0.01)[0]
    return a[max(0, nz[0] - 480):nz[-1] + 960]


def words(text, s, e, lid):
    ws = text.split(); w8 = [len(re.sub(r"\W", "", w)) + 2 for w in ws]; tot = sum(w8); t = s; r = []
    for w, k in zip(ws, w8):
        d = (e - s) * k / tot; r.append({"w": w, "start": round(t, 3), "end": round(t + d, 3), "line_id": lid}); t += d
    return r


def run(ep):
    script = json.loads((ep / "03_script/script.json").read_text())
    (ep / "05_voice/lines").mkdir(parents=True, exist_ok=True)
    t = 0.25; chunks = [np.zeros(int(SR * t), np.float32)]; W = []; lines = []
    for l in script["lines"]:
        a = say(prep(l["text"]))
        sf.write(ep / f"05_voice/lines/{l['id']}.wav", a, SR)
        d = len(a) / SR
        lines.append({"id": l["id"], "start": round(t, 3), "end": round(t + d, 3)})
        W += words(l["text"], t, t + d, l["id"])
        g = GAP.get(l.get("beat"), 0.22)
        chunks += [a, np.zeros(int(SR * g), np.float32)]; t += d + g
    chunks.append(np.zeros(int(SR * 1.2), np.float32))
    audio = np.concatenate(chunks)
    sf.write(ep / "05_voice/voice.wav", audio, SR)
    (ep / "05_voice/words.json").write_text(json.dumps({"audio": "05_voice/voice.wav", "duration_s": round(len(audio) / SR, 3),
                                                        "words": W, "lines": lines}, indent=1))
    print(ep.name, round(len(audio) / SR, 1), "s")


if __name__ == "__main__":
    run(Path(sys.argv[1]))
