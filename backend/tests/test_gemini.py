"""Tests for Gemini media analysis using mocked Interactions API requests."""

import base64
import json

import httpx
import pytest
import respx

from app.services import gemini
from app.services.gemini import (
    FUNGUS_SAFETY_NOTE,
    GeminiError,
    MediaAnalysis,
    analyze_media,
)

INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"


@pytest.fixture(autouse=True)
def reset_gemini_client(monkeypatch):
    """Use a test API key and a fresh Gemini client for each test."""
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    gemini._client = None
    yield
    gemini._client = None


def interaction_response(output_text: str) -> dict:
    """Build the completed Interactions API response used by the tests."""
    return {
        "id": "v1_x",
        "model": "gemini-3.8-flash",
        "object": "interaction",
        "status": "completed",
        "created": "2026-10-25T07:00:00Z",
        "updated": "2026-10-25T07:00:00Z",
        "steps": [
            {
                "type": "model_output",
                "content": [{"type": "text", "text": output_text}],
            }
        ],
    }


def valid_output(**updates) -> str:
    """Return a valid analysis JSON string with optional field overrides."""
    payload = {
        "caption": "A small bird sings from a green hedgerow.",
        "tags": ["bird", "hedgerow"],
        "is_organism": True,
        "candidates": [
            {
                "common_name": "Wren",
                "scientific_name": "Troglodytes troglodytes",
                "confidence": 0.8,
                "group": "bird",
            }
        ],
        "safety_note": None,
    }
    payload.update(updates)
    return json.dumps(payload)


def analysis_route(*outputs: str):
    """Mock one or more completed Interactions API responses."""
    responses = [
        httpx.Response(200, json=interaction_response(output))
        for output in outputs
    ]
    return respx.post(INTERACTIONS_URL).mock(side_effect=responses)


def contains_key(value: object, key: str) -> bool:
    """Check nested request values for a forbidden configuration key."""
    if isinstance(value, dict):
        return key in value or any(contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(contains_key(item, key) for item in value)
    return False


@respx.mock
def test_photo_happy_path_sends_structured_image_request():
    route = analysis_route(valid_output())
    image_data = b"sample-image"
    context = {
        "place": "Lake District",
        "lat": 54.123456,
        "lon": -3.234567,
        "date": "2026-10-25",
        "hike_title": "Autumn walk",
        "ignored": "not included",
    }

    result = analyze_media(image_data, "image/jpeg", context)

    assert isinstance(result, MediaAnalysis)
    assert result.caption == "A small bird sings from a green hedgerow."
    assert route.call_count == 1
    body = json.loads(route.calls.last.request.content)
    assert body["model"] == "gemini-3.8-flash"
    assert body["generation_config"]["thinking_level"] == "low"
    assert body["response_format"]["mime_type"] == "application/json"
    assert "properties" in body["response_format"]["schema"]
    assert body["input"][0]["content"][1] == {
        "type": "image",
        "data": base64.b64encode(image_data).decode("ascii"),
        "mime_type": "image/jpeg",
    }
    context_text = body["input"][0]["content"][0]["text"]
    assert "- Place: Lake District" in context_text
    assert "- Lat: 54.1235" in context_text
    assert "- Lon: -3.2346" in context_text
    assert "- Date: 2026-10-25" in context_text
    for key in ("temperature", "top_p", "top_k", "thinking_budget"):
        assert not contains_key(body, key)


@respx.mock
def test_audio_request_uses_audio_part():
    route = analysis_route(valid_output())

    analyze_media(b"sample-audio", "audio/wav", {})

    body = json.loads(route.calls.last.request.content)
    audio_part = body["input"][0]["content"][1]
    assert audio_part["type"] == "audio"
    assert audio_part["mime_type"] == "audio/wav"


@respx.mock
def test_model_override_is_sent_to_gemini():
    route = analysis_route(valid_output())

    analyze_media(b"image", "image/png", {}, model="custom-media-model")

    body = json.loads(route.calls.last.request.content)
    assert body["model"] == "custom-media-model"


@respx.mock
def test_invalid_json_is_retried_once_then_valid_result_is_returned():
    route = analysis_route("{invalid", valid_output())

    result = analyze_media(b"image", "image/jpeg", {})

    assert route.call_count == 2
    assert result.caption == "A small bird sings from a green hedgerow."


@respx.mock
def test_invalid_json_twice_raises_gemini_error():
    route = analysis_route("{invalid", "{also invalid")

    with pytest.raises(GeminiError, match="invalid media analysis JSON twice"):
        analyze_media(b"image", "image/jpeg", {})

    assert route.call_count == 2


@respx.mock
def test_non_organism_analysis_discards_candidates():
    route = analysis_route(valid_output(is_organism=False))

    result = analyze_media(b"image", "image/jpeg", {})

    assert route.call_count == 1
    assert result.is_organism is False
    assert result.candidates == []


@respx.mock
def test_candidates_and_tags_are_sorted_and_cleaned():
    candidates = [
        {
            "common_name": f"Candidate {confidence}",
            "scientific_name": "Test species",
            "confidence": confidence,
            "group": "plant",
        }
        for confidence in (0.2, 0.9, 0.4, 0.8, 0.6)
    ]
    route = analysis_route(
        valid_output(
            tags=[
                " WOODLAND ",
                "Fox",
                "woodland",
                "Bird",
                "Trail",
                "Moss",
                "Autumn",
                "Nature",
                "Extra",
            ],
            candidates=candidates,
        )
    )

    result = analyze_media(b"image", "image/jpeg", {})

    assert route.call_count == 1
    assert result.tags == [
        "woodland",
        "fox",
        "bird",
        "trail",
        "moss",
        "autumn",
        "nature",
        "extra",
    ]
    assert [candidate.confidence for candidate in result.candidates] == [0.9, 0.8, 0.6]


@respx.mock
def test_fungus_candidate_gets_standard_safety_note():
    fungus = {
        "common_name": "Fly agaric",
        "scientific_name": "Amanita muscaria",
        "confidence": 0.7,
        "group": "fungus",
    }
    route = analysis_route(valid_output(candidates=[fungus]))

    result = analyze_media(b"image", "image/jpeg", {})

    assert route.call_count == 1
    assert result.safety_note == FUNGUS_SAFETY_NOTE


@respx.mock
def test_unsupported_media_type_makes_no_request():
    route = respx.post(INTERACTIONS_URL).mock(
        return_value=httpx.Response(200, json=interaction_response(valid_output()))
    )

    with pytest.raises(GeminiError, match="Unsupported media type"):
        analyze_media(b"video", "video/mp4", {})

    assert route.call_count == 0


@respx.mock
def test_http_400_is_wrapped_and_not_retried():
    route = respx.post(INTERACTIONS_URL).mock(
        return_value=httpx.Response(400, json={"error": {"message": "bad request"}})
    )

    with pytest.raises(GeminiError, match="Gemini request failed"):
        analyze_media(b"image", "image/jpeg", {})

    assert route.call_count == 1
