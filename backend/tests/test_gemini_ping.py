"""Tests for Gemini model smoke checks."""

from app.services import gemini


def test_ping_models_reports_success_and_gemini_errors(monkeypatch):
    """Ping records successful calls and Gemini failures independently."""
    def fake_create_interaction(**kwargs):
        if kwargs["model"] == gemini.ARGON:
            raise gemini.GeminiError("offline")
        return object()

    monkeypatch.setattr(gemini, "create_interaction", fake_create_interaction)

    results = gemini.ping_models()

    assert results[gemini.ARGON] == {
        "ok": False,
        "latency_s": None,
        "error": "offline",
    }
    assert results[gemini.FLASH]["ok"] is True
    assert isinstance(results[gemini.FLASH]["latency_s"], float)
    assert results[gemini.FLASH]["error"] is None
