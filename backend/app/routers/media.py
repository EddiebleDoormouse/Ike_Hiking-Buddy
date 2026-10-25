"""Media upload and file routes."""

from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.models import UploadMediaResponse

router = APIRouter()


@router.post(
    "/hikes/{hike_id}/media",
    response_model=UploadMediaResponse,
    status_code=201,
    responses={501: {"description": "Not implemented yet"}},
)
def upload_media(
    hike_id: str,
    file: UploadFile = File(...),
    kind: str | None = Form(None),
    text: str | None = Form(None),
) -> UploadMediaResponse:
    """Upload media to a hike."""
    raise HTTPException(
        status_code=501,
        detail="not implemented yet (DV-P1)",
    )


@router.get(
    "/media/{media_id}/file",
    responses={501: {"description": "Not implemented yet"}},
)
def get_media_file(
    media_id: str,
    variant: Literal["original", "display", "thumb"] = "display",
) -> None:
    """Stream a requested media-file variant."""
    raise HTTPException(
        status_code=501,
        detail="not implemented yet (DV-P1)",
    )
