from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import ValidationError
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import camera_for, require_roles, venue_for
from ..models import Camera, DensityReading, User
from ..schemas import CameraBase, CameraCreated, CameraOut, DensityOut
from ..security import new_ingest_key
from ..services import camera_out, camera_thresholds, next_camera_code, polygon_area, reading_out

router = APIRouter(tags=["cameras"])
STAFF = ("superadmin", "admin", "security")
EDITORS = ("superadmin", "admin")


def _apply(cam: Camera, data: CameraBase) -> None:
    cam.zone_name = data.zone_name
    cam.stream_url = data.stream_url
    cam.ip_address = data.ip_address
    cam.range_m = data.range_m
    cam.th_caution, cam.th_warning, cam.th_critical = data.thresholds.caution, data.thresholds.warning, data.thresholds.critical
    cam.zone_polygon = data.zone_polygon
    cam.camera_xy = data.camera_xy
    cam.homography = data.homography
    if data.zone_polygon is None:
        cam.area_sqm = None
    else:
        area = polygon_area(data.zone_polygon)
        if area <= 0:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "zone_polygon must have a non-zero area")
        cam.area_sqm = round(area, 3)


@router.get("/venues/{venue_id}/cameras", response_model=list[CameraOut])
def list_cameras(venue_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*STAFF))):
    venue_for(user, venue_id, db)
    cams = db.scalars(select(Camera).where(Camera.venue_id == venue_id).order_by(Camera.code)).all()
    return [camera_out(c) for c in cams]


@router.post("/venues/{venue_id}/cameras", response_model=CameraCreated, status_code=201)
def create_camera(
    venue_id: int, body: CameraBase, db: Session = Depends(get_db), user: User = Depends(require_roles(*EDITORS)),
):
    venue_for(user, venue_id, db)
    key, key_hash = new_ingest_key()
    cam = Camera(venue_id=venue_id, code=next_camera_code(db, venue_id), ingest_key_hash=key_hash)
    _apply(cam, body)
    db.add(cam)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Could not create the camera, try again")
    return CameraCreated(**camera_out(cam), ingest_key=key)


@router.get("/cameras/{camera_id}", response_model=CameraOut)
def get_camera(camera_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*STAFF))):
    return camera_out(camera_for(user, camera_id, db))


@router.patch("/cameras/{camera_id}", response_model=CameraOut)
def patch_camera(
    camera_id: int, body: dict, db: Session = Depends(get_db), user: User = Depends(require_roles(*EDITORS)),
):
    cam = camera_for(user, camera_id, db)
    current = camera_out(cam)
    allowed = {"zone_name", "stream_url", "ip_address", "range_m", "thresholds", "zone_polygon", "camera_xy", "homography"}
    unknown = set(body) - allowed
    if unknown:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Cannot change: {', '.join(sorted(unknown))}")
    merged = {k: current[k] for k in allowed} | body
    try:
        data = CameraBase(**merged)
    except ValidationError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, e.errors(include_url=False, include_context=False, include_input=False))
    _apply(cam, data)
    db.commit()
    return camera_out(cam)


@router.delete("/cameras/{camera_id}", status_code=204)
def delete_camera(camera_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*EDITORS))):
    cam = camera_for(user, camera_id, db)
    db.execute(delete(DensityReading).where(DensityReading.camera_id == cam.id))
    db.delete(cam)
    db.commit()
    return Response(status_code=204)


@router.post("/cameras/{camera_id}/rotate-key", response_model=dict)
def rotate_key(camera_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*EDITORS))):
    cam = camera_for(user, camera_id, db)
    key, key_hash = new_ingest_key()
    cam.ingest_key_hash = key_hash
    db.commit()
    return {"ingest_key": key}


@router.get("/cameras/{camera_id}/density", response_model=list[DensityOut])
def camera_density(
    camera_id: int, limit: int = Query(100, ge=1, le=1000), since: datetime | None = None,
    db: Session = Depends(get_db), user: User = Depends(require_roles(*STAFF)),
):
    cam = camera_for(user, camera_id, db)
    q = select(DensityReading).where(DensityReading.camera_id == cam.id)
    if since is not None:
        q = q.where(DensityReading.ts >= since.replace(tzinfo=None))
    rows = db.scalars(q.order_by(DensityReading.ts.desc(), DensityReading.id.desc()).limit(limit)).all()
    return [reading_out(r) for r in rows]
