import json, os, sys, base64, urllib.request
model, prompt_file, out = sys.argv[1], sys.argv[2], sys.argv[3]
prompt = open(prompt_file).read()
body = {"contents": [{"parts": [{"text": prompt}]}]}
req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={os.environ['GEMINI_API_KEY']}",
    data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
r = json.load(urllib.request.urlopen(req, timeout=600))
n = 0
for c in r.get('candidates', []):
    for p in c.get('content', {}).get('parts', []):
        if 'inlineData' in p:
            mt = p['inlineData']['mimeType']; ext = mt.split('/')[-1].replace('mpeg', 'mp3')
            fn = f"{out}.{ext}" if n == 0 else f"{out}-{n}.{ext}"
            open(fn, 'wb').write(base64.b64decode(p['inlineData']['data'])); print('wrote', fn, mt); n += 1
        elif 'text' in p:
            print('TEXT:', p['text'][:1500])
if not n: print(json.dumps(r)[:2000])
