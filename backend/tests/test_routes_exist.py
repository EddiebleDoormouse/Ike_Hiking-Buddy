"""Tests that the scaffold API routes are registered."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

ROUTES = [
    (
        "POST",
        "/hikes",
        {
            "json": {
                "title": "Morning walk",
                "trail_name": "Example Trail",
                "hiker": "Edouard",
                "date": "2026-10-24",
                "status": "completed",
            }
        },
    ),
    ("GET", "/hikes", {}),
    ("GET", "/hikes/hike-1", {}),
    (
        "POST",
        "/hikes/hike-1/media",
        {
            "files": {
                "file": ("sample.jpg", b"test", "image/jpeg"),
                "kind": (None, "photo"),
                "text": (None, "A sample note"),
            }
        },
    ),
    ("GET", "/media/media-1/file?variant=display", {}),
    (
        "POST",
        "/hikes/hike-1/track",
        {"files": {"file": ("sample.gpx", b"<gpx />", "application/gpx+xml")}},
    ),
    ("POST", "/hikes/hike-1/plan", {}),
    ("GET", "/search?q=fox", {}),
    ("GET", "/species/near?lat=51.5&lon=-0.1", {}),
]


@pytest.mark.parametrize(("method", "path", "request_kwargs"), ROUTES)
def test_scaffold_routes_return_not_implemented(
    method: str,
    path: str,
    request_kwargs: dict,
):
    """Every scaffold endpoint is registered and returns its placeholder."""
    response = client.request(method, path, **request_kwargs)

    assert response.status_code == 501
    assert "not implemented yet" in response.json()["detail"]


def test_health_route_is_registered():
    """The health endpoint responds successfully."""
    response = client.get("/health")

    assert response.status_code == 200
