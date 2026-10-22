"""Forgot-password by recovery question.

Safeguards, because recovery questions are the weakest way back into an account:
- the answer is stored as a bcrypt hash, never as text, and is compared after normalising case and spaces
- 5 wrong answers lock recovery for that account for 15 minutes
- at most 20 recovery requests per 15 minutes from one IP address (kept in memory, single process)
- unknown usernames and accounts without a question get a believable fake question and the same error
  messages, so nobody can use this form to find out who has an account
- weak answers (very short, common colours, and so on) are refused
- the platform admin (superadmin) cannot use this. Use: python -m app.reset_password
"""
import hashlib
import time
import unicodedata
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..deps import get_current_user
from ..models import Recovery, User, utcnow
from ..security import hash_password, password_ok_length, verify_password

router = APIRouter(tags=["recovery"])

# Roles that may recover their own password with a question. Remove "admin" and "security"
# if you would rather have staff passwords reset by the platform admin only.
ALLOWED_ROLES = {"attendee", "admin", "security"}
MIN_ANSWER = {"attendee": 6, "admin": 10, "security": 10}   # characters, after normalising
MAX_FAILS = 5
LOCK_MINUTES = 15
IP_LIMIT = 20
IP_WINDOW_SECONDS = 900
MIN_PASSWORD = 10

WEAK_ANSWERS = {
    "red", "blue", "green", "yellow", "black", "white", "purple", "orange", "pink", "brown", "grey", "gray",
    "password", "qwerty", "123456", "1234567", "12345678", "iloveyou", "jaipur", "india", "delhi", "rajasthan",
}
FAKE_QUESTIONS = [
    "What was the name of your first school?",
    "What is the name of the street you grew up on?",
    "What was the name of your childhood best friend?",
    "What was the name of your first pet?",
    "In which town did your parents meet?",
    "What was the name of your first teacher?",
]
GENERIC_FAIL = "That answer is not right, or recovery is locked for a while. Try again later, or ask the platform admin to reset your password."

_attempts: dict[str, list[float]] = {}


def reset_limiter() -> None:
    _attempts.clear()


def _ip_limited(request: Request) -> bool:
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    recent = [t for t in _attempts.get(ip, []) if now - t < IP_WINDOW_SECONDS]
    if len(recent) >= IP_LIMIT:
        _attempts[ip] = recent
        return True
    recent.append(now)
    _attempts[ip] = recent
    if len(_attempts) > 10000:                      # keep memory bounded
        for k in [k for k, v in _attempts.items() if not v or now - v[-1] >= IP_WINDOW_SECONDS]:
            _attempts.pop(k, None)
    return False


def _guard(request: Request) -> None:
    if _ip_limited(request):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts. Wait a few minutes and try again.")


def normalise(answer: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", answer).lower().split())


def answer_problem(answer: str, role: str) -> str | None:
    """Return a message if the answer is too weak, otherwise None."""
    a = normalise(answer)
    need = MIN_ANSWER.get(role, 10)
    if len(a) < need:
        return f"Use an answer of at least {need} characters."
    if len(a.encode()) > 72:
        return "Use an answer of at most 60 characters."
    if a in WEAK_ANSWERS or len(set(a.replace(" ", ""))) < 4:
        return "That answer is too easy to guess. Pick something only you would know."
    return None


def set_recovery(db: Session, user: User, question: str, answer: str) -> None:
    """Save or replace a user's recovery question. Raises ValueError with a message if the answer is weak.
    Call this from signup too, after the user row exists (it commits)."""
    if user.role not in ALLOWED_ROLES:
        raise ValueError("This account type cannot use a recovery question.")
    q = " ".join(question.split())
    if not (10 <= len(q) <= 160):
        raise ValueError("The question must be 10 to 160 characters.")
    problem = answer_problem(answer, user.role)
    if problem:
        raise ValueError(problem)
    row = db.get(Recovery, user.id)
    if row is None:
        row = Recovery(user_id=user.id, question=q, answer_hash=hash_password(normalise(answer)))
        db.add(row)
    else:
        row.question, row.answer_hash = q, hash_password(normalise(answer))
        row.failed_attempts, row.locked_until, row.updated_at = 0, None, utcnow()
    db.commit()


def _fake_question(username: str) -> str:
    seed = hashlib.sha256((username + get_settings().jwt_secret).encode()).digest()
    return FAKE_QUESTIONS[seed[0] % len(FAKE_QUESTIONS)]


# ---------- schemas ----------
class QuestionIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)


class QuestionOut(BaseModel):
    question: str


class ResetIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    answer: str = Field(min_length=1, max_length=120)
    new_password: str = Field(min_length=MIN_PASSWORD, max_length=72)


class SetRecoveryIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=72)
    question: str = Field(min_length=1, max_length=200)
    answer: str = Field(min_length=1, max_length=120)


class RecoveryStatus(BaseModel):
    has_recovery: bool
    question: str | None


def _find(db: Session, username: str):
    user = db.scalars(select(User).where(User.username == username.strip().lower())).first()
    row = db.get(Recovery, user.id) if user and user.role in ALLOWED_ROLES else None
    return user, row


# ---------- public endpoints ----------
@router.post("/auth/recovery/question", response_model=QuestionOut)
def get_question(body: QuestionIn, request: Request, db: Session = Depends(get_db)):
    _guard(request)
    _, row = _find(db, body.username)
    return QuestionOut(question=row.question if row else _fake_question(body.username.strip().lower()))


@router.post("/auth/recovery/reset")
def reset_password(body: ResetIn, request: Request, db: Session = Depends(get_db)):
    _guard(request)
    if not password_ok_length(body.new_password):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Use a password of at most 72 bytes.")
    user, row = _find(db, body.username)
    locked = bool(row and row.locked_until and row.locked_until > utcnow())
    # Always do exactly one bcrypt comparison, so timing does not reveal whether the account exists.
    matches = verify_password(normalise(body.answer), row.answer_hash if row else None)
    if row is None or locked or not matches:
        if row is not None and not locked:
            row.failed_attempts += 1
            if row.failed_attempts >= MAX_FAILS:
                row.locked_until = utcnow() + timedelta(minutes=LOCK_MINUTES)
                row.failed_attempts = 0
            db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, GENERIC_FAIL)
    user.password_hash = hash_password(body.new_password)
    row.failed_attempts, row.locked_until = 0, None
    db.commit()
    return {"detail": "Password changed. You can log in with the new password."}


# ---------- logged-in endpoints ----------
@router.get("/me/recovery", response_model=RecoveryStatus)
def my_recovery(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(Recovery, user.id)
    return RecoveryStatus(has_recovery=row is not None, question=row.question if row else None)


@router.put("/me/recovery", status_code=204)
def save_my_recovery(body: SetRecoveryIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in ALLOWED_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account type cannot use a recovery question.")
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your current password is not right.")
    try:
        set_recovery(db, user, body.question, body.answer)
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e))
    return Response(status_code=204)
