import json
W='/home/user/work/03_godwit'
L={l['id']:l for l in json.load(open(W+'/godwit/05_voice/words.json'))['lines']}
def short(id_, a, b, hook, title, plan):
    st=L[a]['start']-0.15; end=L[b]['end']+0.6; shots=[]; n=0
    for lid, specs in plan:
        la=0 if lid==a else L[lid]['start']-0.15-st
        nxt=[k for k,_ in plan]; i=nxt.index(lid)
        lb=(L[nxt[i+1]]['start']-0.15-st) if i+1<len(nxt) else end-st
        dd=(lb-la)/len(specs)
        for k,(lay,mids,params) in enumerate(specs):
            n+=1; shots.append({'id':f'{id_}_{n:02d}','layout':lay,'start_s':round(la+k*dd,3),'duration_s':round(dd,3),'media_ids':mids,'params':params})
    return {'id':id_,'line_ids':[k for k,_ in plan],'start_s':round(st,3),'end_s':round(end,3),'hook_text':hook,'title':title,'shots':shots}
S=[
short('short1','l01','l05','11 DAYS. NO LANDING.','A 4-month-old bird flew 11 days without landing once',[
 ('l01',[('v_film_crop',['m_ocean2'],{'trim':3,'x':0.5,'label':'PACIFIC · FROM THE ISS'}),('v_photo_pan',['m_b6'],{'from':[0.55,0.5,1.0],'to':[0.6,0.6,1.2],'label':'B6 · USGS PHOTO'})]),
 ('l02',[('v_number',[],{'label':'DAYS IN THE AIR','value':11,'unit':'DAYS','note':'NOT ONE LANDING'})]),
 ('l03',[('v_photo_pan',['m_aleut'],{'from':[0.3,0.5,1.0],'to':[0.6,0.6,1.2],'label':'OPEN PACIFIC'}),('v_number',[],{'label':'AT LEAST','value':13560,'unit':'KM','note':'NONSTOP · GUINNESS / USGS'})]),
 ('l04',[('v_photo_pan',['m_flight'],{'from':[0.4,0.5,1.0],'to':[0.5,0.45,1.25],'label':'BAR-TAILED GODWIT · NOT B6'}),('v_photo_pan',['m_b6_band'],{'from':[0.5,0.3,1.0],'to':[0.5,0.5,1.2],'label':'A SATELLITE TAG'})]),
 ('l05',[('v_custom',[],{'component':'VTurn','mode':'turn'}),('v_type',[],{'lines':['NEVER','SUPPOSED','TO GO','THERE'],'accent':3})]),
]),
short('short2','l17','l22','HALF ITS BODY IS FUEL','Why this bird can\'t stop flying for days',[
 ('l17',[('v_photo_pan',['m_flock'],{'from':[0.3,0.5,1.0],'to':[0.7,0.5,1.1],'label':'GODWITS · ALASKA · NOT B6'}),('v_number',[],{'label':'FAT, SHARE OF BODY WEIGHT','value':55,'unit':'%','note':'ADULTS · GILL ET AL. 2009'})]),
 ('l18',[('v_photo_pan',['m_flight'],{'from':[0.45,0.5,1.0],'to':[0.45,0.5,1.3],'label':'GUT SHRINKS · HEART GROWS'})]),
 ('l19',[('v_number',[],{'label':'E7 · 2007 · ADULT FEMALE','value':11700,'unit':'KM','note':'ALASKA → NEW ZEALAND · ~8 DAYS'}),('v_photo_pan',['m_flock'],{'from':[0.6,0.4,1.1],'to':[0.4,0.6,1.3],'label':'FIRST NONSTOP CROSSING TRACKED'}),('v_film_crop',['m_ocean3'],{'trim':4,'x':0.5,'label':'ALASKA → NEW ZEALAND'})]),
 ('l20',[('v_type',[],{'lines':['THE PART','THAT','MATTERS'],'accent':2})]),
 ('l21',[('v_photo_pan',['m_b6_band'],{'from':[0.5,0.5,1.0],'to':[0.47,0.75,1.4],'label':'NO WEBBED FEET'}),('v_film_crop',['m_ocean1'],{'trim':6,'x':0.4,'label':'NOWHERE TO LAND'})]),
 ('l22',[('v_film_crop',['m_ocean4'],{'trim':8,'x':0.6,'label':'DAY AND NIGHT'}),('v_type',[],{'lines':['IT DOES','NOT STOP'],'accent':1})]),
]),
short('short3','l40','l48','IT TURNED THE WRONG WAY','It flew past Australia, then turned. Lost, or on purpose?',[
 ('l40',[('v_photo_pan',['m_flock'],{'from':[0.4,0.5,1.0],'to':[0.6,0.5,1.15],'label':'ALASKA GODWITS · NOT B6'})]),
 ('l41',[('v_number',[],{'label':'OFF SYDNEY','value':600,'unit':'KM','note':'STILL HEADING SOUTH'}),('v_photo_pan',['m_tasmania'],{'from':[0.5,0.4,1.0],'to':[0.5,0.55,1.2],'label':'TASMAN SEA · NASA'})]),
 ('l42',[('v_photo_pan',['m_tasmania'],{'from':[0.3,0.5,1.2],'to':[0.6,0.5,1.4],'label':'LATITUDE OF NEW ZEALAND'})]),
 ('l43',[('v_custom',[],{'component':'VTurn','mode':'turn'})]),
 ('l44',[('v_type',[],{'lines':['BLOWN OFF','COURSE?'],'accent':1}),('v_type',[],{'lines':['OR ON','PURPOSE?'],'accent':1,'variant':'unredact'})]),
 ('l45',[('v_photo_pan',['m_tracking'],{'from':[0.4,0.5,1.0],'to':[0.6,0.4,1.2],'label':'USGS RESEARCHERS'})]),
 ('l46',[('v_photo_pan',['m_tasmania'],{'from':[0.6,0.5,1.1],'to':[0.4,0.5,1.3],'label':'WEATHER MODEL · OCT 23'}),('v_custom',[],{'component':'VTurn','mode':'north'})]),
 ('l47',[('v_custom',[],{'component':'VTurn','mode':'ne'})]),
 ('l48',[('v_type',[],{'lines':['OVERSHOOT:','THE WIND'],'accent':1}),('v_type',[],{'lines':['THE TURN:','NOT CLEARLY'],'accent':1})]),
]),
]
plan={'music':'ep/bed.wav','shorts':S}
json.dump(plan,open(W+'/render/src/ep/shorts.json','w'),indent=1)
import os; os.makedirs(W+'/godwit/06_render/shorts',exist_ok=True)
json.dump(plan,open(W+'/godwit/06_render/shorts/shorts.json','w'),indent=1)
for s in S: print(s['id'], round(s['end_s']-s['start_s'],1), len(s['shots']))
