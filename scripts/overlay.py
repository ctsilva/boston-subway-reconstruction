"""QA overlay: draw the digitized features on top of the scan, zoomed, to check the fit."""
import os
import sys
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(__file__))
from tracelib import load_features, densify

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COL = {'track': (220, 30, 30), 'wall': (20, 90, 230), 'platform': (0, 160, 70), 'stairs': (230, 120, 0),
       'passage': (150, 0, 200), 'conduit': (0, 170, 190), 'curb': (200, 0, 160), 'building_line': (120, 90, 30),
       'section_line': (90, 90, 90), 'footway': (60, 140, 60)}

def main(out, x0, y0, x1, y1, s):
    doc = load_features()
    src = Image.open(os.path.join(ROOT, doc['image'])).convert('RGB')
    im = src.crop((x0, y0, x1, y1)).resize(((x1 - x0) * s, (y1 - y0) * s), Image.LANCZOS)
    d = ImageDraw.Draw(im, 'RGBA')
    for f in doc['features']:
        pts = densify(f)
        if f.get('closed'): pts = pts + [pts[0]]
        xy = [((x - x0 + 0.5) * s, (y - y0 + 0.5) * s) for x, y in pts]
        d.line(xy, fill=COL.get(f['kind'], (0, 0, 0)) + (190,), width=2)
    im.save(out)

if __name__ == '__main__':
    # python scripts/overlay.py [out.png x0 y0 x1 y1 zoom]   (default: whole sheet at 2x into docs/)
    a = sys.argv
    if len(a) >= 7:
        main(a[1], *[int(v) for v in a[2:7]])
    else:
        os.makedirs(os.path.join(ROOT, 'docs'), exist_ok=True)
        main(os.path.join(ROOT, 'docs', 'trace_overlay.png'), 0, 0, 972, 596, 2)
