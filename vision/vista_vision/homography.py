"""Map image points (pixels) onto the ground plane (metres in the venue frame)."""
import numpy as np

_MIN_RANK_RATIO = 1e-9


def _normalise(p: np.ndarray):
    centre = p.mean(axis=0)
    spread = np.mean(np.linalg.norm(p - centre, axis=1))
    if spread == 0:
        raise ValueError("calibration points are all the same point")
    s = np.sqrt(2) / spread
    T = np.array([[s, 0, -s * centre[0]], [0, s, -s * centre[1]], [0, 0, 1]])
    ph = np.c_[p, np.ones(len(p))] @ T.T
    return ph[:, :2], T


def compute_homography(image_pts, ground_pts) -> np.ndarray:
    """Direct linear transform from 4 or more point pairs. Returns a 3x3 matrix H.

    ground = H @ image (in homogeneous coordinates).
    """
    src = np.asarray(image_pts, dtype=float)
    dst = np.asarray(ground_pts, dtype=float)
    if src.ndim != 2 or src.shape[1] != 2 or src.shape != dst.shape:
        raise ValueError("image_pts and ground_pts must both be N x 2 with the same N")
    if len(src) < 4:
        raise ValueError("need at least 4 point pairs")

    s, Ts = _normalise(src)
    d, Td = _normalise(dst)
    rows = []
    for (x, y), (u, v) in zip(s, d):
        rows.append([-x, -y, -1, 0, 0, 0, u * x, u * y, u])
        rows.append([0, 0, 0, -x, -y, -1, v * x, v * y, v])
    A = np.array(rows)
    _, sv, vt = np.linalg.svd(A)
    if sv[-2] / sv[0] < _MIN_RANK_RATIO:
        raise ValueError("calibration points are collinear or duplicated; pick 4 spread-out points")
    H = np.linalg.inv(Td) @ vt[-1].reshape(3, 3) @ Ts
    if abs(H[2, 2]) < 1e-12:
        raise ValueError("could not compute a stable homography")
    return H / H[2, 2]


def apply_homography(H, pts) -> np.ndarray:
    """Return N x 2 ground points. Points that map to or behind the horizon become NaN."""
    p = np.asarray(pts, dtype=float).reshape(-1, 2)
    if len(p) == 0:
        return np.empty((0, 2))
    ph = np.c_[p, np.ones(len(p))] @ np.asarray(H, dtype=float).T
    w = ph[:, 2]
    out = np.full((len(p), 2), np.nan)
    ok = w > 1e-9
    out[ok] = ph[ok, :2] / w[ok, None]
    return out


def reprojection_errors(H, image_pts, ground_pts) -> np.ndarray:
    """Distance in metres between each mapped image point and where it should be."""
    mapped = apply_homography(H, image_pts)
    return np.linalg.norm(mapped - np.asarray(ground_pts, dtype=float), axis=1)
