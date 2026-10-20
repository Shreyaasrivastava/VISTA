from datetime import timedelta
from sqlalchemy import insert, text
from app.db import engine
from app.routers.public import events, meta, utcnow

meta.create_all(engine)
with engine.begin() as con:
    venues = con.execute(text("SELECT * FROM venues")).mappings().all()
    if not venues:
        raise SystemExit("No venues found. Create your venues first, then run this again.")

    def pick(word):                      # choose a venue whose name contains the word
        for v in venues:
            if word in v["name"].lower():
                return v
        return venues[0]

    now = utcnow()
    plan = [  # title, description, venue keyword, starts in (hours), ends in (hours)
        ("Evening Aarti and Darshan", "Large evening gathering, the entry courtyard gets busy.", "temple", -1, 3),
        ("State Cricket Match", "Gates open two hours before the toss.", "stadium", -2, 5),
        ("Festival Travel Rush", "Extra trains and heavy platform traffic.", "railway", 20, 30),
        ("Weekend Cultural Fair", "Stalls, music and food, expect crowds after 5 pm.", "temple", 48, 56),
    ]
    con.execute(events.delete())
    for title, desc, word, s, e in plan:
        con.execute(insert(events).values(title=title, venue_id=str(pick(word)["id"]), description=desc,
                                          starts_at=now + timedelta(hours=s), ends_at=now + timedelta(hours=e)))
    print("Added", len(plan), "events")