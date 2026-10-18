"""Create demo venues, users and cameras. Run once: python -m app.seed

Passwords and camera ingest keys are random and printed ONCE here (only hashes are stored).
Set SEED_PASSWORD to use one password for every demo user instead.
"""
import os
import secrets

from sqlalchemy import select

from .db import SessionLocal
from .models import Camera, User, Venue
from .security import hash_password, new_ingest_key
from .services import next_camera_code, polygon_area


def rect(x, y, w, h):
    return [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]


# (venue, city, admin username, security username, [(zone, w, h, ip)])
DEMO = [
    ("Jaipur Junction Railway Station", "Jaipur", "jaipur.admin", "jaipur.security",
     [("Platform 1", 14, 10, "10.0.4.21"), ("Foot overbridge", 12, 5, "10.0.4.22"), ("Main concourse", 20, 15, "10.0.4.23")]),
    ("Govind Dev Ji Temple", "Jaipur", "govind.admin", "govind.security",
     [("Entry courtyard", 20, 11, "10.0.7.10"), ("Inner hall", 10, 9, "10.0.7.11")]),
    ("SMS Stadium", "Jaipur", "stadium.admin", "stadium.security",
     [("Gate 3 approach", 18, 10, "10.0.9.31")]),
]


def main():
    shared = os.environ.get("SEED_PASSWORD")
    db = SessionLocal()
    lines = []

    def make_user(username, role, venue_id):
        if db.scalars(select(User).where(User.username == username)).first():
            return
        pw = shared or secrets.token_urlsafe(12)
        db.add(User(username=username, password_hash=hash_password(pw), role=role, venue_id=venue_id))
        lines.append(f"  user   {username:<18} {role:<10} password: {pw}")

    make_user("platform.admin", "superadmin", None)
    make_user("attendee", "attendee", None)
    for name, city, admin, sec, zones in DEMO:
        venue = db.scalars(select(Venue).where(Venue.name == name)).first()
        if venue is None:
            venue = Venue(name=name, city=city)
            db.add(venue)
            db.flush()
        make_user(admin, "admin", venue.id)
        make_user(sec, "security", venue.id)
        for i, (zone, w, h, ip) in enumerate(zones):
            exists = db.scalars(select(Camera).where(Camera.venue_id == venue.id, Camera.zone_name == zone)).first()
            if exists:
                continue
            key, key_hash = new_ingest_key()
            poly = rect(i * 25, 0, w, h)
            db.add(Camera(
                venue_id=venue.id, code=next_camera_code(db, venue.id), zone_name=zone,
                stream_url=f"rtsp://{ip}/s1", ip_address=ip, range_m=35, zone_polygon=poly,
                area_sqm=polygon_area(poly), camera_xy=[i * 25 + w / 2, -3],
                homography=[[1, 0, 0], [0, 1, 0], [0, 0, 1]],  # placeholder until the camera is really calibrated
                ingest_key_hash=key_hash,
            ))
            db.flush()
            lines.append(f"  camera {venue.name} / {zone:<16} ingest key: {key}")
    db.commit()
    print("Seeded. Save this now, it is not shown again:" if lines else "Nothing to seed, everything exists.")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
