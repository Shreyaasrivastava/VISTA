from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models import Camera, DensityReading, utcnow
from ..schemas import DensityIn, DensityOut
from ..security import hash_key
from ..services import camera_thresholds, occupancy_pct, reading_out, tier_for

router = APIRouter(tags=["density"])


@router.post("/density-events", response_model=DensityOut, status_code=201)
def post_density(body: DensityIn, x_camera_key: str | None = Header(default=None), db: Session = Depends(get_db)):
    """Called by the vision service. It authenticates with the camera's ingest key, not a user login."""
    if not x_camera_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing X-Camera-Key header")
    cam = db.scalars(select(Camera).where(Camera.ingest_key_hash == hash_key(x_camera_key))).first()
    if cam is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown camera key")
    if not cam.area_sqm:
        raise HTTPException(status.HTTP_409_CONFLICT, "This camera has no zone polygon yet. Calibrate it first.")
    pct = occupancy_pct(body.people_count, cam.area_sqm, get_settings().ref_density)
    reading = DensityReading(
        camera_id=cam.id, venue_id=cam.venue_id, ts=body.ts or utcnow(), people_count=body.people_count,
        density=body.people_count / cam.area_sqm, occupancy_pct=pct,
        tier=tier_for(pct, camera_thresholds(cam)), confidence=body.confidence, degraded=body.degraded,
    )
    db.add(reading)
    db.commit()
    return reading_out(reading)
