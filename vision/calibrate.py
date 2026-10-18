"""Compute a camera's homography from clicked points.

Usage:
  python calibrate.py points.json --out calibration.json

points.json:
  {
    "image_points":      [[x, y], ...],   pixels, 4 or more
    "ground_points_m":   [[x, y], ...],   metres in the VENUE frame, same order
    "camera_xy":         [x, y],          where the camera stands, venue frame
    "zone_polygon":      [[x, y], ...],   zone corners, venue frame
    "range_m":           35
  }

Writes calibration.json (used by pipeline.py) and camera_patch.json (the body to PATCH to the API).
"""
import argparse
import json
import sys

from vista_vision import calibration

WARN_RMS_M = 0.25
FAIL_RMS_M = 0.5


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("points")
    ap.add_argument("--out", default="calibration.json")
    ap.add_argument("--patch-out", default="camera_patch.json")
    ap.add_argument("--force", action="store_true", help="write the files even if the error is large")
    args = ap.parse_args()

    with open(args.points) as f:
        p = json.load(f)
    cal = calibration.build(p["image_points"], p["ground_points_m"], p["zone_polygon"], p["camera_xy"], p["range_m"])
    print(f"reprojection error: rms {cal.rms_error_m:.3f} m, worst {cal.max_error_m:.3f} m")
    if cal.rms_error_m > FAIL_RMS_M and not args.force:
        print(f"Error is above {FAIL_RMS_M} m. Re-click the points, or use --force to save anyway.", file=sys.stderr)
        return 2
    if cal.rms_error_m > WARN_RMS_M:
        print(f"Warning: error is above {WARN_RMS_M} m. Counts near the zone edge may be wrong.")
    d = calibration.to_dict(cal)
    with open(args.out, "w") as f:
        json.dump(d, f, indent=2)
    with open(args.patch_out, "w") as f:
        json.dump({k: d[k] for k in ("homography", "zone_polygon", "camera_xy", "range_m")}, f, indent=2)
    print(f"wrote {args.out} and {args.patch_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
