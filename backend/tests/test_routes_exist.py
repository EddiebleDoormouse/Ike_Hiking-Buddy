"""Tests that the scaffold API routes are registered."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

ROUTES = [
    (
        "POST",
        "/hikes/hike-1/track",
        {"files": {"file": ("sample.gpx", b"<gpx />", "application/gpx+xml")}},
    ),
    ("GET", "/search?q=fox", {}),
    ("GET", "/species/near?lat=51.5&lon=-0.1", {}),
    ("POST", "/hikes/hike-1/recap", {}),
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


def test_dv_p1_routes_are_registered():
    routes = {
        (method, route.path)
        for route in app.routes
        if hasattr(route, "methods")
        for method in route.methods
    }
    # FastAPI 0.162 keeps included routers lazy; inspect their effective routes.
    for route in app.routes:
        if hasattr(route, "effective_route_contexts"):
            routes.update(
                (method, context.path_format)
                for context in route.effective_route_contexts()
                for method in context.original_route.methods
            )
    expected = {
        ("POST", "/hikes"),
        ("GET", "/hikes"),
        ("GET", "/hikes/{hike_id}"),
        ("POST", "/hikes/{hike_id}/media"),
        ("GET", "/media/{media_id}"),
        ("GET", "/media/{media_id}/file"),
    }

    assert expected <= routes
