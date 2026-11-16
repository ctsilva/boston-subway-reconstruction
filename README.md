# Boylston St. station, 1897: a 3D model of the station and its duck-under

*This model was created for Claudia Wysocky's project at Boston University (the VANTAGE research
initiative), which studies the engineering of the early Boston subway and the duck-under at
Boylston Street station.*

It turns one historical drawing into a 3D model you can explore in a web browser, with linked
plots beside it, and uses it to look at two questions:

> **1. How steep is the duck-under, and what other inclinations would have fitted?**
> The southbound track to Pleasant Street dives under the Boylston Street tracks. The model
> measures that ramp and tests alternatives against the space available.
>
> **2. How would the station fare if the street above it were graded differently?**
> Lowered, raised, or given a different slope: how much earth would be left over the roof?

Throughout, the model keeps **what the drawing shows** apart from **what had to be guessed**. One
switch in the viewer colours every part by how well it is supported
([section 4](#4-fact-and-hypothesis)).

The drawing is the plan of Boylston Street station on the Tremont Street Subway (opened 1897),
published by Geo. H. Walker & Co.:

![The source drawing](boylston_station_plan_1897.png)

And this is the model built from it, shown in [Autark](https://github.com/urban-toolkit/autark),
a toolkit for urban visual analytics. The roof and the ground are switched off so you can see
inside: platforms (yellow), stairs (orange), walls (grey), and tracks coloured by how steep they
are. The dark red track is the ramp of the duck-under. The plots on the left show the same tracks.

![Inside the model](docs/viewer_interior.png)

You do not need to know how to program to run this. Follow the steps below in order.

## Contents

1. [What you need](#1-what-you-need)
2. [Set it up, step by step](#2-set-it-up-step-by-step)
3. [Using the viewer](#3-using-the-viewer)
4. [Fact and hypothesis](#4-fact-and-hypothesis)
5. [Results: the duck-under](#5-results-the-duck-under)
6. [Results: grading the street](#6-results-grading-the-street)
7. [Adding your own scenario](#7-adding-your-own-scenario)
8. [Using the numbers in MATLAB or Excel](#8-using-the-numbers-in-matlab-or-excel)
9. [How the model was made](#9-how-the-model-was-made)
10. [What is in each folder](#10-what-is-in-each-folder)
11. [Using the data in your own Autark code](#11-using-the-data-in-your-own-autark-code)
12. [What the model cannot tell you](#12-what-the-model-cannot-tell-you)
13. [Troubleshooting](#13-troubleshooting)
14. [Glossary](#14-glossary)
15. [Credits](#15-credits)

---

## 1. What you need

| You need | Why | How to check |
| :--- | :--- | :--- |
| **A recent Chrome or Edge** | The viewer draws with WebGPU, which Chrome and Edge have switched on by default. Firefox and Safari may not work. | Open `chrome://gpu` and look for "WebGPU: Hardware accelerated". |
| **Node.js** (version 22 or newer) | Runs the small web server for the viewer. | Type `node --version` in a terminal. |
| **Python 3** (3.10 or newer) | Only needed if you want to rebuild the data or add a scenario. | Type `python3 --version`. |
| **An internet connection, once** | Step 1 downloads the Autark toolkit and one other tool (about 70 MB). | |

A "terminal" is the app called **Terminal** on a Mac, or **PowerShell** on Windows. Steps 1 and 2
are the same on every system. The Python commands in Step 3 are written for Mac and Linux; on
Windows, replace `.venv/bin/` with `.venv\Scripts\`.

## 2. Set it up, step by step

### Step 1. Download what the viewer needs

Open a terminal, go to the `viewer` folder inside this project, and install:

```bash
cd boston-subway-reconstruction/viewer
npm install
```

This downloads Autark (the published packages `autk-map`, `autk-plot` and `autk-core`) and Vite,
a small web server, into a folder called `node_modules`. It takes about a minute and you do it
once. You do not need Autark's source code.

### Step 2. Start the viewer

The data is already built and included. In the same folder:

```bash
npm run dev
```

You should see something like:

```
  VITE v8.3.8  ready in 257 ms
  ➜  Local:   http://localhost:5199/
```

Leave that terminal window open. Open **http://localhost:5199/** in Chrome. After a second or two
you should see this:

![What you should see first](docs/viewer_overview.png)

The grey box is the subway seen from the south-east, with its roof coloured blue. The wire grid is
the street and the Common above it. The left panel has the controls and two plots.

To stop the viewer, go back to the terminal and press `Ctrl` + `C`. Next time, only Step 2 is
needed.

### Step 3 (optional). Rebuild the data

You only need this if you change the tracing, the measurements, or the list of scenarios.

```bash
cd boston-subway-reconstruction
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/build.py
```

The first two lines create a private Python environment in a folder called `.venv` and install
four libraries into it. You do that once. The last line rebuilds everything under `data/` in a few
seconds and prints two summary lines per scenario. Then reload the page in Chrome.

## 3. Using the viewer

### Moving around

| To do this | Do this |
| :--- | :--- |
| Slide the view | Drag with the left mouse button |
| Turn and tilt the view | Hold `Shift` and drag |
| Zoom | Scroll the mouse wheel |
| Go back to the starting view | Press the **Reset view** button in the left panel |
| Read the numbers for one piece | Double-click it (see "Double-click to inspect" below) |

Do not press the `r` key to reset. That is Autark's own shortcut, and it zooms out to the size of a
whole city, which makes the station a speck. If that happens, press **Reset view**.

### Looking inside

The **Layers** list in the left panel switches parts of the model on and off. Untick boxes to peel
the station open:

| Untick | You see |
| :--- | :--- |
| Roof slab, Ground (wireframe) | The inside of the station, as in the picture at the top of this page. |
| ...and Walls | The floor, platforms and stairs standing free. The floor steps down along the duck-under ramp, and the water conduit (blue-green) passes underneath. |
| ...and Floor, Platforms, Stairs | Only the tracks. The Pleasant St track dips below the others and passes under the two that turn west. |

Without the walls, looking from the west at the ramp going down beside the platform:

![Roof and walls removed](docs/viewer_no_walls.png)

Only the tracks, with the conduit and the passage under the tracks:

![Tracks only](docs/viewer_tracks_only.png)

### The colours

Three layers are coloured by a number instead of having one fixed colour:

| Layer | Coloured by | How to read the colour |
| :--- | :--- | :--- |
| Tracks | Slope, in percent | **Pale yellow** = flat. **Dark red** = steep (9% or more). |
| Roof slab | Cover, in metres | **Blue** = earth on top of the roof (darker = more). **White** = none. **Red** = the roof would stick out above the ground. |
| Ground (wireframe) | Cut or fill, in metres | **Brown** = earth removed. **Green** = earth added. **Grey/white** = unchanged. |

The ground is drawn as a wire grid so that you can see the subway underneath it. "Ground (solid)"
draws it as a full surface, coloured by elevation, but it hides everything below.

Autark shows one colour scale in the bottom-right corner. It belongs to whichever layer was loaded
last, so use the table above to read the others.

### The plots, and how they are linked to the 3D view

The two plots in the left panel are drawn by Autark's plotting module (`autk-plot`) from the same
data as the 3D tracks. Every dot or bar stands for 3 m pieces of track.

- **Track profile.** Each dot is one piece of track: left to right is how far north it is, up and
  down is the height of its rail. This is the side view an engineer would draw. The long diagonal
  line of dark red dots is the duck-under ramp, dropping about 4 m.
- **How much track at each slope.** A bar chart counting pieces of track by slope. Most of the
  station is within 2% of level; the short bars far to the left are the ramp.

The plots and the 3D view are linked both ways:

- **Drag a box over dots** in the profile, or **drag across bars** in the bar chart, and those
  pieces of track light up in blue in the 3D view and in the other plot.
- **Double-click a piece of track** in the 3D view and it is marked in both plots, and its numbers
  appear lower down in the panel. The tracks are narrow, so zoom in first and aim for the middle
  of the track.
- **Clear selection** removes the highlight.

Here the ramp was selected by dragging a box over it in the profile plot (the grey box). The same
pieces are lit in the 3D view:

![Selecting in the plot highlights in 3D](docs/viewer_linked_plots.png)

And the other way round: one piece of the ramp was double-clicked in the 3D view (it turns blue),
and the same piece is marked in the profile and in the bar chart.

![Double-clicking in 3D marks the plots](docs/viewer_pick_track.png)

### The rest of the left panel

**Scenario.** Choose which version of the station to look at. The model reloads in about a second.
There are nine to start with:

| Scenario | What it means |
| :--- | :--- |
| Existing grade | Today's ground, with the subway as drawn. This is the baseline. |
| Street lowered 1 m | 1 m of earth is cut away over the subway. |
| Street raised 1 m | 1 m of earth is added over the subway. |
| Uniform grade, no cross slope | The ground over the subway is flattened side to side, so it no longer rises toward the Common. |
| 3% street grade | The street is made to climb 3 m for every 100 m going north. |
| 3% street grade, subway re-profiled | The same street, but the subway is rebuilt to follow it at its original depth. |
| Duck-under at 5% | The ramp is made gentler, 5%, and still reaches full depth where the drawing shows it. |
| Duck-under at 9% | The ramp is made steeper and shorter. |
| Duck-under, longest ramp that fits | The ramp is stretched as far as the plan allows. |

**Colour by.** Switches between the analysis colours above and the evidence colours of
[section 4](#4-fact-and-hypothesis).

**Double-click to inspect.** Pick a layer in this list, then double-click a piece of that layer in
the 3D view. Its numbers appear in the panel: for a piece of track, for example, its rail height,
its depth below the street, its slope, and how well it is supported by the drawing.

**The duck-under ramp** and **Cover over the roof.** Two tables with one row per scenario, at the
bottom of the panel. Red marks a problem. Click a row to switch to that scenario.

![The two tables](docs/viewer_tables.png)

## 4. Fact and hypothesis

A 3D model looks equally solid everywhere, including where it is a guess. To keep the two apart,
every piece of the model carries a label, `basis`, saying how its **level** (its height) is known.
Positions on the map are all traced from the plan.

| Label | Meaning | Where |
| :--- | :--- | :--- |
| **Measured** | Level scaled off a cross section on the drawing. | The main station box: tracks, platforms, floor, roof, walls. |
| **Inferred** | Level follows from a stated rule and a measured point. | The duck-under ramp and its level run (anchored on section A-B), and the two branches leaving the station (assumed to follow the street). |
| **Assumed** | The drawing gives no level. | The duck-under south of the crossing, the water conduit, the passage under the tracks. |
| **Hypothetical** | An alternative that was never built. | Whatever a scenario changes: an alternative ramp, or a re-profiled subway. |

In the viewer, set **Colour by** to **Evidence**. A legend appears under the menu:

![Coloured by evidence](docs/viewer_evidence.png)

Green is measured, purple is inferred, orange is assumed. Now choose the scenario **Duck-under at
5%**: the ramp turns pink, because that ramp is hypothetical, while everything else keeps its
colour.

![A hypothetical ramp, in pink](docs/viewer_duck_under_5pct.png)

The same label is in the data files (the `basis` property of every feature), so it travels with
the model into any other tool. The ground is not labelled: it is today's ground, measured, but it
is standing in for the ground of 1897.

## 5. Results: the duck-under

The duck-under is called the **sub-subway** on the drawing. It carries the southbound track to
Pleasant Street down and underneath the two Boylston Street tracks, so trains do not cross each
other on the level.

Three things on the drawing limit the ramp that leads down to it:

1. **It cannot start before the southbound platform ends**, because cars stop at that platform on
   this track.
2. **It must be at full depth before it passes under the Boylston Street tracks**: 13.7 ft (4.2 m)
   below the main rail, which leaves the 12.8 ft of headroom drawn in section A-B.
3. **Section A-B shows it already at full depth** well before that crossing.

Measured along the track, there are 81 m between the end of the platform and the crossing, but
only 62 m between the end of the platform and section A-B.

| Scenario | Ramp length (m) | Average slope | Runs beside the platform for (m) | Fits the plan | Agrees with section A-B |
| :--- | ---: | ---: | ---: | :---: | :---: |
| As modelled from the drawing | 62 | 6.8% | 0 | yes | yes |
| Duck-under at 5% | 84 | 5.0% | 22 | **no** | yes |
| Duck-under at 9% | 46 | 9.0% | 0 | yes | yes |
| Longest ramp that fits | 81 | 5.1% | 0 | yes | **no** |

What this says:

- **If section A-B is right, the ramp averages at least 6.8%.** That is the gentlest ramp that
  starts at the end of the platform and reaches the drawn depth at A-B. Starting any later makes it
  steeper.
- **A 5% ramp does not fit.** It would have to begin 22 m back, alongside the platform, where the
  track has to be level with the platform.
- **The gentlest ramp the plan has room for at all is about 5.1%**, and only by staying shallow
  past section A-B, which contradicts the drawing.

"Average slope" is the drop divided by the ramp length. The steepest 3 m piece is steeper (8.8% as
modelled), because the station floor itself slopes slightly and the ramp eases in and out.

Treat these as the model's findings, not as history: they rest on where the platform edge ends and
where section A-B falls on a small scan. See [section 12](#12-what-the-model-cannot-tell-you).

## 6. Results: grading the street

**Cover** is the thickness of earth between the top of the roof slab and the street. Positive cover
is good. Zero or negative cover means the roof would be at or above street level.

| Scenario | Least cover (m) | Average cover (m) | Roof exposed (m²) | Tunnel slope | Earth cut / filled (m³) |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Existing grade | -0.24 | 0.46 | 152 | 0.74% | 0 / 0 |
| Street lowered 1 m | -1.24 | -0.54 | 5647 | 0.74% | 17012 / 0 |
| Street raised 1 m | 0.76 | 1.46 | 0 | 0.74% | 0 / 17012 |
| Uniform grade, no cross slope | -0.08 | 0.47 | 1155 | 0.74% | 3318 / 4170 |
| 3% street grade | -1.04 | 1.33 | 1032 | 0.74% | 4383 / 17744 |
| 3% street grade, subway re-profiled | -0.41 | 0.40 | 445 | 2.85% | 4383 / 17744 |

The whole roof is 5647 m². With **3% street grade** chosen, the roof turns red at the south end
(bottom left) and dark blue at the north end, and the wire grid shows where earth is removed
(brown) and added (green):

![3% street grade](docs/viewer_grade_3pct.png)

What this says:

- **The station was built very close to the surface.** The drawing shows only about 0.25 m (10
  inches) of earth over the roof on the Tremont Street side. Lowering the street by 1 m would
  expose the entire roof.
- **The earth over the roof comes mostly from the Common.** The ground rises from Tremont Street
  toward the Common. Flatten that rise and a fifth of the roof loses its cover.
- **Changing the street's slope helps one end and hurts the other**, unless the tunnel is rebuilt
  to match, and then the cars have to climb the steeper slope.

**One caution.** The baseline itself shows 152 m² of roof "exposed". That is not real. It is the
size of the model's own uncertainty, about ±0.3 m up or down. Compare each scenario against the
baseline; do not read a single number on its own.

## 7. Adding your own scenario

Scenarios are listed in `config/scenarios.json`, a plain text file. Open it in any text editor.
Each scenario is one entry between `{` and `}`.

**To try another ramp slope**, say 7.5%, add this after the opening `"scenarios": [` line:

```json
{"id": "duck_under_7_5pct", "title": "Duck-under at 7.5%", "description": "Hypothetical 7.5% ramp.", "surface": {"type": "existing"}, "duck_under": {"grade_pct": 7.5, "full_depth_at": "section_ab"}},
```

**To try another street grading**, say lowered by half a metre:

```json
{"id": "lowered_half", "title": "Street lowered 0.5 m", "description": "Ground cut 0.5 m over the subway.", "surface": {"type": "offset", "dz_m": -0.5}},
```

Mind the comma at the end: every entry except the last one needs it. Then rebuild
([Step 3](#step-3-optional-rebuild-the-data)) and reload the page. The new scenario appears in the
list and in both tables.

The parts of an entry:

| Part | Meaning |
| :--- | :--- |
| `id` | A short name with no spaces. It becomes a folder name under `data/scenarios/`. |
| `title`, `description` | What the viewer shows. |
| `surface` | The ground (see below). Use `{"type": "existing"}` to leave it alone. |
| `duck_under` | Optional. Replaces the ramp (see below). |
| `structure` | Optional. `"structure": "follow_surface"` rebuilds the subway at its original depth below a regraded street. |

Settings for `duck_under`:

| Setting | Meaning |
| :--- | :--- |
| `grade_pct` | The average slope of the ramp, in percent. Leave it out to start the ramp at the end of the platform. |
| `full_depth_at` | `"section_ab"`: full depth where the drawing shows it. `"crossing"`: full depth as late as possible, just before passing under the Boylston St tracks. |

Three kinds of `surface`:

| `"type"` | What it does | Settings |
| :--- | :--- | :--- |
| `"existing"` | Today's ground, unchanged. | none |
| `"offset"` | Raises or lowers the ground. | `dz_m`: metres, negative to lower. |
| `"plane"` | Replaces the ground with a flat, tilted street. | `grade_long_pct`: climb going north, in percent (`null` keeps today's average). `grade_cross_pct`: climb toward the Common, in percent. `dz_m`: optional shift up or down. |

A grading changes the ground over the subway and for 12 m around it, then blends back into today's
ground over the next 15 m. To change those distances, add `"reach_m"` and `"blend_m"` to `surface`.

The measurements themselves (the 13.7 ft drop, the headroom, where the platform ends) are in
`config/model.json`.

## 8. Using the numbers in MATLAB or Excel

Every scenario has a folder under `data/scenarios/` with two files of numbers:

- **`profiles.csv`** opens in Excel or MATLAB. One row for every 3 m of every track: the rail
  height, the roof height, the ground height, the depth, the cover and the slope.
- **`stats.json`** holds the totals shown in the viewer's two tables, and more: the ramp length,
  its slope, the headroom at the crossing, the rise of each stair.

To draw the long profile of the duck-under track in MATLAB:

```matlab
T = readtable('data/scenarios/existing/profiles.csv');
t = T(strcmp(T.track, 'track_sb_pleasant'), :);     % the track that ducks under

plot(t.chainage_m, t.ele_surface_m, t.chainage_m, t.ele_roof_top_m, t.chainage_m, t.ele_rail_m)
legend('street', 'top of roof', 'rail'); xlabel('distance along the track, m'); ylabel('elevation, m')
```

To compare two ramps, read the same file from two scenario folders (`existing` and
`duck_under_5pct`, say) and plot both `ele_rail_m` columns. The track names are
`track_sb_pleasant`, `track_sb_boylston`, `track_nb_boylston`, `track_nb_pleasant`,
`crossover_mid` and `crossover_north`.

## 9. How the model was made

### Tracing the drawing

Every line that matters was traced by hand as a chain of points: the centerline of each track, the
walls, the two platforms, the stairs, the passage under the tracks, the water conduit, the curbs
and the building lines. Curves were smoothed between the points. The tracing is stored in
`trace/features.json`.

The coloured lines below are the tracing laid over the drawing: tracks in red, walls in blue,
platforms in green, stairs in orange, curbs in magenta.

![The tracing over the drawing](docs/trace_overlay.png)

### Placing it on the real map

The Green Line still runs through this tunnel. So the traced tracks were matched to the Green Line
tracks in OpenStreetMap, the free world map. The computer looked for the rotation, size and
position that put one on top of the other.

It is a close match: the typical gap is 0.3 m, and the scale it found agrees with the scale bar
printed on the drawing to within 0.2%. In the picture below, today's map is drawn over the 1897
plan. Today's tracks (red) and platforms (green) fall on the old ones, today's station entrances
(magenta circles) fall on the 1897 stairs, and today's buildings (orange) fall on the old blocks.

![Today's map over the 1897 plan](docs/osm_overlay.png)

### Getting the heights

The plan is flat. The heights come from the two cross sections drawn at the top of the sheet, which
were measured with their own scale bar:

![The cross sections on the drawing](docs/cross_sections.png)

| Measured | Value |
| :--- | ---: |
| Top of rail below the Tremont Street side, at section A-B | 17.2 ft (5.2 m) |
| Top of rail below the Tremont Street side, at section C-D | 18.3 ft (5.6 m) |
| Clear height above the rail | 14.5 ft (4.4 m) |
| Roof and floor slab thickness | 2.5 ft (0.76 m) |
| Sub-subway rail below the main rail | 13.7 ft (4.2 m) |
| Clear height in the sub-subway | 12.8 ft (3.9 m) |

The sub-subway is the lower box at the right of section A-B, with a car in it.

### The ground

There is no survey of the 1897 ground in the drawing, so today's ground is used in its place:
120 spot heights from the U.S. Geological Survey's 3DEP elevation data.

### Putting it together

`scripts/build.py` reads the tracing, the measurements and the list of scenarios, and writes the 3D
model for each scenario as stacks of simple blocks. Every number it uses is in `config/model.json`,
with a note saying whether it was measured or assumed.

## 10. What is in each folder

| Path | What it is |
| :--- | :--- |
| `boylston_station_plan_1897.png` | The scanned drawing. |
| `trace/features.json` | The tracing, in positions on the scan (pixels). |
| `config/model.json` | The map placement and every height, each marked measured or assumed. |
| `config/scenarios.json` | The list of scenarios. **This is the file to edit.** |
| `scripts/build.py` | Builds everything in `data/`. |
| `scripts/georeference.py` | Redoes the match to OpenStreetMap and redraws `docs/osm_overlay.png`. |
| `scripts/overlay.py` | Redraws `docs/trace_overlay.png`. |
| `viewer/` | The web page: the 3D view and the plots. `package.json` lists the Autark version it uses (4.1.1). |
| `data/plan_1897.geojson` | The flat plan on the real map. |
| `data/scenarios/<name>/tracks.geojson` | The tracks in 3D, in 3 m pieces, each with height, depth, cover, slope and `basis`. |
| `data/scenarios/<name>/subway_3d.geojson` | The structure as blocks: roof, walls, floor, platforms, tracks, stairs, passage, conduit. |
| `data/scenarios/<name>/surface_3d.geojson` | The ground, as a surface and as a wire grid. |
| `data/scenarios/<name>/stats.json`, `profiles.csv` | The numbers. |
| `data/osm/` | The piece of OpenStreetMap used for the match. |
| `data/dem/` | The ground heights from the USGS. |
| `docs/` | The pictures in this README. |

The `.geojson` files are a standard map format. They open in free tools such as
[QGIS](https://qgis.org) or [geojson.io](https://geojson.io) (the smaller ones), as well as Autark.

The tracks are described the way OpenStreetMap describes roads, as centerlines with labels:
`railway=tram`, `tunnel=yes`, `layer=-1` (or `-2` for the sub-subway), `ele` (height), and
`incline` (slope). Think of the subway as a road that happens to be underground.

## 11. Using the data in your own Autark code

This section is for people writing code. `subway_3d.geojson` and `surface_3d.geojson` load as
ordinary Autark `buildings` layers, and `autk-plot` draws plots from the same collection. Install
the packages with `npm install @urban-toolkit/autk-map @urban-toolkit/autk-plot`.

```ts
map.loadCollection('tracks', { collection: tracks, type: 'buildings' });
map.updateThematic('tracks', { collection: tracks, property: 'properties.abs_grade_pct' });
map.updateRenderInfo('tracks', { isColorMap: true, isPick: true });

const profile = new AutkPlot(div, {
    type: 'scatterplot', collection: tracks,
    attributes: { axis: ['station_m', 'ele'], color: 'abs_grade_pct' },
    events: [PlotEvent.BRUSH],
});

// link the two: a feature's position in the collection identifies it in both
profile.events.on(PlotEvent.BRUSH, ({ selection }) => map.setHighlightedIds('tracks', selection));
map.events.on(MapEvent.PICKING, ({ selection }) => profile.setSelection(selection));
```

`viewer/src/main.ts` is a complete, short example. Three things to know:

- **Heights are measured from a level 8 m below sea level**, not from sea level. Autark draws on a
  flat plane at height zero and the subway is below ground, so everything is lifted to stay above
  that plane. `ele_top` and `ele_bottom` on each block hold the true heights.
- **Scale.** The viewer converts the coordinates to plain metres so the model has true
  proportions. In Autark's default projection (EPSG:3395) the map is stretched 1.353 times at
  Boston's latitude and heights are not, so multiply `height` and `min_height` by 1.353 there.
- **See-through layers.** Autark does not blend one 3D layer over another, so a half-transparent
  ground will not show the subway beneath it. Use the `ground_grid` wireframe, as the viewer does.

## 12. What the model cannot tell you

- **It is good to about ±0.3 m vertically.** Today's ground is not the 1897 ground, and the tunnel
  is modelled as following the smoothed street, which the real one only roughly does. Use the model
  to compare scenarios with each other, not to read off exact depths.
- **The duck-under results depend on two readings of a small scan:** where the southbound platform
  edge ends, and where section A-B crosses the track. Moving either by 5 m changes the 6.8% by
  about half a percentage point. A sharper scan, or a profile drawing of the sub-subway if one
  survives in the archives, would settle it.
- **Some heights are guesses**, marked "assumed" or "inferred" in the viewer: how the sub-subway
  climbs back up to the south, the levels along the two branches leaving the station, the depth of
  the water conduit, and the headroom of the passage under the tracks. They are listed under
  `"assumptions"` in `config/model.json` and can be changed there.
- **Slopes are drawn as small steps**, 2 to 3 m long, because the model is made of blocks.
- **Not traced:** the footpaths on the Common, the turnstiles, the ticket booths, the columns, and
  the detail of the building fronts.
- **The scan is small** (972 × 596 pixels), so a traced line can be off by about half a metre.
- **This is a geometric model, not an engineering one.** It measures slopes, clearances and the
  earth over the roof. It does not check whether a car could climb the ramp or whether the
  structure could carry the load.

## 13. Troubleshooting

**The page is blank, or the 3D area is empty.**
Your browser probably does not have WebGPU. Use a current Chrome or Edge, and check
`chrome://gpu`. Then press `F12`, open the "Console" tab and look for a message in red.

**I see the panel but only a tiny dot where the model should be.**
The view is zoomed out to city scale. Press **Reset view**.

**`npm run dev` says "vite: command not found", or the page says "Failed to resolve import
@urban-toolkit/autk-map".**
Step 1 has not been run in this folder, or it did not finish. Run `npm install` in the `viewer`
folder again and check that it ends without errors.

**`npm install` fails.**
Check your internet connection and that `node --version` shows 22 or newer.

**The terminal shows a different address, such as `http://localhost:5200/`.**
Port 5199 was busy, most likely because the viewer is already running in another terminal window.
Open the address the terminal shows.

**Dragging in a plot selects nothing.**
Start the drag inside the plot area, on or next to the dots or bars, and release inside it too.

**`python3 -m venv` or `pip install` fails.**
Check `python3 --version` shows 3.10 or newer. If a library refuses to install, a slightly older
Python (3.12 or 3.13) is the safest choice.

**I edited `scenarios.json` and the build fails with "JSONDecodeError".**
There is a typo in the file, most often a missing or extra comma, or a missing quote. The error
message gives the line number.

**My new scenario does not show up.**
Rebuild the data ([Step 3](#step-3-optional-rebuild-the-data)), then reload the page.

## 14. Glossary

| Word | Meaning |
| :--- | :--- |
| **Duck-under** | A track that dips beneath other tracks so trains do not cross on the level. The 1897 drawing calls this one the **sub-subway**. |
| **Grade / inclination / slope** | How steeply a track or street climbs. A 5% grade climbs 5 m in 100 m. |
| **Grading** | Shaping the surface of a street. "Regrading" changes its height or slope. |
| **Long profile** | A side view of a track: distance along it against height. |
| **Headroom / clear height** | The free height above the rail, under the roof or slab above. |
| **Cover** | The thickness of earth between the top of the tunnel roof and the street. |
| **Cut and fill** | Earth removed (cut) and earth added (fill) to reach a new grading. |
| **Cross slope** | The slope across the street, here from Tremont Street up toward the Common. |
| **Cut-and-cover** | How this subway was built: dig a trench from the street, build the tunnel in it, cover it over. It is why the roof is so close to the surface. |
| **Chainage** | Distance measured along a track from its start. |
| **Georeferencing** | Working out where a drawing sits on the real map. |
| **GeoJSON** | A common text format for map shapes. |
| **OpenStreetMap (OSM)** | A free, editable map of the world. |
| **NAVD88** | The standard zero for heights in North America, close to mean sea level. |
| **WebGPU** | The browser feature Autark uses to draw 3D quickly. |

## 15. Credits

- Created for Claudia Wysocky's project at Boston University (VANTAGE).
- Drawing: plan of Boylston St. station, Tremont Street Subway, Geo. H. Walker & Co., Boston.
- Map data: © OpenStreetMap contributors, under the Open Database License.
- Ground elevations: U.S. Geological Survey, 3D Elevation Program.
- Viewer: [Autark](https://github.com/urban-toolkit/autark) (`autk-map` for 3D, `autk-plot` for the plots).
