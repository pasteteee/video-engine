import json,os,sys,urllib.request
KEY=os.environ["GEMINI_API_KEY"]; EP=sys.argv[1]; MODEL=sys.argv[2]
ch=json.load(open('/home/user/video-engine/channels/realstory/channel.json'))
s=json.load(open(f"{EP}/03_script/script.json"))
SYS=ch['voice']['base_direction']+" Read only the transcript you are given, word for word; never read these instructions aloud."
reqs=[]
for l in s['lines']:
  for take in 'ab':
    reqs.append({"metadata":{"key":f"{l['id']}_{take}"},"request":{"contents":[{"parts":[{"text":l["text"]}]}],
      "generationConfig":{"responseModalities":["AUDIO"],"speechConfig":{"voiceConfig":{"prebuiltVoiceConfig":{"voiceName":ch['voice']['voice']}}}}}})
req=urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:batchGenerateContent",method="POST",
  data=json.dumps({"batch":{"display_name":"apollo12_vo","input_config":{"requests":{"requests":reqs}}}}).encode(),headers={"x-goog-api-key":KEY,"Content-Type":"application/json"})
try: print(json.load(urllib.request.urlopen(req))["name"])
except urllib.error.HTTPError as e: print(e.code,e.read().decode()[:600])
