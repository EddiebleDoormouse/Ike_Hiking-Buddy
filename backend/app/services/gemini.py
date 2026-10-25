"""Shared Gemini Interactions API helpers."""

import base64
import logging
import time
from typing import Any

from google import genai
from pydantic import BaseModel, ValidationError

from app.config import settings
from app.models import Candidate

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


MEDIA_THINKING_LEVEL = "low"
MAX_CANDIDATES = 3
FUNGUS_SAFETY_NOTE = "Never eat anything based on this ID"
MEDIA_PROMPT = """You are a careful UK naturalist helping a hiker log what they saw on a walk in the United Kingdom.
You will receive one photo or one audio clip, plus context (place, coordinates, date, hike title).

Return JSON matching the schema:
- caption: 1-2 plain sentences that would help someone find this item later by search. Name the main subject, its colours, the habitat, the landscape, and the light or weather if visible. For audio, describe what can be heard (e.g. "A wren singing loudly from dense scrub, with a stream in the background").
- tags: 3 to 8 short lowercase tags (e.g. "oak", "woodland", "autumn", "mushroom", "birdsong", "moorland").
- is_organism: true only if a living (or recently living) wild plant, animal, fungus or lichen is the clear subject. Landscapes, views, trails, buildings, people, pets, farm livestock and food are false.
- candidates: if is_organism is false, return an empty list. Otherwise give at most 3 candidate identifications, most likely first. Prefer species that occur in the UK at this place and time of year. Each has common_name (UK English), scientific_name (Latin binomial, or genus if you cannot go further), confidence (0 to 1) and group.
- confidence must be honest: it is your probability that the candidate is correct. Use high values (above 0.8) only when the diagnostic features are clearly visible or audible. Blurry, distant, partial or noisy input gets low values. Confidences across candidates should not add up to more than 1.
- group: exactly one of "plant", "fungus", "bird", "mammal", "insect", "reptile_amphibian", "other". This routes the sighting to a specialist checker (plants and fungi to image specialists, birds to a song checker), so choose it carefully: mushrooms, toadstools and brackets are "fungus", not "plant"; moths, butterflies, beetles and bees are "insect"; lichens, fish, spiders and slugs are "other"; frogs, toads, newts, lizards and snakes are "reptile_amphibian".
- safety_note: if any candidate is a fungus, or the photo shows berries or fruit, set it to exactly "Never eat anything based on this ID". Otherwise null. Never say that anything is edible or safe to eat.

Audio clips: identify birds by their song or call. If no bird or other animal can be heard (e.g. only wind, water or people), set is_organism to false and give no candidates.
Never present an identification as certain."""


class MediaAnalysis(BaseModel):
    caption: str
    tags: list[str]
    is_organism: bool
    candidates: list[Candidate] = []
    safety_note: str | None = None


logger = logging.getLogger(__name__)


def _format_context(ctx: dict) -> str:
    """Format the useful hike details for Gemini."""
    labels = (
        ("place", "Place"),
        ("lat", "Lat"),
        ("lon", "Lon"),
        ("date", "Date"),
        ("hike_title", "Hike title"),
    )
    lines = []
    for key, label in labels:
        value = ctx.get(key)
        if value is None:
            continue
        if key in ("lat", "lon"):
            value = f"{float(value):.4f}"
        lines.append(f"- {label}: {value}")
    return "\n".join(lines)


def _clean_analysis(analysis: MediaAnalysis) -> MediaAnalysis:
    """Normalize tags, candidates, and the required safety wording."""
    tags = []
    seen_tags = set()
    for tag in analysis.tags:
        cleaned_tag = tag.strip().lower()
        if cleaned_tag and cleaned_tag not in seen_tags:
            seen_tags.add(cleaned_tag)
            tags.append(cleaned_tag)
        if len(tags) == 8:
            break

    has_fungus = any(candidate.group == "fungus" for candidate in analysis.candidates)
    if analysis.is_organism:
        candidates = sorted(
            analysis.candidates,
            key=lambda candidate: candidate.confidence,
            reverse=True,
        )[:MAX_CANDIDATES]
    else:
        candidates = []

    safety_note = (
        FUNGUS_SAFETY_NOTE
        if has_fungus or (analysis.safety_note is not None and analysis.safety_note.strip())
        else None
    )
    return analysis.model_copy(
        update={
            "tags": tags,
            "candidates": candidates,
            "safety_note": safety_note,
        }
    )


def analyze_media(
    data: bytes,
    mime: str,
    ctx: dict,
    model: str | None = None,
) -> MediaAnalysis:
    """Ask Gemini for a structured caption and identification candidates."""
    if mime.startswith("image/"):
        media_type = "image"
    elif mime.startswith("audio/"):
        media_type = "audio"
    else:
        raise GeminiError(f"Unsupported media type {mime!r}")

    media_part = {
        "type": media_type,
        "data": base64.b64encode(data).decode("ascii"),
        "mime_type": mime,
    }
    input_content = [
        {
            "type": "text",
            "text": MEDIA_PROMPT + "\n\nContext:\n" + _format_context(ctx),
        },
        media_part,
    ]
    model_name = model or settings.MEDIA_MODEL

    for attempt in range(1, 3):
        start_time = time.perf_counter()
        try:
            interaction = create_interaction(
                model=model_name,
                input=input_content,
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": MediaAnalysis.model_json_schema(),
                },
                generation_config={"thinking_level": MEDIA_THINKING_LEVEL},
            )
        finally:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            logger.info(
                "gemini analyze_media model=%s mime=%s attempt=%d latency_ms=%d",
                model_name,
                mime,
                attempt,
                latency_ms,
            )

        try:
            output_text = getattr(interaction, "output_text", None)
            if output_text is None:
                raise ValueError("Gemini returned no media analysis JSON")
            analysis = MediaAnalysis.model_validate_json(output_text)
        except (ValidationError, TypeError, ValueError) as exc:
            if attempt == 2:
                raise GeminiError(
                    f"Gemini returned invalid media analysis JSON twice: {exc}"
                ) from exc
            continue

        return _clean_analysis(analysis)

    raise GeminiError("Gemini returned invalid media analysis JSON twice.")
