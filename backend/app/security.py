import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from .config import get_settings

ALGORITHM = "HS256"
_DUMMY_HASH = bcrypt.hashpw(b"not-a-real-password", bcrypt.gensalt(rounds=4)).decode()


def password_ok_length(password: str) -> bool:
    return 0 < len(password.encode()) <= 72  # bcrypt limit


def hash_password(password: str) -> str:
    if not password_ok_length(password):
        raise ValueError("password must be 1 to 72 bytes")
    rounds = get_settings().bcrypt_rounds
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=rounds)).decode()


def verify_password(password: str, password_hash: str | None) -> bool:
    """Always does one bcrypt check, so a wrong username takes as long as a wrong password."""
    target = password_hash or _DUMMY_HASH
    try:
        ok = password_ok_length(password) and bcrypt.checkpw(password.encode(), target.encode())
    except ValueError:
        ok = False
    return ok and password_hash is not None


def make_token(user_id: int, role: str, venue_id: int | None) -> str:
    s = get_settings()
    exp = datetime.now(timezone.utc) + timedelta(minutes=s.jwt_minutes)
    payload = {"sub": str(user_id), "role": role, "venue_id": venue_id, "exp": exp}
    return jwt.encode(payload, s.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGORITHM])


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def new_ingest_key() -> tuple[str, str]:
    key = secrets.token_urlsafe(32)
    return key, hash_key(key)
