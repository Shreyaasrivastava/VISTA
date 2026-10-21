import hmac
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models import User, Venue
from ..schemas import USERNAME_RE
from ..security import hash_password, password_ok_length

router = APIRouter(prefix="/auth", tags=["auth"])
ROLE = {"organiser": "admin", "security": "security", "attendee": "attendee"}


class SignupIn(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=8, max_length=72)
    role: Literal["organiser", "security", "attendee"]
    venue_id: Optional[int] = None
    access_code: Optional[str] = None


def code_ok(given, expected):
    return bool(expected) and hmac.compare_digest((given or "").encode(), expected.encode())


@router.post("/signup", status_code=201)
def signup(body: SignupIn, db: Session = Depends(get_db)):
    cfg = get_settings()
    username = body.username.strip().lower()
    if len(username) < 3 or not USERNAME_RE.match(username):
        raise HTTPException(422, "Username may use letters, digits, dot, dash and underscore (at least 3 characters)")
    if not password_ok_length(body.password):
        raise HTTPException(422, "Password is too long (72 bytes at most)")
    if db.scalars(select(User).where(User.username == username)).first():
        raise HTTPException(409, "That username is already taken")

    needs_venue = body.role in ("organiser", "security")
    if body.role == "organiser" and not code_ok(body.access_code, cfg.organiser_code):
        raise HTTPException(403, "Wrong or missing organiser access code")
    if body.role == "security" and not code_ok(body.access_code, cfg.security_code):
        raise HTTPException(403, "Wrong or missing security access code")
    if needs_venue:
        if body.venue_id is None:
            raise HTTPException(422, "Choose your venue")
        if db.get(Venue, body.venue_id) is None:
            raise HTTPException(422, "That venue does not exist")

    user = User(username=username, password_hash=hash_password(body.password), role=ROLE[body.role],
                venue_id=body.venue_id if needs_venue else None)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "That username is already taken")
    return {"ok": True, "username": username, "role": ROLE[body.role]}