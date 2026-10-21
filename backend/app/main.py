from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import auth, cameras, density, venues

app = FastAPI(title="VISTA API", version="0.1.0", description="Phase 1: login, venue-scoped access, cameras, density ingest.")

origins = get_settings().cors_list
if origins:
    app.add_middleware(
        CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Camera-Key"],
    )

for r in (auth.router, venues.router, cameras.router, density.router):
    app.include_router(r)
    app.include_router(public.router)
    app.include_router(signup.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
