# Hiking Buddy: Project Plan (v1, 22 Oct 2026)

The working plan for the team. Hackathon rules and challenge briefs are in `docs/encode-london-2026-context.md`. Update this doc when a decision changes.

## Decisions so far
- **Tracks:** Google DeepMind Gemini 4 Argon, MongoDB Atlas, and The Real World (open challenge). Not entering Saint or Agents That Ship.
- **Region:** UK. The demo trail is one that a friend has already hiked; pick it once their data arrives.
- **Stack:** Python **FastAPI** backend; **React + Vite + Tailwind** frontend, a mobile-friendly web app with no native app; **MongoDB Atlas** (free M0 now, upgraded to **M10** on Friday with the $100 credit, because Automated Embedding needs M10+); Gemini through `google-genai>=2.3.0` and the Interactions API. Coding agents in Antigravity write most of the code.
- **No project code before kickoff** (Fri 23 Oct; hacking starts 17:00). Start a fresh repo at kickoff. Tutorials before then are throwaway.
- **Data:** friends' past UK hikes: Strava exports, original photos, audio and notes, used with their consent. Collecting data before kickoff is allowed; only code is restricted.
- **Named user:** Edouard, a less experienced hiker planning a UK trail, plus an experienced friend ([friend], TBC) whose past hike on that trail feeds the plan. Interview her for a quote about her real pain points (questions below).

## Team roles
- **Edouard:** owns the architecture, backend, Gemini and MongoDB integration, and the repo.
- **Teammate A (some coding):** frontend pages, built with the coding agent against the FastAPI `/docs` contract.
- **Teammate B (beginner):** friend data collection and consent tracking, the accuracy test set and its scoring, prompt testing, demo script, demo video, README and submission text, pitch rehearsal.
- Git: one branch per person, separate folders (`backend/` and `frontend/`), merge through PRs. Teach the basics on Friday night.

## Demo script (3 min, live, no slides)
1. **0:00–0:20 Who and why.** "I want to hike [trail] next Saturday. [friend] did it in [month]. Planning takes ten tabs, and afterwards the photos rot in a camera roll."
2. **0:20–1:10 Plan.** Enter the trail and date. Show the live forecast, sunrise/sunset, a duration estimate (Naismith's rule, adjusted to past pace), a "leave by HH:MM" turnaround time, the kit checklist, hazards and closures with sources, and "what you might see here" from past sightings and GBIF. Then show the **verification panel**: which checks passed or failed, and what Argon revised.
3. **1:10–2:10 Hike folder.** Open [friend]'s past hike: stats, map, photos placed on the track. **Upload live** a photo (an object brought on stage, or one of her photos): species candidates, then the GBIF check, then a Confirmed / Plausible / Unsure label, then the sighting appears on the map. Play a bird recording: Gemini and BirdNET agree or disagree.
4. **2:10–2:45 Search and recap.** Hybrid search across every hike ("fox sightings", "misty ridge photos"), then the AI recap of the hike.
5. **2:45–3:00 Proof.** The accuracy number from the test set (e.g. "17/20 correct, all misses flagged unsure"), and what comes next.

## Scope
**Must (needed for the demo)**
- M1: Create a hike from a trail name or GPX route, plus a date. Status is `planned` or `completed`.
- M2: **Prep report with a verification loop.** Argon drafts the report. Then automatic checks run: forecast thresholds (wind, rain, temperature), finish ≥1h before sunset (Naismith's rule), and every hazard or closure claim has a cited source. Any failure goes back to Argon for revision. The report includes an interactive kit checklist and a "leave by" time.
- M3: **Media pipeline.** Upload photos, audio and notes. `gemini-3.8-flash` writes a caption and the top-3 species candidates, with multiple items processed in parallel. GBIF checks for records nearby in that season. Audio is cross-checked with BirdNET. The result is a status label.
- M4: Sightings log and a gallery for each hike folder.
- M5: **Hybrid search** across hikes, combining Automated Embedding on captions with Atlas Search.
- M6: Import GPX/FIT files and compute stats: distance, time, ascent, and heart rate if the file has it.
- M7: **Accuracy test set:** about 20 labelled photos and recordings, scored in a sheet. The resulting number goes in the pitch.

**Should**
- S1: Map (Leaflet + OSM) showing the track and sightings.
- S2: Place photos on the track by matching the photo's EXIF timestamp to GPX time, for photos with no GPS.
- S3: "What you might see" in the plan: past sightings near the route (geo query) plus GBIF seasonal records.
- S4: Duration estimate adjusted to the hiker's past pace.
- S5: Post-hike recap from Argon over the whole folder in one call (the 1M context).
- S6: Simple badges (species count, ascent milestones).

**Could:** voice-note transcription; a recap postcard (`gemini-nano-banana-2.1`) or soundtrack (`lyria-3.5`); a CSV export of sightings for conservation groups; image-to-image search with `voyage-multimodal-3.5`; dates beyond the 16-day forecast fall back to climate data, clearly flagged.

**Won't:** live smartwatch sync, a native mobile app, offline mode, real authentication (use a simple hiker picker), permit coverage for every region, social features.

## Architecture
```
React web app (phone/laptop)
   │ REST (FastAPI /docs is the contract)
FastAPI backend (Python)
 ├─ planner/   Open-Meteo forecast + sunrise/sunset + elevation; route from GPX (OSM optional)
 │             grounded search / deep-research-preview-04-2026 for closures (cited, background)
 │             gemini-4-argon draft → checks → revise loop
 ├─ media/     gemini-3.8-flash caption + candidates (parallel) → GBIF match + occurrence check
 │             audio → BirdNET (birdnetlib) cross-check → status
 ├─ tracks/    GPX (gpxpy) / FIT (fitdecode) → stats; EXIF time → position on track
 ├─ recap/     gemini-4-argon over full hike folder
 └─ db/        MongoDB Atlas (pymongo ≥4.7), GridFS for media files
```

**Models:** `gemini-4-argon` for planning, revision, recap and orchestration; `gemini-3.8-flash` for per-item media analysis; `deep-research-preview-04-2026` or grounded search for closures and hazards. Argon API rules: use `thinking_level`, not `thinking_budget`; no `temperature`, `top_p` or `top_k`; set `background=True` to generate past 65k tokens. Use a lower `thinking_level` on demo-critical paths if they turn out slow.

**External data:** Open-Meteo (forecast, daily sunrise/sunset, elevation); GBIF (species match and occurrence search by lat/lon and month); BirdNET via `birdnetlib`, which needs TFLite, librosa and ffmpeg (it takes `lat`, `lon` and `date`, and returns `common_name`, `scientific_name`, `confidence`); grounded web search for closures from sources such as National Trails, National Trust, Natural England and land managers.

**Python libraries:** fastapi, uvicorn, pymongo, google-genai, httpx, gpxpy, fitdecode, Pillow/exifread, birdnetlib. **Frontend libraries:** react, vite, tailwind, react-leaflet.

**Endpoints (first draft)**
- `POST /hikes`, `GET /hikes`, `GET /hikes/{id}`
- `POST /hikes/{id}/plan`: runs the planner loop
- `POST /hikes/{id}/track`: GPX/FIT upload
- `POST /hikes/{id}/media`: upload, which triggers the ID pipeline
- `GET /search?q=`: hybrid search
- `POST /hikes/{id}/recap`

## Data model (MongoDB)
- **hikes:** `title, trail_name, hiker, status, date, route (GeoJSON LineString), start (Point), stats{distance_km, duration_s, moving_s, ascent_m, avg_hr, max_hr}, plan{report_md, checks[{name, passed, detail}], sources[{title, url, checked_at}], kit[{item, done}], leave_by}, recap_md, badges[]`
- **media:** `hike_id, kind (photo|audio|video|note), file_id (GridFS), taken_at, location (Point), caption, tags[], text`
- **sightings:** `hike_id, media_id, common_name, scientific_name, gbif_key, candidates[{name, confidence}], verification{gbif_nearby_count, birdnet{name, confidence}, status}, location (Point), seen_at`
- **Indexes:** 2dsphere on `location` and `route`. Automated Embedding vector index on `media.caption` (model `voyage-3.5`, filters `hike_id` and `kind`). Atlas Search index on captions, tags and species names. Hybrid query through `$rankFusion` (confirm at the MongoDB workshop).
- Automated Embedding is text-only and in preview, which is why captions are what get embedded. Fallback: embed with the Voyage API and use a normal vector index.

## Friend data checklist (Teammate B tracks this)
For each hike: the Strava **Export Original** (FIT, which has heart rate) and **Export GPX**. Both are on the strava.com website: open the activity, then the ⋯ menu. The phone app can't export. Also collect:
- **Original** photos, not sent through WhatsApp, which strips location and time. AirDrop, a Drive or iCloud link, or WhatsApp "Document" mode all work.
- Any bird or ambient audio and videos.
- A few notes: what they saw, what went wrong, how long it took.
- Consent for demo use.

Aim for 5–8 hikes from 3–4 friends, including the demo trail.

**Privacy:** keep raw friend data out of the public repo (put `data/` in `.gitignore`), blur faces in demo media, don't publish routes that start from someone's home, and strip EXIF from anything shared.

## Named-user interview ([friend])
Ask about her real process and pains, not "would you use this?" (everyone says yes).
1. How do you plan a hike now? Which apps or sites, and how long does it take?
2. When did a hike last catch you out (weather, dark, a closure, taking longer than expected)?
3. What happens to your photos and notes afterwards? Do you ever go back to them?
4. Do you try to identify plants or birds on the way? How?
5. What would you not trust an app to tell you?

Capture one quotable line for the pitch.

## Timeline
- **Before kickoff (no code):**
  - Accounts: Atlas M0, Google AI Studio, Antigravity, GitHub, Discord, Encode platform team.
  - Collect friend data and interview [friend].
  - Label the accuracy set.
  - Sketch UI screens.
  - Read the Gemini and MongoDB docs.
- **Fri 14:30–16:30:** DeepMind and MongoDB workshops; claim Gemini credits and the Atlas credit; upgrade to M10.
- **Fri 17:00–24:00:**
  - Create the repo and the FastAPI + React skeleton; connect to MongoDB.
  - **First vertical slice:** photo upload → flash ID → stored → shown.
  - Test the BirdNET install (drop it if not working within an hour).
  - Measure Argon latency.
- **Sat AM:** planner and checks loop; GPX/FIT stats; GBIF verification.
- **Sat PM:** gallery; search indexes and hybrid query; map.
- **Sat evening:** make it reachable from a phone (deploy or tunnel); Should items; run the accuracy evaluation; latency fixes.
- **Sun 08:00–09:00:** bug fixes. **09:00 feature freeze.**
- **Sun 09:00–11:00:** record the 3-minute video (show MongoDB explicitly); write the README and the explanations for each track, including the models used.
- **Sun by 11:45:** submit (closes 12:00). Then rehearse the live demo.

## Risks and fallbacks
- **BirdNET install fails:** verify with GBIF only, and have Gemini analyse the audio.
- **Automated Embedding problems:** embed manually with the Voyage API and use a standard vector index.
- **Argon too slow for a live demo:** lower `thinking_level`, run in the background with progress, or pre-run the plan and do only the photo ID live.
- **Photos missing EXIF:** ask for originals; fall back to manual placement on the map.
- **Too little data:** add a second hike from Edouard's own Strava, or a short London park walk.

## Submission checklist
- Encode platform: description, how the project meets each track, repo link, demo video.
- Gemini: GitHub repo, 3-minute video plus live demo, which models and agents were used and how.
- MongoDB: repo, 3-minute video showing MongoDB in use.
- Real World: working demo; repo with README and setup steps; a 2–4 minute video on real inputs; a note on models and data sources.
