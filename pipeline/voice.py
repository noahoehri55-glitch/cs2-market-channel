"""Script -> narration wav + timeline.json + captions.srt.
Usage: voice.py <job>   reads jobs/<job>/script.json, writes build/<job>/{voice.wav,timeline.json,captions.srt}
TTS backend: env TTS=elevenlabs (default in CI, needs ELEVENLABS_API_KEY) or TTS=kokoro (local, free).
A beat is a string or {"text": ..., "pause": seconds_of_silence_after}.
ElevenLabs audio is cached per beat in tts_cache/ so re-renders don't spend credits again."""
import hashlib, io, json, os, subprocess, sys, time
import numpy as np, soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
job = sys.argv[1]
J = f"{ROOT}/build/{job}"
os.makedirs(J, exist_ok=True)
s = json.load(open(f"{ROOT}/jobs/{job}/script.json"))
SR = 24000
TTS = os.environ.get("TTS", "elevenlabs")
SPEED = s.get("speed", 1.0)

if TTS == "kokoro":
    from kokoro_onnx import Kokoro
    _k = Kokoro(f"{ROOT}/models/kokoro-v1.0.onnx", f"{ROOT}/models/voices-v1.0.bin")
    _lang = "en-gb" if s["voice"].startswith("b") else "en-us"

    def synth(text, prev, nxt):
        y, sr = _k.create(text, voice=s["voice"], speed=SPEED, lang=_lang)
        assert sr == SR
        return y
else:
    import requests
    KEY = os.environ["ELEVENLABS_API_KEY"]
    MODEL = s.get("el_model", "eleven_multilingual_v2")
    API = "https://api.elevenlabs.io/v1"
    FALLBACK = {"George": "JBFqnCBsd6RMkjVDRZzb"}  # ElevenLabs premade voice

    def voice_id():
        if os.environ.get("ELEVENLABS_VOICE_ID"):
            return os.environ["ELEVENLABS_VOICE_ID"]
        name = s.get("el_voice", "George")
        try:
            r = requests.get(f"{API}/voices", headers={"xi-api-key": KEY}, timeout=30)
            r.raise_for_status()
            for v in r.json()["voices"]:
                if v["name"].split(" ")[0].lower() == name.lower():
                    return v["voice_id"]
        except Exception as e:  # key may lack voices_read permission
            print("voice lookup failed, using fallback:", e)
        return FALLBACK.get(name, FALLBACK["George"])

    VID = voice_id()
    print("ElevenLabs voice", VID, "model", MODEL)
    os.makedirs(f"{ROOT}/tts_cache", exist_ok=True)

    def synth(text, prev, nxt):
        h = hashlib.sha1(json.dumps([VID, MODEL, SPEED, prev, text, nxt]).encode()).hexdigest()[:20]
        path = f"{ROOT}/tts_cache/{h}.mp3"
        if not os.path.exists(path):
            body = {"text": text, "model_id": MODEL, "previous_text": prev, "next_text": nxt,
                    "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.15, "speed": SPEED}}
            for attempt in range(4):
                r = requests.post(f"{API}/text-to-speech/{VID}?output_format=mp3_44100_128",
                                  headers={"xi-api-key": KEY, "Content-Type": "application/json"}, json=body, timeout=120)
                if r.status_code == 200:
                    break
                print("ElevenLabs", r.status_code, r.text[:300])
                if r.status_code in (401, 402, 403):
                    sys.exit(1)
                time.sleep(5 * (attempt + 1))
            r.raise_for_status()
            open(path, "wb").write(r.content)
        pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "wav", "-"],
                             capture_output=True, check=True).stdout
        y, _ = sf.read(io.BytesIO(pcm), dtype="float32")
        # trim leading/trailing near-silence so our own gaps control pacing
        nz = np.where(np.abs(y) > 0.01)[0]
        return y[max(0, nz[0] - 600): nz[-1] + 1200] if len(nz) else y

BEAT_GAP, SCENE_GAP, LEAD = s.get("beat_gap", .28), s.get("scene_gap", .55), s.get("lead", .35)
flat = [b if isinstance(b, dict) else {"text": b} for sc in s["scenes"] for b in sc["beats"]]
audio, t, tl, srt, n = [np.zeros(int(SR * LEAD))], LEAD, [], [], 0
for sc in s["scenes"]:
    start, beats = t, []
    for b in sc["beats"]:
        b = b if isinstance(b, dict) else {"text": b}
        prev = " ".join(x["text"] for x in flat[max(0, n - 2):n])
        nxt = flat[n + 1]["text"] if n + 1 < len(flat) else ""
        y = synth(b["text"], prev, nxt)
        n += 1
        d = len(y) / SR
        beats.append({"text": b["text"], "start": round(t - start, 3), "dur": round(d, 3)})
        srt.append((t, t + d, b["text"]))
        gap = BEAT_GAP + b.get("pause", 0)
        audio += [y, np.zeros(int(SR * gap))]
        t += d + gap
    audio.append(np.zeros(int(SR * SCENE_GAP)))
    t += SCENE_GAP
    tl.append({"type": sc["type"], "start": round(start, 3), "dur": round(t - start, 3), "beats": beats})
audio.append(np.zeros(int(SR * .8)))
t += .8
y = np.concatenate(audio)
y = y / np.abs(y).max() * .89
sf.write(f"{J}/voice.wav", y, SR)
json.dump({"total": round(t, 3), "scenes": tl}, open(f"{J}/timeline.json", "w"), indent=1)


def ts(x):
    ms = int(round(x * 1000))
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


open(f"{J}/captions.srt", "w").write("\n".join(f"{i + 1}\n{ts(a)} --> {ts(b)}\n{x}\n" for i, (a, b, x) in enumerate(srt)))
print(job, "total", round(t, 1), [round(x["dur"], 1) for x in tl])
