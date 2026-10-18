import jwt

from app.security import ALGORITHM
from .conftest import PW, auth


def test_login_ok_returns_role_and_venue(client, world):
    r = client.post("/auth/login", json={"username": "admin.a", "password": PW})
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "admin" and body["venue_id"] == world["a"] and body["access_token"]


def test_login_is_case_insensitive_on_username(client, world):
    assert client.post("/auth/login", json={"username": "ADMIN.A", "password": PW}).status_code == 200


def test_wrong_password_and_unknown_user_look_the_same(client, world):
    a = client.post("/auth/login", json={"username": "admin.a", "password": "nope-nope-nope"})
    b = client.post("/auth/login", json={"username": "ghost", "password": "nope-nope-nope"})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_me_needs_a_token(client, world):
    assert client.get("/me").status_code == 401
    assert client.get("/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_me_returns_current_user(client, world):
    r = client.get("/me", headers=auth(client, "sec.a"))
    assert r.json()["username"] == "sec.a" and r.json()["role"] == "security"


def test_token_signed_with_wrong_secret_is_rejected(client, world):
    forged = jwt.encode({"sub": "1", "role": "superadmin"}, "some-other-secret-value", algorithm=ALGORITHM)
    assert client.get("/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_role_comes_from_database_not_token(client, world, db):
    from app.models import User
    headers = auth(client, "admin.a")
    user = db.query(User).filter_by(username="admin.a").one()
    user.role = "attendee"
    user.venue_id = None
    db.commit()
    assert client.get("/venues", headers=headers).status_code == 403


def test_only_superadmin_creates_users(client, world):
    body = {"username": "new.admin", "password": "long-enough-pw", "role": "admin", "venue_id": world["b"]}
    assert client.post("/users", json=body, headers=auth(client, "admin.a")).status_code == 403
    r = client.post("/users", json=body, headers=auth(client, "root"))
    assert r.status_code == 201 and r.json()["venue_id"] == world["b"]
    assert "password" not in r.text
    assert client.post("/users", json=body, headers=auth(client, "root")).status_code == 409
    assert client.post("/auth/login", json={"username": "new.admin", "password": "long-enough-pw"}).status_code == 200


def test_user_rules(client, world):
    h = auth(client, "root")
    no_venue = {"username": "x.admin", "password": "long-enough-pw", "role": "admin"}
    assert client.post("/users", json=no_venue, headers=h).status_code == 422
    short = {"username": "x.admin", "password": "short", "role": "admin", "venue_id": world["a"]}
    assert client.post("/users", json=short, headers=h).status_code == 422
    missing = {"username": "x.admin", "password": "long-enough-pw", "role": "admin", "venue_id": 9999}
    assert client.post("/users", json=missing, headers=h).status_code == 404
    root_role = {"username": "x.root", "password": "long-enough-pw", "role": "superadmin"}
    assert client.post("/users", json=root_role, headers=h).status_code == 422
