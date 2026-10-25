# Model use

| Call | Model | Thinking level | Tools / output |
|---|---|---|---|
| `analyze_media` (photo: display JPEG; audio: original clip) | `gemini-3.8-flash` (`settings.MEDIA_MODEL`) | `low` | Structured JSON matching `MediaAnalysis` (caption, tags, is_organism, ≤3 candidates with group, safety_note); one retry on invalid JSON |

All calls use the Gemini Interactions API. Do not set `temperature`, `top_p`,
`top_k`, or `thinking_budget`.

## Latency

Each `analyze_media` call logs `latency_ms` (logger `app.services.gemini`).

| Call | Input | Latency | Notes |
|---|---|---|---|
| `analyze_media` | — | not measured yet | no `GEMINI_API_KEY` in the build environment |
