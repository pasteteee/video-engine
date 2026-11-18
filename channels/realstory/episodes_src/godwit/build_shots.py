import json, os, shutil, subprocess
W='/home/user/work/03_godwit'; EP=W+'/godwit'; R=W+'/render'
exec(open(W+'/scripts/plan.py').read())
words=json.load(open(EP+'/05_voice/words.json')); lines=words['lines']; T=words['duration_s']
media={m['id']:m for m in json.load(open(EP+'/02_research/media.json'))['items']}
LEAD=0.2
shots=[]; n=0
for i,l in enumerate(lines):
    a=0 if i==0 else l['start']-LEAD
    b=(lines[i+1]['start']-LEAD) if i+1<len(lines) else T+1.8
    spec=P[l['id']]
    durs=[]
    if len(spec)==1: durs=[b-a]
    else:
        first=spec[0][0]
        if first=='chapter_card' and not spec[0][3].get('end'): d0=min(2.4,(b-a)*0.45)
        elif spec[-1][0]=='chapter_card': d0=(b-a)-3.6
        else: d0=(b-a)/2
        durs=[d0,(b-a)-d0]
    t=a
    for (st,var,mids,params,ex),d in zip(spec,durs):
        n+=1; s={'id':f's{n:02d}','line_ids':[l['id']],'scene_type':st,'duration_s':round(d,3),'media_ids':mids,'params':dict(params,start_s=round(t,3))}
        if var: s['variant']=var
        if ex.get('src'): s['source_line']=SRC[ex['src']]
        if ex.get('sfx'): s['sfx']=ex['sfx']
        if ex.get('custom'): s['custom']={'component':ex['custom'][0],'brief':ex['custom'][1],'register':'blueprint'}
        s['transition_in']='cut' if st in('chapter_card','kinetic_type','question_card') else ('dissolve' if st in ('photo_parallax','film_clip','stock_broll') else 'push')
        s['motion']='camera push/drift and animated elements the whole shot'
        shots.append(s); t+=d
ALT={'chapter_card':['hairline_index','big_index'],'photo_parallax':['push_in','lateral_drift','rack_focus'],'photo_detail_zoom':['circle_lands','crop_marks','magnifier'],'film_clip':['full_frame','projector_flicker','split_reel'],'kinetic_type':['rise_narrow','stagger_weight','type_on']}
prev={}
for s_ in shots:
    t_=s_['scene_type']; v_=s_.get('variant')
    if t_ in ALT and v_ and prev.get(t_)==v_ and v_!='unredact':
        al=ALT[t_]; s_['variant']=al[(al.index(v_)+1)%len(al)] if v_ in al else al[0]
        if prev.get(t_)==s_['variant']: s_['variant']=al[(al.index(s_['variant'])+1)%len(al)]
    if v_: prev[t_]=s_.get('variant')
cues=[{'at_shot':shots[0]['id'],'level':1}]
for s in shots:
    if s['scene_type']=='chapter_card': cues.append({'at_shot':s['id'],'level':2})
look={'ground':'#1a130d','ground_2':'#2e2219','accent':'#d98a4a','tint':'#b8a58a','why':'Season direction: mudflat brown ground (dark mud of the staging flats) + rufous-orange accent sampled from the godwit plumage (#9a6939 in m_flight, lifted to #d98a4a for contrast 6.7:1 on ground). vengine look gave an olive ground #171101 and a sky-blue accent; the blue sat on the sky, not on the bird, so the director overrode it with the plumage hue.'}
SL={'fps':30,'width':1920,'height':1080,'look':look,'music_cues':cues,'shots':shots}
json.dump(SL,open(EP+'/04_shots/shotlist.json','w'),indent=1)
os.makedirs(R+'/src/ep',exist_ok=True); os.makedirs(R+'/public/ep',exist_ok=True)
json.dump(SL,open(R+'/src/ep/shotlist.json','w'))
json.dump(words,open(R+'/src/ep/words.json','w'))
sc=json.load(open(EP+'/03_script/script.json'))
json.dump([{'id':l['id'],'chapter':l['chapter'],'text':l['text']} for l in sc['lines']],open(R+'/src/ep/lines.json','w'))
mm={}
for k,m in media.items():
    fn=os.path.basename(m['path']); dst=R+'/public/ep/'+fn
    if not os.path.exists(dst): os.link(EP+'/02_research/'+m['path'],dst)
    mm[k]={'src':fn,'w':m['width'],'h':m['height']}
json.dump(mm,open(R+'/src/ep/media.json','w'))
if not os.path.exists(R+'/public/ep/voice.wav'): os.link(EP+'/05_voice/voice.wav',R+'/public/ep/voice.wav')
print(len(shots),'shots', round(T,1),'s')
