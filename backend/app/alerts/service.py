import logging
from datetime import timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Alert, Camera, DensityReading
from ..services import camera_thresholds
from .engine import WARNING, AlertEngine

log = logging.getLogger("vista.alerts")
engine = AlertEngine()  # state memory mein hai; server restart pe reset


def _open_alert(db: Session, camera_id: int) -> Alert | None:
    return db.scalars(
        select(Alert).where(Alert.camera_id == camera_id, Alert.resolved_at.is_(None))
        .order_by(Alert.id.desc()).limit(1)
    ).first()


def process_reading(db: Session, cam: Camera, reading: DensityReading) -> None:
    """Density reading ke baad call hota hai. Kabhi ingest ko fail nahi karta."""
    try:
        th = camera_thresholds(cam)
        ts = reading.ts.replace(tzinfo=timezone.utc).timestamp()
        events = engine.update(cam.id, reading.occupancy_pct, ts, (th.caution, th.warning, th.critical))
        open_alert = _open_alert(db, cam.id)
        if open_alert and reading.occupancy_pct > open_alert.peak_pct:
            open_alert.peak_pct = reading.occupancy_pct
        for e in events:
            if e.kind == "escalated" and open_alert:
                open_alert.escalated = True
            elif e.kind == "tier_change":
                if open_alert:
                    open_alert.resolved_at = reading.ts
                open_alert = None
                if e.new_tier >= WARNING:
                    open_alert = Alert(venue_id=cam.venue_id, camera_id=cam.id, tier=e.new_tier,
                                       peak_pct=reading.occupancy_pct, started_at=reading.ts)
                    db.add(open_alert)
        db.commit()
    except Exception:  # alert bug se density ingest nahi rukna chahiye
        db.rollback()
        log.exception("alert processing failed")
