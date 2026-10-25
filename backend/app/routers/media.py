"""Upload, retrieve, and serve hike media."""

import logging
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from gridfs import GridFSBucket
from gridfs.errors import NoFile
from pymongo.database import Database

from app.db import get_db, get_files
from app.models import MediaItem, MediaAnalysis, Sighting, UploadMediaResponse
from app.services import gemini
from app.services.images import thumbnail, to_display_jpeg

router = APIRouter(tags=["media"])
logger = logging.getLogger(__name__)
MediaKind = Literal["photo", "audio", "video", "note"]
IMAGE_EXTENSIONS = {".heic", ".heif", ".jpg", ".jpeg", ".png", ".webp"}
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".ogg", ".aac", ".flac"}
VIDEO_EXTENSIONS = {".mp4", ".mov"}
NOTE_EXTENSIONS = {".txt", ".md"}
GEMINI_ERROR_DETAIL = (
    "Gemini couldn't analyse this file right now. Please try again in a moment."
)


def _object_id(value: str, detail: str = "Media not found") -> ObjectId:
    """Parse an API id or return a not-found error for invalid values."""
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail=detail) from None


def _id_string(value: ObjectId | str | None) -> str | None:
    """Convert a stored MongoDB id to its API string representation."""
    if value is None:
        return None
    return str(value)


def _utc_datetime(value: datetime | None) -> datetime | None:
    """Treat naive MongoDB datetimes as UTC for API responses."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def media_from_doc(document: dict) -> MediaItem:
    """Convert one MongoDB media document to its API model."""
    return MediaItem(
        id=str(document["_id"]),
        hike_id=str(document["hike_id"]),
        kind=document["kind"],
        filename=document["filename"],
        mime=document["mime"],
        original_file_id=_id_string(document.get("original_file_id")),
        display_file_id=_id_string(document.get("display_file_id")),
        thumb_file_id=_id_string(document.get("thumb_file_id")),
        taken_at=_utc_datetime(document.get("taken_at")),
        location=document.get("location"),
        location_source=document.get("location_source"),
        caption=document.get("caption"),
        tags=document.get("tags", []),
        text=document.get("text"),
        created_at=_utc_datetime(document["created_at"]),
    )


def sighting_from_doc(document: dict) -> Sighting:
    """Convert one MongoDB sighting document to its API model."""
    return Sighting(
        id=str(document["_id"]),
        hike_id=str(document["hike_id"]),
        media_id=str(document["media_id"]),
        candidates=document.get("candidates", []),
        verification=document["verification"],
        location=document.get("location"),
        seen_at=_utc_datetime(document.get("seen_at")),
        safety_note=document.get("safety_note"),
    )


def _infer_kind(filename: str, mime: str) -> MediaKind | None:
    """Infer a supported media kind from its extension or content type."""
    extension = Path(filename).suffix.lower()
    content_type = mime.lower()
    if extension in IMAGE_EXTENSIONS or content_type.startswith("image/"):
        return "photo"
    if extension in AUDIO_EXTENSIONS or content_type.startswith("audio/"):
        return "audio"
    if extension in VIDEO_EXTENSIONS or content_type.startswith("video/"):
        return "video"
    if extension in NOTE_EXTENSIONS or content_type == "text/plain":
        return "note"
    return None


def _hike_context(hike: dict) -> dict:
    """Build the place and date context used by Gemini."""
    context = {
        "place": hike.get("trail_name"),
        "hike_title": hike.get("title"),
    }
    hike_date = hike.get("date")
    if isinstance(hike_date, datetime):
        context["date"] = hike_date.date().isoformat()
    elif hike_date is not None:
        context["date"] = hike_date.isoformat()

    start = hike.get("start")
    coordinates = start.get("coordinates") if isinstance(start, dict) else None
    if isinstance(coordinates, (list, tuple)) and len(coordinates) >= 2:
        context["lon"], context["lat"] = coordinates[0], coordinates[1]
    return context


def _upload_file(
    files: GridFSBucket,
    filename: str,
    data: bytes,
    content_type: str,
) -> ObjectId:
    """Store one byte stream with its content type in GridFS."""
    return files.upload_from_stream(
        filename,
        data,
        metadata={"content_type": content_type},
    )


@router.post(
    "/hikes/{hike_id}/media",
    response_model=UploadMediaResponse,
    status_code=201,
)
async def upload_media(
    hike_id: str,
    file: UploadFile | None = File(None),
    kind: MediaKind | None = Form(None),
    text: str | None = Form(None),
    db: Database = Depends(get_db),
    files: GridFSBucket = Depends(get_files),
) -> UploadMediaResponse:
    """Upload a photo, audio clip, video, or note to a hike."""
    hike_oid = _object_id(hike_id, detail="Hike not found")
    hike = db.hikes.find_one({"_id": hike_oid})
    if hike is None:
        raise HTTPException(status_code=404, detail="Hike not found")

    if file is None and not text:
        raise HTTPException(status_code=400, detail="A file or note text is required")

    if file is not None:
        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail="File is empty")
        filename = file.filename or "upload"
        mime = file.content_type or mimetypes.guess_type(filename)[0]
        mime = mime or "application/octet-stream"
        selected_kind = kind or _infer_kind(filename, mime)
        if selected_kind is None:
            raise HTTPException(status_code=400, detail="Unsupported file type")
    else:
        data = b""
        filename = "note.txt"
        mime = "text/plain"
        selected_kind = kind or "note"
        if selected_kind != "note":
            raise HTTPException(status_code=400, detail="A file is required")

    note_text = None
    if selected_kind == "note":
        if file is None:
            note_text = text
        else:
            try:
                note_text = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise HTTPException(
                    status_code=400,
                    detail="Note files must contain UTF-8 text",
                ) from exc

    display = None
    thumb = None
    analysis: MediaAnalysis | None = None
    caption = note_text if selected_kind == "note" else None
    tags: list[str] = []

    if selected_kind == "photo":
        try:
            display = to_display_jpeg(data, filename)
            thumb = thumbnail(data, 400)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail="Could not read this image",
            ) from exc
        try:
            analysis = gemini.analyze_media(display, "image/jpeg", _hike_context(hike))
        except gemini.GeminiError as exc:
            logger.warning("Gemini analysis failed: %s", exc)
            raise HTTPException(status_code=502, detail=GEMINI_ERROR_DETAIL) from exc
    elif selected_kind == "audio":
        analysis_mime = mime
        if not analysis_mime.lower().startswith("audio/"):
            analysis_mime = mimetypes.guess_type(filename)[0] or "audio/mpeg"
            if not analysis_mime.lower().startswith("audio/"):
                analysis_mime = "audio/mpeg"
        try:
            analysis = gemini.analyze_media(
                data,
                analysis_mime,
                _hike_context(hike),
            )
        except gemini.GeminiError as exc:
            logger.warning("Gemini analysis failed: %s", exc)
            raise HTTPException(status_code=502, detail=GEMINI_ERROR_DETAIL) from exc

    if analysis is not None:
        caption = analysis.caption
        tags = analysis.tags

    original_file_id = None
    display_file_id = None
    thumb_file_id = None
    if file is not None:
        original_file_id = _upload_file(files, filename, data, mime)
        if display is not None and thumb is not None:
            stem = Path(filename).stem or "image"
            display_file_id = _upload_file(
                files,
                f"{stem}.jpg",
                display,
                "image/jpeg",
            )
            thumb_file_id = _upload_file(
                files,
                f"{stem}_thumb.jpg",
                thumb,
                "image/jpeg",
            )

    now = datetime.now(timezone.utc)
    media_document = {
        "hike_id": hike_oid,
        "kind": selected_kind,
        "filename": filename,
        "mime": mime,
        "original_file_id": original_file_id,
        "display_file_id": display_file_id,
        "thumb_file_id": thumb_file_id,
        "taken_at": None,
        "location": None,
        "location_source": None,
        "caption": caption,
        "tags": tags,
        "text": note_text,
        "is_organism": analysis.is_organism if analysis is not None else False,
        "created_at": now,
    }
    media_result = db.media.insert_one(media_document)
    media_document["_id"] = media_result.inserted_id

    sighting_document = None
    if analysis is not None and analysis.is_organism:
        candidates = [candidate.model_dump() for candidate in analysis.candidates]
        sighting_document = {
            "hike_id": hike_oid,
            "media_id": media_result.inserted_id,
            "candidates": candidates,
            "verification": {
                "status": "unsure",
                "chosen": candidates[0] if candidates else None,
                "gbif_nearby_count": None,
                "gbif_key": None,
                "specialist": None,
                "specialist_agrees": None,
                "reasons": ["Not verified yet"],
            },
            "location": None,
            "seen_at": None,
            "safety_note": analysis.safety_note,
            "created_at": now,
        }
        sighting_result = db.sightings.insert_one(sighting_document)
        sighting_document["_id"] = sighting_result.inserted_id

    return UploadMediaResponse(
        media=media_from_doc(media_document),
        sighting=(
            sighting_from_doc(sighting_document)
            if sighting_document is not None
            else None
        ),
    )


@router.get("/media/{media_id}", response_model=MediaItem)
def get_media(
    media_id: str,
    db: Database = Depends(get_db),
) -> MediaItem:
    """Return metadata for one media item."""
    media_oid = _object_id(media_id)
    document = db.media.find_one({"_id": media_oid})
    if document is None:
        raise HTTPException(status_code=404, detail="Media not found")
    return media_from_doc(document)


@router.get("/media/{media_id}/file")
def get_media_file(
    media_id: str,
    variant: Literal["display", "thumb", "original"] = "display",
    db: Database = Depends(get_db),
    files: GridFSBucket = Depends(get_files),
) -> Response:
    """Stream a media file, using a photo display variant by default."""
    media_oid = _object_id(media_id)
    document = db.media.find_one({"_id": media_oid})
    if document is None:
        raise HTTPException(status_code=404, detail="Media not found")

    selected_id = None
    is_jpeg_variant = False
    if document["kind"] == "photo" and variant in ("display", "thumb"):
        selected_id = document.get(f"{variant}_file_id")
        is_jpeg_variant = selected_id is not None
    if selected_id is None:
        selected_id = document.get("original_file_id")
    if selected_id is None:
        raise HTTPException(status_code=404, detail="This item has no file")

    try:
        stream = files.open_download_stream(selected_id)
    except NoFile as exc:
        raise HTTPException(status_code=404, detail="Media file not found") from exc

    if is_jpeg_variant:
        media_type = "image/jpeg"
        filename = f"{Path(document['filename']).stem or 'image'}.jpg"
    else:
        media_type = document["mime"]
        filename = document["filename"]
    filename = Path(filename.replace("\\", "/")).name.replace('"', "")
    return Response(
        content=stream.read(),
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
