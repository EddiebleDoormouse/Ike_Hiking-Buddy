# Build Spec: Work Packages, Agent Rules, Overnight Runs (v1, Fri 23 Oct 16:15)

Turns `docs/hiking-buddy-plan.md` into tasks that several coding agents (Antigravity/Gemini, Devin, Claude) and people can work on in parallel without conflicts. The rule for every package: **fixed interfaces, owned files, tests as the pass/fail signal.**

## Principles for a polished, winning build
1. **Demo path first.** Build the 3-minute demo end to end, roughly, by Saturday lunch, then polish only what's on that path. Anything off the path is Should or Could.
2. **The golden dataset.** The friends' hikes, loaded by an import script (WP9), make the demo reproducible. Never demo on hand-entered data.
3. **Interfaces before implementations.** Each service below has a fixed signature, so agents work in parallel against mocks.
4. **Review is the bottleneck, not code generation.** Run at most **3 agent streams at once**, sized to what Edouard can review the next morning.
5. **Rehearsal milestones:** Sat 18:00 demo rehearsal #1 (finds the gaps). Sun 10:30 dress rehearsal after recording the video.
6. **Keep a model log as we go** (`docs/MODELS.md`: which Gemini model or agent does what). The Gemini track requires it in the submission.

## Repo layout
```
hiking-buddy/
  AGENTS.md                 # agent rules (content below); Antigravity reads AGENTS.md/GEMINI.md at root
  README.md  .gitignore  .env.example
  backend/
    pyproject.toml or requirements.txt   # Python 3.11 (safest for BirdNET/TFLite)
    app/main.py  app/config.py  app/db.py  app/models.py
    app/routers/{hikes,media,plan,search,tracks}.py
    app/services/{gemini,tracks,exif,gbif,verify,weather,planning,birdnet,recap}.py
    scripts/{setup_indexes,import_hike,eval_accuracy}.py
    tests/  tests/fixtures/  (synthetic only)
  frontend/                 # Vite + React + TypeScript + Tailwind
    src/api/{client.ts,types.ts,mocks.ts}
    src/pages/{HikesGallery,HikeFolder,NewHike,Search}.tsx
    src/components/...
  data/                     # GITIGNORED: friends' real hikes
    hikes/<slug>/{meta.json,track.gpx,track.fit,photos/,audio/,notes.md}
  docs/MODELS.md
```
Env vars (`.env`, never committed): `GEMINI_API_KEY`, `MONGODB_URI`, `MONGODB_DB=hikingbuddy`, optional `VOYAGE_API_KEY`, and `VITE_API_URL` plus `VITE_USE_MOCKS` for the frontend.

## Service interfaces (the contract)
Pydantic models go in `app/models.py`. Times are UTC unless a name says local.
- **tracks.py**
  - `parse_track(data: bytes, filename: str) -> list[TrackPoint]`. Handles `.gpx`, `.fit` and `.fit.gz`. `TrackPoint(time, lat, lon, ele|None, hr|None)`.
  - `compute_stats(points) -> TrackStats`. Fields: `distance_km, duration_s, moving_s, ascent_m, descent_m, avg_hr, max_hr, start_time, end_time`. Smooth elevation before computing ascent.
  - `to_geojson_line(points, max_points=500) -> dict`.
  - `locate_at(points, when) -> (lat, lon) | None`. Interpolates; returns None if more than 10 min outside the track.
- **exif.py**
  - `read_photo_meta(data) -> PhotoMeta(taken_at_local|None, lat|None, lon|None)`.
  - `strip_exif(data) -> bytes`.
- **gbif.py**
  - `match_species(name) -> GbifMatch|None`. Fields: `usage_key, scientific_name, rank, match_type, confidence`.
  - `nearby_count(taxon_key, lat, lon, month, radius_km=10, month_window=1) -> int`.
- **verify.py**
  - `verify_sighting(candidates, lat, lon, when, birdnet=None) -> Verification`. Fields: `status ∈ {confirmed, plausible, unsure}, chosen, gbif_nearby_count, birdnet_agrees, reasons[]`.
  - Default rules, with thresholds in `config.py`:
    - **confirmed:** top candidate confidence ≥ 0.7 AND (gbif_nearby ≥ 5 OR BirdNET agrees with confidence ≥ 0.5).
    - **plausible:** confidence ≥ 0.4 AND gbif_nearby ≥ 1.
    - **unsure:** anything else.
  - `reasons` must say why, in plain English. The UI shows them.
- **weather.py**
  - `get_day_forecast(lat, lon, day) -> DayForecast`. Fields: `sunrise, sunset, hourly[{time, temp_c, precip_mm, precip_prob, wind_kmh, gust_kmh, code}], in_forecast_range, source_url, fetched_at`.
  - Source is Open-Meteo. If the date is out of forecast range, set `in_forecast_range=False` and leave `hourly` empty.
- **planning.py**
  - `naismith_minutes(distance_km, ascent_m, pace_factor=1.0) -> int`.
  - `leave_by(sunset, duration_min, buffer_min=60) -> datetime`.
  - `run_checks(draft, forecast, stats) -> list[Check(name, passed, detail)]`. Checks:
    - finishes ≥ buffer before sunset
    - max gust < 50 km/h
    - max precipitation probability < 70%
    - min temperature > 0 °C, or kit includes cold-weather items
    - every hazard or closure claim has a source URL
  - `plan_hike(hike) -> Plan`: an Argon loop of draft → `run_checks` → revise, at most 2 revisions. Store every check result. **HUMAN REVIEW:** the prompts.
- **gemini.py**
  - `analyze_media(data, mime, ctx) -> MediaAnalysis`. Fields: `caption, tags[], is_organism, candidates[{common_name, scientific_name, confidence, group}], safety_note|None`. Uses `gemini-3.8-flash` with structured JSON output.
  - `draft_plan(...)`, `revise_plan(...)`, `recap(hike_bundle)`. Use `gemini-4-argon`.
  - **Get Gemini API usage from the `gemini-api-dev` skill and docs. Never guess the API.**
- **birdnet.py**
  - `detect(data, lat, lon, day) -> list[Detection(common_name, scientific_name, confidence, start_s, end_s)]`.
  - Returns `[]` with a logged warning if BirdNET is unavailable, so the app still works.
- **db.py**
  - `get_db()`, collections `hikes`, `media`, `sightings`, and a GridFS bucket `media_files`. Schemas are in the plan doc.

## API contract (FastAPI; `/docs` is the source of truth once it exists)
- `GET /health`: returns `{ok, mongo}`.
- `POST /hikes` and `GET /hikes`: create a hike `{title, trail_name, hiker, date, status}`, and list hike cards (cover photo, stats summary, species count).
- `GET /hikes/{id}`: the full hike with stats, plan, media and sightings.
- `POST /hikes/{id}/track`: multipart GPX/FIT upload. Returns stats and the route.
- `POST /hikes/{id}/media`: multipart photo/audio/note upload. Returns the media item plus a sighting with its verification.
- `GET /media/{id}/file`: streams from GridFS (EXIF stripped for photos).
- `POST /hikes/{id}/plan`: runs the planner and returns the plan with its checks.
- `GET /search?q=&hike_id=`: hybrid search across media captions and sightings.
- `POST /hikes/{id}/recap`: returns the recap markdown.

## Work packages
| WP | What | Executor | When | Depends on | Done when |
|---|---|---|---|---|---|
| WP0 | Scaffold: layout above, FastAPI `/health` with a Mongo ping, Vite+Tailwind shell calling `/health`, `.env.example`, `.gitignore`, pytest and `npm run build` both working, AGENTS.md committed | Edouard + Antigravity | Fri 17:00–17:45 | none | Both servers run and the frontend shows "API ok, Mongo ok" |
| WP1 | **Vertical slice:** POST hike → upload photo → GridFS → `analyze_media` → store media and sighting (verification stubbed as `unsure`) → shown in the hike folder | Edouard + Antigravity | Fri 17:45–21:00 | WP0 | A real photo shows a caption and 3 candidates in the UI |
| WP2 | `tracks.py` + `exif.py` + `POST /hikes/{id}/track` | **Devin** (overnight) | Fri 22:00 → Sat 08:00 | WP0 | pytest green on synthetic GPX, FIT and .gz fixtures generated in the tests; stats within 2% of hand-computed values |
| WP3 | `gbif.py` + `verify.py`, wired into the media pipeline | Antigravity agent 1 (overnight) | overnight | WP1 | pytest green with mocked HTTP; rule tables tested; one live smoke test is OK |
| WP4 | `weather.py` + planning functions (`naismith_minutes`, `leave_by`, `run_checks`) + tests; `plan_hike` loop with a stubbed LLM | Antigravity agent 1 (after WP3) | overnight | WP0 | pytest green; loop proven with fake drafts that fail and then pass |
| WP5 | `setup_indexes.py` (2dsphere, Atlas Search, Automated Embedding vector index on `media.caption`) + `/search` hybrid | Edouard | Sat AM | WP1, M10 cluster | "fox" returns the fox photo; a vague query like "orange animal" also finds it |
| WP6 | Frontend screens against mocks: gallery, hike folder (stats bar, map, media grid, sightings with status badges and reasons, plan tab with checks panel, kit checklist and leave-by), new hike, search | Teammate A (Fri: shell + gallery) → Antigravity agent 2 or Devin (overnight: remaining screens) | Fri → Sat AM | WP0 | `npm run build` green; every screen renders mock data on phone width |
| WP7 | BirdNET install + `birdnet.py` | Edouard | Fri night, **1-hour cap** | WP0 | A known clip returns the right species; otherwise ship the fallback |
| WP8 | Prompts for `analyze_media`, `draft_plan`, `revise_plan`, `recap` | Edouard + Teammate B testing in AI Studio | Fri eve → Sat | none | Teammate B's 5-photo test produces sensible output |
| WP9 | `import_hike.py`: loads `data/hikes/<slug>/` (meta, track, photos, audio, notes) and runs the pipelines | Antigravity | Sat AM | WP1–3 | One command loads all friend hikes |
| WP10 | `eval_accuracy.py`: runs the labelled set and outputs a CSV plus a score | Antigravity | Sat PM | WP3, labels | The pitch number exists |
| WP11 | Recap, map polish, badges, other Should items | anyone | Sat PM/eve | the demo path works | n/a |

**Teammate B (no code):**
- Organise the friend data into `data/hikes/<slug>/` locally.
- Label the accuracy set in a sheet (file, true species, source).
- Run 5 test photos through AI Studio for WP8.
- Draft the demo script and voiceover.
- Track consent in `friend-outreach.md`.

## AGENTS.md (commit at 17:00 as-is; under the 12k-character limit)
```
# Hiking Buddy: rules for coding agents
Project: hackathon app (Encode London, 23-25 Oct 2026). Deadline Sun 25 Oct 12:00 London. Tracks: Gemini 4 Argon, MongoDB Atlas, "The Real World".
Product: plan a UK hike (forecast, daylight, checks), then log the hike (GPX/FIT stats, photos/audio → species ID verified with GBIF/BirdNET), then search across hikes.

Stack: backend = Python 3.11, FastAPI, pymongo>=4.7, google-genai>=2.3.0 (Interactions API), gpxpy, fitdecode, httpx, pytest. frontend = Vite + React + TypeScript + Tailwind, react-router, react-leaflet, react-markdown.
DB: MongoDB Atlas, collections hikes/media/sightings, GridFS bucket media_files.

Gemini rules: use gemini-4-argon for planning/recap, gemini-3.8-flash for per-media analysis. Use thinking_level (low|medium|high), never thinking_budget. Do not set temperature/top_p/top_k or cached_content. Use background=True only for outputs over 65k tokens. Follow the gemini-api-dev skill; never invent API calls. Prefer structured JSON output with Pydantic schemas.

Working rules:
1. Only edit the files your task says you own. If you need a change elsewhere, write it in NOTES.md and stop.
2. Keep the service signatures in docs/build-spec (see task) unchanged unless the task says so.
3. Every function you add gets a pytest test. Run `pytest -q` (backend) / `npm run build` (frontend) after each change. Never report done with failing tests.
4. Mock all network calls in tests (httpx mocking / fixtures). No real API keys in tests.
5. Never commit secrets, .env, or anything in data/. Use synthetic fixtures only.
6. No new dependency without adding it to requirements/package.json and noting why in the PR.
7. Small commits with clear messages. Work on the branch named in your task. Open a PR at the end.
8. If blocked or unsure, stop, write what you tried and the open question in NOTES.md. Do not guess around a missing requirement.
9. PR description must list: what was done, what was not, how to test, any assumptions.
10. Code must be readable by beginners: short functions, docstrings, no clever tricks.
11. Responsibility: never present species ID as certain; always return confidence and reasons. Never say a plant/fungus is safe to eat. Strip EXIF GPS from any image served publicly.
```

## Overnight prompt template (fill in at ~21:30 once WP0/WP1 exist)
```
You are working on the Hiking Buddy repo. Read AGENTS.md first and follow it strictly.
Task: <WP id + title>
Branch: <wp2-tracks>   Files you own: <list>   Do not touch: everything else.
Goal: <one paragraph>
Interfaces to implement exactly: <paste signatures from the build spec>
Acceptance (all must pass):
- <tests/commands>
- <behavioural checks, e.g. stats within 2% on fixture X>
Fixtures: generate synthetic GPX/FIT in tests (e.g. a 5 km loop with 300 m ascent, 1 Hz, HR 90-150). Do not use real user data.
Process: write tests first, implement, run tests after every change, commit small. When done: open a PR with the required description. If blocked for more than 20 minutes on one issue: write NOTES.md and move to the next sub-task.
Out of scope: <list>
```
Before leaving each run going: confirm it has started, run the tests once, and pushed its first commit. Stop the laptop sleeping and keep it on power. Check Antigravity and Devin quotas so a run doesn't stall at 2am.

## Morning review protocol (Sat 08:00–09:00)
1. Read each PR description and NOTES.md.
2. Check out each branch and run the tests yourself (or have a Claude session review the diff against this spec).
3. Merge in this order: WP2 → WP3 → WP4 → WP6. Rebase and fix conflicts after each merge.
4. Run the vertical slice end to end on `main`.
5. Update `00-start-here.md` (status and log) and re-plan Saturday.
