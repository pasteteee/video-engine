import json, os, sys, base64, urllib.request
prompt, out = open(sys.argv[1]).read(), sys.argv[2]
model = sys.argv[3] if len(sys.argv) > 3 else 'gemini-3-pro-image'
body = {"contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "9:16", "imageSize": "4K"}}}
req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={os.environ['GEMINI_API_KEY']}",
    data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
r = json.load(urllib.request.urlopen(req, timeout=600))
for c in r.get('candidates', []):
    for p in c.get('content', {}).get('parts', []):
        if 'inlineData' in p:
            open(out, 'wb').write(base64.b64decode(p['inlineData']['data'])); print('wrote', out, p['inlineData']['mimeType']); sys.exit()
print(json.dumps(r)[:1500])
