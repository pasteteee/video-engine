import json, os, sys, base64, urllib.request
f = sys.argv[1]
b = base64.b64encode(open(f,'rb').read()).decode()
q = ("Listen to this song. Give a precise timeline: for every sung/shouted lyric line, the start time in seconds (to 0.1 s) and the words; "
     "also mark big hits/stabs, silences, the drop start and the end. Then describe in 2 sentences the vibe and how hard it hits. Plain text.")
body = {"contents": [{"parts": [{"inlineData": {"mimeType": "audio/mpeg", "data": b}}, {"text": q}]}]}
req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={os.environ['GEMINI_API_KEY']}", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
r = json.load(urllib.request.urlopen(req, timeout=600))
print(r['candidates'][0]['content']['parts'][0]['text'])
