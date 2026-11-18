# Voice assembly with archival listening slots (sound_after on a line): narration + records -> voice.wav, words.json, cues.json
import json, sys, wave, subprocess, numpy as np, soundfile as sf
EP = sys.argv[1]; s = json.load(open(f"{EP}/03_script/script.json")); SR = 48000
media = {m["id"]: m for m in json.load(open(f"{EP}/02_research/media.json"))["items"]}
def load(p):
    x, sr = sf.read(p); x = x if x.ndim == 1 else x.mean(1)
    if sr != SR: x = np.interp(np.arange(int(len(x) * SR / sr)) * sr / SR, np.arange(len(x)), x)
    return x
def trim(a, th=0.015):
    i = np.argmax(np.abs(a) > th); j = len(a) - np.argmax(np.abs(a[::-1]) > th)
    return a[max(0, i - int(.04 * SR)): j + int(.08 * SR)]
vo = [np.zeros(int(0.6 * SR))]; rec = [np.zeros(int(0.6 * SR))]; t = 0.6
words, lines, sounds = [], [], []; prev = None
def push(v, r):
    global t; vo.append(v); rec.append(r); t += len(v) / SR
for l in s["lines"]:
    d = l.get("delivery") or {}
    if prev is not None:
        gap = 0.25 + (0.45 if prev != l["chapter"] else 0) + d.get("pause_before_ms", 0) / 1000
        push(np.zeros(int(gap * SR)), np.zeros(int(gap * SR)))
    a = trim(load(f"{EP}/05_voice/lines/{l['id']}.wav")); dur = len(a) / SR
    ws = l["text"].split(); tot = sum(len(w) + 1 for w in ws); c = 0
    for w in ws:
        st = t + dur * c / tot; c += len(w) + 1
        words.append({"w": w, "start": round(st, 3), "end": round(t + dur * c / tot, 3), "line_id": l["id"]})
    lines.append({"id": l["id"], "start": round(t, 3), "end": round(t + dur, 3)})
    push(a, np.zeros(len(a)))
    sa = l.get("sound_after")
    if sa and sa.get("media_id") in media:
        clip = load(f"{EP}/02_research/{media[sa['media_id']]['path']}")
        clip = clip[int(sa.get('from_s', 0) * SR): int((sa.get('from_s', 0) + sa['seconds']) * SR)]
        if np.abs(clip).max() < 0.01:
            print("EMPTY record", sa); prev = l["chapter"]; continue
        n = len(clip); fade = np.minimum(1, np.minimum(np.arange(n), n - np.arange(n)) / (0.25 * SR))
        rms = np.sqrt(np.mean((clip * fade) ** 2)) + 1e-9; gain = round(float(min(1.0, 0.11 / rms)), 3)
        clip = clip * fade * gain
        lead = int(0.35 * SR); tail = int(0.35 * SR)
        sounds.append({"line_id": l["id"], "media_id": sa["media_id"], "start": round(t + 0.35, 3), "seconds": round(n / SR, 3), "from_s": sa.get("from_s", 0), "gain": gain})
        push(np.zeros(lead + n + tail), np.concatenate([np.zeros(lead), clip, np.zeros(tail)]))
    pa = d.get("pause_after_ms", 0) / 1000
    if pa: push(np.zeros(int(pa * SR)), np.zeros(int(pa * SR)))
    prev = l["chapter"]
push(np.zeros(int(1.5 * SR)), np.zeros(int(1.5 * SR)))
V = np.concatenate(vo); R = np.concatenate(rec)
sf.write(f"{EP}/05_voice/voice_raw.wav", V, SR); sf.write(f"{EP}/05_voice/records.wav", np.clip(R, -1, 1), SR)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{EP}/05_voice/voice_raw.wav", "-af", "highpass=f=70,acompressor=threshold=-20dB:ratio=2.5:attack=5:release=80,loudnorm=I=-16:TP=-1.5:LRA=7", "-ar", "48000", f"{EP}/05_voice/voice_only.wav"], check=True)
vn, _ = sf.read(f"{EP}/05_voice/voice_only.wav"); m = min(len(vn), len(R))
sf.write(f"{EP}/05_voice/voice.wav", vn, SR)                      # narration stem; the kit plays the records from 'sounds'
sf.write(f"{EP}/05_voice/voice_with_records.wav", np.clip(vn[:m] + R[:m], -1, 1), SR)   # for listening and the music ducking
json.dump({"audio": "05_voice/voice.wav", "duration_s": round(t, 3), "timing": "line timing exact (per-line Kokoro TTS); word timing proportional to characters inside a line (no aligner in the cloud); archival records in 'sounds' play from their own files (voice.wav is narration only)",
           "lines": lines, "words": words, "sounds": sounds}, open(f"{EP}/05_voice/words.json", "w"), indent=1)
json.dump({"duration": round(t, 3), "archive": [[x["start"], round(x["start"] + x["seconds"], 3)] for x in sounds], "tense": [], "hits": []}, open(f"{EP}/05_voice/cues.json", "w"))
print("total", round(t, 2), "s", len(words), "words", len(sounds), "records")
