---
name: spec-check
description: Read-only audit of the Hiking Buddy repo against the hackathon scoring rubric in docs/hackathon-spec.md, ending with the five cheapest fixes for the 3-minute demo. Run only when the user types /spec-check or asks for a rubric audit.
---

# /spec-check

Audit only. Do not change any code or docs.

1. Read `docs/hackathon-spec.md` (the rubric) and the scope and demo script in `docs/hiking-buddy-plan.md`.
2. For every criterion in the rubric (Gemini 4 Argon, MongoDB Atlas, The Real World), find evidence in the repo: file, function, endpoint or UI component. Mark each **Met**, **Partial** or **Missing**, with the evidence or the gap in one line.
3. Pay special attention to:
   - a real verification loop that a judge can see in the UI (plan checks pass/fail, sighting status with reasons);
   - which Atlas features are actually used (Automated Embedding, Vector Search, Atlas Search, hybrid, geo) and whether a video could show them;
   - honesty about uncertainty and privacy (confidence and status shown, EXIF GPS stripped from public images);
   - `docs/MODELS.md` exists and lists every Gemini call;
   - README has setup steps, and a note on models and data sources.
4. List the **5 cheapest fixes**, ranked by impact on the 3-minute demo, each with a rough effort (minutes) and the file it touches.
5. Keep the whole report under one page.
