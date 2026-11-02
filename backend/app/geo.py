"""Small geometry helpers (no external deps)."""
import math

R_EARTH = 6371000.0


def haversine_m(lat1, lng1, lat2, lng2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R_EARTH * math.asin(math.sqrt(a))


def _xy(lat, lng, lat0):
    # local equirectangular projection in metres, fine for city-scale distances
    return (math.radians(lng) * math.cos(math.radians(lat0)) * R_EARTH, math.radians(lat) * R_EARTH)


def dist_to_polyline_m(lat, lng, path):
    """Shortest distance (m) from a point to a [[lat,lng],...] polyline, plus nearest segment index."""
    if not path:
        return float("inf"), 0
    if len(path) == 1:
        return haversine_m(lat, lng, path[0][0], path[0][1]), 0
    px, py = _xy(lat, lng, lat)
    best, best_i = float("inf"), 0
    for i in range(len(path) - 1):
        ax, ay = _xy(path[i][0], path[i][1], lat)
        bx, by = _xy(path[i + 1][0], path[i + 1][1], lat)
        dx, dy = bx - ax, by - ay
        seg2 = dx * dx + dy * dy
        t = 0.0 if seg2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg2))
        d = math.hypot(px - (ax + t * dx), py - (ay + t * dy))
        if d < best:
            best, best_i = d, i
    return best, best_i


def polyline_length_m(path):
    return sum(haversine_m(a[0], a[1], b[0], b[1]) for a, b in zip(path, path[1:]))


def resample(path, step_m):
    """Evenly spaced points along a polyline (always includes first and last point)."""
    if len(path) < 2:
        return [list(p) for p in path]
    out = [list(path[0])]
    carried = 0.0
    for a, b in zip(path, path[1:]):
        seg = haversine_m(a[0], a[1], b[0], b[1])
        if seg == 0:
            continue
        d = step_m - carried
        while d <= seg:
            f = d / seg
            out.append([a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f])
            d += step_m
        carried = seg - (d - step_m)
    if out[-1] != list(path[-1]):
        out.append(list(path[-1]))
    return out
