"""Lazy MongoDB and GridFS access."""

from gridfs import GridFSBucket
from pymongo import MongoClient
from pymongo.database import Database

from app.config import settings

_client: MongoClient | None = None


def get_client() -> MongoClient:
    """Create and cache a MongoDB client when it is first requested."""
    global _client
    if not settings.MONGODB_URI:
        raise RuntimeError("MONGODB_URI is not set")
    if _client is None:
        _client = MongoClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=2000,
        )
    return _client


def get_db() -> Database:
    """Return the configured application database."""
    return get_client()[settings.MONGODB_DB]


def get_bucket() -> GridFSBucket:
    """Return the GridFS bucket used to store uploaded media."""
    return GridFSBucket(get_db(), bucket_name="media_files")


def ping() -> bool:
    """Check MongoDB connectivity without raising connection errors."""
    if not settings.MONGODB_URI:
        return False
    try:
        get_client().admin.command("ping")
        return True
    except Exception:
        return False
