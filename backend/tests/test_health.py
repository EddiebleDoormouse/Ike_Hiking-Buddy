"""Tests for the health endpoint and MongoDB ping fallback."""

from fastapi.testclient import TestClient

from app import db
from app.config import settings
from app.main import app

client = TestClient(app)


def test_health_reports_mongo_available(monkeypatch):
    """Health reports a successful MongoDB ping."""
    monkeypatch.setattr(db, "ping", lambda: True)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "mongo": True}


def test_health_reports_mongo_unavailable(monkeypatch):
    """Health remains available when MongoDB is down."""
    monkeypatch.setattr(db, "ping", lambda: False)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "mongo": False}


def test_ping_without_uri_returns_false(monkeypatch):
    """A missing MongoDB URI makes ping return false without raising."""
    monkeypatch.setattr(settings, "MONGODB_URI", None)

    assert db.ping() is False
