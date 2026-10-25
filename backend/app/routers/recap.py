"""Hike recap route: packs a whole hike into one Argon long-context call."""

import base64
import logging
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException

from app import db
from app.models import RecapResponse
from app.services import gemini
from app.services.images import to_display_jpeg

logger = logging.getLogger(__name__)
router = APIRouter()

# Photos go to the model with this maximum edge length.
RECAP_IMAGE_MAX_PX = 768
LOCAL_TZ = ZoneInfo("Europe/London")

# Verification statuses become the words shown in the species log.
_STATUS_WORDS = {
    "confirmed": "confirmed",
    "plausible": "probably",
    "unsure": "unsure",
    "not_applicable": "unsure",
}


def _coord_text(coords: Any) -> str | None:
    """Format a [lon, lat, ele?] coordinate as "lat, lon (ele m)"."""
    if not coords or len(coords) < 2:
        return None
    text = f"{coords[1]:.5f}, {coords[0]:.5f}"
    if len(coords) > 2 and coords[2] is not None:
        text += f" ({coords[2]:.0f} m)"
    return text


def _point_text(point: dict | None) -> str | None:
    """Format a GeoJSON Point for the prompt."""
    return _coord_text((point or {}).get("coordinates"))


def _local_time(value: Any) -> str | None:
    """Return "HH:MM" in Europe/London for a stored UTC datetime.

    Naive datetimes are read as UTC (what pymongo returns); non-datetime
    values pass through as text.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(LOCAL_TZ).strftime("%H:%M")
    return str(value)


def _date_text(value: Any) -> str:
    """Render a stored date/datetime as an ISO date for the prompt."""
    if isinstance(value, datetime):
        return value.date().isoformat()
    return str(value or "")


def _hike_doc_or_404(database: Any, hike_id: str) -> dict:
    """Load the hike document or raise a 404.

    Accepts the ObjectId hex form and falls back to a plain-string _id so
    imported fixtures keep working.
    """
    doc = None
    try:
        doc = database.hikes.find_one({"_id": ObjectId(hike_id)})
    except InvalidId:
        pass
    if doc is None:
        doc = database.hikes.find_one({"_id": hike_id})
    if doc is None:
        raise HTTPException(status_code=404, detail="hike not found")
    return doc


def _hike_id_variants(hike_id: str) -> list:
    """The shapes media/sightings may store hike_id in (string or ObjectId)."""
    variants: list = [hike_id]
    try:
        variants.append(ObjectId(hike_id))
    except InvalidId:
        pass
    return variants


def _route_summary(hike: dict) -> dict[str, str | None]:
    """Start, end and highest point of the recorded route."""
    route = hike.get("route") or {}
    coords = route.get("coordinates") or []
    first = last = highest = None
    if coords:
        first, last = coords[0], coords[-1]
        with_ele = [c for c in coords if len(c) > 2 and c[2] is not None]
        if with_ele:
            highest = max(with_ele, key=lambda c: c[2])
    return {
        "start": _point_text(hike.get("start")) or _coord_text(first),
        "end": _coord_text(last),
        "highest": _coord_text(highest),
    }


def _display_jpeg_b64(bucket: Any, media_doc: dict) -> str | None:
    """Fetch a media item's display JPEG from GridFS, downsized, as base64.

    Reuses the upload pipeline's JPEG encoder so orientation and EXIF
    handling match what was stored. Missing or unreadable files are
    skipped with a warning so one bad upload can't sink the whole recap.
    """
    file_id = media_doc.get("display_file_id")
    if not file_id:
        return None
    try:
        data = bucket.open_download_stream(ObjectId(str(file_id))).read()
        small = to_display_jpeg(
            data, media_doc.get("filename") or "photo.jpg", RECAP_IMAGE_MAX_PX
        )
    except Exception as exc:
        logger.warning(
            "recap: skipping media %s, display file unreadable: %s",
            media_doc.get("_id"),
            exc,
        )
        return None
    return base64.b64encode(small).decode("ascii")


def _media_sort_key(media_doc: dict) -> float:
    """Chronological key for media ordering; undated items go last."""
    taken = media_doc.get("taken_at")
    if isinstance(taken, datetime):
        if taken.tzinfo is None:
            taken = taken.replace(tzinfo=timezone.utc)
        return taken.timestamp()
    return float("inf")


def _sighting_entry(sighting: dict) -> dict:
    """Pick the species name, status word and time out of a sighting doc."""
    verification = sighting.get("verification") or {}
    chosen = verification.get("chosen") or {}
    candidates = sighting.get("candidates") or []
    top = candidates[0] if candidates else {}
    status = verification.get("status") or "unsure"
    return {
        "name": chosen.get("common_name") or top.get("common_name"),
        "scientific_name": (
            chosen.get("scientific_name") or top.get("scientific_name")
        ),
        "status": _STATUS_WORDS.get(status, "unsure"),
        "seen_at": _local_time(sighting.get("seen_at")),
    }


def build_hike_bundle(
    hike: dict,
    media_docs: list[dict],
    sighting_docs: list[dict],
    bucket: Any,
) -> dict:
    """Pack the hike, media and sightings for gemini.recap's hike_bundle."""
    media_sorted = sorted(media_docs, key=_media_sort_key)
    media = [
        {
            "kind": doc.get("kind"),
            "caption": doc.get("caption"),
            "taken_at": _local_time(doc.get("taken_at")),
            "location": _point_text(doc.get("location")),
            "text": doc.get("text"),
            "image_b64": _display_jpeg_b64(bucket, doc),
        }
        for doc in media_sorted
    ]
    return {
        "title": hike.get("title"),
        "trail_name": hike.get("trail_name"),
        "hiker": hike.get("hiker"),
        "date": _date_text(hike.get("date")),
        "stats": hike.get("stats") or {},
        "route_summary": _route_summary(hike),
        "notes": [doc["text"] for doc in media_sorted if doc.get("text")],
        "media": media,
        "sightings": [_sighting_entry(s) for s in sighting_docs],
    }


@router.post(
    "/hikes/{hike_id}/recap",
    response_model=RecapResponse,
    responses={
        404: {"description": "Hike not found"},
        502: {"description": "Gemini recap failed"},
    },
)
def create_recap(hike_id: str) -> RecapResponse:
    """Generate the hike recap, store it on the hike, and return it."""
    database = db.get_db()
    hike = _hike_doc_or_404(database, hike_id)
    related = {"hike_id": {"$in": _hike_id_variants(hike_id)}}
    media_docs = list(database.media.find(related))
    sighting_docs = list(database.sightings.find(related))
    bundle = build_hike_bundle(
        hike, media_docs, sighting_docs, db.get_bucket()
    )
    try:
        result = gemini.recap(bundle)
    except gemini.GeminiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    database.hikes.update_one(
        {"_id": hike["_id"]},
        {"$set": {"recap_md": result["recap_md"]}},
    )
    logger.info(
        "recap for hike %s: latency_s=%s usage=%s",
        hike_id,
        result["latency_s"],
        result["usage"],
    )
    return RecapResponse(recap_md=result["recap_md"])
