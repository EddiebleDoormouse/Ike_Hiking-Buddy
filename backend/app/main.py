"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.config import settings
from app.models import Health
from app.routers import hikes, media, plan, recap, search, tracks


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Close shared resources when FastAPI shuts down."""
    # FastAPI invokes this lifespan hook during application shutdown.
    yield
    db.close_client()


app = FastAPI(title="Hiking Buddy API", lifespan=lifespan)
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
