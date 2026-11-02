# Hiking Buddy: rules for coding agents
Project: hackathon app (Encode London, 23-25 Oct 2026). Deadline Sun 25 Oct 12:00 London. Tracks: Gemini 4 Argon, MongoDB Atlas, "The Real World".
Product: plan a UK hike (forecast, daylight, checks), then log the hike (GPX/FIT stats, photos/audio → species ID verified with GBIF/BirdNET), then search across hikes.

Stack: backend = Python 3.11, FastAPI, pymongo>=4.7, google-genai>=2.3.0 (Interactions API), gpxpy, fitdecode, httpx, pytest. frontend = Vite + React + TypeScript + Tailwind, react-router, react-leaflet, react-markdown.
DB: MongoDB Atlas, collections hikes/media/sightings, GridFS bucket media_files.

Gemini rules: use gemini-4-argon for planning/recap, gemini-3.8-flash for per-media analysis. Use thinking_level (low|medium|high), never thinking_budget. Do not set temperature/top_p/top_k or cached_content. Use background=True only for outputs over 65k tokens. Follow the gemini-api-dev skill; never invent API calls. Prefer structured JSON output with Pydantic schemas.
Gemini code: read skills/gemini-api-dev/SKILL.md in https://github.com/google-gemini/gemini-skills and the official docs; gemini-4-argon is newer than most models' training data, so follow the docs, not memory.

Working rules:
1. Only edit the files your task says you own. If you need a change elsewhere, write it in NOTES.md and stop.
2. Keep the service signatures in docs/build-spec (see task) unchanged unless the task says so.
3. Every function you add gets a pytest test. Run `pytest -q` (backend) / `npm run build` (frontend) after each change. Never report done with failing tests.
4. Mock all network calls in tests (httpx mocking / fixtures). No real API keys in tests.
5. Never commit secrets, .env, or anything in HB_DATA_DIR (outside the repo). Use synthetic fixtures only.
6. No new dependency without adding it to requirements/package.json and noting why in the PR.
7. Small commits with clear messages. Work on the branch named in your task. Open a PR at the end.
8. If blocked or unsure, stop, write what you tried and the open question in NOTES.md. Do not guess around a missing requirement.
9. PR description must list: what was done, what was not, how to test, any assumptions.
10. Code must be readable by beginners: short functions, docstrings, no clever tricks.
11. Responsibility: never present species ID as certain; always return confidence and reasons. Never say a plant/fungus is safe to eat. Strip EXIF GPS from any image served publicly.

Spec rules (hackathon scoring):
12. Before designing anything user-facing, read docs/hackathon-spec.md. Task details are in docs/build-spec.md (section for your WP).
13. Every demo-path feature needs a check an agent can run: a pytest, a script, or the /browser agent at 390px width. No check, not done.
14. All Gemini calls go through backend/app/services/gemini.py. When you add or change one, update docs/MODELS.md (function, model, thinking_level, why).
15. UI honesty: every AI-generated claim shows its confidence/status and its source. Plans are labelled "suggested; check conditions before you go". Never hide a failed check.
16. If a Gemini or Atlas call fails, read the skill/docs. Never silently swap in an older model or invent parameters. Write the failure in NOTES.md.
17. Never read or open anything outside the workspace. Real friend data is not in the repo; use synthetic fixtures.
