"""Create and retrieve hikes."""

from datetime import date, datetime, time, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database

from app.db import get_db
from app.models import Hike, HikeCard, HikeCreate, HikeDetail
from app.routers.media import media_from_doc, sighting_from_doc

router = APIRouter(tags=["hikes"])


def hike_from_doc(document: dict) -> Hike:
    """Convert one MongoDB hike document to its API model."""
    values = dict(document)
    values["id"] = str(values.pop("_id"))
    created_at = values.get("created_at")
    if isinstance(created_at, datetime):
        if created_at.tzinfo is None:
            values["created_at"] = created_at.replace(tzinfo=timezone.utc)
        else:
            values["created_at"] = created_at.astimezone(timezone.utc)
    return Hike.model_validate(values)


def _species_key(sighting: dict) -> str | None:
    """Return a normalized scientific name for a sighting."""
    verification = sighting.get("verification") or {}
    chosen = verification.get("chosen")
    name = (
        chosen.get("scientific_name")
        if isinstance(chosen, dict)
        else None
    )
    if name is None:
        # Until D4 sets chosen, use the top candidate as the fallback key.
        candidates = sighting.get("candidates") or []
        candidate = candidates[0] if candidates else None
        name = (
            candidate.get("scientific_name")
            if isinstance(candidate, dict)
            else None
        )
    if not isinstance(name, str):
        return None
    key = " ".join(name.split()).casefold()
    return key or None


def _object_id(hike_id: str) -> ObjectId:
    """Parse a hike id or return the standard not-found response."""
    try:
        return ObjectId(hike_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Hike not found") from None


def _sort_datetime(value: datetime | date | str | None) -> datetime:
    """Return an aware UTC sort key for a stored date or timestamp."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, date):
        return datetime.combine(value, time.min, tzinfo=timezone.utc)
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return datetime.min.replace(tzinfo=timezone.utc)


@router.post("/hikes", response_model=Hike, status_code=201)
def create_hike(
    hike: HikeCreate,
    db: Database = Depends(get_db),
) -> Hike:
    """Create a hike with empty route, stats, and plan fields."""
    document = hike.model_dump()
    document["date"] = datetime.combine(
        hike.date,
        time.min,
        tzinfo=timezone.utc,
    )
    document.update(
        {
            "route": None,
            "start": None,
            "stats": None,
            "pace_factor": None,
            "plan": None,
            "recap_md": None,
            "created_at": datetime.now(timezone.utc),
        }
    )
    result = db.hikes.insert_one(document)
    document["_id"] = result.inserted_id
    return hike_from_doc(document)


@router.get("/hikes", response_model=list[HikeCard])
def list_hikes(db: Database = Depends(get_db)) -> list[HikeCard]:
    """Return hike cards ordered from newest to oldest."""
    documents = list(db.hikes.find({}))
    documents.sort(
        key=lambda document: _sort_datetime(document.get("date")),
        reverse=True,
    )

    cards = []
    for document in documents:
        hike_id = document["_id"]
        photos = list(
            db.media.find({"hike_id": hike_id, "kind": "photo"})
        )
        photos.sort(
            key=lambda photo: _sort_datetime(photo.get("created_at"))
        )
        stats = document.get("stats") or {}
        species_keys = set()
        sightings = db.sightings.find(
            {
                "hike_id": hike_id,
                "verification.status": {"$ne": "not_applicable"},
            },
            {"verification.chosen": 1, "candidates": 1},
        )
        for sighting in sightings:
            key = _species_key(sighting)
            if key is not None:
                species_keys.add(key)
        cards.append(
            HikeCard(
                id=str(hike_id),
                title=document["title"],
                trail_name=document["trail_name"],
                hiker=document["hiker"],
                date=document["date"],
                status=document["status"],
                cover_media_id=str(photos[0]["_id"]) if photos else None,
                distance_km=stats.get("distance_km"),
                ascent_m=stats.get("ascent_m"),
                species_count=len(species_keys),
            )
        )
    return cards


@router.get("/hikes/{hike_id}", response_model=HikeDetail)
def get_hike(
    hike_id: str,
    db: Database = Depends(get_db),
) -> HikeDetail:
    """Return one hike with its media and sightings."""
    hike_oid = _object_id(hike_id)
    document = db.hikes.find_one({"_id": hike_oid})
    if document is None:
        raise HTTPException(status_code=404, detail="Hike not found")

    media_documents = list(db.media.find({"hike_id": hike_oid}))
    media_documents.sort(
        key=lambda item: _sort_datetime(item.get("created_at"))
    )
    sighting_documents = list(db.sightings.find({"hike_id": hike_oid}))
    sighting_documents.sort(
        key=lambda item: _sort_datetime(item.get("created_at"))
    )

    return HikeDetail(
        hike=hike_from_doc(document),
        media=[media_from_doc(item) for item in media_documents],
        sightings=[sighting_from_doc(item) for item in sighting_documents],
    )
