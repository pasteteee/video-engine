# Re-voice an episode that has real archive audio inserts (Kokoro or any per-line TTS).
# python assemble_inserts.py EPISODE OLD_WORDS.json MEDIA_DIR  (old words.json lists the inserts; gaps of the old cut are kept)
"""Assemble Kokoro lines + real NASA audio inserts, keeping the old cut's gap pattern.
Writes 05_voice/voice.wav (48k mono, voice -16 LUFS, inserts mixed in), words.json, timemap.json (old->new anchors)."""
import json, wave, array, subprocess, sys, os
EP=sys.argv[1]; OLD=json.load(open(sys.argv[2])); PUB=sys.argv[3]
SR=24000
s=json.load(open(f"{EP}/03_script/script.json")); text={l['id']:l['text'] for l in s['lines']}
def load(p):
    w=wave.open(p); return array.array('h',w.readframes(w.getnframes()))
def trim(a,th=500):
    i=0
    while i<len(a) and abs(a[i])<th: i+=1
    j=len(a)-1
    while j>i and abs(a[j])<th: j-=1
    return a[max(0,i-int(.04*SR)):j+int(.08*SR)]
items=[dict(kind='line',id=l['id'],os=l['start'],oe=l['end']) for l in OLD['lines']]
items+=[dict(kind='ins',id=x['id'],os=x['start'],oe=x['end'],src=x['src'],fr=x['from'],to=x['to'],note=x.get('note','')) for x in OLD['inserts']]
items.sort(key=lambda x:x['os'])
t=items[0]['os']; prev_oe=None; anchors=[(0.0,0.0)]
out=array.array('h',[0]*int(t*SR)); words=[]; lines=[]; inserts=[]
for it in items:
    if prev_oe is not None:
        gap=max(0.25,it['os']-prev_oe); out.extend([0]*int(gap*SR)); t+=gap
    if it['kind']=='line':
        a=trim(load(f"{EP}/05_voice/lines/{it['id']}.wav")); d=len(a)/SR; out.extend(a)
        ws=text[it['id']].split(); tot=sum(len(w)+1 for w in ws); c=0
        for w in ws:
            st=t+d*c/tot; c+=len(w)+1; words.append({"w":w,"start":round(st,3),"end":round(t+d*c/tot,3),"line_id":it['id']})
        lines.append({"id":it['id'],"start":round(t,3),"end":round(t+d,3)})
    else:
        d=it['oe']-it['os']; out.extend([0]*int(round(d*SR)))
        inserts.append({"id":it['id'],"src":it['src'],"from":it['fr'],"to":it['to'],"note":it['note'],"start":round(t,3),"end":round(t+d,3)})
    anchors.append((it['os'],round(t,3))); anchors.append((it['oe'],round(t+d,3)))
    t+=d; prev_oe=it['oe']
tail=OLD['duration_s']-prev_oe; out.extend([0]*int(tail*SR)); t+=tail; anchors.append((OLD['duration_s'],round(t,3)))
w=wave.open(f"{EP}/05_voice/voice_raw.wav","wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(out.tobytes()); w.close()
subprocess.run(["ffmpeg","-v","error","-y","-i",f"{EP}/05_voice/voice_raw.wav","-af","highpass=f=70,acompressor=threshold=-20dB:ratio=2.5:attack=5:release=80,loudnorm=I=-16:TP=-1.5:LRA=7","-ar","48000","-ac","1",f"{EP}/05_voice/voice_only.wav"],check=True)
# inserts: cut, normalise, place
srcmap={'descent_audio':f'{PUB}/descent_audio.wav','wind':f'{PUB}/wind_audio.wav'}
inputs=["-i",f"{EP}/05_voice/voice_only.wav"]; fl=[]
for k,x in enumerate(inserts):
    lv=-20 if x['src']=='wind' else -17
    d=x['to']-x['from']
    p=f"{EP}/05_voice/ins_{x['id']}.wav"
    subprocess.run(["ffmpeg","-v","error","-y","-ss",str(x['from']),"-to",str(x['to']),"-i",srcmap[x['src']],"-af",f"loudnorm=I={lv}:TP=-2:LRA=11,afade=t=in:d=0.12,afade=t=out:st={d-0.25}:d=0.25","-ar","48000","-ac","1",p],check=True)
    inputs+=["-i",p]; ms=int(x['start']*1000); fl.append(f"[{k+1}]adelay={ms}|{ms}[i{k}]")
mix="".join(f"[i{k}]" for k in range(len(inserts)))
fc=";".join(fl)+f";[0]{mix}amix=inputs={len(inserts)+1}:normalize=0:duration=first[o]"
subprocess.run(["ffmpeg","-v","error","-y",*inputs,"-filter_complex",fc,"-map","[o]","-ar","48000",f"{EP}/05_voice/voice.wav"],check=True)
json.dump({"audio":"05_voice/voice.wav","duration_s":round(t,3),"timing":"line timing exact (per-line Kokoro TTS); word timing proportional to characters inside a line; real NASA audio inserts listed separately and mixed into voice.wav","lines":lines,"inserts":inserts,"words":words},open(f"{EP}/05_voice/words.json","w"),indent=1)
json.dump(anchors,open(f"{EP}/05_voice/timemap.json","w"))
print('total',round(t,2))
