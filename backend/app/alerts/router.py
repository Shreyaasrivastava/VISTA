from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_roles, venue_for
from ..models import Alert, Camera, User
from ..schemas import TIER_NAMES, iso_utc

router = APIRouter(tags=["alerts"])
STAFF = ("superadmin", "admin", "security")


@router.get("/venues/{venue_id}/alerts")
def list_alerts(venue_id: int, active_only: bool = False, limit: int = 100,
                db: Session = Depends(get_db), user: User = Depends(require_roles(*STAFF))):
    venue_for(user, venue_id, db)  # dusre venue ke liye 404
    q = (select(Alert, Camera).join(Camera, Camera.id == Alert.camera_id)
         .where(Alert.venue_id == venue_id).order_by(Alert.started_at.desc(), Alert.id.desc())
         .limit(max(1, min(limit, 500))))
    if active_only:
        q = q.where(Alert.resolved_at.is_(None))
    return [{
        "id": a.id, "camera_id": a.camera_id, "camera_code": c.code, "zone_name": c.zone_name,
        "tier": a.tier, "tier_name": TIER_NAMES[a.tier], "peak_pct": round(a.peak_pct, 2),
        "escalated": a.escalated, "started_at": iso_utc(a.started_at),
        "resolved_at": iso_utc(a.resolved_at) if a.resolved_at else None,
    } for a, c in db.execute(q).all()]
