import json,sys,re
W='/home/user/work/03_godwit'
words=json.load(open(W+'/godwit/05_voice/words.json'))
def ts(t):
    t=max(0,t); h=int(t//3600); m=int(t%3600//60); s=t%60; return f"{h:02d}:{m:02d}:{int(s):02d},{int(round((s-int(s))*1000)):03d}".replace(',1000',',999')
def cues(line_ids=None, off=0.0, maxc=84):
    out=[]
    for l in words['lines']:
        if line_ids and l['id'] not in line_ids: continue
        ws=[w for w in words['words'] if w['line_id']==l['id']]
        cur=[]
        for i,w in enumerate(ws):
            cur.append(w)
            txt=' '.join(x['w'] for x in cur)
            nxt=ws[i+1]['w'] if i+1<len(ws) else None
            if nxt is None or len(txt)+len(nxt)+1>maxc or (re.search(r'[.?!]$',w['w']) and len(txt)>30):
                out.append((cur[0]['start']-off, cur[-1]['end']-off, txt)); cur=[]
    return out
def write(path,cs):
    with open(path,'w') as f:
        for i,(a,b,t) in enumerate(cs,1):
            if len(t)>42:
                ws=t.split(); best=min(range(1,len(ws)),key=lambda k:abs(len(' '.join(ws[:k]))-len(t)/2)); t=' '.join(ws[:best])+'\n'+' '.join(ws[best:])
            f.write(f"{i}\n{ts(a)} --> {ts(b)}\n{t}\n\n")
if __name__=='__main__':
    write('/home/user/work/out/03_godwit/subtitles_en.srt',cues())
    sh=json.load(open(W+'/render/src/ep/shorts.json'))['shorts']
    names={'short1':'short1_never_landed','short2':'short2_cant_stop','short3':'short3_wrong_turn'}
    import os
    for s in sh:
        d=f"/home/user/work/out/03_godwit/{names[s['id']]}"; os.makedirs(d,exist_ok=True)
        write(d+'/subtitles_en.srt',cues(s['line_ids'],s['start_s'],42))
