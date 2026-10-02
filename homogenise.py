"""
homogenise.py -- standalone, copy-paste-able version of SanPyCAD 2D
Sketch's "Homogenise" tool.

Resamples a path (open polyline or closed loop) to evenly spaced points
`pitch` apart, WITHOUT losing the path's own original vertices (a plain
even-spacing resample replaces every point with a fresh interpolation,
so real corners get rounded away) -- and, if you give it other shapes to
check against, includes every real crossing point with them too.

No external dependencies -- just the standard library (math). This file
is fully self-contained: it does not need SanPyCAD's own ocad.py/
geom_ops.py to run.

Usage:
    from homogenise import homogenise

    rect = [[0, 0], [10, 0], [10, 10], [0, 10]]
    pts = homogenise(rect, pitch=2.0, closed=True)
    # -> evenly-spaced points 2 apart, PLUS all 4 original corners.

    square_a = [[0, 0], [10, 0], [10, 10], [0, 10]]
    square_b = [[5, 5], [15, 5], [15, 15], [5, 15]]
    pts = homogenise(
        square_a, pitch=3.0, closed=True,
        other_shapes=[{"points": square_b, "closed": True}],
    )
    # -> also includes the 2 real points where square_a's boundary
    #    actually crosses square_b's.
"""

import math


# ---------------------------------------------------------------------
# Path helpers (segment list, arc-length position of an arbitrary point,
# segment-segment intersection). Small and self-contained on purpose --
# every point homogenise() deals with (vertices, resampled fill points,
# intersections) is checked against the SAME path via the same math.
# ---------------------------------------------------------------------

def _path_segments(points, closed):
    n = len(points)
    rng = n if closed else n - 1
    return [(points[i], points[(i + 1) % n]) for i in range(rng)]


def _arc_length_params(points, closed):
    segs = _path_segments(points, closed)
    cum = [0.0]
    for a, b in segs:
        cum.append(cum[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    return cum


def _nearest_param_on_path(points, closed, click):
    """Arc-length distance, along `points`' own path, of whichever point
    on that path lies closest to `click`. Used to position every point
    from every source (original vertices, resampled fill, intersections)
    on one shared number line so they can be merged in order."""
    segs = _path_segments(points, closed)
    cum = _arc_length_params(points, closed)
    best = None
    for i, (a, b) in enumerate(segs):
        vx, vy = b[0] - a[0], b[1] - a[1]
        L2 = vx * vx + vy * vy
        if L2 < 1e-12:
            continue
        t = ((click[0] - a[0]) * vx + (click[1] - a[1]) * vy) / L2
        t = max(0.0, min(1.0, t))
        fx, fy = a[0] + vx * t, a[1] + vy * t
        d = math.hypot(click[0] - fx, click[1] - fy)
        param = cum[i] + t * math.hypot(vx, vy)
        if best is None or d < best[0]:
            best = (d, param)
    if best is None:
        raise ValueError("homogenise: degenerate path (all-coincident points)")
    return best[1]


def _seg_intersect(p1, p2, p3, p4):
    """Point where segment p1-p2 crosses segment p3-p4, or None."""
    x1, y1 = p1; x2, y2 = p2; x3, y3 = p3; x4, y4 = p4
    d = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(d) < 1e-12:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / d
    u = ((x1 - x3) * (y1 - y2) - (y1 - y3) * (x1 - x2)) / d
    if -1e-9 <= t <= 1 + 1e-9 and -1e-9 <= u <= 1 + 1e-9:
        return [x1 + t * (x2 - x1), y1 + t * (y2 - y1)]
    return None


# ---------------------------------------------------------------------
# Even-spacing resample. This is a plain, dependency-free arc-length
# resample -- the same job SanPyCAD's own ocad.homogenise() does
# (equidistant_path()/equidistant_pathc() there), reimplemented here so
# this file doesn't need the rest of SanPyCAD to run. Like that original,
# it only guarantees the FIRST point (and, for an open path, the LAST
# point) land exactly on the input -- everything else is a fresh
# interpolation, which is exactly why homogenise_merge() below exists.
# ---------------------------------------------------------------------

def resample_evenly(points, pitch, closed):
    if pitch <= 0:
        raise ValueError("pitch must be positive")
    if len(points) < 2:
        raise ValueError("need at least 2 points to resample")

    segs = _path_segments(points, closed)
    total_len = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in segs)
    if total_len < 1e-9:
        return list(points)

    out = [list(points[0])]
    d = pitch
    while d < total_len - 1e-9:
        remaining = d
        for a, b in segs:
            seg_len = math.hypot(b[0] - a[0], b[1] - a[1])
            if remaining <= seg_len:
                t = remaining / seg_len if seg_len > 1e-12 else 0.0
                out.append([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t])
                break
            remaining -= seg_len
        d += pitch

    if not closed:
        out.append(list(points[-1]))
    return out


# ---------------------------------------------------------------------
# The merge: combines the resample above with the path's own original
# points, and (optionally) real crossing points with other shapes.
# ---------------------------------------------------------------------

def homogenise_merge(original_points, closed, resampled_points, other_shapes=None, dedupe_frac=1e-3):
    """
    Combines an evenly-spaced resample of `original_points` with two more
    point sources so nothing meaningful about the shape gets lost by the
    resample:

    - `original_points` itself. A plain even-spacing resample only ever
      keeps the path's very first point as-is (and, for an OPEN path, its
      very last one too) -- every OTHER point is a fresh arc-length
      interpolation with no reason to land back on an original vertex.
      Without this, a polyline with real corners loses them: homogenising
      a rectangle gives back a rounded-looking dense point cloud, not a
      rectangle with evenly-filled edges.

    - real crossings with `other_shapes` (each {"points": [...],
      "closed": bool}), if given -- so a homogenised shape's own point set
      stays exactly aligned with wherever it actually meets a neighbour it
      was homogenised alongside (useful before a Trim/Difference/
      Intersection-style operation).

    Every point from any of the 3 sources gets positioned by its arc-
    length distance along `original_points`' own path via
    _nearest_param_on_path() -- exact for all 3, since every point from
    every source genuinely lies ON that path already (original vertices;
    resampled points, which are linear interpolations WITHIN the path's
    own segments; and real segment-segment intersections). Sorting by
    that shared position stitches all 3 sources into one coherent path in
    order; near-duplicates (within a small fraction of the shape's own
    total length) are then collapsed, keeping whichever source was listed
    FIRST -- original vertices and intersection points ahead of the
    resampled fill -- so a corner or a crossing stays exactly where it is
    instead of being silently replaced by a nearby but not-quite-
    coincident resampled point.
    """
    segs = _path_segments(original_points, closed)
    total_len = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in segs)
    if total_len < 1e-9:
        return list(resampled_points)
    dedupe_tol = max(total_len * dedupe_frac, 1e-6)

    cross_pts = []
    if other_shapes:
        for other in other_shapes:
            other_pts = other.get("points") or []
            other_closed = bool(other.get("closed", False))
            if len(other_pts) < 2:
                continue
            other_segs = _path_segments(other_pts, other_closed)
            for (a, b) in segs:
                for (c, d) in other_segs:
                    ip = _seg_intersect(a, b, c, d)
                    if ip is not None:
                        cross_pts.append(ip)

    # Order matters here: original vertices and crossings (groups 0/1)
    # are preferred over the resampled fill (group 2) on a near-tie --
    # see the dedupe loop below.
    groups = [original_points, cross_pts, list(resampled_points)]

    tagged = []
    for gi, group in enumerate(groups):
        for p in group:
            param = _nearest_param_on_path(original_points, closed, p)
            tagged.append((param, gi, [float(p[0]), float(p[1])]))
    tagged.sort(key=lambda x: (x[0], x[1]))

    out = []
    last_param = None
    for param, gi, p in tagged:
        if last_param is not None and (param - last_param) < dedupe_tol:
            continue
        out.append(p)
        last_param = param

    # Closed loops: the sort/dedupe above only ever compares ADJACENT
    # entries, so a point near the very start (param~0) and one near the
    # very end (param~total_len) -- the SAME spot on a closed loop, once
    # it wraps back around -- would otherwise both survive as if they
    # were far apart instead of being caught as a near-duplicate.
    if closed and len(out) > 1 and last_param is not None and (total_len - last_param) < dedupe_tol:
        out = out[:-1]

    return out if len(out) >= 2 else list(resampled_points)


# ---------------------------------------------------------------------
# Convenience one-call wrapper: resample + merge in one step.
# ---------------------------------------------------------------------

def homogenise(points, pitch, closed, other_shapes=None):
    """
    Resample `points` to `pitch`-apart spacing, keeping its own original
    vertices and any real crossing points with `other_shapes` (each
    {"points": [...], "closed": bool}).
    """
    resampled = resample_evenly(points, pitch, closed)
    return homogenise_merge(points, closed, resampled, other_shapes)


if __name__ == "__main__":
    # Quick self-test / demo.
    rect = [[0, 0], [10, 0], [10, 10], [0, 10]]
    pts = homogenise(rect, pitch=2.0, closed=True)
    print("Rectangle, pitch=2, closed:")
    print(" ", pts)
    corners_kept = all(
        any(abs(p[0] - c[0]) < 1e-6 and abs(p[1] - c[1]) < 1e-6 for p in pts)
        for c in rect
    )
    print("  all 4 corners preserved:", corners_kept)

    square_a = [[0, 0], [10, 0], [10, 10], [0, 10]]
    square_b = [[5, 5], [15, 5], [15, 15], [5, 15]]
    pts2 = homogenise(
        square_a, pitch=3.0, closed=True,
        other_shapes=[{"points": square_b, "closed": True}],
    )
    print("\nSquare A homogenised against overlapping Square B:")
    print(" ", pts2)
    for expected in [(10, 5), (5, 10)]:
        hit = any(abs(p[0] - expected[0]) < 1e-6 and abs(p[1] - expected[1]) < 1e-6 for p in pts2)
        print(f"  intersection {expected} present:", hit)
