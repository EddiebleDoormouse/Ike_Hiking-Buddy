"""Tests for the hike recap route and the Gemini recap call."""

import base64
import io
from datetime import datetime
from types import SimpleNamespace

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from PIL import Image

from app import db
from app.config import settings
from app.main import app
from app.routers import recap as recap_router
from app.services import gemini

client = TestClient(app)

HIKE_OID = ObjectId()
HIKE_ID = str(HIKE_OID)
FILE_1 = str(ObjectId())
FILE_2 = str(ObjectId())

RECAP_MD = (
    "You climbed the ridge in cold wind and earned the view.\n\n"
    "## Highlights\n- Mist clearing over the ridge\n- A fox at the wall\n"
    "- Fungi after the rain\n\n"
    "## Species log\n| Species | Status | Time |\n|---|---|---|\n"
    "| Red fox | confirmed | 15:01 |\n| Fly agaric | probably | 16:05 |\n\n"
    "## Next time\n- Start earlier for the light\n- Pack an extra layer"
)


def make_jpeg(width: int = 100, height: int = 60, color=(180, 40, 40)) -> bytes:
    """Generate a small synthetic JPEG for GridFS fixtures."""
    image = Image.new("RGB", (width, height), color)
    out = io.BytesIO()
    image.save(out, format="JPEG")
    return out.getvalue()


class FakeCollection:
    """In-memory stand-in for a pymongo collection."""

    def __init__(self, docs):
        self.docs = list(docs)
        self.updates = []

    def find_one(self, query):
        wanted = query.get("_id")
        for doc in self.docs:
            if doc.get("_id") == wanted:
                return doc
        return None

    def find(self, query):
        wanted = (query.get("hike_id") or {}).get("$in") or [
            query.get("hike_id")
        ]
        return [d for d in self.docs if d.get("hike_id") in wanted]

    def update_one(self, query, update):
        self.updates.append((query, update))


class FakeBucket:
    """In-memory GridFS stand-in keyed by file-id string."""

    def __init__(self, files):
        self.files = files

    def open_download_stream(self, file_id):
        data = self.files[str(file_id)]
        return SimpleNamespace(read=lambda: data)


def fixture_db() -> SimpleNamespace:
    """A fake database with one hike, three media items, three sightings."""
    hike = {
        "_id": HIKE_OID,
        "title": "Ridge loop",
        "trail_name": "Test Ridge",
        "hiker": "Edouard",
        "date": "2026-01-10",
        "status": "completed",
        "stats": {
            "distance_km": 12.4,
            "duration_s": 14400,
            "moving_s": 12600,
            "ascent_m": 640,
            "avg_hr": 118,
            "max_hr": 162,
        },
        "start": {"type": "Point", "coordinates": [-1.5432, 53.3412, 210]},
        "route": {
            "type": "LineString",
            "coordinates": [
                [-1.5432, 53.3412, 210],
                [-1.5010, 53.3500, 812],
                [-1.4600, 53.3000, 150],
            ],
        },
    }
    media = [
        {
            "_id": ObjectId(),
            "hike_id": HIKE_ID,
            "kind": "note",
            "caption": "Ridge note",
            "text": "Wind picked up hard on the ridge",
            "taken_at": datetime(2026, 1, 10, 16, 10),
            "location": None,
        },
        {
            "_id": ObjectId(),
            "hike_id": HIKE_ID,
            "kind": "photo",
            "caption": "Mist on the ridge",
            "display_file_id": FILE_1,
            "taken_at": datetime(2026, 1, 10, 14, 32),
            "location": {
                "type": "Point",
                "coordinates": [-1.5010, 53.3500],
            },
        },
        {
            "_id": ObjectId(),
            "hike_id": HIKE_ID,
            "kind": "photo",
            "caption": "Fox by the wall",
            "display_file_id": FILE_2,
            "taken_at": datetime(2026, 1, 10, 15, 1),
            "location": {
                "type": "Point",
                "coordinates": [-1.4900, 53.3400],
            },
        },
    ]
    sightings = [
        {
            "_id": ObjectId(),
            "hike_id": HIKE_ID,
            "media_id": "m2",
            "candidates": [],
            "verification": {
                "status": "confirmed",
                "chosen": {
                    "common_name": "Red fox",
                    "scientific_name": "Vulpes vulpes",
                    "confidence": 0.92,
                    "group": "mammal",
                },
            },
            "seen_at": datetime(2026, 1, 10, 15, 1),
        },
        {
            "_id": ObjectId(),
            "hike_id": HIKE_ID,
            "media_id": "m1",
            "candidates": [],
            "verification": {
                "status": "plausible",
                "chosen": {
                    "common_name": "Fly agaric",
                    "scientific_name": "Amanita muscaria",
                    "confidence": 0.55,
                    "group": "fungus",
                },
            },
            "seen_at": datetime(2026, 1, 10, 16, 5),
        },
        {
            "_id": ObjectId(),
            "hike_id": HIKE_ID,
            "media_id": "m3",
            "candidates": [
                {
                    "common_name": "Unidentified warbler",
                    "scientific_name": "Phylloscopus sp.",
                    "confidence": 0.3,
                    "group": "bird",
                }
            ],
            "verification": {"status": "unsure", "chosen": None},
            "seen_at": datetime(2026, 1, 10, 16, 20),
        },
    ]
    return SimpleNamespace(
        hikes=FakeCollection([hike]),
        media=FakeCollection(media),
        sightings=FakeCollection(sightings),
    )


def fake_create_factory(captured: dict, output_text: str = RECAP_MD):
    """A create_interaction replacement that records its kwargs."""

    def fake_create_interaction(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            status="completed",
            output_text=output_text,
            usage=SimpleNamespace(
                total_input_tokens=5200,
                total_output_tokens=430,
                total_thought_tokens=120,
                total_tokens=5630,
            ),
        )

    return fake_create_interaction


@pytest.fixture
def wired(monkeypatch):
    """Wire fake db, fake GridFS and a recording Gemini stub."""
    captured = {}
    fake_db = fixture_db()
    bucket = FakeBucket(
        {FILE_1: make_jpeg(1600, 900), FILE_2: make_jpeg(1200, 1600)}
    )
    monkeypatch.setattr(db, "get_db", lambda: fake_db)
    monkeypatch.setattr(db, "get_bucket", lambda: bucket)
    monkeypatch.setattr(
        gemini, "create_interaction", fake_create_factory(captured)
    )
    return SimpleNamespace(db=fake_db, captured=captured, bucket=bucket)


def test_recap_route_returns_and_saves_markdown(wired):
    """POST /hikes/{id}/recap stores recap_md on the hike and returns it."""
    response = client.post(f"/hikes/{HIKE_ID}/recap")

    assert response.status_code == 200
    assert response.json() == {"recap_md": RECAP_MD}
    assert wired.db.hikes.updates == [
        ({"_id": HIKE_OID}, {"$set": {"recap_md": RECAP_MD}})
    ]


def test_recap_request_contains_every_media_item_and_image(wired):
    """The single request carries all media metadata plus every JPEG."""
    client.post(f"/hikes/{HIKE_ID}/recap")

    captured = wired.captured
    assert captured["model"] == gemini.ARGON
    assert captured["generation_config"] == {"thinking_level": "medium"}

    blocks = captured["input"]
    prompt = next(b["text"] for b in blocks if b["type"] == "text")

    # every caption, time and location is in the prompt text
    for expected in (
        "Mist on the ridge",
        "14:32",
        "53.35000, -1.50100",
        "Fox by the wall",
        "15:01",
        "53.34000, -1.49000",
        "Wind picked up hard on the ridge",
        "12.4 km",
        "640 m ascent",
        "53.35000, -1.50100 (812 m)",  # highest route point
    ):
        assert expected in prompt

    # one image block per photo (the note has no display file)
    images = [b for b in blocks if b["type"] == "image"]
    assert len(images) == 2
    for image_block in images:
        assert image_block["mime_type"] == "image/jpeg"
        raw = base64.b64decode(image_block["data"])
        resized = Image.open(io.BytesIO(raw))
        assert max(resized.size) <= recap_router.RECAP_IMAGE_MAX_PX


def test_recap_marks_plausible_species_probably(wired):
    """Plausible sightings reach the model worded as "probably"."""
    client.post(f"/hikes/{HIKE_ID}/recap")

    prompt = wired.captured["input"][0]["text"]
    lines = prompt.splitlines()
    agaric = next(line for line in lines if "Fly agaric" in line)
    fox = next(line for line in lines if "Red fox" in line)
    warbler = next(line for line in lines if "Unidentified warbler" in line)

    assert "probably" in agaric
    assert "confirmed" in fox and "probably" not in fox
    assert "unsure" in warbler
    # the output contract repeats the probably wording and excludes unsure
    assert 'Status cell exactly as given' in prompt


def test_recap_unknown_hike_returns_404(wired):
    """Missing or malformed hike ids answer 404 before calling Gemini."""
    assert client.post("/hikes/not-an-id/recap").status_code == 404
    assert client.post(f"/hikes/{ObjectId()}/recap").status_code == 404


def test_recap_gemini_failure_returns_502(wired, monkeypatch):
    """A GeminiError from the service surfaces as a 502."""

    def fail_recap(bundle):
        raise gemini.GeminiError("recap returned an empty or failed reply")

    monkeypatch.setattr(gemini, "recap", fail_recap)

    response = client.post(f"/hikes/{HIKE_ID}/recap")
    assert response.status_code == 502


def test_recap_service_raises_on_empty_reply(monkeypatch):
    """An empty or failed interaction is a GeminiError, not an empty recap."""
    monkeypatch.setattr(
        gemini,
        "create_interaction",
        lambda **kwargs: SimpleNamespace(status="failed", output_text=""),
    )

    with pytest.raises(gemini.GeminiError):
        gemini.recap({"title": "x"})


def test_recap_service_reports_usage(monkeypatch):
    """Latency and usage metadata come back with the recap."""
    captured = {}
    monkeypatch.setattr(
        gemini, "create_interaction", fake_create_factory(captured)
    )

    result = gemini.recap({"title": "x", "media": [], "sightings": []})

    assert result["recap_md"] == RECAP_MD
    assert isinstance(result["latency_s"], float)
    assert result["usage"]["total_tokens"] == 5630


def test_downsize_jpeg_caps_long_edge():
    """Display images are re-encoded no larger than 768 px on the long edge."""
    raw = recap_router._downsize_jpeg(make_jpeg(2000, 1000))
    image = Image.open(io.BytesIO(raw))

    assert image.format == "JPEG"
    assert max(image.size) <= 768


@pytest.mark.live
@pytest.mark.skipif(
    not settings.GEMINI_API_KEY, reason="needs a real GEMINI_API_KEY"
)
def test_recap_live_argon_call():
    """Live smoke test: one real Argon call over a synthetic bundle."""
    bundle = {
        "title": "Synthetic loop",
        "trail_name": "Test Hill",
        "hiker": "Devin",
        "date": "2026-01-10",
        "stats": {"distance_km": 5.0, "duration_s": 5400, "ascent_m": 180},
        "route_summary": {
            "start": "53.30000, -1.50000",
            "end": "53.30000, -1.50000",
            "highest": "53.31000, -1.49000 (410 m)",
        },
        "notes": ["Cold and bright; icy stiles."],
        "media": [
            {
                "kind": "photo",
                "caption": "Summit cairn",
                "taken_at": "11:20",
                "location": "53.31000, -1.49000",
                "image_b64": base64.b64encode(make_jpeg(200, 120)).decode(),
            }
        ],
        "sightings": [
            {
                "name": "Red kite",
                "scientific_name": "Milvus milvus",
                "status": "probably",
                "seen_at": "12:05",
            }
        ],
    }

    result = gemini.recap(bundle)

    assert result["recap_md"]
    assert result["usage"]["total_tokens"] > 0
    assert result["latency_s"] > 0
