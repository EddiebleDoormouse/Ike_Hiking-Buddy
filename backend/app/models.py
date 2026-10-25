"""API models shared by routers and services."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

Group = Literal[
    "plant",
    "fungus",
    "bird",
    "mammal",
    "insect",
    "reptile",
    "amphibian",
    "fish",
    "lichen",
    "other",
]


class Candidate(BaseModel):
    """One possible identification for a wild organism."""

    common_name: str = Field(description="Common name in UK English.")
    scientific_name: str = Field(description="Scientific name or genus.")
    confidence: float = Field(ge=0, le=1, description="Confidence from 0 to 1.")
    group: Group = Field(description="Organism group.")


class MediaAnalysis(BaseModel):
    """Structured caption and possible identification for uploaded media."""

    caption: str
    tags: list[str]
    is_organism: bool
    candidates: list[Candidate] = []
    safety_note: str | None = None


class SpecialistAlternative(BaseModel):
    """One alternative name returned by a specialist service."""

    name: str
    common_name: str | None
    score: float


class SpecialistResult(BaseModel):
    """Result returned by a plant or fungus specialist service."""

    source: Literal["plantnet", "mushroom_id"]
    top_name: str
    top_common_name: str | None
    top_score: float
    alternatives: list[SpecialistAlternative]
    gbif_key: str | None


class Verification(BaseModel):
    """Evidence and outcome for a sighting identification."""

    status: Literal["confirmed", "plausible", "unsure", "not_applicable"]
    chosen: Candidate | None
    gbif_nearby_count: int | None
    gbif_key: str | None
    specialist: SpecialistResult | None
    specialist_agrees: Literal["species", "genus", "no"] | None
    reasons: list[str]


class HikeCreate(BaseModel):
    """Fields needed to create a hike."""

    title: str
    trail_name: str
    hiker: str
    date: date
    status: Literal["planned", "completed"]
    based_on_hike_id: str | None = None


class HikeStats(BaseModel):
    """Summary statistics for a recorded hike."""

    distance_km: float | None
    duration_s: float | None
    moving_s: float | None
    ascent_m: float | None
    descent_m: float | None
    avg_hr: float | None
    max_hr: float | None
    start_time: datetime | None
    end_time: datetime | None
    avg_moving_speed_kmh: float | None


class Hike(HikeCreate):
    """A hike and its optional route, stats, and planning data."""

    id: str
    route: dict | None
    start: dict | None
    stats: dict | None
    pace_factor: float | None
    plan: dict | None
    recap_md: str | None
    created_at: datetime


class HikeCard(BaseModel):
    """Compact information shown in the hikes list."""

    id: str
    title: str
    trail_name: str
    hiker: str
    date: date
    status: Literal["planned", "completed"]
    cover_media_id: str | None
    distance_km: float | None
    ascent_m: float | None
    species_count: int | None


class GeoJSONPoint(BaseModel):
    """A GeoJSON point in longitude, latitude order."""

    type: Literal["Point"]
    coordinates: tuple[float, float]


class MediaItem(BaseModel):
    """Stored metadata for one uploaded media item."""

    id: str
    hike_id: str
    kind: Literal["photo", "audio", "video", "note"]
    filename: str
    mime: str
    original_file_id: str | None
    display_file_id: str | None
    thumb_file_id: str | None
    taken_at: datetime | None
    location: GeoJSONPoint | None
    location_source: str | None
    caption: str | None
    tags: list[str]
    text: str | None
    created_at: datetime


class Sighting(BaseModel):
    """An organism sighting and its verification state."""

    id: str
    hike_id: str
    media_id: str
    candidates: list[Candidate]
    verification: Verification
    location: GeoJSONPoint | None
    seen_at: datetime | None
    safety_note: str | None


class HikeDetail(BaseModel):
    """A hike with all of its media and sightings."""

    hike: Hike
    media: list[MediaItem]
    sightings: list[Sighting]


class UploadMediaResponse(BaseModel):
    """Media upload result and its optional sighting."""

    media: MediaItem
    sighting: Sighting | None
