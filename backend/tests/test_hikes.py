"""Tests for hike creation and retrieval routes."""

from datetime import datetime, timezone

from bson import ObjectId
from fastapi.testclient import TestClient
import pytest

from app.db import get_db, get_files
from app.main import app
from test_media import FakeBucket, FakeCollection, FakeDB


class ProjectedFakeCollection(FakeCollection):
    """Support the inclusion projection used by the hike-card route."""

    def find(self, filters, projection=None):
        documents = super().find(filters)
        if projection is None:
            return documents
        return [
            {
                "_id": document["_id"],
                "verification": {
                    "chosen": (document.get("verification") or {}).get("chosen")
                },
                "candidates": document.get("candidates", []),
            }
            for document in documents
        ]


@pytest.fixture
def fake_db():
    database = FakeDB()
    database.sightings = ProjectedFakeCollection()
    return database


@pytest.fixture
def fake_bucket():
    return FakeBucket()


@pytest.fixture
def client(fake_db, fake_bucket):
    app.dependency_overrides[get_db] = lambda: fake_db
    app.dependency_overrides[get_files] = lambda: fake_bucket
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def create_hike(client, hike_date="2026-10-24", title="Autumn loop"):
    return client.post(
        "/hikes",
        json={
            "title": title,
            "trail_name": "Epping Forest",
            "hiker": "Test hiker",
            "date": hike_date,
            "status": "completed",
        },
    )


def species_count_for(client, hike_id):
    response = client.get("/hikes")
    assert response.status_code == 200
    return next(
        card["species_count"]
        for card in response.json()
        if card["id"] == hike_id
    )


def make_media(hike_id, kind, created_at, filename="walk.jpg"):
    return {
        "hike_id": hike_id,
        "kind": kind,
        "filename": filename,
        "mime": "image/jpeg",
        "original_file_id": None,
        "display_file_id": None,
        "thumb_file_id": None,
        "taken_at": None,
        "location": None,
        "location_source": None,
        "caption": None,
        "tags": [],
        "text": None,
        "created_at": created_at,
    }


def make_sighting(
    hike_id,
    created_at,
    status="unsure",
    chosen=None,
    candidates=None,
):
    return {
        "hike_id": hike_id,
        "media_id": ObjectId(),
        "candidates": candidates if candidates is not None else [],
        "verification": {
            "status": status,
            "chosen": chosen,
            "gbif_nearby_count": None,
            "gbif_key": None,
            "specialist": None,
            "specialist_agrees": None,
            "reasons": [],
        },
        "location": None,
        "seen_at": None,
        "safety_note": None,
        "created_at": created_at,
    }


def test_post_hike_returns_id_and_stand_in_fields(client):
    response = create_hike(client)

    assert response.status_code == 201
    result = response.json()
    assert len(result["id"]) == 24
    assert result["route"] is None
    assert result["start"] is None
    assert result["stats"] is None
    assert result["plan"] is None
    assert result["pace_factor"] is None
    assert result["recap_md"] is None
    assert result["created_at"].endswith("Z")


def test_get_hikes_returns_empty_list(client):
    response = client.get("/hikes")

    assert response.status_code == 200
    assert response.json() == []


def test_hike_cards_cover_species_stats_and_date_sort(
    client,
    fake_db,
):
    older = create_hike(client, hike_date="2026-10-23", title="Older hike").json()
    newer = create_hike(client, hike_date="2026-10-24", title="Newer hike").json()
    older_oid = ObjectId(older["id"])
    newer_oid = ObjectId(newer["id"])
    older_document = fake_db.hikes.find_one({"_id": older_oid})
    newer_document = fake_db.hikes.find_one({"_id": newer_oid})
    older_document["stats"] = {"distance_km": 4.5, "ascent_m": 120}
    newer_document["stats"] = {"distance_km": 9.2, "ascent_m": 310}

    first_photo = fake_db.media.insert_one(
        make_media(
            newer_oid,
            "photo",
            datetime(2026, 10, 24, 8, tzinfo=timezone.utc),
            "first.jpg",
        )
    ).inserted_id
    fake_db.media.insert_one(
        make_media(
            newer_oid,
            "photo",
            datetime(2026, 10, 24, 10, tzinfo=timezone.utc),
            "second.jpg",
        )
    )
    fake_db.media.insert_one(
        make_media(
            newer_oid,
            "audio",
            datetime(2026, 10, 24, 7, tzinfo=timezone.utc),
            "song.mp3",
        )
    )
    fake_db.sightings.insert_one(
        make_sighting(
            newer_oid,
            datetime.now(timezone.utc),
            chosen={"scientific_name": "Cyanistes caeruleus"},
        )
    )
    fake_db.sightings.insert_one(
        make_sighting(
            newer_oid,
            datetime.now(timezone.utc),
            status="not_applicable",
            chosen={"scientific_name": "Turdus merula"},
        )
    )
    fake_db.sightings.insert_one(
        make_sighting(
            older_oid,
            datetime.now(timezone.utc),
            chosen={"scientific_name": "Erithacus rubecula"},
        )
    )

    response = client.get("/hikes")

    assert response.status_code == 200
    cards = response.json()
    assert [card["id"] for card in cards] == [newer["id"], older["id"]]
    assert cards[0]["cover_media_id"] == str(first_photo)
    assert cards[0]["species_count"] == 1
    assert cards[0]["distance_km"] == 9.2
    assert cards[0]["ascent_m"] == 310
    assert cards[1]["cover_media_id"] is None
    assert cards[1]["species_count"] == 1
    assert cards[1]["distance_km"] == 4.5
    assert cards[1]["ascent_m"] == 120


def test_species_count_is_distinct_and_uses_top_candidate(client, fake_db):
    hike = create_hike(client).json()
    hike_oid = ObjectId(hike["id"])
    created_at = datetime.now(timezone.utc)

    def add_sighting(status="unsure", chosen=None, candidates=None):
        fake_db.sightings.insert_one(
            make_sighting(
                hike_oid,
                created_at,
                status=status,
                chosen=chosen,
                candidates=candidates,
            )
        )

    add_sighting(chosen={"scientific_name": "Cyanistes caeruleus"})
    add_sighting(chosen={"scientific_name": " cyanistes  CAERULEUS"})
    assert species_count_for(client, hike["id"]) == 1

    add_sighting(chosen={"scientific_name": "Erithacus rubecula"})
    assert species_count_for(client, hike["id"]) == 2

    add_sighting(
        status="not_applicable",
        chosen={"scientific_name": "Turdus merula"},
    )
    add_sighting()
    add_sighting(chosen={"scientific_name": " \t "})
    assert species_count_for(client, hike["id"]) == 2

    add_sighting(
        chosen=None,
        candidates=[{"scientific_name": "Hedera helix"}],
    )
    assert species_count_for(client, hike["id"]) == 3


def test_get_hike_detail_sorts_media_and_sightings(client, fake_db):
    created = create_hike(client).json()
    hike_oid = ObjectId(created["id"])
    earlier = datetime(2026, 10, 24, 8, tzinfo=timezone.utc)
    later = datetime(2026, 10, 24, 9, tzinfo=timezone.utc)
    earlier_media = fake_db.media.insert_one(
        make_media(hike_oid, "photo", earlier, "early.jpg")
    ).inserted_id
    later_media = fake_db.media.insert_one(
        make_media(hike_oid, "audio", later, "later.mp3")
    ).inserted_id
    earlier_sighting = fake_db.sightings.insert_one(
        make_sighting(hike_oid, earlier)
    ).inserted_id
    later_sighting = fake_db.sightings.insert_one(
        make_sighting(hike_oid, later)
    ).inserted_id

    response = client.get(f"/hikes/{created['id']}")

    assert response.status_code == 200
    detail = response.json()
    assert detail["hike"]["id"] == created["id"]
    assert [item["id"] for item in detail["media"]] == [
        str(earlier_media),
        str(later_media),
    ]
    assert [item["id"] for item in detail["sightings"]] == [
        str(earlier_sighting),
        str(later_sighting),
    ]


def test_invalid_hike_id_returns_not_found(client):
    response = client.get("/hikes/not-an-object-id")

    assert response.status_code == 404
    assert response.json()["detail"] == "Hike not found"
