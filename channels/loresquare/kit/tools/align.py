"""Replace estimated word timings in 05_voice/words.json with faster-whisper word timestamps per line.
python3 align.py <episode_dir>"""
import difflib, json, re, sys
from pathlib import Path
import numpy as np, soundfile as sf, scipy.signal as ss
from faster_whisper import WhisperModel

M = WhisperModel("small", device="cpu", compute_type="int8")
norm = lambda w: re.sub(r"[^a-z0-9]", "", w.lower())


def run(ep):
    W = json.loads((ep / "05_voice/words.json").read_text())
    by = {}
    for x in W["words"]:
        by.setdefault(x["line_id"], []).append(x)
    hit = tot = 0
    for l in W["lines"]:
        a, sr = sf.read(ep / f"05_voice/lines/{l['id']}.wav", dtype="float32")
        a = ss.resample_poly(a, 16000, sr).astype(np.float32)
        segs, _ = M.transcribe(a, language="en", word_timestamps=True, beam_size=5)
        hw = [w for s in segs for w in s.words]
        sw = by[l["id"]]
        sm = difflib.SequenceMatcher(a=[norm(x["w"]) for x in sw], b=[norm(w.word) for w in hw], autojunk=False)
        for blk in sm.get_matching_blocks():
            for k in range(blk.size):
                x, w = sw[blk.a + k], hw[blk.b + k]
                x["start"], x["end"], x["_ok"] = round(l["start"] + w.start, 3), round(l["start"] + w.end, 3), 1
        tot += len(sw); hit += sum(1 for x in sw if x.get("_ok"))
        # unmatched words: spread between matched neighbours
        i = 0
        while i < len(sw):
            if sw[i].get("_ok"): i += 1; continue
            j = i
            while j < len(sw) and not sw[j].get("_ok"): j += 1
            s0 = sw[i - 1]["end"] if i else l["start"]
            e0 = sw[j]["start"] if j < len(sw) else l["end"]
            n = j - i
            for k in range(n):
                sw[i + k]["start"] = round(s0 + (e0 - s0) * k / n, 3); sw[i + k]["end"] = round(s0 + (e0 - s0) * (k + 1) / n, 3)
            i = j
        for x in sw: x.pop("_ok", None)
    (ep / "05_voice/words.json").write_text(json.dumps(W, indent=1))
    print(ep.name, f"aligned {hit}/{tot} words")


if __name__ == "__main__":
    run(Path(sys.argv[1]))
