from .conftest import PW, auth

ORG, SEC = "org-code-123", "sec-code-456"


def test_attendee_signup_then_login(client, world):
    r = client.post("/auth/signup", json={"username": "New.Guest", "password": PW, "role": "attendee"})
    assert r.status_code == 201 and r.json()["role"] == "attendee"
    assert client.post("/auth/login", json={"username": "new.guest", "password": PW}).status_code == 200


def test_duplicate_username_is_409(client, world):
    body = {"username": "guest1", "password": PW, "role": "attendee"}
    assert client.post("/auth/signup", json=body).status_code == 409


def test_organiser_needs_code_and_venue(client, world):
    base = {"username": "org.one", "password": PW, "role": "organiser"}
    assert client.post("/auth/signup", json=base | {"venue_id": world["a"]}).status_code == 403
    assert client.post("/auth/signup", json=base | {"venue_id": world["a"], "access_code": "wrong"}).status_code == 403
    assert client.post("/auth/signup", json=base | {"access_code": ORG}).status_code == 422
    assert client.post("/auth/signup", json=base | {"venue_id": 9999, "access_code": ORG}).status_code == 422
    r = client.post("/auth/signup", json=base | {"venue_id": world["a"], "access_code": ORG})
    assert r.status_code == 201 and r.json()["role"] == "admin"
    assert [v["id"] for v in client.get("/venues", headers=auth(client, "org.one")).json()] == [world["a"]]


def test_security_needs_code_and_venue(client, world):
    base = {"username": "sec.two", "password": PW, "role": "security"}
    assert client.post("/auth/signup", json=base | {"venue_id": world["b"], "access_code": ORG}).status_code == 403
    assert client.post("/auth/signup", json=base | {"access_code": SEC}).status_code == 422
    r = client.post("/auth/signup", json=base | {"venue_id": world["b"], "access_code": SEC})
    assert r.status_code == 201 and r.json()["role"] == "security"
    assert auth(client, "sec.two")


def test_bad_username_is_422(client, world):
    body = {"username": "has space", "password": PW, "role": "attendee"}
    assert client.post("/auth/signup", json=body).status_code == 422