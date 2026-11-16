#!/usr/bin/env python3
"""Plot the long profile of one track, for one or more scenarios.

A small example of working with the model's numbers in Python. It reads profiles.csv, which has
one row for every 3 m of every track, and draws distance along the track against height.

Run:
    python scripts/plot_profile.py                              # baseline against the 5% ramp
    python scripts/plot_profile.py existing duck_under_9pct     # any scenarios you like
    python scripts/plot_profile.py --track track_nb_pleasant existing

The picture is saved as profile.png in the folder you run it from.
"""
import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent


def read_profile(scenario, track):
    """Returns the rows of one track in one scenario, as a list of dictionaries of numbers."""
    rows = []
    path = ROOT / 'data' / 'scenarios' / scenario / 'profiles.csv'
    if not path.exists():
        names = sorted(p.name for p in path.parent.parent.iterdir() if p.is_dir())
        raise SystemExit(f"No scenario called {scenario!r}. Choose from: {', '.join(names)}")
    with open(path) as file:
        for row in csv.DictReader(file):
            if row['track'] == track:
                # empty cells (no roof above this point) become None
                rows.append({key: float(value) if value else None
                             for key, value in row.items() if key != 'track'})
    if not rows:
        raise SystemExit(f"No track called {track!r} in scenario {scenario!r}.")
    return rows


def column(rows, name):
    return [row[name] for row in rows]


parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
parser.add_argument('scenarios', nargs='*', default=['existing', 'duck_under_5pct'],
                    help="scenario folder names under data/scenarios/")
parser.add_argument('--track', default='track_sb_pleasant', help="the track to plot (default: the one that ducks under)")
parser.add_argument('--output', default='profile.png', help="file to save the picture to")
args = parser.parse_args()

figure, axes = plt.subplots(figsize=(9, 4.5))

# The street and the roof come from the first scenario.
first = read_profile(args.scenarios[0], args.track)
distance = column(first, 'chainage_m')
axes.plot(distance, column(first, 'ele_surface_m'), color='#5f7f52', label='street')
axes.plot(distance, column(first, 'ele_roof_top_m'), color='#7d838c', linestyle='--', label='top of roof')

# One rail line per scenario.
for scenario in args.scenarios:
    rows = read_profile(scenario, args.track)
    steepest = max(abs(g) for g in column(rows, 'grade_pct'))
    axes.plot(column(rows, 'chainage_m'), column(rows, 'ele_rail_m'), linewidth=2,
              label=f"rail, {scenario} (steepest {steepest:.1f}%)")

axes.set_xlabel('distance along the track, m')
axes.set_ylabel('elevation, m')
axes.set_title(args.track)
axes.grid(True, color='#e6e5e0')
axes.legend()
figure.tight_layout()
figure.savefig(args.output, dpi=150)
print(f"saved {args.output}")
