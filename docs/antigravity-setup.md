# Antigravity Setup: Team Checklist (Fri 23 Oct, before 17:00; updated 19:55)

Sources read 23 Oct: antigravity.google/docs (plans, permissions, rules, ide/settings, workflows, migration/workflows-to-skills). "3p" = third-party guide or forum. **Unverified** = check in the app (2 min). Nothing here is project code: install, settings and docs only. `docs/hackathon-spec.md` (§5) and the three check skills (§7) are now in the repo.

## 1. Credits: three separate pools
| Pool | Powers | Notes |
|---|---|---|
| Antigravity quota | The coding agents | Per Google account, set by the Google AI plan. Free = "meaningful quota, refreshed weekly" + weekly rate limit. Pro/Ultra = 5-hour refresh. AI-credit overage is Pro/Ultra only. No bring-your-own-key. |
| Gemini API / Cloud credits (DeepMind, collect at kickoff) | The app's runtime calls (Argon, flash) | Probably cannot top up Antigravity quota (**unverified**). Ask the DeepMind booth (Amit Vadi, Geneviève Huskens). |
| Atlas $100 | M10 cluster | MongoDB booth, ground floor. |

- **Overnight risk:** free quota plus parallel subagents hits 429s fast (3p reports). Three Antigravity streams on free quota may stall at 2am. Decide at 21:30 how many to launch; Devin (separate credit) takes more tickets if quota is thin.
- Everyone signs in with **their own** Google account (quota is per account).
- Check gemini.google.com/students with the Imperial email. Sources conflict on whether UK students get free AI Plus or Pro; either lifts the free tier. Read the card/renewal terms first.
- Use a Flash-class model for routine edits and the top model for planning (Gemini models share one limit, drawn down by price: 3p). Watch usage on the Settings page.

## 2. Per-laptop checklist (about 15 min)
1. Update Antigravity (docs show IDE v2.1.x). Sign in with your own account. Open the **repo root** as the workspace.
2. Permissions (section 3).
3. Gemini skill: `npx skills add google-gemini/gemini-skills --skill gemini-api-dev -a antigravity` (alternative: `agy plugin install https://github.com/google-gemini/gemini-skills`). MongoDB skills are already in. Keep total skills under about 5 (3p: huge skill packs make first load take 10+ minutes). Skill folders per the official migration page: workspace `.agents/skills/<name>/SKILL.md`, global `~/.gemini/config/skills/<name>/SKILL.md`. Older guides say `.agent/skills` and `~/.gemini/antigravity/skills`; if a skill doesn't load, check which folder the installer used.
4. **Skill test.** New chat: "List your loaded skills. Per gemini-api-dev: how do I set reasoning effort on gemini-4-argon and which parameters must I not pass?" Correct answer: `thinking_level`; no `thinking_budget`, `temperature`, `top_p`, `top_k`. If it says `thinking_budget`, the skill isn't loading: fix now, not at 2am.
5. Edouard only: MongoDB MCP (section 6). Teammates skip it; each extra MCP server adds tool definitions to every agent's context (costs quota).
6. Friends' raw data stays **outside** the repo folder (e.g. `~/hb-data`), and Settings → non-workspace file access = Deny. Antigravity sends file contents to Google models; the import script (WP9) should read the path from an env var `HB_DATA_DIR` instead of `data/` inside the repo.
7. `git pull` the repo, then type `/ship-check` to confirm the three check skills are picked up (section 7).

## 3. Permissions (Settings / Customizations)
Lists are evaluated Deny > Ask > Allow. Anything unlisted prompts, and **an overnight agent stops at a prompt until morning**. So: run one real task, watch which prompts appear, add them to Allow. Syntax is from the docs example; adjust if the UI rejects it.
```
Allow:
command(git (status|diff|add|commit|checkout|switch|branch|log|push|pull|fetch))
command(pytest)
command(python -m pytest)
command(pip install)
command(npm (install|run (build|lint|test|dev)))
command(uvicorn)
command(ruff)
mcp(mongodb/*)          # Edouard's laptop only

Deny:
command(rm -rf)
command(git push --force)
command(git push -f)
command(git reset --hard)
```
- Overnight: Artifact Review Policy = Always Proceed. Strict Mode **off** (it forces review on every command and ignores the allow list). Even in auto mode agents can still pause at file edits, MCP calls and browser actions (3p), so test it.
- Daytime with a beginner at the keyboard: keep Planning mode and read the Plan artifact before approving.
- Terminal sandboxing is optional; leave off unless you test that pip/npm still work.

## 4. Rules: additions to AGENTS.md
Antigravity reads root `AGENTS.md` and `GEMINI.md`; 12,000 characters max per rule file. Scoped rules live in `.agents/rules/*.md` (`.agent/rules` is listed as legacy). **Every file in `rules/` must start with YAML frontmatter declaring a `trigger`** (`always_on`, `model_decision`, `glob` or `manual`), per the official rules page; root `AGENTS.md` is plain markdown. Our AGENTS.md is about 3.3k characters, so there is room. Append:
```
Spec rules (hackathon scoring):
12. Before designing anything user-facing, read docs/hackathon-spec.md. Task details are in docs/build-spec.md (section for your WP).
13. Every demo-path feature needs a check an agent can run: a pytest, a script, or the /browser agent at 390px width. No check, not done.
14. All Gemini calls go through backend/app/services/gemini.py. When you add or change one, update docs/MODELS.md (function, model, thinking_level, why).
15. UI honesty: every AI-generated claim shows its confidence/status and its source. Plans are labelled "suggested; check conditions before you go". Never hide a failed check.
16. If a Gemini or Atlas call fails, read the skill/docs. Never silently swap in an older model or invent parameters. Write the failure in NOTES.md.
17. Never read or open anything outside the workspace. Real friend data is not in the repo; use synthetic fixtures.
```
Optional scoped rules (Customizations → Rules, glob trigger): `frontend/**` = mobile-first at 390px, API calls only through `src/api/client.ts`, mocks when `VITE_USE_MOCKS`, comment code for beginners. `backend/**` = type hints, pydantic models, mock all network in tests.

**Done 23 Oct 19:55:** `docs/build-spec.md` and `docs/hackathon-spec.md` are in the repo (mirrored from the Project), so the AGENTS.md references resolve.

## 5. docs/hackathon-spec.md (now in the repo)
```
# What the judges score (condensed from the Encode page)
Demo: 3 min, live, real inputs, no slides.

## Google DeepMind: Gemini 4 Argon (50% live demo / 25% problem / 15% originality / 10% pitch)
- Runs live on real inputs in under 3 min; Argon used effectively with a REAL verification loop.
  -> Plan loop: Argon drafts, run_checks verifies (forecast limits, finish before sunset, sources cited), revise. Show checks in the UI.
  -> Sighting loop: flash proposes species, GBIF/BirdNET verify, status Confirmed/Plausible/Unsure.
- Needs Argon: whole-hike recap in one long-context call; multimodal (photo, audio); orchestration (parallel flash analysis).
- People stay in control: nothing automatic that affects the outside world; plans are suggestions.
- Avoid: chat wrapper, static page, unverified safety advice.
- Submission: say which Gemini models/agents were used and how (docs/MODELS.md).

## MongoDB Atlas
- Must use at least one Atlas feature; more features = more points: Atlas Search, Vector Search, Hybrid Search, Automated Embedding, Stream Processing, Voyage models.
  -> We use: Automated Embedding (voyage-3.5) + Vector Search on captions, Atlas Search on captions/tags/species, hybrid query, 2dsphere geo queries.
- Video must show the app working AND MongoDB in use (mongosh/Compass/app search).

## The Real World
- Usefulness; how well it reads messy inputs and gaps (photos without EXIF, missing HR, no forecast beyond 16 days); working end to end on real data; responsibility (privacy, honesty about uncertainty).
- Needs: README with setup steps, 2-4 min video on real inputs, short note on models and data sources.
  -> Always show uncertainty; never present species ID or hazards as certain; strip EXIF GPS from public images; no one's home start point.
```

## 6. MongoDB MCP (Edouard's laptop only)
Agent panel → "…" → MCP Servers → Manage MCP Servers → View raw config (3p docs for the MCP store path):
```json
{
  "mcpServers": {
    "mongodb": {
      "command": "npx",
      "args": ["-y", "mongodb-mcp-server@latest", "--readOnly"],
      "env": { "MDB_MCP_CONNECTION_STRING": "<Atlas connection string>" }
    }
  }
}
```
Read-only on purpose: agents can inspect data and test queries but can't drop collections. Index creation stays in `scripts/setup_indexes.py` (WP5). The config lives on the laptop, not in the repo. Antigravity may need a restart to load it.

## 7. Check skills (replacing workflows)
**Workflows are retired.** The official workflows page says "Current workflows will stop working on October 19, 2026" (a third-party page says 1 Nov; the official date wins), which is why they can't be found in the app. The replacement is a skill: `.agents/skills/<name>/SKILL.md` with `name` and `description` frontmatter, typed as `/<name>`. If a skill and a workflow share a name, the skill runs. (`/migrate-workflows` converts old workflows; we don't need it.)

Our three checks are in the repo at `.agents/skills/{ship-check,spec-check,demo-check}/SKILL.md`:
- **/ship-check:** backend tests, frontend build, secrets and data scan. Before every merge.
- **/spec-check:** read-only audit of the repo against `docs/hackathon-spec.md`; lists the 5 cheapest fixes for the demo. Sat 18:00 and Sun 08:00.
- **/demo-check:** walks demo-script steps 2–4 (in `docs/hiking-buddy-plan.md`) with the browser agent at 390px and reports what breaks, without fixing. Before each rehearsal.

Skills are also picked up by description, so an agent may use them unprompted; each description says "run only when asked". Unverified: whether `/name` autocompletes for skills in your build. If not, say "run the ship-check skill".

## 8. Working habits for best output
- One WP per conversation. Start with "Read AGENTS.md, then docs/build-spec.md WPx". Give owned files and acceptance tests (overnight template).
- Planning mode for WP1, 3, 4, 5. Fast mode for CSS and small edits.
- Tests are the pass/fail signal. Never accept "done" without a green run.
- One branch per agent. Small commits. PR description lists done / not done / how to test.
- Don't paste real keys or friend data into chats.

## 9. treg
What it is (verified): a pay-per-call catalog of third-party APIs and vendor CLIs for agents, with credentials held server-side. Docs say $1.00 free credit per new verified team (you mentioned $20: maybe a hackathon promo; `treg balance` shows the truth). Its skill (`treg:treg`) will offer to run `treg mcp install`.
For us it adds little: Open-Meteo and GBIF are free with no key, and Gemini grounded search covers closures. Recommendation: keep the CLI installed, **decline `treg mcp install`**, send no friend data through it. Revisit only if we need a paid API (one team key, then).
