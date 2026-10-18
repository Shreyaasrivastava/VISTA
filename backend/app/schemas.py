import ipaddress
import re
from datetime import datetime, timedelta, timezone
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TIER_NAMES = ["Normal", "Caution", "Warning", "Critical"]
USERNAME_RE = re.compile(r"^[a-z0-9._-]+$")


def iso_utc(dt: datetime) -> str:
    return dt.replace(tzinfo=None).isoformat(timespec="seconds") + "Z"


# ---------- auth and users ----------
class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=72)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    venue_id: int | None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    role: str
    venue_id: int | None


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=10, max_length=72)
    role: Literal["admin", "security", "attendee"]
    venue_id: int | None = None

    @field_validator("username")
    @classmethod
    def _username(cls, v: str) -> str:
        if not USERNAME_RE.match(v):
            raise ValueError("username may use lowercase letters, digits, dot, dash and underscore")
        return v

    @model_validator(mode="after")
    def _venue_rule(self):
        if self.role in ("admin", "security") and self.venue_id is None:
            raise ValueError("admin and security accounts need a venue_id")
        if self.role == "attendee" and self.venue_id is not None:
            raise ValueError("attendee accounts have no venue_id")
        return self


# ---------- venues ----------
class VenueIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    city: str = Field(min_length=2, max_length=80)


class VenuePatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    city: str | None = Field(default=None, min_length=2, max_length=80)


class VenueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    city: str


# ---------- cameras ----------
class Thresholds(BaseModel):
    caution: float = 50
    warning: float = 75
    critical: float = 90

    @model_validator(mode="after")
    def _order(self):
        if not (0 < self.caution < self.warning < self.critical <= 100):
            raise ValueError("thresholds must increase: 0 < caution < warning < critical <= 100")
        return self


class CameraBase(BaseModel):
    zone_name: str = Field(min_length=1, max_length=80)
    stream_url: str = Field(max_length=300)
    ip_address: str
    range_m: float = Field(gt=0, le=200)
    thresholds: Thresholds = Thresholds()
    zone_polygon: list[list[float]] | None = None
    camera_xy: list[float] | None = None
    homography: list[list[float]] | None = None

    @field_validator("stream_url")
    @classmethod
    def _url(cls, v: str) -> str:
        p = urlparse(v)
        if p.scheme not in ("rtsp", "rtmp", "http", "https") or not p.hostname or re.search(r"\s", v):
            raise ValueError("stream_url must look like rtsp://host/path (rtsp, rtmp, http or https)")
        return v

    @field_validator("ip_address")
    @classmethod
    def _ip(cls, v: str) -> str:
        try:
            ipaddress.IPv4Address(v)
        except ValueError:
            raise ValueError("ip_address must be a valid IPv4 address, like 10.0.4.21")
        return v

    @field_validator("zone_polygon")
    @classmethod
    def _poly(cls, v):
        if v is None:
            return v
        if len(v) < 3 or any(len(p) != 2 for p in v):
            raise ValueError("zone_polygon needs at least 3 points, each [x, y] in metres")
        return v

    @field_validator("camera_xy")
    @classmethod
    def _xy(cls, v):
        if v is not None and len(v) != 2:
            raise ValueError("camera_xy must be [x, y] in metres")
        return v

    @field_validator("homography")
    @classmethod
    def _h(cls, v):
        if v is not None and (len(v) != 3 or any(len(r) != 3 for r in v)):
            raise ValueError("homography must be a 3 by 3 matrix")
        return v


class CameraOut(BaseModel):
    id: int
    venue_id: int
    code: str
    zone_name: str
    stream_url: str
    ip_address: str
    range_m: float
    thresholds: Thresholds
    zone_polygon: list[list[float]] | None
    area_sqm: float | None
    camera_xy: list[float] | None
    homography: list[list[float]] | None
    calibrated: bool


class CameraCreated(CameraOut):
    ingest_key: str


# ---------- density ----------
class DensityIn(BaseModel):
    people_count: int = Field(ge=0, le=20000)
    confidence: float | None = Field(default=None, ge=0, le=1)
    degraded: bool = False
    ts: datetime | None = None

    @field_validator("ts")
    @classmethod
    def _ts(cls, v):
        if v is None:
            return v
        if v.tzinfo is not None:
            v = v.astimezone(timezone.utc).replace(tzinfo=None)
        if v > datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=5):
            raise ValueError("ts is in the future")
        return v


class DensityOut(BaseModel):
    id: int
    camera_id: int
    ts: str
    people_count: int
    density: float
    occupancy_pct: float
    tier: int
    tier_name: str
    confidence: float | None
    degraded: bool


class LatestZoneOut(BaseModel):
    camera_id: int
    code: str
    zone_name: str
    reading: DensityOut | None
