from datetime import datetime, timedelta

from app.alerts import service
from .conftest import auth, make_camera

# Camera zone 140 m2, ref 1.08 => 151.2 log = 100%. Warning 75% ~ 114, Critical 90% ~ 137.
NORMAL, WARN, CRIT = 40, 125, 145


def feed(client, cam, counts, t0=datetime(2026, 1, 1, 10, 0, 0)):
    for i, n in enumerate(counts):
        r = client.post("/density-events", json={"people_count": n, "ts": (t0 + timedelta(seconds=i)).isoformat() + "Z"},
                        headers={"X-Camera-Key": cam["ingest_key"]})
        assert r.status_code == 201, r.text


def setup_function(_):
    service.engine.states.clear()


def test_alert_opens_and_resolves(client, world):
    h = auth(client, "admin.a")
    cam = make_camera(client, h, world["a"])
    feed(client, cam, [NORMAL] * 3 + [WARN] * 7 + [CRIT] * 7 + [NORMAL] * 15)
    rows = client.get(f"/venues/{world['a']}/alerts", headers=h).json()
    assert [r["tier_name"] for r in rows] == ["Critical", "Warning"]  # newest pehle
    assert all(r["resolved_at"] for r in rows)
    assert rows[0]["peak_pct"] > 90
    assert client.get(f"/venues/{world['a']}/alerts?active_only=true", headers=h).json() == []


def test_active_alert_listed(client, world):
    h = auth(client, "admin.a")
    cam = make_camera(client, h, world["a"])
    feed(client, cam, [WARN] * 8)
    rows = client.get(f"/venues/{world['a']}/alerts?active_only=true", headers=h).json()
    assert len(rows) == 1 and rows[0]["tier_name"] == "Warning" and rows[0]["resolved_at"] is None


def test_alerts_are_venue_scoped(client, world):
    ha = auth(client, "admin.a")
    cam = make_camera(client, ha, world["a"])
    feed(client, cam, [WARN] * 8)
    hb = auth(client, "admin.b")
    assert client.get(f"/venues/{world['a']}/alerts", headers=hb).status_code == 404
    assert client.get(f"/venues/{world['b']}/alerts", headers=hb).json() == []


def test_alerts_need_staff_login(client, world):
    assert client.get(f"/venues/{world['a']}/alerts").status_code == 401
    assert client.get(f"/venues/{world['a']}/alerts", headers=auth(client, "guest1")).status_code == 403
