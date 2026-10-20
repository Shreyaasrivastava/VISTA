from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, Text, select, text
from sqlalchemy.orm import Session
from ..db import engine, get_db

router = APIRouter(tags=["public"])
meta = MetaData()
events = Table(
    "events", meta,
    Column("id", Integer, primary_key=True),
    Column("title", String(120), nullable=False),
    Column("venue_id", String(64), nullable=False),
    Column("description", Text, default=""),
    Column("starts_at", DateTime, nullable=False),
    Column("ends_at", DateTime, nullable=False),
)
meta.create_all(engine)          # creates the events table if it does not exist


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def venue_map(db):
    rows = db.execute(text("SELECT * FROM venues")).mappings().all()
    return {str(v["id"]): v for v in rows}


@router.get("/events")
def list_events(db: Session = Depends(get_db)):
    now, out = utcnow(), []
    venues = venue_map(db)
    for r in db.execute(select(events).order_by(events.c.starts_at)).mappings().all():
        if r["ends_at"] < now:
            continue                                   # already finished
        v = venues.get(str(r["venue_id"]), {})
        out.append({
            "id": r["id"], "title": r["title"], "description": r["description"] or "",
            "venue": v.get("name"), "city": v.get("city"),
            "starts_at": r["starts_at"].isoformat(), "ends_at": r["ends_at"].isoformat(),
            "status": "live" if r["starts_at"] <= now else "upcoming",
        })
    return out


@router.get("/public/venues")
def public_venues(db: Session = Depends(get_db)):
    return [{"id": v["id"], "name": v.get("name"), "city": v.get("city")} for v in venue_map(db).values()]