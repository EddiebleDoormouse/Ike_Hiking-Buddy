"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.config import settings
from app.models import Health
from app.routers import hikes, media, plan, recap, search, tracks

app = FastAPI(title="Hiking Buddy API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list(),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hikes.router)
app.include_router(media.router)
app.include_router(tracks.router)
app.include_router(plan.router)
app.include_router(search.router)
app.include_router(recap.router)


@app.get("/health", response_model=Health)
def health() -> Health:
    """Return application and MongoDB health."""
    return Health(ok=True, mongo=db.ping())
