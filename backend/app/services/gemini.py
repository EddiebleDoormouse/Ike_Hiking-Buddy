"""Shared Gemini Interactions API helpers."""

import logging
import time
from typing import Any

from google import genai

from app.config import settings

ARGON = "gemini-4-argon"
FLASH = "gemini-3.8-flash"
RECAP_THINKING_LEVEL = "medium"

logger = logging.getLogger(__name__)

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


# --- Hike recap (one long-context Argon call per hike) ---

RECAP_INSTRUCTIONS = """Write the recap in markdown with exactly these sections, in this order:
1. A 150-250 word story of the hike in the second person ("you"), grounded
   in the stats, route, photos and sightings above. No heading on this section.
2. "## Highlights": exactly 3 bullet points.
3. "## Species log": a markdown table with columns "Species | Status | Time".
   List only species whose status is "confirmed" or "probably", and write the
   Status cell exactly as given. If none qualify, write
   "_Nothing confirmed or probable this time._" instead of a table.
4. "## Next time": exactly 2 practical tips drawn from this hike's pace
   and conditions.

Never present a species identification as more certain than its status, and
never suggest that any plant or fungus is safe to eat."""


def _fmt_duration(minutes: int) -> str:
    """Format minutes as e.g. "3 h 05 min"."""
    hours, mins = divmod(int(minutes), 60)
    return f"{hours} h {mins:02d} min"


def _stats_text(stats: dict | None) -> str:
    """One line of track stats for the recap prompt, skipping missing fields."""
    if not stats:
        return "no track stats recorded"
    parts = []
    if stats.get("distance_km") is not None:
        parts.append(f"{stats['distance_km']:.1f} km")
    if stats.get("duration_s") is not None:
        parts.append(f"{_fmt_duration(round(stats['duration_s'] / 60))} elapsed")
    if stats.get("moving_s") is not None:
        parts.append(f"{_fmt_duration(round(stats['moving_s'] / 60))} moving")
    if stats.get("ascent_m") is not None:
        parts.append(f"{stats['ascent_m']:.0f} m ascent")
    if stats.get("avg_hr") is not None:
        parts.append(f"avg HR {stats['avg_hr']:.0f}")
    if stats.get("max_hr") is not None:
        parts.append(f"max HR {stats['max_hr']:.0f}")
    return ", ".join(parts) if parts else "no track stats recorded"


def _media_line(index: int, media: dict) -> str:
    """One media item's metadata as a prompt line, numbered like its photo."""
    kind = media.get("kind") or "media"
    caption = media.get("caption") or "no caption"
    when = media.get("taken_at") or "time unknown"
    where = media.get("location") or "location unknown"
    return f"- Media {index} ({kind}): {caption} — {when} — {where}"


def _sighting_line(sighting: dict) -> str:
    """One sighting as a prompt line: name, status word, and time seen."""
    name = sighting.get("name") or "unidentified species"
    scientific = sighting.get("scientific_name")
    label = f"{name} ({scientific})" if scientific else name
    status = sighting.get("status") or "unsure"
    when = sighting.get("seen_at") or "time unknown"
    return f"- {label} — {status} — seen {when}"


def build_recap_prompt(hike_bundle: dict[str, Any]) -> str:
    """Render the whole hike bundle as the recap request's text block.

    `hike_bundle` is assembled by the recap router:
      title, trail_name, hiker, date: hike fields.
      stats: the track stats dict (may be empty).
      route_summary: {"start", "end", "highest"} short strings or None.
      notes: list of trail-note texts.
      media: list of {kind, caption, taken_at, location, text, image_b64};
        image_b64 (a <=768 px JPEG) is set for photos only.
      sightings: list of {name, scientific_name, status, seen_at}; status is
        "confirmed", "probably" (plausible) or "unsure".
    """
    route = hike_bundle.get("route_summary") or {}
    media = hike_bundle.get("media") or []
    sightings = hike_bundle.get("sightings") or []
    notes = hike_bundle.get("notes") or []

    media_lines = [_media_line(i, m) for i, m in enumerate(media, start=1)]
    species_lines = [_sighting_line(s) for s in sightings]

    return "\n".join(
        [
            "You are writing the post-hike recap of one UK hike. Everything "
            "the recap may use is in this single request; do not invent "
            "sightings, photos or conditions.",
            "",
            f"Hike: {hike_bundle.get('title')} — "
            f"{hike_bundle.get('trail_name')}, walked by "
            f"{hike_bundle.get('hiker')} on {hike_bundle.get('date')}.",
            f"Stats: {_stats_text(hike_bundle.get('stats'))}",
            "Route: start {} · end {} · highest point {}".format(
                route.get("start") or "unknown",
                route.get("end") or "unknown",
                route.get("highest") or "unknown",
            ),
            "",
            "Trail notes:",
            *(notes or ["- none"]),
            "",
            f"Media ({len(media)} items; photo images follow below "
            "in the same order):",
            *(media_lines or ["- none"]),
            "",
            "Species sightings (status is confirmed, probably or unsure):",
            *(species_lines or ["- none"]),
            "",
            RECAP_INSTRUCTIONS,
        ]
    )


def build_recap_input(hike_bundle: dict[str, Any]) -> list[dict]:
    """Build the Interactions input: one text block plus every photo image.

    Each photo gets a short label block naming its Media number so the model
    can match images to the captions, times and locations in the prompt.
    """
    blocks: list[dict] = [
        {"type": "text", "text": build_recap_prompt(hike_bundle)}
    ]
    for index, media in enumerate(hike_bundle.get("media") or [], start=1):
        image_b64 = media.get("image_b64")
        if not image_b64:
            continue
        caption = media.get("caption") or "no caption"
        blocks.append({"type": "text", "text": f"Media {index} photo: {caption}"})
        blocks.append(
            {"type": "image", "data": image_b64, "mime_type": "image/jpeg"}
        )
    return blocks


def _usage_dict(usage: Any) -> dict[str, int]:
    """Pull the token counts worth logging out of the usage metadata."""
    if usage is None:
        return {}
    keys = (
        "total_input_tokens",
        "total_output_tokens",
        "total_thought_tokens",
        "total_tokens",
    )
    return {
        key: getattr(usage, key)
        for key in keys
        if getattr(usage, key, None) is not None
    }


def recap(hike_bundle: dict[str, Any]) -> dict[str, Any]:
    """Generate a hike's recap markdown in one Argon long-context call.

    Returns {"recap_md", "latency_s", "usage"}; the caller stores recap_md on
    the hike. Raises GeminiError when the interaction fails or has no text.
    """
    start_time = time.perf_counter()
    interaction = create_interaction(
        model=ARGON,
        input=build_recap_input(hike_bundle),
        generation_config={"thinking_level": RECAP_THINKING_LEVEL},
    )
    latency_s = round(time.perf_counter() - start_time, 2)
    usage = _usage_dict(getattr(interaction, "usage", None))
    logger.info(
        "recap model=%s thinking_level=%s latency_s=%s usage=%s",
        ARGON,
        RECAP_THINKING_LEVEL,
        latency_s,
        usage,
    )
    recap_md = (getattr(interaction, "output_text", None) or "").strip()
    if getattr(interaction, "status", None) == "failed" or not recap_md:
        raise GeminiError("recap returned an empty or failed reply")
    return {"recap_md": recap_md, "latency_s": latency_s, "usage": usage}
