from datetime import datetime, timezone

from sqlalchemy import (
    JSON, Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer,
    String, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def utcnow() -> datetime:
    """Naive UTC. All timestamps in the database are UTC."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Venue(Base):
    __tablename__ = "venues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    city: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role in ('superadmin','admin','security','attendee')", name="ck_users_role"),
        CheckConstraint(
            "role in ('superadmin','attendee') or venue_id is not null", name="ck_users_venue_required"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20))
    venue_id: Mapped[int | None] = mapped_column(ForeignKey("venues.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Camera(Base):
    __tablename__ = "cameras"
    __table_args__ = (UniqueConstraint("venue_id", "code", name="uq_camera_venue_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    venue_id: Mapped[int] = mapped_column(ForeignKey("venues.id"), index=True)
    code: Mapped[str] = mapped_column(String(20))
    zone_name: Mapped[str] = mapped_column(String(80))
    stream_url: Mapped[str] = mapped_column(String(300))
    ip_address: Mapped[str] = mapped_column(String(15))
    range_m: Mapped[float] = mapped_column(Float)
    th_caution: Mapped[float] = mapped_column(Float, default=50)
    th_warning: Mapped[float] = mapped_column(Float, default=75)
    th_critical: Mapped[float] = mapped_column(Float, default=90)
    # Calibration, all in the venue coordinate frame (metres).
    zone_polygon: Mapped[list | None] = mapped_column(JSON, nullable=True)
    area_sqm: Mapped[float | None] = mapped_column(Float, nullable=True)
    camera_xy: Mapped[list | None] = mapped_column(JSON, nullable=True)
    homography: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ingest_key_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class DensityReading(Base):
    __tablename__ = "density_readings"
    __table_args__ = (Index("ix_density_camera_ts", "camera_id", "ts"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id"))
    venue_id: Mapped[int] = mapped_column(ForeignKey("venues.id"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime)
    people_count: Mapped[int] = mapped_column(Integer)
    density: Mapped[float] = mapped_column(Float)
    occupancy_pct: Mapped[float] = mapped_column(Float)
    tier: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    degraded: Mapped[bool] = mapped_column(Boolean, default=False)
class Recovery(Base):
    """Password recovery question for one user. The answer is stored only as a hash."""
    __tablename__ = "recoveries"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    question: Mapped[str] = mapped_column(String(160))
    answer_hash: Mapped[str] = mapped_column(String(100))
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)