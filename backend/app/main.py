"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import get_client
from app.routers.hikes import router as hikes_router
from app.routers.media import router as media_router

app = FastAPI(title="Hiking Buddy")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(hikes_router)
app.include_router(media_router)


@app.get("/health")
def health() -> dict[str, bool]:
    """Report application health and whether MongoDB responds to a ping."""
    try:
        get_client().admin.command("ping", maxTimeMS=2000)
    except Exception:
        return {"ok": True, "mongo": False}
    return {"ok": True, "mongo": True}
