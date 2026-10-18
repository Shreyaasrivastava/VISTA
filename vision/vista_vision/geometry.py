"""Zone maths: area, point-in-polygon, and counting people in a zone."""
from dataclasses import dataclass

import numpy as np


def polygon_area(poly) -> float:
    p = np.asarray(poly, dtype=float)
    x, y = p[:, 0], p[:, 1]
    return float(abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2)


def points_in_polygon(points, poly) -> np.ndarray:
    """Ray casting. NaN points are outside. Points exactly on an edge may go either way."""
    pts = np.asarray(points, dtype=float).reshape(-1, 2)
    poly = np.asarray(poly, dtype=float)
    inside = np.zeros(len(pts), dtype=bool)
    valid = ~np.isnan(pts).any(axis=1)
    x, y = pts[:, 0], pts[:, 1]
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        with np.errstate(invalid="ignore", divide="ignore"):
            crosses = ((yi > y) != (yj > y)) & (x < (xj - xi) * (y - yi) / (yj - yi) + xi)
        inside ^= crosses & valid
        j = i
    return inside & valid


@dataclass
class CountResult:
    count: int
    outside_zone: int
    out_of_range: int
    invalid: int


def count_people(ground_pts, polygon, camera_xy=None, range_m=None) -> CountResult:
    """Count foot points that fall inside the zone and within the camera's range."""
    pts = np.asarray(ground_pts, dtype=float).reshape(-1, 2)
    invalid = int(np.isnan(pts).any(axis=1).sum())
    in_zone = points_in_polygon(pts, polygon)
    keep = in_zone.copy()
    out_of_range = 0
    if camera_xy is not None and range_m is not None and len(pts):
        dist = np.linalg.norm(pts - np.asarray(camera_xy, dtype=float), axis=1)
        far = in_zone & (dist > range_m)
        out_of_range = int(far.sum())
        keep &= ~far
    return CountResult(
        count=int(keep.sum()),
        outside_zone=int((~in_zone).sum()) - invalid,
        out_of_range=out_of_range,
        invalid=invalid,
    )
