from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_roles, venue_for
from ..models import Camera, User, Venue
from ..schemas import LatestZoneOut, VenueIn, VenueOut, VenuePatch
from ..services import latest_reading, reading_out

router = APIRouter(tags=["venues"])
STAFF = ("superadmin", "admin", "security")


@router.get("/venues", response_model=list[VenueOut])
def list_venues(db: Session = Depends(get_db), user: User = Depends(require_roles(*STAFF))):
    q = select(Venue).order_by(Venue.id)
    if user.role != "superadmin":
        q = q.where(Venue.id == user.venue_id)
    return db.scalars(q).all()


@router.post("/venues", response_model=VenueOut, status_code=201)
def create_venue(body: VenueIn, db: Session = Depends(get_db), _: User = Depends(require_roles("superadmin"))):
    venue = Venue(name=body.name.strip(), city=body.city.strip())
    db.add(venue)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "A venue with that name exists")
    return venue


@router.get("/venues/{venue_id}", response_model=VenueOut)
def get_venue(venue_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*STAFF))):
    return venue_for(user, venue_id, db)


@router.patch("/venues/{venue_id}", response_model=VenueOut)
def patch_venue(
    venue_id: int, body: VenuePatch, db: Session = Depends(get_db),
    user: User = Depends(require_roles("superadmin", "admin")),
):
    venue = venue_for(user, venue_id, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(venue, field, value.strip())
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "A venue with that name exists")
    return venue


@router.get("/venues/{venue_id}/density/latest", response_model=list[LatestZoneOut])
def latest_density(venue_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*STAFF))):
    venue_for(user, venue_id, db)
    cams = db.scalars(select(Camera).where(Camera.venue_id == venue_id).order_by(Camera.code)).all()
    out = []
    for c in cams:
        r = latest_reading(db, c.id)
        out.append(LatestZoneOut(camera_id=c.id, code=c.code, zone_name=c.zone_name, reading=reading_out(r) if r else None))
    return out
