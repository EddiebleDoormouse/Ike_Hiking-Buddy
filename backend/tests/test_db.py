"""Tests for lazy MongoDB client and GridFS helpers."""

from types import SimpleNamespace

import pytest
from gridfs import GridFSBucket

from app import db
from app.config import settings


@pytest.fixture
def local_mongo_settings(monkeypatch):
    """Configure a lazy local client without issuing MongoDB commands."""
    monkeypatch.setattr(settings, "MONGODB_URI", "mongodb://localhost:1")
    db._client = None
    yield
    db.close_client()


def test_get_client_returns_cached_instance(local_mongo_settings):
    """Repeated requests reuse one MongoDB client."""
    assert db.get_client() is db.get_client()


def test_get_client_requires_uri(local_mongo_settings, monkeypatch):
    """A missing MongoDB URI raises a clear error."""
    monkeypatch.setattr(settings, "MONGODB_URI", None)

    with pytest.raises(RuntimeError, match="MONGODB_URI is not set"):
        db.get_client()


def test_get_db_uses_configured_database_name(local_mongo_settings):
    """The application database uses its configured name."""
    assert db.get_db().name == settings.MONGODB_DB


def test_get_bucket_uses_media_files_collection(local_mongo_settings):
    """The GridFS bucket uses the expected files collection."""
    bucket = db.get_bucket()

    assert isinstance(bucket, GridFSBucket)
    assert bucket._files.name == "media_files.files"


def test_close_client_clears_cached_instance(local_mongo_settings):
    """Closing the client resets the lazy cache."""
    db.get_client()

    db.close_client()

    assert db._client is None


def test_ping_returns_false_when_command_fails(
    local_mongo_settings,
    monkeypatch,
):
    """MongoDB command errors are reported as an unsuccessful ping."""
    def fail_command(command):
        raise RuntimeError("unavailable")

    fake_client = SimpleNamespace(
        admin=SimpleNamespace(command=fail_command),
    )
    monkeypatch.setattr(db, "get_client", lambda: fake_client)

    assert db.ping() is False
