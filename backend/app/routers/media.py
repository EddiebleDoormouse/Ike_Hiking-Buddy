"""Upload, retrieve, and serve hike media."""

import logging
import mimetypes
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote, unquote

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse
from gridfs import GridFSBucket
from gridfs.errors import NoFile
from pymongo.database import Database

from app.db import get_db, get_files
from app.models import MediaItem, MediaAnalysis, Sighting, UploadMediaResponse
from app.services import gemini
from app.services.images import thumbnail, to_display_jpeg

router = APIRouter(tags=["media"])
logger = logging.getLogger(__name__)
MAX_UPLOAD_BYTES = 100 * 1024 * 1024
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


def _stream_chunks(stream: Any) -> Iterator[bytes]:
    """Yield a GridFS file in bounded chunks, then close its stream."""
    try:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            yield chunk
    finally:
        stream.close()


def _safe_filename(name: str) -> str:
    """Remove path components and header-sensitive characters from a filename."""
    filename = Path(unquote(name).replace("\\", "/")).name
    return filename.replace('"', "").replace("\r", "").replace("\n", "")


def _content_disposition(name: str) -> str:
    """Build a Latin-1-safe disposition with RFC 5987 for Unicode names."""
    safe = _safe_filename(name)
    fallback = safe.encode("ascii", "ignore").decode() or "file"
    if safe.isascii():
        return f'inline; filename="{safe}"'
    return f"inline; filename=\"{fallback}\"; filename*=UTF-8''{quote(safe)}"


@router.post(
    "/hikes/{hike_id}/media",
    response_model=UploadMediaResponse,
    status_code=201,
)
def upload_media(
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
        data = file.file.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail="File is too large (max 100 MB)",
            )
        if not data:
            raise HTTPException(status_code=400, detail="File is empty")
        filename = file.filename or "upload"
        mime = file.content_type or "application/octet-stream"
        if mime.lower() == "application/octet-stream":
            guessed_mime = mimetypes.guess_type(filename)[0]
            if guessed_mime:
                mime = guessed_mime
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
    safe_original = None
    analysis: MediaAnalysis | None = None
    caption = note_text if selected_kind == "note" else None
    tags: list[str] = []

    if selected_kind == "photo":
        try:
            display = to_display_jpeg(data, filename)
            thumb = thumbnail(data, 400)
            safe_original = to_display_jpeg(data, filename, max_px=100_000)
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
    safe_original_file_id = None
    now = datetime.now(timezone.utc)
    media_document = {
        "hike_id": hike_oid,
        "kind": selected_kind,
        "filename": filename,
        "mime": mime,
        "original_file_id": original_file_id,
        "display_file_id": display_file_id,
        "thumb_file_id": thumb_file_id,
        "safe_original_file_id": safe_original_file_id,
        "taken_at": None,
        "location": None,
        "location_source": None,
        "caption": caption,
        "tags": tags,
        "text": note_text if selected_kind == "note" else text,
        "is_organism": analysis.is_organism if analysis is not None else False,
        "created_at": now,
    }
    uploaded_file_ids = []
    media_id = None
    sighting_document = None
    try:
        if file is not None:
            original_file_id = _upload_file(files, filename, data, mime)
            uploaded_file_ids.append(original_file_id)
            if (
                display is not None
                and thumb is not None
                and safe_original is not None
            ):
                stem = Path(filename).stem or "image"
                display_file_id = _upload_file(
                    files,
                    f"{stem}.jpg",
                    display,
                    "image/jpeg",
                )
                uploaded_file_ids.append(display_file_id)
                thumb_file_id = _upload_file(
                    files,
                    f"{stem}_thumb.jpg",
                    thumb,
                    "image/jpeg",
                )
                uploaded_file_ids.append(thumb_file_id)
                safe_original_file_id = _upload_file(
                    files,
                    f"{stem}_original.jpg",
                    safe_original,
                    "image/jpeg",
                )
                uploaded_file_ids.append(safe_original_file_id)
            media_document["original_file_id"] = original_file_id
            media_document["display_file_id"] = display_file_id
            media_document["thumb_file_id"] = thumb_file_id
            media_document["safe_original_file_id"] = safe_original_file_id

        media_result = db.media.insert_one(media_document)
        media_id = media_result.inserted_id
        media_document["_id"] = media_id

        if analysis is not None and analysis.is_organism:
            candidates = [candidate.model_dump() for candidate in analysis.candidates]
            sighting_document = {
                "hike_id": hike_oid,
                "media_id": media_id,
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
    except Exception:
        for file_id in uploaded_file_ids:
            try:
                files.delete(file_id)
            except Exception:
                logger.warning(
                    "Failed to clean up GridFS file %s after upload failure",
                    file_id,
                    exc_info=True,
                )
        if media_id is not None:
            try:
                db.media.delete_one({"_id": media_id})
            except Exception:
                logger.warning(
                    "Failed to clean up media document %s after upload failure",
                    media_id,
                    exc_info=True,
                )
        raise

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
    """Stream photos from metadata-free JPEGs, re-encoding legacy originals."""
    media_oid = _object_id(media_id)
    document = db.media.find_one({"_id": media_oid})
    if document is None:
        raise HTTPException(status_code=404, detail="Media not found")

    selected_id = None
    is_jpeg_variant = False
    is_safe_photo_original = False
    is_legacy_photo_original = False
    is_photo = document["kind"] == "photo"
    if is_photo and variant in ("display", "thumb"):
        selected_id = document.get(f"{variant}_file_id")
        is_jpeg_variant = selected_id is not None
    if selected_id is None:
        if is_photo:
            selected_id = document.get("safe_original_file_id")
            is_safe_photo_original = selected_id is not None
            if selected_id is None:
                selected_id = document.get("original_file_id")
                is_legacy_photo_original = selected_id is not None
        else:
            selected_id = document.get("original_file_id")
    if selected_id is None:
        raise HTTPException(status_code=404, detail="This item has no file")

    try:
        stream = files.open_download_stream(selected_id)
    except NoFile as exc:
        raise HTTPException(status_code=404, detail="Media file not found") from exc

    if is_safe_photo_original:
        filename = f"{Path(document['filename']).stem or 'image'}.jpg"
        return StreamingResponse(
            _stream_chunks(stream),
            media_type="image/jpeg",
            headers={"Content-Disposition": _content_disposition(filename)},
        )

    if is_legacy_photo_original:
        try:
            raw = stream.read()
        finally:
            stream.close()
        safe_image = to_display_jpeg(
            raw,
            document["filename"],
            max_px=4096,
        )
        filename = f"{Path(document['filename']).stem or 'image'}.jpg"
        return Response(
            content=safe_image,
            media_type="image/jpeg",
            headers={"Content-Disposition": _content_disposition(filename)},
        )

    if is_jpeg_variant:
        media_type = "image/jpeg"
        filename = f"{Path(document['filename']).stem or 'image'}.jpg"
    else:
        media_type = document["mime"]
        filename = document["filename"]
    return StreamingResponse(
        _stream_chunks(stream),
        media_type=media_type,
        headers={"Content-Disposition": _content_disposition(filename)},
    )
