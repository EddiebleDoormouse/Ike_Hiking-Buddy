# Model use

| Call | Model | Thinking level | Tools / output |
|---|---|---|---|
| `research_hazards` | `gemini-4-argon` | `low` | Google Search; URL citation annotations become sourced hazards |
| `draft_plan` | `gemini-4-argon` | `medium` | Structured JSON matching `PlanDraft` |
| `revise_plan` | `gemini-4-argon` | `medium`; `low` if the loop has already taken more than 45 seconds | Structured JSON matching `PlanDraft` |

All calls use the Gemini Interactions API. Do not set `temperature`, `top_p`,
`top_k`, or `thinking_budget`.

## Latency

Not measured yet (no API key in the build environment).
