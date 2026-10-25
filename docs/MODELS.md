# Model use

| Call | Model | Thinking level | Tools / output |
|---|---|---|---|
| `research_hazards` | `gemini-4-argon` | `high` | Google Search; URL citation annotations become sourced hazards |
| `draft_plan` | `gemini-4-argon` | `high` | Structured JSON matching `PlanDraft` |
| `revise_plan` | `gemini-4-argon` | `high`; `low` if the loop has already taken more than 45 seconds | Structured JSON matching `PlanDraft` |

All calls use the Gemini Interactions API. Do not set `temperature`, `top_p`,
`top_k`, or `thinking_budget`.

## Progress

`POST /hikes/{id}/plan` stores the latest planner event in `plan_progress`.
Events include `stage`, `message`, `revision`, `failed`, `elapsed_ms`, and
`updated_at` (UTC ISO timestamp). The UI can poll
`GET /hikes/{id}/plan/progress`; it returns the latest event, or
`{"stage": "idle", "message": "Not started"}` before planning begins.

## Latency

Live run, 25 Oct 2026, all calls at `high`, for a synthetic Chilterns hike (Tring to Ivinghoe Beacon, 13 km, 330 m ascent) on Sat 31 Oct:

| Step | ms |
|---|---|
| forecast (Open-Meteo) | 337 |
| research_hazards | 96307 |
| draft_plan | 57273 |
| total (0 revisions, all checks passed) | 153917 |

The hazard search accounts for most of the time. Any revision after this point would run at `low`, because the loop is already past 45 s.
