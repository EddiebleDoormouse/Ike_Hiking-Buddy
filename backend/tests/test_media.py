"""Tests for image conversion and thumbnail creation."""

import os
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock

from bson import ObjectId
from fastapi.testclient import TestClient
from gridfs import GridFSBucket
from gridfs.errors import NoFile
from PIL import Image
from pymongo import MongoClient
import pytest

from app.db import get_db, get_files
from app.main import app
from app.models import Candidate, MediaAnalysis
from app.services import gemini
from app.services.images import thumbnail, to_display_jpeg


# --- images.py ---

def test_to_display_jpeg_applies_orientation_and_strips_metadata():
    source = Image.new("RGB", (3000, 2000), "navy")
    exif = Image.Exif()
    exif[0x0112] = 6
    exif[0x8825] = {
        1: "N",
        2: (51.5, 30.0, 0.0),
        3: "W",
        4: (0.0, 7.0, 0.0),
    }
    source_buffer = BytesIO()
    source.save(source_buffer, format="JPEG", exif=exif)
    with Image.open(BytesIO(source_buffer.getvalue())) as original:
        assert original.getexif().get_ifd(0x8825)

    output = to_display_jpeg(source_buffer.getvalue(), "hike.jpg")

    with Image.open(BytesIO(output)) as image:
        assert image.format == "JPEG"
        assert image.height == 1600
        assert image.width < image.height
        assert image.getexif() == {}
        assert 0x8825 not in image.getexif()
        assert 0x0112 not in image.getexif()
        assert "icc_profile" not in image.info


def test_to_display_jpeg_reads_heic_without_upscaling():
    source = Image.new("RGB", (320, 240), "forestgreen")
    source_buffer = BytesIO()
    source.save(source_buffer, format="HEIF")

    output = to_display_jpeg(source_buffer.getvalue(), "hike.heic")

    with Image.open(BytesIO(output)) as image:
        assert image.format == "JPEG"
        assert image.size == (320, 240)


def test_to_display_jpeg_converts_rgba_png_to_rgb_jpeg():
    source = Image.new("RGBA", (80, 60), (255, 0, 0, 128))
    source_buffer = BytesIO()
    source.save(source_buffer, format="PNG")

    output = to_display_jpeg(source_buffer.getvalue(), "overlay.png")

    with Image.open(BytesIO(output)) as image:
        assert image.format == "JPEG"
        assert image.mode == "RGB"


def test_thumbnail_resizes_longest_side_to_size():
    source = Image.new("RGB", (1200, 800), "darkgreen")
    source_buffer = BytesIO()
    source.save(source_buffer, format="JPEG")

    output = thumbnail(source_buffer.getvalue(), 400)

    with Image.open(BytesIO(output)) as image:
        assert image.format == "JPEG"
        assert max(image.size) == 400


def test_to_display_jpeg_rejects_garbage_bytes():
    with pytest.raises(ValueError, match="Could not read image 'broken.jpg'"):
        to_display_jpeg(b"not an image", "broken.jpg")


class FakeCollection:
    """A small in-memory collection with the query operations routers use."""

    def __init__(self):
        self.documents = []

    def insert_one(self, document):
        stored = dict(document)
        stored.setdefault("_id", ObjectId())
        self.documents.append(stored)
        return SimpleNamespace(inserted_id=stored["_id"])

    def find_one(self, filters):
        return next(
            (document for document in self.documents if self._matches(document, filters)),
            None,
        )

    def find(self, filters):
        return [
            document
            for document in self.documents
            if self._matches(document, filters)
        ]

    def count_documents(self, filters):
        return len(self.find(filters))

    @staticmethod
    def _dotted_value(document, key):
        value = document
        for part in key.split("."):
            if not isinstance(value, dict) or part not in value:
                return None
            value = value[part]
        return value

    @classmethod
    def _matches(cls, document, filters):
        for key, expected in filters.items():
            actual = cls._dotted_value(document, key)
            if isinstance(expected, dict) and "$ne" in expected:
                if actual == expected["$ne"]:
                    return False
            elif actual != expected:
                return False
        return True


class FakeDB:
    """Fake database exposing the three application collections."""

    def __init__(self):
        self.hikes = FakeCollection()
        self.media = FakeCollection()
        self.sightings = FakeCollection()


class FakeDownload:
    """GridFS download stream backed by bytes in the fake bucket."""

    def __init__(self, record):
        self._data = record["data"]
        self.metadata = record["metadata"]

    def read(self):
        return self._data


class FakeBucket:
    """In-memory replacement for the GridFS operations used by routers."""

    def __init__(self):
        self.files = {}

    def upload_from_stream(self, filename, data, metadata=None):
        file_id = ObjectId()
        self.files[file_id] = {
            "filename": filename,
            "data": data,
            "metadata": metadata or {},
        }
        return file_id

    def open_download_stream(self, file_id):
        if file_id not in self.files:
            raise NoFile(f"No file with id {file_id}")
        return FakeDownload(self.files[file_id])


@pytest.fixture
def fake_db():
    return FakeDB()


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


def create_hike(client):
    return client.post(
        "/hikes",
        json={
            "title": "Autumn loop",
            "trail_name": "Epping Forest",
            "hiker": "Test hiker",
            "date": "2026-10-24",
            "status": "completed",
        },
    )


def sample_analysis(is_organism=True):
    candidates = [
        Candidate(
            common_name="Blue tit",
            scientific_name="Cyanistes caeruleus",
            confidence=0.8,
            group="bird",
        ),
        Candidate(
            common_name="Great tit",
            scientific_name="Parus major",
            confidence=0.12,
            group="bird",
        ),
        Candidate(
            common_name="Coal tit",
            scientific_name="Periparus ater",
            confidence=0.05,
            group="bird",
        ),
    ]
    return MediaAnalysis(
        caption="A small bird in a green hedgerow.",
        tags=["bird", "hedgerow"],
        is_organism=is_organism,
        candidates=candidates if is_organism else [],
    )


def make_jpeg(size=(1800, 1200)):
    output = BytesIO()
    Image.new("RGB", size, "darkgreen").save(output, format="JPEG")
    return output.getvalue()


def test_photo_upload_creates_display_thumb_and_unsure_sighting(
    client,
    fake_db,
    fake_bucket,
    monkeypatch,
):
    hike_response = create_hike(client)
    assert hike_response.status_code == 201
    hike_id = hike_response.json()["id"]
    fake_db.hikes.documents[0]["start"] = {
        "type": "Point",
        "coordinates": [-0.05, 51.65],
    }
    analysis = Mock(return_value=sample_analysis())
    monkeypatch.setattr(gemini, "analyze_media", analysis)
    original = make_jpeg()

    response = client.post(
        f"/hikes/{hike_id}/media",
        files={"file": ("ivy.jpg", original, "image/jpeg")},
    )

    assert response.status_code == 201
    payload = response.json()
    media = payload["media"]
    assert media["kind"] == "photo"
    assert media["caption"] == "A small bird in a green hedgerow."
    assert media["tags"] == ["bird", "hedgerow"]
    assert len(fake_bucket.files) == 3
    sighting = payload["sighting"]
    assert sighting["verification"]["status"] == "unsure"
    assert sighting["verification"]["reasons"] == ["Not verified yet"]
    assert len(sighting["candidates"]) == 3
    analysis.assert_called_once()
    analyzed_bytes, analyzed_mime, context = analysis.call_args.args
    assert analyzed_bytes != original
    assert analyzed_mime == "image/jpeg"
    assert context == {
        "place": "Epping Forest",
        "hike_title": "Autumn loop",
        "date": "2026-10-24",
        "lon": -0.05,
        "lat": 51.65,
    }
    with Image.open(BytesIO(analyzed_bytes)) as image:
        assert image.format == "JPEG"
        assert max(image.size) <= 1600


def test_heic_upload_with_octet_stream_is_inferred_as_photo(
    client,
    fake_bucket,
    monkeypatch,
):
    hike_id = create_hike(client).json()["id"]
    monkeypatch.setattr(gemini, "analyze_media", Mock(return_value=sample_analysis()))
    heic = BytesIO()
    Image.new("RGB", (120, 80), "forestgreen").save(heic, format="HEIF")

    response = client.post(
        f"/hikes/{hike_id}/media",
        files={"file": ("x.heic", heic.getvalue(), "application/octet-stream")},
    )

    assert response.status_code == 201
    assert response.json()["media"]["kind"] == "photo"
    assert len(fake_bucket.files) == 3
    display_id = ObjectId(response.json()["media"]["display_file_id"])
    with Image.open(BytesIO(fake_bucket.files[display_id]["data"])) as image:
        assert image.format == "JPEG"


def test_landscape_analysis_does_not_create_sighting(
    client,
    fake_db,
    monkeypatch,
):
    hike_id = create_hike(client).json()["id"]
    monkeypatch.setattr(
        gemini,
        "analyze_media",
        Mock(return_value=sample_analysis(is_organism=False)),
    )

    response = client.post(
        f"/hikes/{hike_id}/media",
        files={"file": ("view.jpg", make_jpeg((80, 60)), "image/jpeg")},
    )

    assert response.status_code == 201
    assert response.json()["sighting"] is None
    assert fake_db.sightings.documents == []


def test_audio_upload_uses_original_bytes_and_audio_mime(
    client,
    fake_bucket,
    monkeypatch,
):
    hike_id = create_hike(client).json()["id"]
    analysis = Mock(return_value=sample_analysis())
    monkeypatch.setattr(gemini, "analyze_media", analysis)
    audio = b"synthetic audio bytes"

    response = client.post(
        f"/hikes/{hike_id}/media",
        files={"file": ("song.mp3", audio, "audio/mpeg")},
    )

    assert response.status_code == 201
    assert response.json()["media"]["kind"] == "audio"
    assert len(fake_bucket.files) == 1
    assert analysis.call_args.args[:2] == (audio, "audio/mpeg")


def test_video_upload_is_stored_without_analysis(client, fake_bucket, monkeypatch):
    hike_id = create_hike(client).json()["id"]
    analysis = Mock()
    monkeypatch.setattr(gemini, "analyze_media", analysis)

    response = client.post(
        f"/hikes/{hike_id}/media",
        files={"file": ("clip.mp4", b"video bytes", "video/mp4")},
    )

    assert response.status_code == 201
    assert response.json()["media"]["kind"] == "video"
    assert response.json()["media"]["caption"] is None
    assert len(fake_bucket.files) == 1
    analysis.assert_not_called()


def test_text_form_upload_creates_note_without_a_file(client, fake_bucket):
    hike_id = create_hike(client).json()["id"]
    note = "The path was muddy after rain."

    response = client.post(f"/hikes/{hike_id}/media", data={"text": note})

    assert response.status_code == 201
    media = response.json()["media"]
    assert media["kind"] == "note"
    assert media["caption"] == note
    assert media["text"] == note
    assert media["original_file_id"] is None
    assert fake_bucket.files == {}
    missing_file = client.get(f"/media/{media['id']}/file")
    assert missing_file.status_code == 404
    assert missing_file.json()["detail"] == "This item has no file"


def test_gemini_error_returns_friendly_502_without_storing_media(
    client,
    fake_db,
    fake_bucket,
    monkeypatch,
):
    hike_id = create_hike(client).json()["id"]

    def fail_analysis(*args, **kwargs):
        raise gemini.GeminiError("private SDK error")

    monkeypatch.setattr(gemini, "analyze_media", fail_analysis)
    response = client.post(
        f"/hikes/{hike_id}/media",
        files={"file": ("ivy.jpg", make_jpeg((80, 60)), "image/jpeg")},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == (
        "Gemini couldn't analyse this file right now. Please try again in a moment."
    )
    assert fake_bucket.files == {}
    assert fake_db.media.documents == []


def test_missing_hike_returns_404(client):
    response = client.post(
        "/hikes/000000000000000000000000/media",
        files={"file": ("song.mp3", b"bytes", "audio/mpeg")},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Hike not found"


def test_bad_image_bytes_returns_400_without_storage(
    client,
    fake_bucket,
    monkeypatch,
):
    hike_id = create_hike(client).json()["id"]
    analysis = Mock()
    monkeypatch.setattr(gemini, "analyze_media", analysis)

    response = client.post(
        f"/hikes/{hike_id}/media",
        files={"file": ("broken.jpg", b"not an image", "image/jpeg")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Could not read this image"
    assert fake_bucket.files == {}
    analysis.assert_not_called()


def test_unknown_file_type_is_rejected(client, fake_bucket):
    hike_id = create_hike(client).json()["id"]
    response = client.post(
        f"/hikes/{hike_id}/media",
        files={"file": ("blob.bin", b"bytes", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported file type"
    assert fake_bucket.files == {}


def test_empty_upload_is_rejected(client, fake_bucket):
    hike_id = create_hike(client).json()["id"]
    response = client.post(
        f"/hikes/{hike_id}/media",
        files={"file": ("empty.jpg", b"", "image/jpeg")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "File is empty"
    assert fake_bucket.files == {}


def test_get_media_and_photo_file_variants(
    client,
    fake_bucket,
    monkeypatch,
):
    hike_id = create_hike(client).json()["id"]
    monkeypatch.setattr(gemini, "analyze_media", Mock(return_value=sample_analysis()))
    original = make_jpeg((2400, 1200))
    upload = client.post(
        f"/hikes/{hike_id}/media",
        files={"file": ("canopy.jpg", original, "image/jpeg")},
    )
    assert upload.status_code == 201
    media = upload.json()["media"]
    media_id = media["id"]

    metadata = client.get(f"/media/{media_id}")
    assert metadata.status_code == 200
    assert metadata.json()["id"] == media_id

    display = client.get(f"/media/{media_id}/file")
    thumb = client.get(f"/media/{media_id}/file?variant=thumb")
    original_response = client.get(f"/media/{media_id}/file?variant=original")
    assert display.status_code == thumb.status_code == original_response.status_code == 200
    assert display.headers["content-type"] == "image/jpeg"
    assert 'inline; filename="canopy.jpg"' in display.headers["content-disposition"]
    with Image.open(BytesIO(display.content)) as image:
        assert max(image.size) <= 1600
    with Image.open(BytesIO(thumb.content)) as image:
        assert max(image.size) <= 400
    assert original_response.content == original


def test_audio_display_variant_falls_back_to_original(
    client,
    monkeypatch,
):
    hike_id = create_hike(client).json()["id"]
    monkeypatch.setattr(gemini, "analyze_media", Mock(return_value=sample_analysis()))
    audio = b"original audio"
    upload = client.post(
        f"/hikes/{hike_id}/media",
        files={"file": ("call.mp3", audio, "audio/mpeg")},
    )
    media_id = upload.json()["media"]["id"]

    response = client.get(f"/media/{media_id}/file")

    assert response.status_code == 200
    assert response.content == audio
    assert response.headers["content-type"] == "audio/mpeg"


@pytest.mark.skipif(
    not os.environ.get("MONGODB_URI"),
    reason="no MONGODB_URI",
)
def test_mongodb_photo_upload_detail_and_file_variants(monkeypatch):
    mongo = MongoClient(os.environ["MONGODB_URI"], tz_aware=True)
    db_name = os.environ.get("MONGODB_DB", "hikingbuddy_dev")
    database = mongo[db_name]
    bucket = GridFSBucket(database, bucket_name="media_files")
    app.dependency_overrides[get_db] = lambda: database
    app.dependency_overrides[get_files] = lambda: bucket
    monkeypatch.setattr(gemini, "analyze_media", lambda *args: sample_analysis())
    hike_id = None

    try:
        with TestClient(app) as client:
            hike_response = create_hike(client)
            assert hike_response.status_code == 201
            hike_id = hike_response.json()["id"]
            original = make_jpeg((1800, 1200))
            upload_response = client.post(
                f"/hikes/{hike_id}/media",
                files={"file": ("integration.jpg", original, "image/jpeg")},
            )
            assert upload_response.status_code == 201
            media_id = upload_response.json()["media"]["id"]
            detail = client.get(f"/hikes/{hike_id}")
            assert detail.status_code == 200
            assert len(detail.json()["media"]) == 1
            assert len(detail.json()["sightings"]) == 1
            for variant in ("display", "thumb", "original"):
                response = client.get(
                    f"/media/{media_id}/file?variant={variant}"
                )
                assert response.status_code == 200
            assert (
                client.get(f"/media/{media_id}/file?variant=original").content
                == original
            )
    finally:
        if hike_id is not None:
            hike_oid = ObjectId(hike_id)
            for media_document in database.media.find({"hike_id": hike_oid}):
                for field in (
                    "original_file_id",
                    "display_file_id",
                    "thumb_file_id",
                ):
                    file_id = media_document.get(field)
                    if file_id is not None:
                        bucket.delete(file_id)
                database.media.delete_one({"_id": media_document["_id"]})
            for sighting_document in database.sightings.find({"hike_id": hike_oid}):
                database.sightings.delete_one({"_id": sighting_document["_id"]})
            database.hikes.delete_one({"_id": hike_oid})
        app.dependency_overrides.clear()
        mongo.close()
