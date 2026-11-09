"""Render the same intro with several ElevenLabs voices so they can be compared.
Reads samples.json: {"text": ..., "voices": [names], "model": ...}. Writes samples/<name>.mp3 and samples/voices.txt."""
import json, os, re, sys, requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = json.load(open(f"{ROOT}/samples.json"))
KEY = os.environ["ELEVENLABS_API_KEY"]
API = "https://api.elevenlabs.io/v1"
H = {"xi-api-key": KEY}
out = f"{ROOT}/samples"
os.makedirs(out, exist_ok=True)

r = requests.get(f"{API}/voices", headers=H, timeout=30)
if r.status_code != 200:
    print("cannot list voices:", r.status_code, r.text[:300])
    sys.exit(1)
voices = r.json()["voices"]
with open(f"{out}/voices.txt", "w") as f:
    for v in voices:
        lab = v.get("labels") or {}
        f.write(f"{v['name']} | {v['voice_id']} | {v.get('category')} | {lab.get('gender','')} {lab.get('age','')} {lab.get('accent','')} {lab.get('use_case','') or lab.get('use case','')} | {(v.get('description') or '')[:80]}\n")
by = {v["name"].split(" ")[0].lower(): v for v in voices}
for name in cfg["voices"]:
    v = by.get(name.lower())
    if not v:
        print("not in account:", name)
        continue
    body = {"text": cfg["text"], "model_id": cfg.get("model", "eleven_multilingual_v2"),
            "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.15}}
    r = requests.post(f"{API}/text-to-speech/{v['voice_id']}?output_format=mp3_44100_128", headers=H, json=body, timeout=120)
    if r.status_code != 200:
        print(name, r.status_code, r.text[:200])
        continue
    open(f"{out}/{re.sub(r'[^a-z0-9]+', '-', name.lower())}.mp3", "wb").write(r.content)
    print("ok", name, v["voice_id"])
