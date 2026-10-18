from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import User, Venue
from ..schemas import LoginIn, TokenOut, UserCreate, UserOut
from ..security import hash_password, make_token, verify_password

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalars(select(User).where(User.username == body.username.strip().lower())).first()
    if not verify_password(body.password, user.password_hash if user else None):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect username or password")
    return TokenOut(access_token=make_token(user.id, user.role, user.venue_id), role=user.role, venue_id=user.venue_id)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("superadmin"))):
    if body.venue_id is not None and db.get(Venue, body.venue_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Venue not found")
    user = User(username=body.username, password_hash=hash_password(body.password), role=body.role, venue_id=body.venue_id)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "That username is taken")
    return user
