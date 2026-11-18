"""Free local narration with Kokoro-82M (kokoro-onnx), one wav per script line.

    python tts_kokoro.py EPISODE [--voice am_michael] [--speed 0.95] [--only l3,l7]

Writes 05_voice/lines/<line>.wav (24 kHz mono) and 05_voice/voice_qa.json, then run
assemble_voice.py EPISODE for voice.wav + words.json. Model files come from the kokoro-onnx
GitHub release (HuggingFace is blocked in the cloud) and are cached in $KOKORO_DIR.
No API key, no quota, runs on CPU at about 4x real time.
"""
import argparse, json, os, re, subprocess, sys, wave, array

REL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
DIR = os.environ.get("KOKORO_DIR", os.path.expanduser("~/kokoro"))
FILES = ["kokoro-v1.0.onnx", "voices-v1.0.bin"]

# Words the phonemizer gets wrong in this channel's topics. Spelling, not IPA: keeps it readable.
SAY = {
    r"\bNASA\b": "Nasa", r"\bNOAA\b": "Noah", r"\bUSGS\b": "U S G S", r"\bNTSB\b": "N T S B",
    r"\bEECOM\b": "ee-com", r"\bSCE\b": "S C E", r"\bLVS\b": "L V S", r"\bGOES\b": "goes",
    r"\bMPH\b": "miles per hour", r"\bmph\b": "miles per hour", r"\bkm/h\b": "kilometers per hour",
    r"\bhPa\b": "hectopascals", r"\bEF(\d)\b": r"E F \1", r"\bF(\d)\b": r"F \1",
    r"\bCAPCOM\b": "cap-com", r"\bSOFAR\b": "so-far", r"\bAgena\b": "uh-jee-nuh",
    r"\bJezero\b": "jez-er-oh", r"\bHunga Tonga\b": "Hoonga Tonga", r"\bHa'apai\b": "Ha-ah-pie",
    r"\bOkeanos\b": "Oh-kee-uh-nos", r"\bVecchione\b": "Veh-kee-oh-nee", r"\bocto?pods\b": "octo-pods", r"\boctopod\b": "octo-pod",
}

def say(text: str) -> str:
    t = text.replace("—", ", ").replace("–", " to ").replace("…", "...")
    t = re.sub(r"[\"“”]", "", t)
    for k, v in SAY.items():
        t = re.sub(k, v, t)
    t = re.sub(r"(\d),(\d{3})", r"\1\2", t)  # 13,560 -> 13560 (read as a number, not a list)
    return t

def ensure_model():
    os.makedirs(DIR, exist_ok=True)
    for f in FILES:
        p = os.path.join(DIR, f)
        if not os.path.exists(p) or os.path.getsize(p) < 1_000_000:
            subprocess.run(["curl", "-sSL", "-o", p, REL + f], check=True)
    return [os.path.join(DIR, f) for f in FILES]

def voiced_s(samples, sr, th=0.018):
    i = 0
    while i < len(samples) and abs(samples[i]) < th: i += 1
    j = len(samples) - 1
    while j > i and abs(samples[j]) < th: j -= 1
    return max(0, j - i) / sr

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode"); ap.add_argument("--voice"); ap.add_argument("--speed", type=float)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    import numpy as np
    from kokoro_onnx import Kokoro
    prof = {}
    for c in ("channel.json", "../channel.json"):
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), c)
        if os.path.exists(p): prof = json.load(open(p)).get("voice", {}); break
    voice = a.voice or prof.get("kokoro_voice", "am_michael")
    speed = a.speed or prof.get("kokoro_speed", 0.95)
    model, voices = ensure_model()
    k = Kokoro(model, voices)
    ep = a.episode; s = json.load(open(f"{ep}/03_script/script.json"))
    os.makedirs(f"{ep}/05_voice/lines", exist_ok=True)
    only = set(x for x in a.only.split(",") if x)
    log = []
    for l in s["lines"]:
        if only and l["id"] not in only: continue
        text = say(l["text"])
        sp = speed
        for take in range(3):
            smp, sr = k.create(text, voice=voice, speed=sp, lang="en-us")
            d = voiced_s(smp, sr); n = len(l["text"].split()); wpm = n / max(d, .1) * 60
            if 125 <= wpm <= 175 or n <= 5: break
            sp = sp * (150 / wpm) ** 0.8  # nudge the pace toward 150 wpm, max 3 takes
            sp = min(1.15, max(0.8, sp))
        pcm = (np.clip(smp, -1, 1) * 32767).astype("<i2")
        w = wave.open(f"{ep}/05_voice/lines/{l['id']}.wav", "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(pcm.tobytes()); w.close()
        log.append({"line": l["id"], "words": n, "voiced_s": round(d, 2), "wpm": round(wpm), "speed": round(sp, 3), "takes": take + 1,
                    "spoken_as": text if text != l["text"] else None})
        print(l["id"], n, "w", round(d, 1), "s", round(wpm), "wpm", flush=True)
    qa = f"{ep}/05_voice/voice_qa.json"
    old = json.load(open(qa)) if only and os.path.exists(qa) else {"lines": []}
    keep = [x for x in old.get("lines", []) if x.get("line") not in only]
    json.dump({"method": f"Kokoro-82M (kokoro-onnx, free, local), voice {voice}, base speed {speed}; pace nudged to ~150 wpm, max 3 takes",
               "provider": "kokoro", "voice": voice, "lines": keep + log}, open(qa, "w"), indent=1)

if __name__ == "__main__":
    main()
