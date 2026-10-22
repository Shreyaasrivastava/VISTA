from datetime import timedelta

import pytest

from app.models import Recovery, User, utcnow
from app.routers import recovery as rec
from app.security import verify_password
from .conftest import PW, auth

GOOD_Q = "What was the name of my first scooter?"
GOOD_A = "Blue Lightning Bolt"          # strong enough for staff (19 chars)


@pytest.fixture(autouse=True)
def clean_limiter():
    rec.reset_limiter()
    yield
    rec.reset_limiter()


def set_rec(client, username, q=GOOD_Q, a=GOOD_A, pw=PW):
    return client.put("/me/recovery", json={"current_password": pw, "question": q, "answer": a}, headers=auth(client, username))


def ask(client, username):
    return client.post("/auth/recovery/question", json={"username": username})


def reset(client, username, answer, new_pw="brand-new-pass-77"):
    return client.post("/auth/recovery/reset", json={"username": username, "answer": answer, "new_password": new_pw})


def login_ok(client, username, pw):
    return client.post("/auth/login", json={"username": username, "password": pw}).status_code == 200


# ---------- setting a question ----------
def test_set_and_read_back_question_without_the_answer(client, world):
    assert set_rec(client, "admin.a").status_code == 204
    r = client.get("/me/recovery", headers=auth(client, "admin.a")).json()
    assert r == {"has_recovery": True, "question": GOOD_Q}
    assert "answer" not in str(r)


def test_status_before_anything_is_set(client, world):
    assert client.get("/me/recovery", headers=auth(client, "guest1")).json() == {"has_recovery": False, "question": None}


def test_setting_needs_login_and_the_current_password(client, world):
    body = {"current_password": PW, "question": GOOD_Q, "answer": GOOD_A}
    assert client.put("/me/recovery", json=body).status_code == 401
    assert set_rec(client, "admin.a", pw="wrong-password-1").status_code == 403


def test_superadmin_cannot_use_recovery(client, world):
    assert set_rec(client, "root").status_code == 403


def test_answer_is_stored_hashed(client, world, db):
    set_rec(client, "admin.a")
    row = db.query(Recovery).one()
    assert row.answer_hash.startswith("$2") and GOOD_A.lower() not in row.answer_hash.lower()


@pytest.mark.parametrize("username,answer,ok", [
    ("guest1", "scooty", True),          # attendees need 6 characters
    ("guest1", "scoot", False),
    ("admin.a", "scooty12", False),      # staff need 10 characters
    ("admin.a", "scooty1234", True),
    ("sec.a", "short", False),
    ("guest1", "purple", False),         # common colour
    ("guest1", "password", False),
    ("guest1", "aaaaaaaa", False),       # one repeated character
])
def test_answer_strength_rules(client, world, username, answer, ok):
    assert (set_rec(client, username, a=answer).status_code == 204) is ok


def test_question_length_rules(client, world):
    assert set_rec(client, "admin.a", q="Too short").status_code == 422
    assert set_rec(client, "admin.a", q="x" * 201).status_code == 422


def test_replacing_a_question_clears_a_lock(client, world, db):
    set_rec(client, "guest1", a="scooty-bike")
    row = db.query(Recovery).one()
    row.failed_attempts, row.locked_until = 3, utcnow() + timedelta(minutes=10)
    db.commit()
    set_rec(client, "guest1", q="What was my first cycle called?", a="hercules-blue")
    db.refresh(row)
    assert row.failed_attempts == 0 and row.locked_until is None and row.question.startswith("What was my first cycle")


# ---------- asking for the question ----------
def test_real_user_gets_their_own_question(client, world):
    set_rec(client, "guest1", a="scooty-bike")
    assert ask(client, "guest1").json() == {"question": GOOD_Q}
    assert ask(client, "GUEST1").json() == {"question": GOOD_Q}          # case-insensitive username


def test_unknown_and_unset_users_get_a_believable_fake_question(client, world):
    unknown = ask(client, "nobody.here")
    unset = ask(client, "admin.b")                    # exists, no question saved
    root = ask(client, "root")                        # superadmin
    for r in (unknown, unset, root):
        assert r.status_code == 200 and r.json()["question"] in rec.FAKE_QUESTIONS
    assert ask(client, "nobody.here").json() == unknown.json()           # stable, so it cannot be told apart by retrying


# ---------- resetting ----------
def test_correct_answer_changes_the_password(client, world):
    set_rec(client, "guest1", a="Scooty  Bike")
    r = reset(client, "guest1", "  scooty bike ")                          # case and spaces do not matter
    assert r.status_code == 200
    assert login_ok(client, "guest1", "brand-new-pass-77") and not login_ok(client, "guest1", PW)


def test_staff_can_recover_too(client, world):
    set_rec(client, "admin.a")
    assert reset(client, "admin.a", "blue lightning bolt").status_code == 200
    assert login_ok(client, "admin.a", "brand-new-pass-77")


def test_wrong_answer_changes_nothing_and_message_is_generic(client, world):
    set_rec(client, "guest1", a="scooty-bike")
    wrong = reset(client, "guest1", "not it")
    unknown = reset(client, "nobody.here", "whatever")
    unset = reset(client, "admin.b", "whatever")
    assert wrong.status_code == unknown.status_code == unset.status_code == 400
    assert wrong.json() == unknown.json() == unset.json() == {"detail": rec.GENERIC_FAIL}
    assert login_ok(client, "guest1", PW)


def test_five_wrong_answers_lock_recovery_even_for_the_right_answer(client, world, db):
    set_rec(client, "guest1", a="scooty-bike")
    for _ in range(rec.MAX_FAILS):
        assert reset(client, "guest1", "wrong guess").status_code == 400
    row = db.query(Recovery).one()
    assert row.locked_until is not None
    assert reset(client, "guest1", "scooty-bike").status_code == 400       # locked
    assert login_ok(client, "guest1", PW)
    row.locked_until = utcnow() - timedelta(seconds=1)                     # lock runs out
    db.commit()
    assert reset(client, "guest1", "scooty-bike").status_code == 200


def test_success_resets_the_failure_counter(client, world, db):
    set_rec(client, "guest1", a="scooty-bike")
    reset(client, "guest1", "x1"); reset(client, "guest1", "x2")
    assert db.query(Recovery).one().failed_attempts == 2
    assert reset(client, "guest1", "scooty-bike").status_code == 200
    db.expire_all()
    assert db.query(Recovery).one().failed_attempts == 0


def test_new_password_rules(client, world):
    set_rec(client, "guest1", a="scooty-bike")
    assert reset(client, "guest1", "scooty-bike", new_pw="short").status_code == 422
    assert reset(client, "guest1", "scooty-bike", new_pw="x" * 80).status_code == 422
    assert login_ok(client, "guest1", PW)


def test_superadmin_cannot_be_reset_this_way(client, world, db):
    assert reset(client, "root", "anything at all").status_code == 400
    assert login_ok(client, "root", PW)


def test_ip_rate_limit(client, world):
    for _ in range(rec.IP_LIMIT):
        assert ask(client, "guest1").status_code == 200
    assert ask(client, "guest1").status_code == 429
    assert reset(client, "guest1", "x" * 8).status_code == 429


def test_other_accounts_are_untouched(client, world):
    set_rec(client, "guest1", a="scooty-bike")
    reset(client, "guest1", "scooty-bike")
    assert login_ok(client, "admin.a", PW) and login_ok(client, "sec.a", PW)
