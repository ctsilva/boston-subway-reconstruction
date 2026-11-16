#!/usr/bin/env python3
"""Checks the built data in data/scenarios/ against itself. Run after scripts/build.py.

These read only the exported files, so they catch a statistic that describes a different model
from the geometry that was written.

  1. Headroom at each crossing, measured from the exported deck and the exported track, matches
     the headroom reported in stats.json.
  2. Every exported polygon is valid and every number is finite.
  3. Raising or lowering only the ground changes the cover over the roof by exactly that amount
     and leaves the rails where they were.
  4. A ramp scenario with a requested grade has that mean rail grade.

Run:  python scripts/check.py        (exit code 1 if anything fails)
"""
import json
import math
import os
import sys

from shapely.geometry import Point, shape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCEN = os.path.join(ROOT, 'data', 'scenarios')
failures = []


def load(sid, name):
    with open(os.path.join(SCEN, sid, name)) as fh:
        return json.load(fh)


def check(ok, message):
    if not ok:
        failures.append(message)


def finite(value):
    return not isinstance(value, float) or math.isfinite(value)


ids = [s['id'] for s in json.load(open(os.path.join(SCEN, 'index.json')))['scenarios']]
for sid in ids:
    stats = load(sid, 'stats.json')
    subway = load(sid, 'subway_3d.geojson')['features']
    surface = load(sid, 'surface_3d.geojson')['features']
    tracks = load(sid, 'tracks.geojson')['features']
    duck = stats['duck_under']

    # 1. crossing headroom from exported geometry
    decks = [(shape(f['geometry']), f['properties']) for f in subway if f['properties'].get('level') == 'deck over sub-subway']
    lower = [f for f in tracks if f['properties']['track'] == 'track_sb_pleasant']
    for c in duck['crossings']:
        pt = Point(c['lonlat'])
        over = [p for g, p in decks if g.buffer(1e-6).contains(pt)]
        seg = min(lower, key=lambda f: abs(f['properties']['chainage_m'] - c['chainage_m']))
        rail = seg['properties']['ele']
        if over:
            measured = over[0]['ele_bottom'] - rail
            # prisms and track pieces are 2 to 3 m long, so levels are stepped by a few centimetres
            check(abs(measured - c['headroom_m']) < 0.15,
                  f"{sid}: headroom under {c['track_above']} is {measured:.2f} m in the geometry, {c['headroom_m']:.2f} m in stats")
        else:
            check(c['headroom_m'] < duck['headroom_required_m'] - 0.05 and not duck['fits'],
                  f"{sid}: no deck is exported under {c['track_above']} but stats report {c['headroom_m']:.2f} m of headroom")

    # 2. valid geometry, finite numbers
    for name, feats in (('subway_3d', subway), ('surface_3d', surface)):
        bad = [f['id'] for f in feats if not shape(f['geometry']).is_valid]
        check(not bad, f"{sid}/{name}: {len(bad)} invalid polygons, e.g. feature {bad[:3]}")
        low = [f['id'] for f in feats if f['properties']['height'] <= f['properties']['min_height'] or f['properties']['min_height'] < 0]
        check(not low, f"{sid}/{name}: {len(low)} prisms with a bad height range")
        check(all(finite(v) for f in feats for v in f['properties'].values()), f"{sid}/{name}: non-finite property value")

    # 4. requested ramp grade
    want = duck.get('requested_mean_rail_grade_pct')
    if want is not None:
        check(abs(duck['mean_rail_grade_pct'] - want) < 0.05,
              f"{sid}: asked for a {want}% ramp, mean rail grade is {duck['mean_rail_grade_pct']}%")

# 3. offsets move the cover, not the rails
base = {'roof': [f['properties'] for f in load('existing', 'subway_3d.geojson')['features'] if f['properties']['part'] == 'roof'],
        'rail': [f['properties']['ele'] for f in load('existing', 'tracks.geojson')['features']]}
for sid in ids:
    surf = load(sid, 'stats.json')['surface']
    if surf.get('type') != 'offset' or load(sid, 'stats.json')['structure'] != 'as_built':
        continue
    roof = [f['properties'] for f in load(sid, 'subway_3d.geojson')['features'] if f['properties']['part'] == 'roof']
    rail = [f['properties']['ele'] for f in load(sid, 'tracks.geojson')['features']]
    check(len(roof) == len(base['roof']), f"{sid}: roof cell count differs from the baseline")
    worst = max(abs((a['cover_m'] - b['cover_m']) - surf['dz_m']) for a, b in zip(roof, base['roof']))
    check(worst < 0.002, f"{sid}: cover changed by something other than {surf['dz_m']} m (off by up to {worst:.3f} m)")
    check(rail == base['rail'], f"{sid}: rail elevations changed although only the ground was offset")

if failures:
    print(f"{len(failures)} check(s) FAILED")
    for f in failures:
        print('  -', f)
    sys.exit(1)
print(f"all checks passed for {len(ids)} scenarios")
