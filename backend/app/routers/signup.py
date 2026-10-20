import hmac
from typing import Literal, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..config import get_settings
from ..db import get_db
from ..models import User                    # same import auth.py uses
from ..security import hash_password         # CHANGE to the real file and name from Step 1

router = APIRouter(prefix="/auth", tags=["auth"])
ROLE = {"organiser": "admin", "security": "security", "attendee": "attendee"}   # CHANGE if your role words differ


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
    if db.scalars(select(User).where(User.username == username)).first():
        raise HTTPException(409, "That username is already taken")
    if body.role == "organiser":
        if not code_ok(body.access_code, cfg.organiser_code):
            raise HTTPException(403, "Wrong or missing organiser access code")
        if body.venue_id is None:
            raise HTTPException(422, "Choose your venue")
    if body.role == "security" and not code_ok(body.access_code, cfg.security_code):
        raise HTTPException(403, "Wrong or missing security access code")
    user = User(username=username, password_hash=hash_password(body.password), role=ROLE[body.role],
                venue_id=body.venue_id if body.role == "organiser" else None)
    db.add(user)
    db.commit()
    return {"ok": True, "username": username, "role": ROLE[body.role]}