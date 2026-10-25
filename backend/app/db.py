"""Lazy MongoDB and GridFS access for FastAPI dependencies."""

from fastapi import Depends
from gridfs import GridFSBucket
from pymongo import MongoClient
from pymongo.database import Database

from app.config import settings

_client: MongoClient | None = None


def get_client() -> MongoClient:
    """Return the cached MongoDB client, creating it on first use."""
    global _client
    if _client is None:
        _client = MongoClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=2000,
        )
    return _client


def get_db() -> Database:
    """Return the configured MongoDB database."""
    return get_client()[settings.MONGODB_DB]


def get_files(db: Database = Depends(get_db)) -> GridFSBucket:
    """Return the media GridFS bucket for the configured database."""
    return GridFSBucket(db, bucket_name="media_files")
