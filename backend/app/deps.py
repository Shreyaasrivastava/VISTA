import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .db import get_db
from .models import Camera, User, Venue
from .security import decode_token

bearer = HTTPBearer(auto_error=False)


def _unauthorized() -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated", headers={"WWW-Authenticate": "Bearer"})


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)
) -> User:
    if creds is None:
        raise _unauthorized()
    try:
        payload = decode_token(creds.credentials)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise _unauthorized()
    user = db.get(User, user_id)
    if user is None:
        raise _unauthorized()
    # Role and venue come from the database, not from the token, so changes apply at once.
    return user


def require_roles(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot do this")
        return user

    return checker


def venue_for(user: User, venue_id: int, db: Session) -> Venue:
    """Return the venue if this user may see it. Other venues look like they do not exist (404)."""
    venue = db.get(Venue, venue_id)
    if venue is None or (user.role != "superadmin" and user.venue_id != venue_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Venue not found")
    return venue


def camera_for(user: User, camera_id: int, db: Session) -> Camera:
    camera = db.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Camera not found")
    venue_for(user, camera.venue_id, db)  # 404 if it belongs to another venue
    return camera
