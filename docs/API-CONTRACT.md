# VISTA API contract (Phase 1, v0.1)

Draft for the Phase 0 contract. Change it here first, then in code.

## Conventions

- **Base URL:** `http://localhost:8000` in development. Interactive docs at `/docs`, machine-readable spec at `/openapi.json` (Postman can import it).
- **Auth:** `POST /auth/login` returns a JWT. Send it as `Authorization: Bearer <token>`. Tokens last 60 minutes by default.
- **Time:** UTC, ISO 8601, always ending in `Z` (for example `2026-10-18T09:30:00Z`).
- **Units:** distances in metres, areas in square metres, density in people per square metre, occupancy in percent.
- **Venue coordinate frame:** every venue picks one origin. x and y are metres from it. All cameras of a venue are calibrated into this same frame, so overlapping cameras can be merged in Phase 4.
- **Errors:** JSON `{"detail": ...}`. `401` not logged in or bad key, `403` your role cannot do this, `404` not found **or belongs to another venue** (we do not reveal which), `409` conflict, `422` invalid input.

## Roles

| Role | Venue bound | Can do |
|---|---|---|
| `superadmin` | no | create venues and users, see every venue |
| `admin` | yes | manage cameras and the venue, read density, own venue only |
| `security` | yes | read cameras and density, own venue only |
| `attendee` | no | nothing in Phase 1 (registration comes in Phase 4) |

Role and venue are read from the database on every request, not from the token.

## Endpoints

| Method and path | Who | Purpose |
|---|---|---|
| `POST /auth/login` | anyone | username and password in, token out |
| `GET /me` | any user | the logged-in user |
| `POST /users` | superadmin | create an admin, security or attendee account |
| `GET /venues` | staff | venues you may see |
| `POST /venues` | superadmin | create a venue |
| `GET /venues/{id}` | staff | one venue |
| `PATCH /venues/{id}` | admin, superadmin | rename or change city |
| `GET /venues/{id}/cameras` | staff | cameras of the venue |
| `POST /venues/{id}/cameras` | admin, superadmin | add a camera. Response includes `ingest_key`, shown only once |
| `GET /cameras/{id}` | staff | one camera |
| `PATCH /cameras/{id}` | admin, superadmin | change stream URL, IP, zone, range, thresholds, polygon, camera position, homography |
| `DELETE /cameras/{id}` | admin, superadmin | delete the camera and its readings |
| `POST /cameras/{id}/rotate-key` | admin, superadmin | new ingest key, old one stops working |
| `GET /cameras/{id}/density?limit=&since=` | staff | readings, newest first |
| `GET /venues/{id}/density/latest` | staff | newest reading per camera (null if none yet) |
| `POST /density-events` | vision service | one reading per second per camera |

"staff" means superadmin, admin or security.

## Density event

The vision service authenticates with the camera's key, not a user login.

```
POST /density-events
X-Camera-Key: <ingest key>

{ "people_count": 82, "confidence": 0.8, "degraded": false, "ts": "2026-10-18T09:30:00Z" }
```

`confidence` and `ts` are optional (server time is used if `ts` is missing). `ts` more than 5 minutes in the future is refused. A camera without a zone polygon gets `409` until it is calibrated.

The server computes:

- `density = people_count / area_sqm`
- `occupancy_pct = people_count / (area_sqm x ref_density) x 100`, with `ref_density` = 1.08 people per m2 (a setting, to be confirmed against the Fruin source)
- `tier`, using the camera's own thresholds with half-open bands: Normal below caution, Caution from caution up to warning, Warning from warning up to critical, Critical from critical upward. Defaults 50, 75, 90.

This tier is the raw tier of one reading. The 10 s hysteresis that decides when an alert fires is built in Phase 2.

## Alert latency (definition for Phase 2 and the Phase 6 stress test)

Measured from the moment a zone's tier change is confirmed (after the 10 s hysteresis) to the moment the push is handed to FCM. It does not include the hysteresis or FCM delivery time to the phone. Target: 5 s.
