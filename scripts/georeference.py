#!/usr/bin/env python3
"""Fit the scan-to-world transform by matching the digitized tracks to OpenStreetMap.

The Green Line still runs in the 1897 tunnel, so OSM's track ways through Boylston station are
used as control: a similarity transform (rotation, scale, translation) is fitted so that the OSM
track points fall on the digitized track centerlines. Prints the parameters to paste into
config/model.json ("georeference") and writes docs/osm_overlay.png for a visual check.

Run:  python scripts/georeference.py        (needs scipy; data/osm/boylston_area.osm)
"""
import math
import os
import sys
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image, ImageDraw
from scipy.optimize import least_squares
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tracelib import ROOT, densify, load_features  # noqa: E402

LAT0, LON0 = 42.3532, -71.0645                 # local tangent-plane origin
ANCHOR = (350.0, 320.0)                        # pixel that the translation refers to
KX, KY = 111320 * math.cos(math.radians(LAT0)), 111132
SCALE_BAR = 0.2396                             # m/px from the drawing's "Scale of Plan" (100 ft = 127.2 px)

osm = ET.parse(os.path.join(ROOT, 'data', 'osm', 'boylston_area.osm')).getroot()
nodes = {n.get('id'): ((float(n.get('lon')) - LON0) * KX, (float(n.get('lat')) - LAT0) * KY) for n in osm.findall('node')}


def way_tags(w):
    return {t.get('k'): t.get('v') for t in w.findall('tag')}


def way_points(w):
    return np.array([nodes[n.get('ref')] for n in w.findall('nd') if n.get('ref') in nodes])


def to_px(P, o):
    """ENU metres -> image pixels. o = (azimuth of the image x axis in degrees, m/px, east, north of ANCHOR)."""
    a = math.radians(o[0])
    d = P - np.array([o[2], o[3]])
    return np.stack([ANCHOR[0] + d @ np.array([math.sin(a), math.cos(a)]) / o[1],
                     ANCHOR[1] + d @ np.array([math.cos(a), -math.sin(a)]) / o[1]], axis=1)


# control: OSM tracks on the Tremont Street Subway level, sampled every 2 m
ctrl = []
for w in osm.findall('way'):
    t = way_tags(w)
    if t.get('railway') in ('light_rail', 'disused', 'abandoned') and t.get('layer') == '-1':
        p = way_points(w)
        for a, b in zip(p[:-1], p[1:]):
            n = max(1, int(np.hypot(*(b - a)) / 2.0))
            ctrl += [a + (b - a) * k / n for k in range(n)]
ctrl = np.array(ctrl)

traced = np.array([q for f in load_features()['features'] if f['kind'] == 'track' and not f.get('approximate')
                   for q in densify(f, 1.0)])
tree = cKDTree(traced)

# coarse search over rotation and translation, then least squares on the points that land on the sheet
best = None
for th in np.arange(-30, 31, 2.0):
    for e in range(-80, 81, 6):
        for n in range(-100, 101, 6):
            q = to_px(ctrl[::3], (th, SCALE_BAR, e, n))
            m = (q[:, 0] > 0) & (q[:, 0] < 972) & (q[:, 1] > 10) & (q[:, 1] < 440)
            if m.sum() < 60:
                continue
            d, _ = tree.query(q[m])
            score = (-(d < 5).sum(), np.minimum(d, 15).mean())
            if best is None or score < best[0]:
                best = (score, (th, SCALE_BAR, e, n))
q0 = to_px(ctrl, best[1])
mask = (q0[:, 0] > 8) & (q0[:, 0] < 960) & (q0[:, 1] > 20) & (q0[:, 1] < 430)
fit = least_squares(lambda o: np.minimum(tree.query(to_px(ctrl[mask], o))[0], 8), best[1], diff_step=1e-3).x
d = tree.query(to_px(ctrl[mask], fit))[0]
print(f'control points: {mask.sum()}   misfit median {np.median(d):.2f} px, 90th percentile {np.percentile(d, 90):.2f} px')
print(f'"lat0": {LAT0}, "lon0": {LON0}, "anchor_px": {list(ANCHOR)}, "anchor_enu_m": [{fit[2]:.4f}, {fit[3]:.4f}],')
print(f'"sheet_x_azimuth_deg": {fit[0]:.4f}, "metres_per_pixel": {fit[1]:.4f}    (scale bar: {SCALE_BAR})')

# visual check: OSM tracks (red), platforms (green), streets (blue), buildings (orange), station entrances (magenta)
im = Image.open(os.path.join(ROOT, load_features()['image'])).convert('RGB')
im = im.resize((im.width * 2, im.height * 2))
dr = ImageDraw.Draw(im)
for w in osm.findall('way'):
    t, p = way_tags(w), way_points(w)
    if len(p) < 2:
        continue
    lvl = t.get('layer') == '-1'
    col = ((230, 0, 0) if t.get('railway') in ('light_rail', 'disused', 'abandoned') and lvl else
           (0, 150, 0) if t.get('railway') == 'platform' and lvl else
           (0, 0, 230) if 'highway' in t and t['highway'] not in ('footway', 'path', 'steps', 'pedestrian', 'cycleway', 'service') else
           (210, 120, 0) if 'building' in t else None)
    if col:
        dr.line([(float(x) * 2, float(y) * 2) for x, y in to_px(p, fit)], fill=col, width=2)
for n in osm.findall('node'):
    if way_tags(n).get('railway') == 'subway_entrance':
        x, y = to_px(np.array([nodes[n.get('id')]]), fit)[0] * 2
        dr.ellipse([x - 7, y - 7, x + 7, y + 7], outline=(255, 0, 255), width=3)
os.makedirs(os.path.join(ROOT, 'docs'), exist_ok=True)
im.save(os.path.join(ROOT, 'docs', 'osm_overlay.png'))
