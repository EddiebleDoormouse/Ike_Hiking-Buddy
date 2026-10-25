"""Hike track upload route."""

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models import TrackUploadResponse

router = APIRouter()


@router.post(
    "/hikes/{hike_id}/track",
    response_model=TrackUploadResponse,
    responses={501: {"description": "Not implemented yet"}},
)
def upload_track(
    hike_id: str,
    file: UploadFile = File(...),
) -> TrackUploadResponse:
    """Upload and parse a hike track."""
    raise HTTPException(
        status_code=501,
        detail="not implemented yet (D1)",
    )
