import json,sys,wave,array,subprocess
EP=sys.argv[1]; s=json.load(open(f"{EP}/03_script/script.json")); SR=24000
def load(p):
    w=wave.open(p); a=array.array('h',w.readframes(w.getnframes())); return a
def trim(a,th=500):
    i=0
    while i<len(a) and abs(a[i])<th: i+=1
    j=len(a)-1
    while j>i and abs(a[j])<th: j-=1
    return a[max(0,i-int(.04*SR)):j+int(.08*SR)]
out=array.array('h'); words=[]; lines=[]; t=0.6; out.extend([0]*int(t*SR)); prev=None
for l in s['lines']:
    d=l.get('delivery',{})
    gap=0.25+(0.45 if prev and prev!=l['chapter'] else 0)+d.get('pause_before_ms',0)/1000
    if prev is not None: out.extend([0]*int(gap*SR)); t+=gap
    a=trim(load(f"{EP}/05_voice/lines/{l['id']}.wav")); dur=len(a)/SR
    out.extend(a)
    ws=l['text'].split(); tot=sum(len(w)+1 for w in ws); c=0
    for w in ws:
        st=t+dur*c/tot; c+=len(w)+1; words.append({"w":w,"start":round(st,3),"end":round(t+dur*c/tot,3),"line_id":l['id']})
    lines.append({"id":l['id'],"start":round(t,3),"end":round(t+dur,3)})
    t+=dur; pa=d.get('pause_after_ms',0)/1000
    if pa: out.extend([0]*int(pa*SR)); t+=pa
    prev=l['chapter']
out.extend([0]*int(1.5*SR)); t+=1.5
w=wave.open(f"{EP}/05_voice/voice_raw.wav","wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(out.tobytes()); w.close()
subprocess.run(["ffmpeg","-v","error","-y","-i",f"{EP}/05_voice/voice_raw.wav","-af","highpass=f=70,acompressor=threshold=-20dB:ratio=2.5:attack=5:release=80,loudnorm=I=-16:TP=-1.5:LRA=7","-ar","48000",f"{EP}/05_voice/voice.wav"],check=True)
json.dump({"audio":"05_voice/voice.wav","duration_s":round(t,3),"timing":"line timing exact (per-line TTS); word timing proportional to characters inside a line (no aligner model in the cloud)","lines":lines,"words":words},open(f"{EP}/05_voice/words.json","w"),indent=1)
print('total',round(t,2),'s',len(words),'words')
