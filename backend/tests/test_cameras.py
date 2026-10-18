import pytest

from .conftest import GOOD_CAMERA, auth, make_camera


def test_create_camera_returns_key_once_and_computes_area(client, world):
    h = auth(client, "admin.a")
    cam = make_camera(client, h, world["a"])
    assert cam["code"] == "CAM-01" and cam["area_sqm"] == 140 and cam["calibrated"] is True
    assert len(cam["ingest_key"]) >= 40
    again = client.get(f"/cameras/{cam['id']}", headers=h).json()
    assert "ingest_key" not in again and "ingest_key_hash" not in again


def test_camera_codes_count_up_per_venue(client, world):
    ha, hb = auth(client, "admin.a"), auth(client, "admin.b")
    assert make_camera(client, ha, world["a"])["code"] == "CAM-01"
    assert make_camera(client, ha, world["a"])["code"] == "CAM-02"
    assert make_camera(client, hb, world["b"])["code"] == "CAM-01"


def test_edit_stream_url_and_ip(client, world):
    h = auth(client, "admin.a")
    cam = make_camera(client, h, world["a"])
    r = client.patch(f"/cameras/{cam['id']}", json={"stream_url": "rtsp://192.168.1.50/live", "ip_address": "192.168.1.50"}, headers=h)
    assert r.status_code == 200
    assert r.json()["stream_url"] == "rtsp://192.168.1.50/live" and r.json()["ip_address"] == "192.168.1.50"
    assert r.json()["zone_name"] == "Platform 1"  # untouched fields stay


def test_edit_thresholds_keeps_ordering_rule(client, world):
    h = auth(client, "admin.a")
    cam = make_camera(client, h, world["a"])
    ok = client.patch(f"/cameras/{cam['id']}", json={"thresholds": {"caution": 40, "warning": 70, "critical": 85}}, headers=h)
    assert ok.status_code == 200 and ok.json()["thresholds"]["warning"] == 70
    bad = client.patch(f"/cameras/{cam['id']}", json={"thresholds": {"caution": 80, "warning": 70, "critical": 85}}, headers=h)
    assert bad.status_code == 422


def test_patch_rejects_unknown_fields(client, world):
    h = auth(client, "admin.a")
    cam = make_camera(client, h, world["a"])
    r = client.patch(f"/cameras/{cam['id']}", json={"venue_id": 2, "ingest_key_hash": "x"}, headers=h)
    assert r.status_code == 422


@pytest.mark.parametrize("change", [
    {"stream_url": "ftp://10.0.0.1/x"},
    {"stream_url": "not a url"},
    {"stream_url": "rtsp://"},
    {"ip_address": "999.1.1.1"},
    {"ip_address": "10.0.4"},
    {"range_m": 0},
    {"range_m": 500},
    {"zone_polygon": [[0, 0], [1, 1]]},
    {"zone_polygon": [[0, 0], [1, 1], [2, 2]]},   # zero area
    {"camera_xy": [1, 2, 3]},
    {"homography": [[1, 0], [0, 1]]},
    {"thresholds": {"caution": 0, "warning": 75, "critical": 90}},
    {"thresholds": {"caution": 50, "warning": 75, "critical": 101}},
])
def test_bad_camera_values_are_rejected(client, world, change):
    h = auth(client, "admin.a")
    r = client.post(f"/venues/{world['a']}/cameras", json=GOOD_CAMERA | change, headers=h)
    assert r.status_code == 422, (change, r.text)


def test_camera_without_polygon_is_not_calibrated(client, world):
    h = auth(client, "admin.a")
    cam = make_camera(client, h, world["a"], zone_polygon=None, camera_xy=None, homography=None)
    assert cam["calibrated"] is False and cam["area_sqm"] is None


def test_delete_camera_removes_it_and_its_readings(client, world):
    h = auth(client, "admin.a")
    cam = make_camera(client, h, world["a"])
    client.post("/density-events", json={"people_count": 10}, headers={"X-Camera-Key": cam["ingest_key"]})
    assert client.delete(f"/cameras/{cam['id']}", headers=h).status_code == 204
    assert client.get(f"/cameras/{cam['id']}", headers=h).status_code == 404
    assert client.post("/density-events", json={"people_count": 10}, headers={"X-Camera-Key": cam["ingest_key"]}).status_code == 401


def test_rotate_key_invalidates_the_old_one(client, world):
    h = auth(client, "admin.a")
    cam = make_camera(client, h, world["a"])
    new = client.post(f"/cameras/{cam['id']}/rotate-key", headers=h).json()["ingest_key"]
    assert new != cam["ingest_key"]
    assert client.post("/density-events", json={"people_count": 1}, headers={"X-Camera-Key": cam["ingest_key"]}).status_code == 401
    assert client.post("/density-events", json={"people_count": 1}, headers={"X-Camera-Key": new}).status_code == 201
