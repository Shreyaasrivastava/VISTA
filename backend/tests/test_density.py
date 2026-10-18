import pytest

from app.services import occupancy_pct, polygon_area, tier_for
from app.schemas import Thresholds
from .conftest import auth, make_camera


def key(cam):
    return {"X-Camera-Key": cam["ingest_key"]}


def test_shoelace_area():
    assert polygon_area([[0, 0], [14, 0], [14, 10], [0, 10]]) == 140
    assert polygon_area([[0, 0], [4, 0], [0, 3]]) == 6


def test_occupancy_uses_reference_density():
    # 140 m2 * 1.08 = 151.2 people is 100%
    assert occupancy_pct(151, 140, 1.08) == pytest.approx(99.87, abs=0.01)
    assert occupancy_pct(0, 140, 1.08) == 0


@pytest.mark.parametrize("pct,tier", [(0, 0), (49.99, 0), (50, 1), (74.99, 1), (75, 2), (89.99, 2), (90, 3), (150, 3)])
def test_tier_bands_are_half_open(pct, tier):
    assert tier_for(pct, Thresholds()) == tier


def test_ingest_stores_reading_with_density_and_tier(client, world):
    cam = make_camera(client, auth(client, "admin.a"), world["a"])
    r = client.post("/density-events", json={"people_count": 82, "confidence": 0.8}, headers=key(cam))
    assert r.status_code == 201
    body = r.json()
    # 82 / 140 = 0.5857 per m2; 82 / 151.2 = 54.2% -> Caution
    assert body["density"] == pytest.approx(0.5857, abs=1e-3)
    assert body["occupancy_pct"] == pytest.approx(54.23, abs=0.01)
    assert body["tier"] == 1 and body["tier_name"] == "Caution"
    assert body["ts"].endswith("Z")


def test_camera_thresholds_decide_the_tier(client, world):
    h = auth(client, "admin.a")
    cam = make_camera(client, h, world["a"], thresholds={"caution": 10, "warning": 20, "critical": 30})
    r = client.post("/density-events", json={"people_count": 82}, headers=key(cam))
    assert r.json()["tier"] == 3


def test_bad_or_missing_key_is_401(client, world):
    make_camera(client, auth(client, "admin.a"), world["a"])
    assert client.post("/density-events", json={"people_count": 5}).status_code == 401
    assert client.post("/density-events", json={"people_count": 5}, headers={"X-Camera-Key": "wrong"}).status_code == 401


def test_uncalibrated_camera_cannot_ingest(client, world):
    cam = make_camera(client, auth(client, "admin.a"), world["a"], zone_polygon=None, camera_xy=None, homography=None)
    r = client.post("/density-events", json={"people_count": 5}, headers=key(cam))
    assert r.status_code == 409


@pytest.mark.parametrize("payload", [
    {"people_count": -1},
    {"people_count": 99999},
    {"people_count": 5, "confidence": 1.5},
    {"people_count": 5, "ts": "2999-01-01T00:00:00Z"},
    {"people_count": "many"},
])
def test_bad_density_payloads_are_422(client, world, payload):
    cam = make_camera(client, auth(client, "admin.a"), world["a"])
    assert client.post("/density-events", json=payload, headers=key(cam)).status_code == 422


def test_reading_belongs_to_the_keys_camera_and_venue(client, world):
    ha, hb = auth(client, "admin.a"), auth(client, "admin.b")
    cam_a, cam_b = make_camera(client, ha, world["a"]), make_camera(client, hb, world["b"])
    client.post("/density-events", json={"people_count": 20}, headers=key(cam_a))
    client.post("/density-events", json={"people_count": 90}, headers=key(cam_b))
    la = client.get(f"/venues/{world['a']}/density/latest", headers=ha).json()
    lb = client.get(f"/venues/{world['b']}/density/latest", headers=hb).json()
    assert [z["reading"]["people_count"] for z in la] == [20]
    assert [z["reading"]["people_count"] for z in lb] == [90]


def test_latest_returns_newest_and_includes_silent_cameras(client, world):
    h = auth(client, "admin.a")
    cam1, cam2 = make_camera(client, h, world["a"]), make_camera(client, h, world["a"], zone_name="Main concourse")
    for n, ts in [(10, "2026-10-01T10:00:00Z"), (30, "2026-10-01T10:00:02Z"), (20, "2026-10-01T10:00:01Z")]:
        client.post("/density-events", json={"people_count": n, "ts": ts}, headers=key(cam1))
    latest = client.get(f"/venues/{world['a']}/density/latest", headers=h).json()
    assert latest[0]["reading"]["people_count"] == 30
    assert latest[1]["zone_name"] == "Main concourse" and latest[1]["reading"] is None


def test_history_is_newest_first_and_limited(client, world):
    h = auth(client, "admin.a")
    cam = make_camera(client, h, world["a"])
    for i in range(5):
        client.post("/density-events", json={"people_count": i, "ts": f"2026-10-01T10:00:0{i}Z"}, headers=key(cam))
    rows = client.get(f"/cameras/{cam['id']}/density?limit=3", headers=h).json()
    assert [r["people_count"] for r in rows] == [4, 3, 2]
