"""Hike planning route."""

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.post(
    "/hikes/{hike_id}/plan",
    response_model=dict,
    responses={501: {"description": "Not implemented yet"}},
)
def plan_hike(hike_id: str) -> dict:
    """Draft a plan for a hike."""
    raise HTTPException(
        status_code=501,
        detail="not implemented yet (DV-P2)",
    )
