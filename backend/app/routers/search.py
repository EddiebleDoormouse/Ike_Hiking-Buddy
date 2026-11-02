"""Search and nearby-species routes."""

from fastapi import APIRouter, HTTPException

from app.models import SearchResult, SpeciesNear

router = APIRouter()


@router.get(
    "/search",
    response_model=list[SearchResult],
    responses={501: {"description": "Not implemented yet"}},
)
def search(q: str, hike_id: str | None = None) -> list[SearchResult]:
    """Search media and sightings."""
    raise HTTPException(
        status_code=501,
        detail="not implemented yet (D5)",
    )


@router.get(
    "/species/near",
    response_model=list[SpeciesNear],
    responses={501: {"description": "Not implemented yet"}},
)
def species_near(
    lat: float,
    lon: float,
    month: int | None = None,
    radius_km: float = 10,
) -> list[SpeciesNear]:
    """List species recorded near a location."""
    raise HTTPException(
        status_code=501,
        detail="not implemented yet (D2)",
    )
