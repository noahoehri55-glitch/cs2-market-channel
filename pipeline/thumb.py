import json,os
from playwright.sync_api import sync_playwright
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
f=json.load(open(f'{R}/build/facts.json'))
h=open(f'{R}/pipeline/thumb.html').read().replace('SERIES',json.dumps([x[1] for x in f['series']]))
open(f'{R}/pipeline/_thumb_render.html','w').write(h)
with sync_playwright() as p:
    b=p.chromium.launch();g=b.new_page(viewport={'width':1280,'height':720});g.goto(f'file://{R}/pipeline/_thumb_render.html');g.evaluate('document.fonts.ready');g.screenshot(path=f'{R}/build/thumbnail.png');b.close()
