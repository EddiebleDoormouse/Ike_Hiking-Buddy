"""Pydantic models for the Hiking Buddy API."""

from datetime import date, datetime
from typing import Any, Literal

from bson import ObjectId
from pydantic import BaseModel, Field

Group = Literal[
    "plant",
    "fungus",
    "bird",
    "mammal",
    "insect",
    "reptile_amphibian",
    "other",
]


class HikeCreate(BaseModel):
    title: str
    trail_name: str
    hiker: str
    date: date
    status: Literal["planned", "completed"]
    based_on_hike_id: str | None = None


class Hike(HikeCreate):
    id: str
    route: dict | None = None
    start: dict | None = None
    stats: dict | None = None
    pace_factor: float | None = None
    plan: dict | None = None
    recap_md: str | None = None
    created_at: datetime


class HikeCard(BaseModel):
    id: str
    title: str
    trail_name: str
    hiker: str
    date: date
    status: Literal["planned", "completed"]
    cover_media_id: str | None = None
    distance_km: float | None = None
    ascent_m: float | None = None
    species_count: int = 0


class Candidate(BaseModel):
    common_name: str
    scientific_name: str
    confidence: float = Field(ge=0, le=1)
    group: Group


class SpecialistResult(BaseModel):
    source: Literal["plantnet", "mushroom_id"]
    top_name: str
    top_common_name: str | None = None
    top_score: float
    alternatives: list[dict] = Field(default_factory=list)
    gbif_key: int | None = None


class Verification(BaseModel):
    status: Literal["confirmed", "plausible", "unsure", "not_applicable"]
    chosen: Candidate | None = None
    gbif_nearby_count: int | None = None
    gbif_key: int | None = None
    specialist: SpecialistResult | None = None
    specialist_agrees: Literal["species", "genus", "no"] | None = None
    reasons: list[str] = Field(default_factory=list)


class MediaItem(BaseModel):
    id: str
    hike_id: str
    kind: Literal["photo", "audio", "video", "note"]
    filename: str
    mime: str
    original_file_id: str
    display_file_id: str | None = None
    thumb_file_id: str | None = None
    taken_at: datetime | None = None
    location: dict | None = None
    location_source: Literal["exif", "track"] | None = None
    caption: str | None = None
    tags: list[str] = Field(default_factory=list)
    text: str | None = None
    created_at: datetime


class Sighting(BaseModel):
    id: str
    hike_id: str
    media_id: str
    candidates: list[Candidate] = Field(default_factory=list)
    verification: Verification
    location: dict | None = None
    seen_at: datetime | None = None
    safety_note: str | None = None


class HikeDetail(BaseModel):
    hike: Hike
    media: list[MediaItem] = Field(default_factory=list)
    sightings: list[Sighting] = Field(default_factory=list)


class SearchResult(BaseModel):
    media: MediaItem
    hike_title: str
    sighting: Sighting | None = None
    score: float


class Health(BaseModel):
    ok: bool
    mongo: bool


class UploadMediaResponse(BaseModel):
    media: MediaItem
    sighting: Sighting | None = None


class TrackUploadResponse(BaseModel):
    stats: dict
    route: dict


class RecapResponse(BaseModel):
    recap_md: str


class SpeciesNear(BaseModel):
    name: str
    scientific_name: str
    count: int


def oid_to_str(value: Any) -> str:
    """Convert an identifier value to its string representation."""
    return str(value)


def _convert_object_ids(value: Any) -> Any:
    """Convert ObjectIds inside dictionaries and lists to strings."""
    if isinstance(value, ObjectId):
        return oid_to_str(value)
    if isinstance(value, dict):
        return {key: _convert_object_ids(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_convert_object_ids(item) for item in value]
    return value


def from_mongo(doc: dict) -> dict:
    """Copy a MongoDB document and convert its identifier values."""
    converted = _convert_object_ids(doc)
    if "_id" in converted:
        converted["id"] = converted.pop("_id")
    return converted


def to_mongo(data: dict) -> dict:
    """Copy API data without its public id field."""
    return {key: value for key, value in data.items() if key != "id"}
