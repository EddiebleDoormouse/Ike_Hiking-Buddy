"""HTTP endpoint for generating and storing a hike plan."""

from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.services import planner
from app.services.gemini import GeminiError
from app.services.planner import PlannerInputError
from app.services.weather import WeatherError

router = APIRouter(tags=["plan"])


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

    try:
        plan = planner.plan_hike(hike, based_on, sightings)
    except PlannerInputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except GeminiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except WeatherError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    db["hikes"].update_one({"_id": hike["_id"]}, {"$set": {"plan": plan}})
    return plan
