import json,os,sys,time,base64,wave,urllib.request
KEY=os.environ["GEMINI_API_KEY"]; NAME=sys.argv[1]; OUT=sys.argv[2]
def get():
  return json.load(urllib.request.urlopen(urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/{NAME}",headers={"x-goog-api-key":KEY})))
while True:
  try: op=get()
  except Exception as e: print('err',e,flush=True); time.sleep(30); continue
  print(time.strftime('%H:%M'),op.get('metadata',{}).get('state'),flush=True)
  if op.get('done'): break
  time.sleep(45)
os.makedirs(OUT,exist_ok=True)
rs=op["response"]["inlinedResponses"]["inlinedResponses"]
for r in rs:
  k=r.get("metadata",{}).get("key")
  if "error" in r: print(k,"ERROR",r["error"]); continue
  pcm=base64.b64decode(r["response"]["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])
  with wave.open(f"{OUT}/{k}.wav","wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm)
print("DONE",len(rs))
