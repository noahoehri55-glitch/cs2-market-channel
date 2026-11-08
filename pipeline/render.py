"""Render an HTML scene frame by frame with the job's narration.
Usage: render.py <job> preview t1 t2 ... | render.py <job> full
Reads jobs/<job>/script.json and build/<job>/{timeline.json,voice.wav}; writes build/<job>/video.mp4."""
import json, os, sys, subprocess, time
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
job, mode = sys.argv[1], sys.argv[2]
J = f"{ROOT}/build/{job}"
facts = json.load(open(f"{ROOT}/build/facts.json"))
tl = json.load(open(f"{J}/timeline.json"))
spec = json.load(open(f"{ROOT}/jobs/{job}/script.json"))
W, H = spec.get("size", [1920, 1080])
SCENE = spec.get("scene", "scene_doc.html")
FPS = 30


def page_for(pw):
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.add_init_script("window.__DATA__=" + json.dumps({"facts": facts, "timeline": tl, "spec": spec}))
    pg.goto("file://" + f"{ROOT}/pipeline/{SCENE}")
    pg.wait_for_function("window.__ready===true", timeout=30000)
    if errs:
        raise SystemExit(errs)
    return br, pg


with sync_playwright() as pw:
    br, pg = page_for(pw)
    if mode == "preview":
        os.makedirs(f"{J}/preview", exist_ok=True)
        for s in sys.argv[3:]:
            pg.evaluate(f"draw({s})")
            pg.screenshot(path=f"{J}/preview/t{float(s):06.1f}.jpg", type="jpeg", quality=88)
    else:
        n = int(tl["total"] * FPS)
        ff = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
             "-i", f"{J}/voice.wav", "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-shortest", "-movflags", "+faststart",
             f"{J}/video.mp4"], stdin=subprocess.PIPE)
        t0 = time.time()
        for i in range(n):
            pg.evaluate(f"draw({i / FPS})")
            ff.stdin.write(pg.screenshot(type="jpeg", quality=93))
            if i % 300 == 0:
                print(job, i, n, round(time.time() - t0), flush=True)
        ff.stdin.close()
        ff.wait()
        print(job, "done", ff.returncode, round(time.time() - t0))
    br.close()
