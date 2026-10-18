"""Load and save a camera's calibration file."""
import json
from dataclasses import dataclass

import numpy as np

from .homography import compute_homography, reprojection_errors


@dataclass
class Calibration:
    H: np.ndarray
    zone_polygon: list
    camera_xy: list
    range_m: float
    rms_error_m: float = 0.0
    max_error_m: float = 0.0


def build(image_pts, ground_pts, zone_polygon, camera_xy, range_m) -> Calibration:
    H = compute_homography(image_pts, ground_pts)
    err = reprojection_errors(H, image_pts, ground_pts)
    return Calibration(
        H=H, zone_polygon=zone_polygon, camera_xy=camera_xy, range_m=range_m,
        rms_error_m=float(np.sqrt(np.mean(err**2))), max_error_m=float(err.max()),
    )


def to_dict(c: Calibration) -> dict:
    return {
        "homography": c.H.tolist(), "zone_polygon": c.zone_polygon, "camera_xy": c.camera_xy,
        "range_m": c.range_m, "rms_error_m": round(c.rms_error_m, 4), "max_error_m": round(c.max_error_m, 4),
    }


def load(path: str) -> Calibration:
    with open(path) as f:
        d = json.load(f)
    return Calibration(
        H=np.array(d["homography"], dtype=float), zone_polygon=d["zone_polygon"], camera_xy=d["camera_xy"],
        range_m=float(d["range_m"]), rms_error_m=d.get("rms_error_m", 0.0), max_error_m=d.get("max_error_m", 0.0),
    )
