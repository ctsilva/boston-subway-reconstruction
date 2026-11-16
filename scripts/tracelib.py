"""Shared helpers for the digitized trace (pixel space)."""
import json, math, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_features():
    with open(os.path.join(ROOT, 'trace', 'features.json')) as fh:
        return json.load(fh)

def _catmull_rom(pts, step=2.0, alpha=0.5):
    """Centripetal Catmull-Rom through pts, sampled about every `step` pixels."""
    if len(pts) < 3:
        return [tuple(p) for p in pts]
    P = [tuple(p) for p in pts]
    ext = [(2 * P[0][0] - P[1][0], 2 * P[0][1] - P[1][1])] + P + [(2 * P[-1][0] - P[-2][0], 2 * P[-1][1] - P[-2][1])]
    out = [P[0]]
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        def tj(ti, a, b):
            return ti + max(math.hypot(b[0] - a[0], b[1] - a[1]), 1e-6) ** alpha
        t0 = 0.0; t1 = tj(t0, p0, p1); t2 = tj(t1, p1, p2); t3 = tj(t2, p2, p3)
        n = max(1, int(math.hypot(p2[0] - p1[0], p2[1] - p1[1]) / step))
        for k in range(1, n + 1):
            t = t1 + (t2 - t1) * k / n
            def lerp(a, b, ta, tb):
                w = (t - ta) / (tb - ta)
                return (a[0] + (b[0] - a[0]) * w, a[1] + (b[1] - a[1]) * w)
            a1 = lerp(p0, p1, t0, t1); a2 = lerp(p1, p2, t1, t2); a3 = lerp(p2, p3, t2, t3)
            b1 = lerp(a1, a2, t0, t2); b2 = lerp(a2, a3, t1, t3)
            out.append(lerp(b1, b2, t1, t2))
    return out

def densify(feature, step=2.0):
    """Pixel-space vertex list for a feature (spline-sampled when 'smooth')."""
    pts = feature['points']
    if feature.get('smooth'):
        return _catmull_rom(pts, step)
    return [tuple(p) for p in pts]
