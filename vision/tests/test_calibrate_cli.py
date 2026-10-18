import json
import subprocess
import sys
from pathlib import Path

import numpy as np

from vista_vision import calibration
from vista_vision.homography import apply_homography

ROOT = Path(__file__).resolve().parent.parent
H = np.array([[0.02, 0.003, -5.0], [0.001, 0.05, -12.0], [0.0001, 0.002, 1.0]])
IMG = [[100, 400], [540, 410], [500, 200], [150, 190]]


def run(tmp_path, points, *extra):
    p = tmp_path / "points.json"
    p.write_text(json.dumps(points))
    return subprocess.run(
        [sys.executable, str(ROOT / "calibrate.py"), str(p), "--out", str(tmp_path / "c.json"),
         "--patch-out", str(tmp_path / "patch.json"), *extra],
        capture_output=True, text=True, cwd=ROOT,
    )


def points(ground):
    return {"image_points": IMG, "ground_points_m": ground, "camera_xy": [7, -3],
            "zone_polygon": [[0, 0], [14, 0], [14, 10], [0, 10]], "range_m": 35}


def test_good_points_write_both_files_and_roundtrip(tmp_path):
    ground = apply_homography(H, IMG).tolist()
    r = run(tmp_path, points(ground))
    assert r.returncode == 0, r.stderr
    cal = calibration.load(str(tmp_path / "c.json"))
    assert np.allclose(apply_homography(cal.H, IMG), ground, atol=1e-5)
    patch = json.loads((tmp_path / "patch.json").read_text())
    assert set(patch) == {"homography", "zone_polygon", "camera_xy", "range_m"}


def test_inconsistent_points_are_refused_unless_forced(tmp_path):
    ground = apply_homography(H, IMG).tolist()
    ground[0][0] += 3          # the first point is badly wrong: not a flat-plane mapping any more
    ground[2][1] -= 2
    ground.append([0, 0])
    bad = points(ground[:4])
    # five image points so the fit cannot be exact
    bad["image_points"] = IMG + [[320, 300]]
    bad["ground_points_m"] = ground
    r = run(tmp_path, bad)
    assert r.returncode == 2 and "Re-click" in r.stderr
    assert not (tmp_path / "c.json").exists()
    assert run(tmp_path, bad, "--force").returncode == 0
