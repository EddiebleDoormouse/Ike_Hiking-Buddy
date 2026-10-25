"""Shared Gemini Interactions API helpers."""

import time
from typing import Any

from google import genai

from app.config import settings

ARGON = "gemini-4-argon"
FLASH = "gemini-3.8-flash"

_client: genai.Client | None = None


class GeminiError(Exception):
    """Raised when a Gemini request or structured response is invalid."""


def get_client() -> genai.Client:
    """Return the cached Gemini client, creating it on first use."""
    global _client
    if _client is None:
        if settings.GEMINI_API_KEY:
            _client = genai.Client(api_key=settings.GEMINI_API_KEY)
        else:
            _client = genai.Client()
    return _client


def create_interaction(**kwargs: Any) -> Any:
    """Call the Interactions API and expose SDK failures as GeminiError."""
    try:
        return get_client().interactions.create(**kwargs)
    except Exception as exc:
        raise GeminiError(f"Gemini request failed: {exc}") from exc


def ping_models() -> dict[str, dict]:
    """Smoke-test the configured Gemini models and report their latency."""
    results = {}
    for model in (ARGON, FLASH):
        start_time = time.perf_counter()
        try:
            interaction = create_interaction(
                model=model,
                input="Reply with the single word OK.",
                generation_config={"thinking_level": "low"},
            )
            reply = (getattr(interaction, "output_text", None) or "").strip()
            latency_s = round(time.perf_counter() - start_time, 2)
            if (
                getattr(interaction, "status", None) == "failed"
                or not reply
            ):
                results[model] = {
                    "ok": False,
                    "latency_s": latency_s,
                    "error": "empty or failed reply",
                    "reply": None,
                }
                continue
            results[model] = {
                "ok": True,
                "latency_s": latency_s,
                "error": None,
                "reply": reply[:40],
            }
        except GeminiError as exc:
            results[model] = {
                "ok": False,
                "latency_s": None,
                "error": str(exc),
                "reply": None,
            }
    return results
