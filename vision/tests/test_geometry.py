import numpy as np
import pytest

from vista_vision.geometry import count_people, points_in_polygon, polygon_area

RECT = [[0, 0], [14, 0], [14, 10], [0, 10]]
L_SHAPE = [[0, 0], [10, 0], [10, 4], [4, 4], [4, 10], [0, 10]]


def test_area():
    assert polygon_area(RECT) == 140
    assert polygon_area(L_SHAPE) == 64
    assert polygon_area(RECT[::-1]) == 140            # direction does not matter


def test_inside_outside():
    r = points_in_polygon([[7, 5], [15, 5], [-1, 5], [7, 11], [0.1, 0.1]], RECT)
    assert r.tolist() == [True, False, False, False, True]


def test_concave_polygon():
    r = points_in_polygon([[2, 2], [8, 2], [2, 8], [8, 8], [6, 6]], L_SHAPE)
    assert r.tolist() == [True, True, True, False, False]


def test_nan_points_are_outside():
    assert points_in_polygon([[np.nan, 3], [3, np.nan]], RECT).tolist() == [False, False]


def test_count_people_all_cases():
    pts = np.array([[7, 5], [8, 5], [20, 5], [np.nan, np.nan], [13, 9]])
    r = count_people(pts, RECT)
    assert (r.count, r.outside_zone, r.invalid, r.out_of_range) == (3, 1, 1, 0)


def test_range_cutoff_drops_far_people():
    pts = np.array([[7, 1], [7, 9]])                  # camera at (7, -3): distances 4 and 12
    r = count_people(pts, RECT, camera_xy=[7, -3], range_m=10)
    assert r.count == 1 and r.out_of_range == 1


def test_no_people():
    assert count_people(np.empty((0, 2)), RECT).count == 0
