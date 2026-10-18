import os

os.environ["JWT_SECRET"] = "test-secret-test-secret-123"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["BCRYPT_ROUNDS"] = "4"
os.environ["CORS_ORIGINS"] = ""

import pytest
from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import Venue, User
from app.security import hash_password

PW = "correct-horse-9"

GOOD_CAMERA = {
    "zone_name": "Platform 1",
    "stream_url": "rtsp://10.0.4.21/s1",
    "ip_address": "10.0.4.21",
    "range_m": 35,
    "thresholds": {"caution": 50, "warning": 75, "critical": 90},
    "zone_polygon": [[0, 0], [14, 0], [14, 10], [0, 10]],   # 140 square metres
    "camera_xy": [7, -3],
    "homography": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
}


@pytest.fixture()
def db():
    Base.metadata.create_all(engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db):
    return TestClient(app)


@pytest.fixture()
def world(db):
    a = Venue(name="Jaipur Junction", city="Jaipur")
    b = Venue(name="Govind Dev Ji Temple", city="Jaipur")
    db.add_all([a, b])
    db.flush()
    users = [
        User(username="root", password_hash=hash_password(PW), role="superadmin"),
        User(username="admin.a", password_hash=hash_password(PW), role="admin", venue_id=a.id),
        User(username="admin.b", password_hash=hash_password(PW), role="admin", venue_id=b.id),
        User(username="sec.a", password_hash=hash_password(PW), role="security", venue_id=a.id),
        User(username="guest1", password_hash=hash_password(PW), role="attendee"),
    ]
    db.add_all(users)
    db.commit()
    return {"a": a.id, "b": b.id}


def auth(client, username, password=PW):
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def make_camera(client, headers, venue_id, **overrides):
    r = client.post(f"/venues/{venue_id}/cameras", json=GOOD_CAMERA | overrides, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()
