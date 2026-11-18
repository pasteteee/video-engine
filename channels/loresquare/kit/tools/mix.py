"""Mix voice, bgm and per-shot sfx under a silent Remotion render.
python3 mix.py <episode_dir> <silent.mp4>  -> 06_render/main.mp4"""
import json, os, subprocess, sys
from pathlib import Path
A = os.environ.get("VENGINE_AUDIO", "assets/audio/")  # bgm/ and sfx/<kind>/ folders
RM = Path(os.environ.get("VENGINE_RM", "rm"))  # Remotion project with props/


def run(ep, video):
    P = json.loads((RM / "props" / f"{ep.name}.json").read_text())
    T = P["duration"]
    S = [("impact/impact-cine-big.mp3", 0.0, -9)]
    for i, s in enumerate(P["shots"]):
        t0, st = s["from"], s["type"]
        if i: S.append(("transition/whoosh-fast.mp3", max(0, t0 - 0.12), -16))
        p = s["params"]
        if st in ("art_backdrop", "kinetic_type"):
            n = len(p.get("slam") or p.get("words") or [])
            for k in range(n):
                S.append(("impact/hit-fast-exciting.mp3" if k == n - 1 else "impact/hit-weak.mp3", t0 + (3 + 6 * k) / 30, -13 if k < n - 1 else -10))
        elif st in ("chapter_card", "custom", "question_card"):
            S.append(("impact/bass-hit-short.mp3", t0 + 0.07, -9))
        elif st == "claim_card":
            S.append(("paper/paper-slide.mp3", t0, -11)); S.append(("impact/hit-blow.mp3", t0 + 0.4, -11))
        elif st == "argument_duel":
            S.append(("impact/hit-weak.mp3", t0 + 0.35, -11)); S.append(("impact/hit-weak.mp3", t0 + 0.8, -11))
        elif st == "confidence_meter":
            S.append(("counter/clock-knob-spin.mp3", t0 + 0.1, -15))
        elif st.startswith("panel"):
            S.append(("camera/camera-shutter-vintage.mp3", t0, -12))
        elif st == "site_screen":
            S.append(("camera/zoom-swipe-fast.mp3", t0, -14))
    ins = ["-i", str(video), "-i", str(ep / "05_voice/voice.wav"), "-stream_loop", "-1", "-i", A + "bgm/tonight-hiphop.mp3"]
    mix = ["[1:a]aresample=48000,pan=stereo|c0=c0|c1=c0,asplit=2[v][vk]",
           f"[2:a]volume=-19dB,afade=t=in:d=0.4,afade=t=out:st={T-1.5:.2f}:d=1.5[b0]",
           "[b0][vk]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=300[b]"]
    lab = ["[v]", "[b]"]
    for i, (fn, at, g) in enumerate(S):
        ins += ["-i", A + "sfx/" + fn]; ms = int(at * 1000)
        mix.append(f"[{i+3}:a]volume={g}dB,adelay={ms}|{ms}[s{i}]"); lab.append(f"[s{i}]")
    fc = ";".join(mix) + ";" + "".join(lab) + f"amix=inputs={len(lab)}:normalize=0:duration=first,atrim=0:{T},loudnorm=I=-14:TP=-1.5:LRA=11[a]"
    (ep / "06_render").mkdir(parents=True, exist_ok=True)
    out = ep / "06_render/main.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", fc, "-map", "0:v", "-map", "[a]", "-t", f"{T:.2f}",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(out)], check=True)
    print(ep.name, f"{T:.1f}s ->", out)


if __name__ == "__main__":
    run(Path(sys.argv[1]), Path(sys.argv[2]))
