#!/usr/bin/env python3
"""Build the georeferenced 2D plan and the 3D grading scenarios for Boylston St. station (1897).

Inputs
  trace/features.json          hand digitization of the scan, in image pixels
  config/model.json            georeferencing, vertical dimensions read off the cross sections, assumptions
  config/scenarios.json        ground-surface gradings to evaluate
  data/dem/usgs_3dep_samples.json   present-day ground elevations (USGS 3DEP)

Outputs (all GeoJSON is EPSG:4326)
  data/plan_1897.geojson                       2D ways and areas with OSM-style tags
  data/scenarios/<id>/tracks.geojson           3D track ways [lon, lat, ele], cut every few metres
  data/scenarios/<id>/subway_3d.geojson        structure as prisms (height / min_height above the datum)
  data/scenarios/<id>/surface_3d.geojson       graded ground as thin prisms
  data/scenarios/<id>/profiles.csv, stats.json
  data/scenarios/index.json

Run:  python scripts/build.py
"""
import csv
import json
import math
import os
import sys

import numpy as np
import shapely
from shapely.geometry import LineString, Polygon, box, mapping
from shapely.ops import substring, unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tracelib import ROOT, densify, load_features  # noqa: E402

FT = 0.3048


def load(path):
    with open(os.path.join(ROOT, path)) as fh:
        return json.load(fh)


MODEL = load('config/model.json')
SCEN = load('config/scenarios.json')
GEO = MODEL['georeference']
V = MODEL['vertical']
IMG_H = 596
SC = GEO['metres_per_pixel']
DATUM = MODEL['datum_m']

# ---------------------------------------------------------------- coordinates
# Sheet frame: metres, X along the sheet's x axis (roughly north along Tremont St), Y up the
# sheet (toward the Common). All modelling happens here; geographic conversion is done on output.
_a = math.radians(GEO['sheet_x_azimuth_deg'])
_KX = 111320.0 * math.cos(math.radians(GEO['lat0']))
_KY = 111132.0


def px2sheet(x, y):
    return (x * SC, (IMG_H - y) * SC)


def sheet2ll(X, Y):
    dx = X / SC - GEO['anchor_px'][0]
    dy = (IMG_H - Y / SC) - GEO['anchor_px'][1]
    e = GEO['anchor_enu_m'][0] + SC * (dx * math.sin(_a) + dy * math.cos(_a))
    n = GEO['anchor_enu_m'][1] + SC * (dx * math.cos(_a) - dy * math.sin(_a))
    return (round(GEO['lon0'] + e / _KX, 8), round(GEO['lat0'] + n / _KY, 8))


def ll2sheet(lon, lat):
    e = (lon - GEO['lon0']) * _KX - GEO['anchor_enu_m'][0]
    n = (lat - GEO['lat0']) * _KY - GEO['anchor_enu_m'][1]
    dx = (e * math.sin(_a) + n * math.cos(_a)) / SC
    dy = (e * math.cos(_a) - n * math.sin(_a)) / SC
    return px2sheet(GEO['anchor_px'][0] + dx, GEO['anchor_px'][1] + dy)


def geom_ll(geom, z=None):
    """shapely geometry in sheet metres -> GeoJSON geometry in lon/lat (optionally with per-vertex z)."""
    def conv(coords):
        return [list(sheet2ll(c[0], c[1])) + ([round(z(c[0], c[1]), 3)] if z else []) for c in coords]
    if geom.geom_type == 'LineString':
        return {'type': 'LineString', 'coordinates': conv(geom.coords)}
    if geom.geom_type == 'Polygon':
        return {'type': 'Polygon', 'coordinates': [conv(geom.exterior.coords)] + [conv(r.coords) for r in geom.interiors]}
    raise ValueError(geom.geom_type)


def polygons(geom):
    if geom.is_empty:
        return []
    if geom.geom_type == 'Polygon':
        return [geom]
    if hasattr(geom, 'geoms'):
        return [p for g in geom.geoms for p in polygons(g)]
    return []


# ---------------------------------------------------------------- digitized features
DOC = load_features()
F = {}
for f in DOC['features']:
    pts = [px2sheet(x, y) for x, y in densify(f)]
    f['_geom'] = Polygon(pts) if f.get('closed') else LineString(pts)
    F[f['id']] = f


def line(fid, reverse=False):
    c = list(F[fid]['_geom'].coords)
    return c[::-1] if reverse else c


X_AB = 287 * SC          # cross section A-B
X_CD = 697 * SC          # cross section C-D

# Excavation footprint: ring through the outer walls, minus the unexcavated wedge at the junction.
_ring = (line('wall_east') + line('wall_west') + line('wall_boylston_north') +
         line('wall_boylston_south') + line('wall_subsubway_west'))
_wedge = Polygon(line('wall_divider_south') + line('wall_divider_south_b') + line('wall_station_south_end', True))
FOOTPRINT = Polygon(_ring).buffer(0).difference(_wedge.buffer(0)).buffer(0)

T1 = F['track_sb_pleasant']['_geom']            # digitized north -> south


def _t1_chainage_at_x(xpx):
    """Chainage along T1 where it crosses a given pixel column (first crossing from the north)."""
    X = xpx * SC
    hit = T1.intersection(LineString([(X, -50), (X, 400)]))
    pts = [hit] if hit.geom_type == 'Point' else list(hit.geoms)
    return min(T1.project(p) for p in pts)


SS = V['subsubway']
C_PLATFORM_END = _t1_chainage_at_x(SS['southbound_platform_end_px_x'])   # ramp cannot start north of this
C_SECTION_AB = _t1_chainage_at_x(SS['ramp_bottom_px_x'])                 # full depth is drawn here
C_PORTAL = T1.project(shapely.Point(px2sheet(*SS['south_portal_px'])))


def _first_crossing():
    """Chainage along T1 where it first passes under one of the Boylston St tracks."""
    cs = []
    for fid in ('track_sb_boylston', 'track_nb_boylston'):
        hit = T1.intersection(F[fid]['_geom'])
        cs += [T1.project(q) for q in ([hit] if hit.geom_type == 'Point' else getattr(hit, 'geoms', []))]
    return min(c for c in cs if c > C_SECTION_AB)


C_CROSSING = _first_crossing()
# The ramp of the duck-under. A scenario may replace it (see set_ramp).
RAMP = {'top': _t1_chainage_at_x(SS['ramp_top_px_x']), 'bottom': C_SECTION_AB, 'hypothetical': False}
DROP = V['subsubway']['rail_below_main_ft'] * FT

# The single-track tunnel south-west of the main box: floor and roof follow T1 here.
_mid = [px2sheet(*p) for p in [(79, 401), (55, 404.5), (30, 408.5), (5, 411.5)]]
PASSAGE = Polygon(
    [px2sheet(138, 307)] + line('wall_subsubway_east') + line('wall_divider_south')[1:] + _mid[1:] +
    line('wall_subsubway_west', True)).buffer(0).intersection(FOOTPRINT)
MAIN = FOOTPRINT.difference(PASSAGE).buffer(0)


def set_ramp(spec):
    """Sets the duck-under ramp for a scenario. spec is the scenario's optional 'duck_under' entry."""
    if not spec:
        RAMP.update(top=_t1_chainage_at_x(SS['ramp_top_px_x']), bottom=C_SECTION_AB, hypothetical=False)
        return
    bottom = C_CROSSING - SS['crossing_margin_m'] if spec.get('full_depth_at') == 'crossing' else C_SECTION_AB
    top = bottom - DROP / (spec['grade_pct'] / 100.0) if spec.get('grade_pct') else C_PLATFORM_END
    RAMP.update(top=max(top, 1.0), bottom=bottom, hypothetical=True)


def t1_corridor():
    return substring(T1, RAMP['top'], T1.length).buffer(SS['outer_width_ft'] * FT / 2, cap_style='flat')


def t1_drop(c):
    """Depth of the sub-subway rail below the main level at chainage c along T1 (metres)."""
    if c <= RAMP['top']:
        return 0.0
    if c <= RAMP['bottom']:
        return DROP * (c - RAMP['top']) / (RAMP['bottom'] - RAMP['top'])
    if c <= C_PORTAL:
        return DROP
    return max(0.0, DROP - V['subsubway']['south_rise_grade_pct'] / 100.0 * (c - C_PORTAL))


def t1_drop_smooth(c, w=6.0):
    """Short vertical curves: average the piecewise-linear profile over +/- w metres."""
    return float(np.mean([t1_drop(c + d) for d in np.linspace(-w, w, 9)]))


# ---------------------------------------------------------------- ground surfaces
GRID = 1.0
NX = int(math.ceil(972 * SC / GRID)) + 1
NY = int(math.ceil(IMG_H * SC / GRID)) + 1
GX, GY = np.meshgrid(np.arange(NX) * GRID, np.arange(NY) * GRID)


def existing_surface():
    dem = load('data/dem/usgs_3dep_samples.json')
    nx, ny = dem['nx'], dem['ny']
    s = np.array(dem['samples'], dtype=float).reshape(ny, nx, 3)
    lons, lats, z = s[0, :, 0], s[:, 0, 1], s[:, :, 2]
    out = np.zeros_like(GX)
    for j in range(NY):
        for i in range(NX):
            lon, lat = sheet2ll(GX[j, i], GY[j, i])
            fi = min(max((lon - lons[0]) / (lons[1] - lons[0]), 0), nx - 1.001)
            fj = min(max((lat - lats[0]) / (lats[1] - lats[0]), 0), ny - 1.001)
            i0, j0 = int(fi), int(fj)
            a, b = fi - i0, fj - j0
            out[j, i] = (z[j0, i0] * (1 - a) * (1 - b) + z[j0, i0 + 1] * a * (1 - b) +
                         z[j0 + 1, i0] * (1 - a) * b + z[j0 + 1, i0 + 1] * a * b)
    return out


def sample(grid, X, Y):
    fi = min(max(X / GRID, 0), NX - 1.001)
    fj = min(max(Y / GRID, 0), NY - 1.001)
    i0, j0 = int(fi), int(fj)
    a, b = fi - i0, fj - j0
    return float(grid[j0, i0] * (1 - a) * (1 - b) + grid[j0, i0 + 1] * a * (1 - b) +
                 grid[j0 + 1, i0] * (1 - a) * b + grid[j0 + 1, i0 + 1] * a * b)


EXISTING = existing_surface()
_dist = shapely.distance(shapely.points(GX.ravel(), GY.ravel()), FOOTPRINT).reshape(GX.shape)
CURB = F['curb_common']['_geom']                 # Tremont St curb above the east wall
_c = [c for c in CURB.coords if c[0] >= 200 * SC]   # the part along Tremont St; x increases northward
_CURB_X = [c[0] for c in _c]
_CURB_Y = [c[1] for c in _c]


def corridor_weight(reach, blend):
    """1 over the subway and `reach` metres around it, falling to 0 over the next `blend` metres."""
    t = np.clip((_dist - reach) / max(blend, 1e-6), 0, 1)
    return 1 - t * t * (3 - 2 * t)


def curb_profile(grid):
    """Least-squares line through the ground elevation along the Tremont St side of the station."""
    xs = np.linspace(X_AB - 30, X_CD + 30, 60)
    zs = [sample(grid, x, float(np.interp(x, _CURB_X, _CURB_Y))) for x in xs]
    slope, icpt = np.polyfit(xs - X_AB, np.array(zs), 1)
    return float(slope), float(icpt)             # z = icpt + slope * (X - X_AB)


def make_surface(spec):
    kind = spec['type']
    if kind == 'existing':
        return EXISTING.copy()
    w = corridor_weight(spec.get('reach_m', 12.0), spec.get('blend_m', 15.0))
    if kind == 'offset':
        target = EXISTING + spec['dz_m']
    elif kind == 'plane':
        slope, icpt = curb_profile(EXISTING)
        g = spec.get('grade_long_pct')
        g = slope if g is None else g / 100.0
        yc = np.interp(GX[0], _CURB_X, _CURB_Y)
        target = icpt + spec.get('dz_m', 0.0) + g * (GX - X_AB) + spec.get('grade_cross_pct', 0.0) / 100.0 * (GY - yc[None, :])
    else:
        raise ValueError(f'unknown surface type {kind}')
    return EXISTING * (1 - w) + target * w


# ---------------------------------------------------------------- structure levels
def smooth(grid, radius_m):
    """Three box-blur passes (close to a Gaussian) with edge replication."""
    r = max(1, int(round(radius_m / GRID)))
    out = grid.astype(float)
    for _ in range(3):
        for axis in (0, 1):
            pad = [(r, r) if a == axis else (0, 0) for a in (0, 1)]
            c = np.cumsum(np.pad(out, pad, mode='edge'), axis=axis)
            c = np.insert(c, 0, 0, axis=axis)
            n = out.shape[axis]
            hi = np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axis)
            lo = np.take(c, np.arange(0, n), axis=axis)
            out = (hi - lo) / (2 * r + 1)
    return out


def _smoothstep(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


_BR = V['branch_blend_m']
_Y_BOYLSTON = px2sheet(0, 285)[1]      # the Boylston St branch leaves the station box north of this row
_X_BOYLSTON = px2sheet(190, 0)[0]
_X_PLEASANT = px2sheet(150, 0)[0]      # the Pleasant St branch leaves the box south of this column
_Y_PLEASANT = px2sheet(0, 330)[1]


def branch_weight(X, Y):
    """0 inside the station box, rising to 1 along the Boylston St and Pleasant St branches."""
    w = 0.0
    if X < _X_BOYLSTON:
        w = max(w, _smoothstep((Y - _Y_BOYLSTON) / _BR))
    if Y < _Y_PLEASANT:
        w = max(w, _smoothstep((_X_PLEASANT - X) / _BR))
    return w


class Levels:
    """Elevations of the structure.

    Cut-and-cover: the main-level rail sits a fixed depth below the smoothed street grade. Inside the
    station box the reference is the Tremont St curb at the same sheet x, so the four tracks are level
    with each other; along the two branches it is the smoothed ground above the tunnel itself.
    """

    def __init__(self, rail_grid):
        self.sm = smooth(rail_grid, V['grade_smoothing_m'])
        self.depth = V['rail_below_street_ft'] * FT
        self.clear = V['clear_height_ft'] * FT
        self.roof_t = V['roof_slab_ft'] * FT
        self.floor_t = V['floor_slab_ft'] * FT
        self.bed = V['rail_above_floor_m']
        self.slope = (self.rail(X_CD, 0) - self.rail(X_AB, 0)) / (X_CD - X_AB)

    def rail(self, X, Y=0.0):
        xc = min(max(X, _CURB_X[0]), _CURB_X[-1])
        ref = sample(self.sm, xc, float(np.interp(xc, _CURB_X, _CURB_Y)))
        w = branch_weight(X, Y)
        if w > 0:
            ref = (1 - w) * ref + w * sample(self.sm, X, Y)
        return ref - self.depth

    def rail_t1(self, X, Y):
        return self.rail(X, Y) - t1_drop_smooth(T1.project(shapely.Point(X, Y)))

    def roof_top(self, X, Y):
        """Top of the uppermost roof slab above a point of the footprint."""
        if PASSAGE.contains(shapely.Point(X, Y)):
            return self.rail_t1(X, Y) + V['subsubway']['clear_height_ft'] * FT + self.roof_t
        return self.rail(X, Y) + self.clear + self.roof_t


# ---------------------------------------------------------------- feature helpers
def tags_for(f):
    k = f['kind']
    base = {'name': f.get('name'), 'start_date': '1897', 'source': 'Geo. H. Walker & Co. plan of Boylston St. station (digitized)'}
    if k == 'track':
        base.update({'railway': 'tram', 'tunnel': 'yes', 'gauge': '1435', 'oneway': 'yes' if f.get('direction') else None,
                     'layer': '-2' if f.get('level') == 'sub-subway' else '-1', 'direction': f.get('direction')})
    elif k == 'wall':
        base.update({'barrier': 'wall', 'location': 'underground', 'tunnel': 'yes'})
    elif k == 'platform':
        base.update({'railway': 'platform', 'tunnel': 'yes', 'layer': '-1'})
    elif k == 'stairs':
        base.update({'highway': 'steps', 'area': 'yes', 'layer': '-1'})
    elif k == 'passage':
        base.update({'highway': 'footway', 'area': 'yes', 'tunnel': 'yes', 'layer': '-2'})
    elif k == 'conduit':
        base.update({'man_made': 'pipeline', 'substance': 'water', 'location': 'underground', 'layer': '-3'})
    elif k == 'curb':
        base.update({'barrier': 'kerb'})
    elif k == 'building_line':
        base.update({'historic': 'building_line'})
    elif k == 'section_line':
        base.update({'note': 'cross-section line on the source drawing'})
    if f.get('approximate'):
        base['fixme'] = 'approximate reading of the scan'
    return {k2: v for k2, v in base.items() if v is not None}


def track_geom(f):
    """Tracks are stored in the direction of travel, like OSM oneway ways."""
    g = f['_geom']
    return LineString(list(g.coords)[::-1]) if f.get('direction') == 'northbound' else g


def write_geojson(path, features, **meta):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as fh:
        json.dump({'type': 'FeatureCollection', **meta, 'features': features}, fh, separators=(',', ':'))
    return len(features)


def strips(poly, step, axis=0):
    """Cut a polygon into strips of width `step` along X (axis 0) or Y (axis 1)."""
    minx, miny, maxx, maxy = poly.bounds
    lo, hi = (minx, maxx) if axis == 0 else (miny, maxy)
    out = []
    k = math.floor(lo / step)
    while k * step < hi:
        a, b = k * step, (k + 1) * step
        cut = poly.intersection(box(a, miny - 1, b, maxy + 1) if axis == 0 else box(minx - 1, a, maxx + 1, b))
        out += [p for p in polygons(cut) if p.area > 0.02]
        k += 1
    return out


def cells(poly, step):
    return [c for s in strips(poly, step, 0) for c in strips(s, step, 1)]


class Collector:
    def __init__(self):
        self.features = []

    def prism(self, poly, zmin, zmax, part, **props):
        if zmax - zmin < 0.01 or poly.is_empty:
            return
        for p in polygons(poly):
            p = shapely.geometry.polygon.orient(p.simplify(0.02), 1.0)
            if p.is_empty or p.area < 0.02:
                continue
            self.features.append({
                'type': 'Feature', 'id': len(self.features),
                'geometry': geom_ll(p),
                'properties': {'part': part, 'height': round(zmax - DATUM, 3), 'min_height': round(zmin - DATUM, 3),
                               'ele_top': round(zmax, 3), 'ele_bottom': round(zmin, 3), **props},
            })


# ---------------------------------------------------------------- plan (2D)
def build_plan():
    feats = []
    for f in DOC['features']:
        g = track_geom(f) if f['kind'] == 'track' else f['_geom']
        props = {'id': f['id'], 'kind': f['kind'], **tags_for(f)}
        if f['kind'] == 'conduit':
            props['width'] = round(f['width_ft'] * FT, 2)
        feats.append({'type': 'Feature', 'id': f['id'], 'geometry': geom_ll(g), 'properties': props})
    feats.append({'type': 'Feature', 'id': 'footprint', 'geometry': geom_ll(FOOTPRINT),
                  'properties': {'id': 'footprint', 'kind': 'footprint', 'name': 'Subway excavation footprint (derived from the walls)',
                                 'tunnel': 'yes', 'layer': '-1'}})
    return write_geojson(os.path.join(ROOT, 'data', 'plan_1897.geojson'), feats,
                         name='Boylston St. station, Tremont Street Subway, 1897 (digitized plan)')


# ---------------------------------------------------------------- one scenario
def build_scenario(spec):
    sid = spec['id']
    out_dir = os.path.join(ROOT, 'data', 'scenarios', sid)
    surf = make_surface(spec['surface'])
    follow = spec.get('structure') == 'follow_surface'
    lv = Levels(surf if follow else EXISTING)
    set_ramp(spec.get('duck_under'))

    def basis(X, Y, sub=False):
        """How well a level is supported: measured, inferred, assumed, or hypothetical (see README)."""
        if follow:
            return 'hypothetical'
        if sub:
            c = T1.project(shapely.Point(X, Y))
            if c > C_PORTAL:
                return 'assumed'
            if c > RAMP['top'] - 6.0:
                return 'hypothetical' if RAMP['hypothetical'] else 'inferred'
        return 'inferred' if branch_weight(X, Y) > 0.05 else 'measured'
    S = lambda X, Y: sample(surf, X, Y)  # noqa: E731
    seg = MODEL['output']['track_segment_m']
    cell = MODEL['output']['cell_m']
    soil = V['soil_unit_weight_kn_m3']
    min_cover = V['min_cover_m']

    # ---- tracks: 3D ways cut into short segments, plus ribbons for the 3D view
    ways, rows = [], []
    col = Collector()
    gauge = 1.435
    for f in DOC['features']:
        if f['kind'] != 'track':
            continue
        g = track_geom(f)
        is_t1 = f['id'] == 'track_sb_pleasant'
        zr = (lambda X, Y: lv.rail_t1(X, Y)) if is_t1 else (lambda X, Y: lv.rail(X, Y))
        n = max(1, int(round(g.length / seg)))
        for k in range(n):
            part = substring(g, g.length * k / n, g.length * (k + 1) / n)
            (xa, ya), (xb, yb) = part.coords[0], part.coords[-1]
            za, zb = zr(xa, ya), zr(xb, yb)
            mid = part.interpolate(0.5, normalized=True)
            zm, sm = zr(mid.x, mid.y), S(mid.x, mid.y)
            inside = FOOTPRINT.contains(mid)
            cover = sm - lv.roof_top(mid.x, mid.y) if inside else None
            grade = 100.0 * (zb - za) / max(part.length, 1e-6)
            props = {
                **tags_for(f), 'track': f['id'], 'scenario': sid, 'segment': k,
                'chainage_m': round(g.length * (k + 0.5) / n, 2), 'length_m': round(part.length, 2),
                'station_m': round(mid.x - X_AB, 2),
                'ele': round(zm, 3), 'ele_surface': round(sm, 3), 'depth_m': round(sm - zm, 3),
                'cover_m': None if cover is None else round(cover, 3),
                'incline': f'{grade:.1f}%', 'grade_pct': round(grade, 2), 'abs_grade_pct': round(abs(grade), 2),
                'basis': basis(mid.x, mid.y, is_t1),
            }
            ways.append({'type': 'Feature', 'id': len(ways), 'geometry': geom_ll(part, zr), 'properties': props})
            col.prism(part.buffer(gauge / 2, cap_style='flat'), zm - 0.05, zm + 0.12, 'track',
                      **{k2: props[k2] for k2 in ('name', 'track', 'station_m', 'chainage_m', 'ele', 'ele_surface', 'depth_m', 'cover_m',
                                               'grade_pct', 'abs_grade_pct', 'basis')})
            rows.append([f['id'], props['chainage_m'], round(mid.x, 2), round(mid.y, 2), *sheet2ll(mid.x, mid.y),
                         props['ele'], round(lv.roof_top(mid.x, mid.y), 3) if inside else '', props['ele_surface'],
                         props['depth_m'], '' if cover is None else props['cover_m'], props['grade_pct']])
    write_geojson(os.path.join(out_dir, 'tracks.geojson'), ways, scenario=sid)
    with open(os.path.join(out_dir, 'profiles.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['track', 'chainage_m', 'sheet_x_m', 'sheet_y_m', 'lon', 'lat', 'ele_rail_m', 'ele_roof_top_m',
                    'ele_surface_m', 'depth_m', 'cover_m', 'grade_pct'])
        w.writerows(rows)

    # ---- roof, as cells carrying the cover above them
    covers = []
    sub_clear = V['subsubway']['clear_height_ft'] * FT
    for region, name in ((MAIN, 'main'), (PASSAGE, 'sub-subway')):
        for c in cells(region, cell):
            p = c.representative_point()
            top = lv.roof_top(p.x, p.y)
            cov = S(p.x, p.y) - top
            covers.append((cov, c.area))
            col.prism(c, top - lv.roof_t, top, 'roof', level=name, basis=basis(p.x, p.y, region is PASSAGE), cover_m=round(cov, 3),
                      soil_load_kpa=round(max(cov, 0) * soil, 2), exposed=bool(cov < 0), thin_cover=bool(cov < min_cover))

    # ---- floors
    ramp = t1_corridor().intersection(MAIN)
    ramp_open = unary_union([s for s in strips(ramp, 2.0) if 0.3 < lv.rail(s.centroid.x, s.centroid.y) - lv.rail_t1(s.centroid.x, s.centroid.y)
                             < sub_clear + 0.2] or [Polygon()])
    for s in cells(MAIN.difference(ramp_open), 6.0):
        r = lv.rail(s.centroid.x, s.centroid.y)
        col.prism(s, r - lv.bed - lv.floor_t, r - lv.bed, 'floor', level='main', basis=basis(s.centroid.x, s.centroid.y))
    for s in strips(unary_union([ramp, PASSAGE]), 2.0):
        p = s.representative_point()
        r1, r = lv.rail_t1(p.x, p.y), lv.rail(p.x, p.y)
        if r - r1 < 0.3 and not PASSAGE.contains(p):
            continue
        col.prism(s, r1 - lv.bed - lv.floor_t, r1 - lv.bed, 'floor', level='sub-subway', ele_rail=round(r1, 3), basis=basis(p.x, p.y, True))
    # retaining walls of the ramp inside the main box
    for s in strips(ramp.buffer(0.45).difference(ramp).intersection(MAIN), 2.0):
        p = s.representative_point()
        r1, r = lv.rail_t1(p.x, p.y), lv.rail(p.x, p.y)
        if r - r1 > 0.3:
            col.prism(s, r1 - lv.bed - lv.floor_t, r - lv.bed, 'wall', level='sub-subway', name='Sub-subway ramp wall', basis=basis(p.x, p.y, True))

    # ---- walls
    wt = V['wall_thickness_ft'] * FT
    for f in DOC['features']:
        if f['kind'] != 'wall' or f['id'] == 'wall_subsubway_inner':
            continue
        g = f['_geom']
        n = max(1, int(round(g.length / 3.0)))
        for k in range(n):
            part = substring(g, g.length * k / n, g.length * (k + 1) / n)
            mid = part.interpolate(0.5, normalized=True)
            (xa, ya), (xb, yb) = part.coords[0], part.coords[-1]
            nx, ny = -(yb - ya), (xb - xa)
            ln = math.hypot(nx, ny) or 1.0
            lo, hi = [], []
            for sgn in (-1.5, 1.5):
                q = shapely.Point(mid.x + sgn * nx / ln, mid.y + sgn * ny / ln)
                if PASSAGE.contains(q):
                    r1 = lv.rail_t1(q.x, q.y)
                    lo.append(r1 - lv.bed - lv.floor_t)
                    hi.append(r1 + sub_clear + lv.roof_t)
                elif MAIN.contains(q):
                    r = lv.rail(q.x, q.y)
                    lo.append(r - lv.bed - lv.floor_t)
                    hi.append(r + lv.clear + lv.roof_t)
            if not lo:
                r = lv.rail(mid.x, mid.y)
                lo, hi = [r - lv.bed - lv.floor_t], [r + lv.clear + lv.roof_t]
            col.prism(part.buffer(wt / 2, cap_style='flat'), min(lo), max(hi), 'wall', name=f['name'], wall=f['id'],
                      basis=basis(mid.x, mid.y, PASSAGE.distance(mid) < 1.5))

    # ---- platforms, stairs, sub-passage, conduit
    plat_h = V['platform_above_rail_m']
    for f in DOC['features']:
        g = f['_geom']
        if f['kind'] == 'platform':
            for s in strips(g, 3.0):
                r = lv.rail(s.centroid.x, s.centroid.y)
                col.prism(s, r - lv.bed, r + plat_h, 'platform', name=f['name'], basis=basis(s.centroid.x, s.centroid.y))
        elif f['kind'] == 'stairs':
            r = lv.rail(g.centroid.x, g.centroid.y)
            top = S(g.centroid.x, g.centroid.y)
            rise = top - (r + plat_h)
            col.prism(g, r + plat_h, max(top, r + plat_h + 0.05), 'stairs', name=f['name'], stairs=f['id'], basis=basis(g.centroid.x, g.centroid.y),
                      rise_m=round(rise, 3), risers=int(math.ceil(max(rise, 0) / V['riser_m'])))
        elif f['kind'] == 'passage':
            r = lv.rail(g.centroid.x, g.centroid.y)
            base = r - lv.bed - lv.floor_t
            col.prism(g, base - V['sub_passage_clear_ft'] * FT, base, 'passage', name=f['name'], basis='assumed')
        elif f['kind'] == 'conduit':
            w_out = f['width_ft'] * FT
            for s in strips(g.buffer(w_out / 2, cap_style='flat'), 4.0):
                r = lv.rail(s.centroid.x, s.centroid.y)
                top = r - lv.bed - lv.floor_t - V['conduit_below_floor_m']
                col.prism(s, top - V['conduit_height_ft'] * FT, top, 'conduit', name=f['name'], basis='assumed')
    write_geojson(os.path.join(out_dir, 'subway_3d.geojson'), col.features, scenario=sid, datum_m=DATUM)

    # ---- ground surface as thin prisms
    ground = Collector()
    step = MODEL['output']['surface_cell_m']
    cut = fill = 0.0
    ymin = (IMG_H - 596) * SC
    for X in np.arange(0, 972 * SC - step / 2, step):
        for Y in np.arange(ymin, (IMG_H - 10) * SC - step / 2, step):
            c = box(X, Y, X + step, Y + step)
            z = S(X + step / 2, Y + step / 2)
            dz = z - sample(EXISTING, X + step / 2, Y + step / 2)
            cut += max(-dz, 0) * step * step
            fill += max(dz, 0) * step * step
            ground.prism(c, z - 0.15, z, 'ground', ele=round(z, 3), dz_m=round(dz, 3),
                         over_subway=bool(FOOTPRINT.contains(c.centroid)))
    # A wireframe of the same surface: Autark does not blend translucent 3D layers over each other,
    # so this is what lets the structure be seen under the ground.
    gs, gw = MODEL['output']['ground_grid_m'], 0.25
    x1, y1 = 972 * SC, (IMG_H - 10) * SC
    for axis in (0, 1):
        for a in np.arange(0, (y1 if axis == 0 else x1) + 0.01, gs):
            for b in np.arange(0, (x1 if axis == 0 else y1) - step / 2, step):
                c = box(b, a - gw / 2, b + step, a + gw / 2) if axis == 0 else box(a - gw / 2, b, a + gw / 2, b + step)
                cx, cy = c.centroid.x, c.centroid.y
                z = S(cx, cy)
                ground.prism(c, z - 0.1, z + 0.05, 'ground_grid', ele=round(z, 3), dz_m=round(z - sample(EXISTING, cx, cy), 3))
    write_geojson(os.path.join(out_dir, 'surface_3d.geojson'), ground.features, scenario=sid, datum_m=DATUM)

    # ---- statistics
    cov = np.array([c for c, _ in covers])
    area = np.array([a for _, a in covers])
    grades = {}
    for f in DOC['features']:
        if f['kind'] == 'track':
            g = [w['properties'] for w in ways if w['properties']['track'] == f['id']]
            grades[f['id']] = {'max_abs_grade_pct': max(p['abs_grade_pct'] for p in g),
                               'min_ele': min(p['ele'] for p in g), 'max_ele': max(p['ele'] for p in g),
                               'max_depth_m': max(p['depth_m'] for p in g)}
    stairs = {f['properties']['stairs']: {'rise_m': f['properties']['rise_m'], 'risers': f['properties']['risers']}
              for f in col.features if f['properties']['part'] == 'stairs'}
    # ---- the duck-under ramp and the restrictions on it
    t1 = [w['properties'] for w in ways if w['properties']['track'] == 'track_sb_pleasant']
    on_ramp = [p for p in t1 if RAMP['top'] - 6 <= p['chainage_m'] <= RAMP['bottom'] + 6]
    slab = SS['slab_over_ft'] * FT
    headroom = t1_drop_smooth(C_CROSSING) - slab
    need = SS['clear_height_ft'] * FT
    overlap = max(0.0, C_PLATFORM_END - RAMP['top'])
    duck = {
        'hypothetical': RAMP['hypothetical'],
        'drop_m': round(DROP, 2),
        'ramp_length_m': round(RAMP['bottom'] - RAMP['top'], 1),
        'mean_grade_pct': round(100 * DROP / (RAMP['bottom'] - RAMP['top']), 2),
        'max_grade_pct': max(p['abs_grade_pct'] for p in on_ramp),
        'room_for_ramp_m': round(C_CROSSING - SS['crossing_margin_m'] - C_PLATFORM_END, 1),
        'platform_overlap_m': round(overlap, 1),
        'headroom_at_crossing_m': round(headroom, 2), 'headroom_required_m': round(need, 2),
        'depth_at_section_ab_m': round(t1_drop_smooth(C_SECTION_AB), 2),
        'agrees_with_section_ab': bool(abs(t1_drop_smooth(C_SECTION_AB) - DROP) < 0.3),
        'fits': bool(overlap < 0.5 and headroom > need - 0.05),
    }
    stats = {
        'id': sid, 'title': spec['title'], 'description': spec.get('description', ''),
        'surface': spec['surface'], 'structure': spec.get('structure', 'as_built'),
        'main_rail': {'ele_at_section_ab_m': round(lv.rail(X_AB, 0), 3), 'ele_at_section_cd_m': round(lv.rail(X_CD, 0), 3),
                      'mean_grade_pct_northward': round(100 * lv.slope, 3)},
        'cover_over_roof': {
            'min_m': round(float(cov.min()), 3), 'mean_m': round(float(np.average(cov, weights=area)), 3),
            'max_m': round(float(cov.max()), 3),
            'area_exposed_m2': round(float(area[cov < 0].sum()), 1),
            'area_below_min_cover_m2': round(float(area[cov < min_cover].sum()), 1),
            'min_cover_criterion_m': min_cover, 'roof_area_m2': round(float(area.sum()), 1),
            'mean_soil_load_kpa': round(float(np.average(np.maximum(cov, 0), weights=area)) * soil, 2),
            'max_soil_load_kpa': round(float(max(cov.max(), 0)) * soil, 2),
        },
        'earthwork_vs_existing': {'cut_m3': round(cut, 1), 'fill_m3': round(fill, 1)},
        'duck_under': duck, 'tracks': grades, 'stairs': stairs,
        'counts': {'subway_3d': len(col.features), 'surface_3d': len(ground.features), 'tracks': len(ways)},
    }
    with open(os.path.join(out_dir, 'stats.json'), 'w') as fh:
        json.dump(stats, fh, indent=1)
    return stats


def main():
    n = build_plan()
    print(f'plan_1897.geojson: {n} features')
    index = []
    for spec in SCEN['scenarios']:
        st = build_scenario(spec)
        c = st['cover_over_roof']
        print(f"{st['id']:<28} cover min/mean {c['min_m']:6.2f}/{c['mean_m']:5.2f} m   exposed {c['area_exposed_m2']:7.1f} m2"
              f"   <min cover {c['area_below_min_cover_m2']:7.1f} m2   main grade {st['main_rail']['mean_grade_pct_northward']:5.2f}%"
              f"   cut/fill {st['earthwork_vs_existing']['cut_m3']:7.0f}/{st['earthwork_vs_existing']['fill_m3']:7.0f} m3")
        d = st['duck_under']
        print(f"{'':<28} duck-under ramp {d['ramp_length_m']:5.1f} m at {d['mean_grade_pct']:4.1f}% (max {d['max_grade_pct']:4.1f}%)"
              f"   platform overlap {d['platform_overlap_m']:5.1f} m   headroom {d['headroom_at_crossing_m']:.2f}/{d['headroom_required_m']:.2f} m"
              f"   {'fits' if d['fits'] else 'DOES NOT FIT'}{'' if d['agrees_with_section_ab'] else ', contradicts section A-B'}")
        index.append({k: st[k] for k in ('id', 'title', 'description', 'structure')})
    sw, ne = sheet2ll(0, 0), sheet2ll(972 * SC, (IMG_H - 140) * SC)
    with open(os.path.join(ROOT, 'data', 'scenarios', 'index.json'), 'w') as fh:
        json.dump({'datum_m': DATUM, 'origin_lonlat': [GEO['lon0'], GEO['lat0']],
                   'sheet_corners_lonlat': [sw, sheet2ll(972 * SC, 0), ne, sheet2ll(0, (IMG_H - 140) * SC)],
                   'scenarios': index}, fh, indent=1)


if __name__ == '__main__':
    main()
