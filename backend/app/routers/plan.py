"""HTTP endpoint for generating and storing a hike plan."""

import logging
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.services import planner
from app.services.gemini import GeminiError
from app.services.planner import PlannerInputError
from app.services.weather import WeatherError

router = APIRouter(tags=["plan"])
logger = logging.getLogger(__name__)


def get_database() -> Any:
    """Load the database lazily so service tests do not need app.db."""
    from app.db import get_db

    return get_db()


def find_hike(db: Any, hike_id: str) -> dict | None:
    """Find a hike by either its BSON ObjectId or its stored string ID."""
    if ObjectId.is_valid(hike_id):
        query = {"_id": {"$in": [ObjectId(hike_id), hike_id]}}
    else:
        query = {"_id": hike_id}
    return db["hikes"].find_one(query)


def _save_progress(db: Any, hike_id: Any, event: dict[str, Any]) -> None:
    """Persist the most recent planner event without interrupting the request."""
    try:
        db["hikes"].update_one(
            {"_id": hike_id}, {"$set": {"plan_progress": event}}
        )
    except Exception:
        logger.exception("failed to save plan progress")


def _error_progress(
    message: str,
    revision: int,
    failed: list[str],
    started: float,
) -> dict[str, Any]:
    """Create a safe error event with the standard progress fields."""
    return {
        "stage": "error",
        "message": message,
        "revision": revision,
        "failed": failed,
        "elapsed_ms": round((perf_counter() - started) * 1000),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/hikes/{hike_id}/plan")
def create_plan(hike_id: str, db: Any = Depends(get_database)) -> dict:
    """Generate a plan, save it on the hike, and return it to the caller."""
    hike = find_hike(db, hike_id)
    if hike is None:
        raise HTTPException(status_code=404, detail="Hike not found")

    based_on = None
    based_on_id = hike.get("based_on_hike_id")
    if based_on_id is not None:
        based_on = find_hike(db, str(based_on_id))
        if based_on is None:
            raise HTTPException(status_code=404, detail="Based-on hike not found")
    sightings = (
        list(
            db["sightings"].find(
                {
                    "hike_id": {
                        "$in": [based_on["_id"], str(based_on["_id"])]
                    }
                }
            )
        )
        if based_on
        else []
    )

    latest_progress: dict[str, Any] = {"revision": 0, "failed": []}

    def save_progress(event: dict) -> None:
        latest_progress.update(event)
        _save_progress(db, hike["_id"], event)

    started = perf_counter()
    try:
        plan = planner.plan_hike(
            hike, based_on, sightings, on_progress=save_progress
        )
    except PlannerInputError as exc:
        _save_progress(
            db,
            hike["_id"],
            _error_progress(
                "Hike details are incomplete.",
                latest_progress["revision"],
                latest_progress["failed"],
                started,
            ),
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (GeminiError, WeatherError) as exc:
        _save_progress(
            db,
            hike["_id"],
            _error_progress(
                "Plan could not be generated.",
                latest_progress["revision"],
                latest_progress["failed"],
                started,
            ),
        )
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    db["hikes"].update_one({"_id": hike["_id"]}, {"$set": {"plan": plan}})
    return plan


@router.get("/hikes/{hike_id}/plan/progress")
def get_plan_progress(hike_id: str, db: Any = Depends(get_database)) -> dict:
    """Return the latest plan progress event for a hike."""
    hike = find_hike(db, hike_id)
    if hike is None:
        raise HTTPException(status_code=404, detail="Hike not found")
    return hike.get("plan_progress") or {
        "stage": "idle",
        "message": "Not started",
    }
