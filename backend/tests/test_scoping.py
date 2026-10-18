from .conftest import auth, make_camera


def test_admin_sees_only_own_venue_in_list(client, world):
    r = client.get("/venues", headers=auth(client, "admin.a"))
    assert [v["id"] for v in r.json()] == [world["a"]]
    r = client.get("/venues", headers=auth(client, "admin.b"))
    assert [v["id"] for v in r.json()] == [world["b"]]
    r = client.get("/venues", headers=auth(client, "root"))
    assert len(r.json()) == 2


def test_other_venue_looks_like_it_does_not_exist(client, world):
    h = auth(client, "admin.a")
    assert client.get(f"/venues/{world['a']}", headers=h).status_code == 200
    assert client.get(f"/venues/{world['b']}", headers=h).status_code == 404
    assert client.get("/venues/9999", headers=h).status_code == 404


def test_cannot_list_or_add_cameras_in_another_venue(client, world):
    ha, hb = auth(client, "admin.a"), auth(client, "admin.b")
    make_camera(client, hb, world["b"])
    assert client.get(f"/venues/{world['b']}/cameras", headers=ha).status_code == 404
    from .conftest import GOOD_CAMERA
    assert client.post(f"/venues/{world['b']}/cameras", json=GOOD_CAMERA, headers=ha).status_code == 404
    assert client.get(f"/venues/{world['b']}/density/latest", headers=ha).status_code == 404


def test_cannot_read_edit_or_delete_another_venues_camera(client, world):
    ha, hb = auth(client, "admin.a"), auth(client, "admin.b")
    cam = make_camera(client, hb, world["b"])
    cid = cam["id"]
    assert client.get(f"/cameras/{cid}", headers=ha).status_code == 404
    assert client.patch(f"/cameras/{cid}", json={"range_m": 10}, headers=ha).status_code == 404
    assert client.delete(f"/cameras/{cid}", headers=ha).status_code == 404
    assert client.post(f"/cameras/{cid}/rotate-key", headers=ha).status_code == 404
    assert client.get(f"/cameras/{cid}/density", headers=ha).status_code == 404
    assert client.get(f"/cameras/{cid}", headers=hb).status_code == 200


def test_security_can_read_own_venue_but_not_edit(client, world):
    ha, hs = auth(client, "admin.a"), auth(client, "sec.a")
    cam = make_camera(client, ha, world["a"])
    assert client.get(f"/venues/{world['a']}/cameras", headers=hs).status_code == 200
    assert client.patch(f"/cameras/{cam['id']}", json={"range_m": 10}, headers=hs).status_code == 403
    assert client.delete(f"/cameras/{cam['id']}", headers=hs).status_code == 403
    from .conftest import GOOD_CAMERA
    assert client.post(f"/venues/{world['a']}/cameras", json=GOOD_CAMERA, headers=hs).status_code == 403


def test_attendee_and_anonymous_get_nothing(client, world):
    hg = auth(client, "guest1")
    assert client.get("/venues", headers=hg).status_code == 403
    assert client.get(f"/venues/{world['a']}/cameras", headers=hg).status_code == 403
    assert client.get("/venues").status_code == 401


def test_only_superadmin_creates_venues(client, world):
    body = {"name": "SMS Stadium", "city": "Jaipur"}
    assert client.post("/venues", json=body, headers=auth(client, "admin.a")).status_code == 403
    assert client.post("/venues", json=body, headers=auth(client, "root")).status_code == 201
    assert client.post("/venues", json=body, headers=auth(client, "root")).status_code == 409


def test_admin_can_rename_own_venue_only(client, world):
    ha = auth(client, "admin.a")
    assert client.patch(f"/venues/{world['a']}", json={"city": "Jaipur City"}, headers=ha).json()["city"] == "Jaipur City"
    assert client.patch(f"/venues/{world['b']}", json={"city": "x" * 5}, headers=ha).status_code == 404
