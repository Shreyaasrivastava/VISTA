from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Camera, DensityReading
from .schemas import TIER_NAMES, CameraOut, DensityOut, Thresholds, iso_utc


def polygon_area(poly: list[list[float]]) -> float:
    """Shoelace formula. Returns square metres."""
    total = 0.0
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        total += x1 * y2 - x2 * y1
    return abs(total) / 2


def occupancy_pct(count: int, area_sqm: float, ref_density: float) -> float:
    return count / (area_sqm * ref_density) * 100


def tier_for(pct: float, th: Thresholds) -> int:
    """Half-open bands: [0, caution) Normal, [caution, warning) Caution, [warning, critical) Warning, [critical, ...) Critical."""
    if pct < th.caution:
        return 0
    if pct < th.warning:
        return 1
    if pct < th.critical:
        return 2
    return 3


def camera_thresholds(cam: Camera) -> Thresholds:
    return Thresholds(caution=cam.th_caution, warning=cam.th_warning, critical=cam.th_critical)


def camera_out(cam: Camera) -> dict:
    return CameraOut(
        id=cam.id, venue_id=cam.venue_id, code=cam.code, zone_name=cam.zone_name,
        stream_url=cam.stream_url, ip_address=cam.ip_address, range_m=cam.range_m,
        thresholds=camera_thresholds(cam), zone_polygon=cam.zone_polygon, area_sqm=cam.area_sqm,
        camera_xy=cam.camera_xy, homography=cam.homography,
        calibrated=bool(cam.zone_polygon and cam.area_sqm and cam.camera_xy and cam.homography),
    ).model_dump()


def reading_out(r: DensityReading) -> DensityOut:
    return DensityOut(
        id=r.id, camera_id=r.camera_id, ts=iso_utc(r.ts), people_count=r.people_count,
        density=round(r.density, 4), occupancy_pct=round(r.occupancy_pct, 2), tier=r.tier,
        tier_name=TIER_NAMES[r.tier], confidence=r.confidence, degraded=r.degraded,
    )


def latest_reading(db: Session, camera_id: int) -> DensityReading | None:
    return db.scalars(
        select(DensityReading).where(DensityReading.camera_id == camera_id)
        .order_by(DensityReading.ts.desc(), DensityReading.id.desc()).limit(1)
    ).first()


def next_camera_code(db: Session, venue_id: int) -> str:
    codes = db.scalars(select(Camera.code).where(Camera.venue_id == venue_id)).all()
    nums = [int(c.split("-")[1]) for c in codes if c.startswith("CAM-") and c.split("-")[1].isdigit()]
    return f"CAM-{(max(nums) + 1) if nums else 1:02d}"
