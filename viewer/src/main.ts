/**
 * Boylston St. station (1897) grading scenarios in Autark.
 *
 * Each scenario is a set of GeoJSON prisms (`height` / `min_height` above a datum plane) that
 * AutkMap extrudes as a `buildings` layer. The files are EPSG:4326; they are converted here to a
 * local metric frame so horizontal and vertical scales match.
 */
import { AutkMap, MapEvent } from '@urban-toolkit/autk-map';
import { AutkPlot, PlotEvent } from '@urban-toolkit/autk-plot';
import { ColorMap, ColorMapDomainStrategy, ColorMapInterpolator } from '@urban-toolkit/autk-core';
import type { Feature, FeatureCollection, Position } from 'geojson';

type Thematic = { property: string; interpolator: ColorMapInterpolator; domain: number[]; label: string };
type LayerDef = {
    id: string; label: string; file: 'subway_3d' | 'surface_3d'; parts: string[];
    color: `#${string}`; opacity: number; visible: boolean; thematic?: Thematic;
};

const LAYERS: LayerDef[] = [
    { id: 'roof', label: 'Roof slab', file: 'subway_3d', parts: ['roof'], color: '#b9b9b9', opacity: 1, visible: true,
      thematic: { property: 'cover_m', interpolator: ColorMapInterpolator.DIV_RED_BLUE, domain: [-1.5, 0, 1.5], label: 'cover, m' } },
    { id: 'walls', label: 'Walls', file: 'subway_3d', parts: ['wall'], color: '#7d838c', opacity: 1, visible: true },
    { id: 'floor', label: 'Floor', file: 'subway_3d', parts: ['floor'], color: '#cfc8ba', opacity: 1, visible: true },
    { id: 'platforms', label: 'Platforms', file: 'subway_3d', parts: ['platform'], color: '#e3b55a', opacity: 1, visible: true },
    { id: 'tracks', label: 'Tracks', file: 'subway_3d', parts: ['track'], color: '#333333', opacity: 1, visible: true,
      thematic: { property: 'abs_grade_pct', interpolator: ColorMapInterpolator.SEQ_YL_OR_RD, domain: [0, 9], label: 'grade, %' } },
    { id: 'stairs', label: 'Stairs', file: 'subway_3d', parts: ['stairs'], color: '#c8642a', opacity: 1, visible: true },
    { id: 'below', label: 'Sub-passage and water conduit', file: 'subway_3d', parts: ['passage', 'conduit'], color: '#3a9db0', opacity: 1, visible: true },
    { id: 'ground-grid', label: 'Ground (wireframe)', file: 'surface_3d', parts: ['ground_grid'], color: '#5f7f52', opacity: 1, visible: true,
      thematic: { property: 'dz_m', interpolator: ColorMapInterpolator.DIV_BR_BG, domain: [-2, 0, 2], label: 'cut / fill, m' } },
    // Opaque: Autark does not blend translucent 3D layers over each other, so this hides what is below it.
    { id: 'ground', label: 'Ground (solid)', file: 'surface_3d', parts: ['ground'], color: '#8fae7c', opacity: 1, visible: false,
      thematic: { property: 'ele', interpolator: ColorMapInterpolator.SEQ_YL_GN, domain: [3, 11], label: 'elevation, m' } },
];

/** How well each level is supported, in the order of the categorical colour scheme below. */
const BASIS = ['measured', 'assumed', 'inferred', 'hypothetical'];
const BASIS_COLOURS = ['#1b9e77', '#d95f02', '#7570b3', '#e7298a'];   // d3.schemeDark2
let colourMode: 'analysis' | 'evidence' = 'analysis';

type Index = { datum_m: number; origin_lonlat: [number, number]; scenarios: { id: string; title: string; description: string }[] };

const $ = <T extends HTMLElement>(sel: string) => document.querySelector(sel) as T;
const getJson = async <T>(url: string): Promise<T> => {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`${url}: ${res.status}`);
    return res.json() as Promise<T>;
};

let map: AutkMap;
let plots: { profile: AutkPlot; grades: AutkPlot } | null = null;
let index: Index;
let toLocal: (p: Position) => Position;
const loaded = new Map<string, FeatureCollection>();   // layer id -> collection currently on the map
const visible = new Map(LAYERS.map(l => [l.id, l.visible]));

/** Converts a collection to local metres around the model origin (true scale near the station). */
function project(fc: FeatureCollection): FeatureCollection {
    const ring = (r: Position[]) => r.map(toLocal);
    return {
        ...fc,
        features: fc.features.map(f => {
            const g = f.geometry;
            if (g.type === 'Polygon') return { ...f, geometry: { ...g, coordinates: g.coordinates.map(ring) } };
            if (g.type === 'LineString') return { ...f, geometry: { ...g, coordinates: ring(g.coordinates) } };
            return f;
        }),
    };
}

function applyStyle(def: LayerDef, fc: FeatureCollection) {
    map.updateRenderInfo(def.id, { opacity: def.opacity, color: ColorMap.hexToRgb(def.color), isSkip: !visible.get(def.id) });
    if (colourMode === 'evidence' && def.file === 'subway_3d') {
        map.updateColorMap(def.id, { colorMap: {
            interpolator: ColorMapInterpolator.CAT_DARK2,
            domainSpec: { type: ColorMapDomainStrategy.USER, params: BASIS },
        } });
        map.updateThematic(def.id, { collection: fc, property: 'properties.basis' });
        map.updateRenderInfo(def.id, { isColorMap: true });
    } else if (def.thematic) {
        map.updateColorMap(def.id, { colorMap: {
            interpolator: def.thematic.interpolator,
            domainSpec: { type: ColorMapDomainStrategy.USER, params: def.thematic.domain },
        } });
        map.updateThematic(def.id, { collection: fc, property: `properties.${def.thematic.property}` });
        map.updateRenderInfo(def.id, { isColorMap: true });
    } else {
        map.updateRenderInfo(def.id, { isColorMap: false });
    }
}

async function loadScenario(id: string) {
    $('#status').textContent = 'Loading…';
    const files = {
        subway_3d: project(await getJson<FeatureCollection>(`/scenarios/${id}/subway_3d.geojson`)),
        surface_3d: project(await getJson<FeatureCollection>(`/scenarios/${id}/surface_3d.geojson`)),
    };
    for (const def of LAYERS) {
        if (loaded.has(def.id)) map.removeLayer(def.id);
        const fc: FeatureCollection = {
            type: 'FeatureCollection',
            features: files[def.file].features.filter(f => def.parts.includes(f.properties?.part)),
        };
        loaded.set(def.id, fc);
        map.loadCollection(def.id, { collection: fc, type: 'buildings' });
        applyStyle(def, fc);
    }
    createPlots(loaded.get('tracks')!);
    setPickLayer(($('#pick') as HTMLSelectElement).value);
    const s = index.scenarios.find(v => v.id === id)!;
    $('#scenario-desc').textContent = s.description;
    document.querySelectorAll('#stats tr[data-id], #duck tr[data-id]').forEach(tr => tr.classList.toggle('active', (tr as HTMLElement).dataset.id === id));
    $('#status').textContent = s.title;
    map.requestRender();
}

/**
 * Two autk-plot charts of the track pieces. They are built from the same collection as the map's
 * `tracks` layer, so a feature's position in the collection identifies it in all three views.
 */
function createPlots(tracks: FeatureCollection) {
    const profileEl = $('#profile'), gradesEl = $('#grades');
    profileEl.replaceChildren();
    gradesEl.replaceChildren();
    const grade = LAYERS.find(l => l.id === 'tracks')!.thematic!;

    const profile = new AutkPlot(profileEl, {
        type: 'scatterplot',
        collection: tracks,
        attributes: { axis: ['station_m', 'ele'], color: grade.property },
        labels: { axis: ['metres north of section A-B', 'rail elevation, m'], title: ' ' },
        colorMapInterpolator: grade.interpolator,
        domainSpec: { type: ColorMapDomainStrategy.USER, params: grade.domain },
        tickFormats: ['d', '.1f'],   // the default '~s' would print 0.5 as "500m"
        margins: { left: 50, right: 12, top: 10, bottom: 44 },
        width: 400, height: 230,
        events: [PlotEvent.BRUSH],
    });
    profile.setSelection([]);   // also paints the dots with the colour map

    const grades = new AutkPlot(gradesEl, {
        type: 'barchart',
        collection: tracks,
        attributes: { axis: ['grade_pct', '@transform'] },
        labels: { axis: ['slope, %', 'pieces of track'], title: ' ' },
        transform: { preset: 'binning-1d', options: { bins: 12 } },
        tickFormats: ['.1f', 'd'],
        margins: { left: 50, right: 12, top: 10, bottom: 90 },
        width: 400, height: 230,
        events: [PlotEvent.BRUSH_X],
    });

    profile.events.on(PlotEvent.BRUSH, ({ selection }) => select(selection, 'profile'));
    grades.events.on(PlotEvent.BRUSH_X, ({ selection }) => select(selection, 'grades'));
    plots = { profile, grades };
}

/** Shows the same pieces of track as selected in the 3D view and in both plots. */
function select(selection: number[], source: 'map' | 'profile' | 'grades') {
    if (source !== 'map') map.setHighlightedIds('tracks', selection);
    if (source !== 'profile') plots?.profile.setSelection(selection);
    if (source !== 'grades') plots?.grades.setSelection(selection);
    map.requestRender();
}

function setPickLayer(id: string) {
    for (const def of LAYERS) map.updateRenderInfo(def.id, { isPick: def.id === id });
}

function showInfo(feature?: Feature) {
    const dl = $('#info');
    dl.replaceChildren();
    const rows = feature ? Object.entries(feature.properties ?? {}).filter(([, v]) => v !== null && v !== '') : [['Nothing selected', '']];
    for (const [k, v] of rows) {
        const dt = document.createElement('dt'); dt.textContent = String(k);
        const dd = document.createElement('dd'); dd.textContent = typeof v === 'number' ? String(Math.round(v * 1000) / 1000) : String(v);
        dl.append(dt, dd);
    }
}

function buildLayerList() {
    const box = $('#layers');
    for (const def of LAYERS) {
        const row = document.createElement('div');
        const cb = Object.assign(document.createElement('input'), { type: 'checkbox', checked: def.visible, id: `l-${def.id}` });
        cb.addEventListener('change', () => {
            visible.set(def.id, cb.checked);
            map.updateRenderInfo(def.id, { isSkip: !cb.checked });
        });
        const sw = document.createElement('span'); sw.className = 'sw'; sw.style.background = def.color;
        const lab = Object.assign(document.createElement('label'), { htmlFor: cb.id, textContent: def.label });
        lab.style.cssText = 'margin:0;text-transform:none;letter-spacing:0;font-weight:400;font-size:13px;color:inherit';
        row.append(cb, sw, lab);
        if (def.thematic) row.append(Object.assign(document.createElement('small'), { textContent: def.thematic.label }));
        box.append(row);
    }
}

async function buildStats() {
    const table = $('#stats');
    const duck = $('#duck');
    duck.innerHTML = '<tr><th>Scenario</th><th>Ramp<br>m</th><th>Slope<br>%</th><th>Beside<br>platform m</th><th>Fits</th><th>Matches<br>section A-B</th></tr>';
    table.innerHTML = '<tr><th>Scenario</th><th>Cover<br>min</th><th>Cover<br>mean</th><th>Roof<br>exposed m²</th><th>Max track<br>grade %</th><th>Cut / fill<br>m³</th></tr>';
    for (const s of index.scenarios) {
        const st = await getJson<any>(`/scenarios/${s.id}/stats.json`);
        const c = st.cover_over_roof;
        const grade = Math.max(...Object.values(st.tracks).map((t: any) => t.max_abs_grade_pct));
        const tr = document.createElement('tr');
        tr.dataset.id = s.id;
        const cells: [string, boolean][] = [
            [s.title, false], [c.min_m.toFixed(2), c.min_m < 0], [c.mean_m.toFixed(2), c.mean_m < 0],
            [c.area_exposed_m2.toFixed(0), c.area_exposed_m2 > 0], [grade.toFixed(1), false],
            [`${st.earthwork_vs_existing.cut_m3.toFixed(0)} / ${st.earthwork_vs_existing.fill_m3.toFixed(0)}`, false],
        ];
        for (const [text, bad] of cells) {
            const td = document.createElement('td'); td.textContent = text; if (bad) td.className = 'bad';
            tr.append(td);
        }
        tr.addEventListener('click', () => { ($('#scenario') as HTMLSelectElement).value = s.id; void loadScenario(s.id); });
        table.append(tr);

        const d = st.duck_under;
        const row = document.createElement('tr');
        row.dataset.id = s.id;
        const duckCells: [string, string][] = [
            [s.title, ''], [d.ramp_length_m.toFixed(0), ''], [d.mean_grade_pct.toFixed(1), ''],
            [d.platform_overlap_m.toFixed(0), d.platform_overlap_m > 0.5 ? 'bad' : ''],
            [d.fits ? 'yes' : 'no', d.fits ? 'ok' : 'bad'],
            [d.agrees_with_section_ab ? 'yes' : 'no', d.agrees_with_section_ab ? 'ok' : 'bad'],
        ];
        for (const [text, cls] of duckCells) {
            const td = document.createElement('td'); td.textContent = text; td.className = cls;
            row.append(td);
        }
        row.addEventListener('click', () => { ($('#scenario') as HTMLSelectElement).value = s.id; void loadScenario(s.id); });
        duck.append(row);
    }
}

async function main() {
    index = await getJson<Index>('/scenarios/index.json');
    const [lon0, lat0] = index.origin_lonlat;
    const kx = 111320 * Math.cos(lat0 * Math.PI / 180), ky = 111132;
    toLocal = p => [(p[0] - lon0) * kx, (p[1] - lat0) * ky];
    $('#datum').textContent = String(index.datum_m);

    map = new AutkMap($<HTMLCanvasElement>('canvas'));
    await map.init();

    const sel = $<HTMLSelectElement>('#scenario');
    for (const s of index.scenarios) sel.add(new Option(s.title, s.id));
    sel.addEventListener('change', () => void loadScenario(sel.value));

    const pick = $<HTMLSelectElement>('#pick');
    for (const def of LAYERS) pick.add(new Option(def.label, def.id));
    pick.value = 'tracks';
    pick.addEventListener('change', () => { setPickLayer(pick.value); showInfo(); });

    map.events.on(MapEvent.PICKING, ({ selection, layerId }) => {
        const fc = loaded.get(layerId);
        const id = selection[selection.length - 1];
        map.setHighlightedIds(layerId, selection.length ? [id] : []);
        if (layerId === 'tracks') select(selection.length ? [id] : [], 'map');
        showInfo(selection.length && fc ? fc.features[id] : undefined);
    });

    $('#clear-selection').addEventListener('click', () => { select([], 'map'); map.setHighlightedIds('tracks', []); showInfo(); });
    document.querySelectorAll<HTMLElement>('#evidence-legend .sw').forEach(sw => {
        sw.style.background = BASIS_COLOURS[BASIS.indexOf(sw.dataset.basis!)];
    });
    $<HTMLSelectElement>('#colour').addEventListener('change', e => {
        colourMode = (e.target as HTMLSelectElement).value as typeof colourMode;
        $('#evidence-legend').hidden = colourMode !== 'evidence';
        for (const def of LAYERS) applyStyle(def, loaded.get(def.id)!);
        map.requestRender();
    });
    buildLayerList();
    await buildStats();
    await loadScenario(index.scenarios[0].id);
    // Autark's default camera (and its `r` shortcut) frames a city; this frames the station from the south-east.
    const resetView = () => { map.camera.resetCamera([0, 0, 1], [0, 0, 10], [150, -220, 170]); map.requestRender(); };
    $('#reset-view').addEventListener('click', resetView);
    resetView();
    map.draw();
    Object.assign(window, { map });
}

main().catch(err => { console.error(err); $('#status').textContent = `Error: ${err.message}`; });
