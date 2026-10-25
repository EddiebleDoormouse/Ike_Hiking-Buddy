# Gemini model calls

| function | model | thinking_level | why | latency |
|---|---|---|---|---|
| `ping_models` | `gemini-4-argon`, `gemini-3.8-flash` | low | Smoke test | not measured: no GEMINI_API_KEY on build VM |
| `analyze_media` (DV-P1) | `gemini-3.8-flash` | low | Fast per-media caption + candidates | Not measured yet |
| `research_hazards` / `draft_plan` / `revise_plan` (DV-P2) | `gemini-4-argon` | high | Planning research and checks loop | Not measured yet |
| `recap` | `gemini-4-argon` | TBD | Long-context hike recap | TBD |

All calls go through the Interactions API in `backend/app/services/gemini.py`. Never set `temperature`, `top_p`, `top_k`, or `thinking_budget`.
