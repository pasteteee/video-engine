import json, wave, array, shutil, sys
EP, T = sys.argv[1], sys.argv[2]
s = json.load(open(f"{EP}/03_script/script.json")); log = []
def voiced(p):
    w = wave.open(p); a = array.array('h', w.readframes(w.getnframes())); sr = w.getframerate(); th = 600; i = 0
    while i < len(a) and abs(a[i]) < th: i += 1
    j = len(a) - 1
    while j > i and abs(a[j]) < th: j -= 1
    return max(0, j - i) / sr
for l in s['lines']:
    n = len(l['text'].split()); c = []
    for k in 'ab':
        d = voiced(f"{T}/{l['id']}_{k}.wav"); wpm = n / max(d, .1) * 60
        ok = 120 <= wpm <= 185 or (n <= 6 and d < 4.5)
        c.append((0 if ok else 1, abs(wpm - 150), k, d, wpm))
    c.sort(); b = c[0]
    shutil.copy(f"{T}/{l['id']}_{b[2]}.wav", f"{EP}/05_voice/lines/{l['id']}.wav")
    log.append({"line": l['id'], "words": n, "take": b[2], "voiced_s": round(b[3], 2), "wpm": round(b[4]), "ok": not b[0],
                "other": {"take": c[1][2], "voiced_s": round(c[1][3], 2), "wpm": round(c[1][4])}})
    print(l['id'], n, 'w', b[2], round(b[3], 1), 's', round(b[4]), 'wpm', '' if not b[0] else 'CHECK', '| alt', round(c[1][3], 1), round(c[1][4]))
json.dump({"method": "Gemini batch TTS, 2 takes per line, pick by pace (wpm near 150); no transcription QA by rule", "lines": log}, open(f"{EP}/05_voice/voice_qa.json", "w"), indent=1)
