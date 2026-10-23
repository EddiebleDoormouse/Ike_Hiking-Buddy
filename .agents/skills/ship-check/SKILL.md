---
name: ship-check
description: Pre-merge verification for the Hiking Buddy repo. Runs the backend tests, the frontend build and a secrets/data scan, then reports pass or fail per step. Run only when the user types /ship-check or asks for the pre-merge checks.
---

# /ship-check

Run these checks from the repo root, in order. Do not fix anything; report only.

1. **Backend tests.** If `backend/` exists: `cd backend && pytest -q`. If it does not exist yet, report "backend: not created yet" (not a failure).
2. **Frontend build.** If `frontend/` exists: `cd frontend && npm run build`. If it does not exist yet, report "frontend: not created yet".
3. **Secrets and data scan.**
   - `git ls-files` must show no `.env` file (`.env.example` is fine) and nothing under `data/`.
   - Search the changes on this branch (`git diff origin/main...HEAD`, plus any uncommitted changes) for `AIza`, `mongodb+srv`, `GEMINI_API_KEY=` followed by a value, and `MONGODB_URI=` followed by a value. Ignore matches inside `docs/` and `.agents/`, which only describe these names.
   - Report any file under the repo that looks like friends' data: `.gpx`, `.fit`, `.fit.gz`, or photos and audio outside `backend/tests/fixtures/`.
4. **Report** one line per step: PASS, FAIL (with the first error and the file) or NOT CREATED YET. Finish with an overall verdict. Never say "done" or "ready to merge" if any step failed.

The repo is public, so a failure in step 3 is serious: say so first and tell the user not to push.
