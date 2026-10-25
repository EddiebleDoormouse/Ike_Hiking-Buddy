# Gemini model calls

| function | model | thinking_level | why | latency |
|---|---|---|---|---|
| `ping_models` | `gemini-4-argon`, `gemini-3.8-flash` | low | Smoke test | not measured: no GEMINI_API_KEY on build VM |
| `analyze_media` (DV-P1) | `gemini-3.8-flash` | low | Fast per-media caption + up to 3 candidates; structured JSON (`MediaAnalysis`), one retry on invalid JSON; photo = display JPEG, audio = original clip | not measured: no GEMINI_API_KEY on build VM |
| `research_hazards` / `draft_plan` / `revise_plan` (DV-P2) | `gemini-4-argon` | high | Planning research and checks loop | Not measured yet |
| `recap` | `gemini-4-argon` | medium | Long-context hike recap: one request with stats, route summary, notes, every media caption/time/location, sightings with status and all display JPEGs (768 px) | logged per call: latency_s + usage tokens (total_input/output/thought/total) via `logging`; live values unmeasured — no GEMINI_API_KEY on build VM |

All calls go through the Interactions API in `backend/app/services/gemini.py`. Never set `temperature`, `top_p`, `top_k`, or `thinking_budget`.

`analyze_media` logs `latency_ms` per call (logger `app.services.gemini`).
