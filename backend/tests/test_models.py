"""Tests for Pydantic API models and MongoDB conversion helpers."""

from datetime import date, datetime, timezone

import pytest
from bson import ObjectId
from pydantic import ValidationError

from app.models import (
    Candidate,
    Health,
    Hike,
    HikeCard,
    HikeCreate,
    HikeDetail,
    MediaItem,
    RecapResponse,
    SearchResult,
    SpeciesNear,
    SpecialistResult,
    Sighting,
    TrackUploadResponse,
    UploadMediaResponse,
    Verification,
    from_mongo,
    oid_to_str,
    to_mongo,
)


def test_all_models_round_trip_json():
    """Every public model can round-trip through JSON validation."""
    created_at = datetime(2026, 10, 24, 9, tzinfo=timezone.utc)
    hike_create = HikeCreate(
        title="Morning walk",
        trail_name="Example Trail",
        hiker="Edouard",
        date=date(2026, 10, 24),
        status="completed",
    )
    hike = Hike(
        **hike_create.model_dump(),
        id="hike-1",
        created_at=created_at,
    )
    card = HikeCard(
        id="hike-1",
        title="Morning walk",
        trail_name="Example Trail",
        hiker="Edouard",
        date=date(2026, 10, 24),
        status="completed",
    )
    candidate = Candidate(
        common_name="Blue tit",
        scientific_name="Cyanistes caeruleus",
        confidence=0.8,
        group="bird",
    )
    specialist = SpecialistResult(
        source="plantnet",
        top_name="Quercus robur",
        top_score=0.9,
    )
    verification = Verification(
        status="plausible",
        chosen=candidate,
        specialist=specialist,
    )
    media = MediaItem(
        id="media-1",
        hike_id="hike-1",
        kind="photo",
        filename="tree.jpg",
        mime="image/jpeg",
        original_file_id="file-1",
        created_at=created_at,
    )
    sighting = Sighting(
        id="sighting-1",
        hike_id="hike-1",
        media_id="media-1",
        candidates=[candidate],
        verification=verification,
    )
    hike_detail = HikeDetail(
        hike=hike,
        media=[media],
        sightings=[sighting],
    )
    models = [
        hike_create,
        hike,
        card,
        candidate,
        specialist,
        verification,
        media,
        sighting,
        hike_detail,
        SearchResult(
            media=media,
            hike_title="Morning walk",
            sighting=sighting,
            score=0.95,
        ),
        Health(ok=True, mongo=False),
        UploadMediaResponse(media=media, sighting=sighting),
        TrackUploadResponse(
            stats={"distance_km": 4.2},
            route={"type": "LineString", "coordinates": []},
        ),
        RecapResponse(recap_md="A pleasant walk."),
        SpeciesNear(
            name="Blue tit",
            scientific_name="Cyanistes caeruleus",
            count=2,
        ),
    ]

    for model in models:
        assert model.__class__.model_validate_json(model.model_dump_json()) == model


def test_candidate_confidence_is_bounded():
    """Candidate confidence cannot exceed one."""
    with pytest.raises(ValidationError):
        Candidate(
            common_name="Blue tit",
            scientific_name="Cyanistes caeruleus",
            confidence=1.5,
            group="bird",
        )


def test_oid_to_str_converts_object_id():
    """ObjectIds can be converted to their public string form."""
    object_id = ObjectId()

    assert oid_to_str(object_id) == str(object_id)


def test_to_mongo_drops_id_and_preserves_other_values():
    """MongoDB write data excludes the public id but keeps other fields."""
    data = {"id": "hike-1", "title": "Morning walk", "stats": {"distance_km": 4}}

    assert to_mongo(data) == {
        "title": "Morning walk",
        "stats": {"distance_km": 4},
    }
    assert data["id"] == "hike-1"


def test_from_mongo_converts_object_ids():
    """MongoDB ids at the top level and in nested values become strings."""
    object_id = ObjectId()

    converted = from_mongo(
        {
            "_id": object_id,
            "nested": {"id": object_id},
            "items": [object_id, {"value": object_id}],
        }
    )

    assert converted == {
        "id": str(object_id),
        "nested": {"id": str(object_id)},
        "items": [str(object_id), {"value": str(object_id)}],
    }
