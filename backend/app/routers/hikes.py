"""Hike API routes."""

from fastapi import APIRouter, HTTPException, status

from app.models import Hike, HikeCard, HikeCreate, HikeDetail

router = APIRouter()


@router.post(
    "/hikes",
    response_model=Hike,
    status_code=status.HTTP_201_CREATED,
    responses={501: {"description": "Not implemented yet"}},
)
def create_hike(hike: HikeCreate) -> Hike:
    """Create a hike."""
    raise HTTPException(
        status_code=501,
        detail="not implemented yet (DV-P1)",
    )


@router.get(
    "/hikes",
    response_model=list[HikeCard],
    responses={501: {"description": "Not implemented yet"}},
)
def list_hikes() -> list[HikeCard]:
    """List hike cards."""
    raise HTTPException(
        status_code=501,
        detail="not implemented yet (DV-P1)",
    )


@router.get(
    "/hikes/{hike_id}",
    response_model=HikeDetail,
    responses={501: {"description": "Not implemented yet"}},
)
def get_hike(hike_id: str) -> HikeDetail:
    """Return a hike and its associated media and sightings."""
    raise HTTPException(
        status_code=501,
        detail="not implemented yet (DV-P1)",
    )
