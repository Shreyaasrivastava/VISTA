import numpy as np
import pytest

from vista_vision.homography import apply_homography, compute_homography, reprojection_errors

# A made-up "true" mapping from image pixels to ground metres (has perspective).
H_TRUE = np.array([[0.02, 0.003, -5.0], [0.001, 0.05, -12.0], [0.0001, 0.002, 1.0]])


def to_ground(pts):
    return apply_homography(H_TRUE, pts)


IMG = np.array([[100, 400], [540, 410], [500, 200], [150, 190], [320, 300]], dtype=float)


def test_recovers_the_true_mapping():
    H = compute_homography(IMG, to_ground(IMG))
    probe = np.array([[200, 250], [400, 350], [320, 220]], dtype=float)
    assert np.allclose(apply_homography(H, probe), to_ground(probe), atol=1e-6)


def test_four_points_are_enough_and_error_is_zero():
    H = compute_homography(IMG[:4], to_ground(IMG[:4]))
    assert reprojection_errors(H, IMG[:4], to_ground(IMG[:4])).max() < 1e-8


def test_small_click_noise_gives_small_ground_error():
    rng = np.random.default_rng(1)
    noisy = IMG + rng.normal(0, 1.0, IMG.shape)       # about 1 pixel of clicking error
    H = compute_homography(noisy, to_ground(IMG))
    probe = np.array([[320, 300]], dtype=float)
    assert np.linalg.norm(apply_homography(H, probe) - to_ground(probe)) < 0.5


def test_too_few_or_bad_points_are_refused():
    with pytest.raises(ValueError):
        compute_homography(IMG[:3], to_ground(IMG[:3]))
    with pytest.raises(ValueError):
        compute_homography(IMG[:4], to_ground(IMG[:5]))
    line = np.array([[0, 0], [10, 10], [20, 20], [30, 30]], dtype=float)
    with pytest.raises(ValueError):
        compute_homography(line, line)
    with pytest.raises(ValueError):
        compute_homography(np.zeros((4, 2)), np.zeros((4, 2)))


def test_points_behind_the_horizon_become_nan():
    H = np.array([[1, 0, 0], [0, 1, 0], [0, 0.01, 1.0]])
    out = apply_homography(H, [[10, 10], [10, -200]])    # second point has w < 0
    assert not np.isnan(out[0]).any() and np.isnan(out[1]).all()


def test_empty_input():
    assert apply_homography(np.eye(3), []).shape == (0, 2)
