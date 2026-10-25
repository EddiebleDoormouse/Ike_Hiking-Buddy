"""Hike recap route."""

from fastapi import APIRouter, HTTPException

from app.models import RecapResponse

router = APIRouter()


@router.post(
    "/hikes/{hike_id}/recap",
    response_model=RecapResponse,
    responses={501: {"description": "Not implemented yet"}},
)
def create_recap(hike_id: str) -> RecapResponse:
    """Create a recap for a hike."""
    raise HTTPException(
        status_code=501,
        detail="not implemented yet (recap)",
    )
