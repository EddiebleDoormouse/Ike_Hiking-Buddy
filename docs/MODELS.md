# Gemini model calls

| function | model | thinking_level | why | latency |
|---|---|---|---|---|
| `ping_models` | `gemini-4-argon`, `gemini-3.8-flash` | low | Smoke test | not measured: no GEMINI_API_KEY on build VM |
| `analyze_media` (DV-P1) | `gemini-3.8-flash` | low | Fast per-media caption + candidates | Not measured yet |
| `research_hazards` / `draft_plan` / `revise_plan` (DV-P2) | `gemini-4-argon` | high | Planning research and checks loop | high: 154 s total (hazards 96 s, draft 57 s); medium 37 s; low 60 s (one run each) |
| `recap` | `gemini-4-argon` | TBD | Long-context hike recap | TBD |

All calls go through the Interactions API in `backend/app/services/gemini.py`. Never set `temperature`, `top_p`, `top_k`, or `thinking_budget`.

## Progress

`POST /hikes/{id}/plan` first stores a `queued` event with a unique `run_id`.
Progress events include `stage`, `message`, `revision`, `failed`, `elapsed_ms`,
`updated_at` (UTC ISO timestamp), and `run_id`. Updates are guarded by the
current run ID, so an older overlapping request cannot overwrite newer
progress. The final `done` event is saved atomically with the plan; a
superseded POST returns HTTP 409. The planner also stores the ordered event
history in `plan_events`. `GET /hikes/{id}/plan/progress` returns the latest
event and the full `events` list, or an idle event with an empty list before
planning begins.

## Latency

The high-thinking-level timing was measured on 25 Oct 2026 for a synthetic
Chilterns hike (Tring to Ivinghoe Beacon, 13 km, 330 m ascent) on Sat 31 Oct.
The summary row compares one run at each level. The high-level run had no
revisions and all checks passed:

| Step | ms |
|---|---|
| forecast (Open-Meteo) | 337 |
| research_hazards | 96307 |
| draft_plan | 57273 |
| total | 153917 |

## Revision thinking-level fallback

Hazard research and the initial draft use `high`. Revisions also use `high`
unless the planner loop has exceeded 45 seconds; revisions then switch to
`low`. These latency measurements are one run per level and should be treated
as indicative, not conclusive.
