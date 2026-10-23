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
