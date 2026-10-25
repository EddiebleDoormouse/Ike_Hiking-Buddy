"""Tests for Gemini model smoke checks."""

from types import SimpleNamespace

import pytest

from app.services import gemini


def test_ping_models_reports_success_and_gemini_errors(monkeypatch):
    """Ping records successful calls and Gemini failures independently."""

    def fake_create_interaction(**kwargs):
        if kwargs["model"] == gemini.ARGON:
            raise gemini.GeminiError("offline")
        return SimpleNamespace(status="completed", output_text=" OK\n")

    monkeypatch.setattr(gemini, "create_interaction", fake_create_interaction)

    results = gemini.ping_models()

    assert results[gemini.ARGON] == {
        "ok": False,
        "latency_s": None,
        "error": "offline",
        "reply": None,
    }
    assert results[gemini.FLASH]["ok"] is True
    assert isinstance(results[gemini.FLASH]["latency_s"], float)
    assert results[gemini.FLASH]["error"] is None
    assert results[gemini.FLASH]["reply"] == "OK"


@pytest.mark.parametrize(
    ("status", "output_text"),
    [
        ("completed", ""),
        ("failed", "OK"),
    ],
)
def test_ping_models_rejects_empty_or_failed_replies(
    monkeypatch,
    status: str,
    output_text: str,
):
    """Ping marks empty text and failed interactions as unsuccessful."""
    monkeypatch.setattr(
        gemini,
        "create_interaction",
        lambda **kwargs: SimpleNamespace(status=status, output_text=output_text),
    )

    results = gemini.ping_models()

    for result in results.values():
        assert result["ok"] is False
        assert isinstance(result["latency_s"], float)
        assert result["error"] == "empty or failed reply"
        assert result["reply"] is None
