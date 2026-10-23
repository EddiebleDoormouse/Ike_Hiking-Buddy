# Encode London Hackathon 2026: Context

Source: https://www.encodeclub.com/programmes/encode-london-2026 (read 22 Oct 2026). Condensed and restructured; the page is the authority if anything conflicts. Re-check it for edits (MongoDB prizes were still TBA).

## Our project
Hiking buddy app, built with Google Antigravity + Gemini 4 Argon (`gemini-4-argon`) and MongoDB Atlas. Team of friends, in person.

## Logistics
- **Dates:** Fri 23 – Sun 25 Oct 2026. In-person, 3 days.
- **Venue:** Encode Hub, 41 Pitfield St, Shoreditch, London N1 6DA. Desks first come first served, Wi-Fi, food and drink provided, shower on lower ground. No sleeping on site.
- **Fri 23:** doors 12:00; welcome 14:00; workshops 14:30 Google DeepMind, 15:00 Arc, 15:30 MongoDB, 16:00 Saint; 16:30 challenges and team formation; **hacking begins 17:00**.
- **Sat 24:** building day, mentors on hand.
- **Sun 25:** **submissions close 12:00 (London)**; judging after; awards and closing; event ends 16:30.
- **Team rules:** solo or team allowed. One project per team; that one project can enter several challenges/bounties if it meets each brief. Each bounty is judged separately by that partner's judges; open challenges are judged by an external panel.
- **Platform:** registration is approved by Encode. Create the project on the hackathon page, share the team code with teammates. Connect Discord for announcements, mentor help and the private channels.
- **Every submission needs:** project description, an explanation of how it meets each challenge entered, repo link, demo video. Extra per-challenge requirements below.
- **Hard rule:** anything built before kickoff is out. Open-source libraries and templates are fine, but the demo must show only code written during the hackathon.

## Challenges and bounties (5)

### 1. Google DeepMind: Build with Gemini 4 Argon ($15k credits) — core target
- **Prizes:** 1st $7,000, 2nd $5,000, 3rd $3,000, all in Gemini API/Google Cloud credits.
- **Brief:** a working app or autonomous agent that solves a specific problem for a real person we can name, and could only be built with Argon (1M-token unified context, long decode, frontier reasoning, multimodal, multi-agent orchestration).
- **Pathways (any domain allowed):** (1) autonomous agents that ship: plan, use tools, verify against a concrete pass/fail signal (tests, compiler, logs, headless browser). (2) real world, hard tech and multimodal creation: voice, video, 3D/WebGPU, physical systems, scientific data.
- **Judging:** live working demo 50% (runs live on real inputs in under 3 min; effective use of Argon/Managed Agents/companion models with a real verification loop); problem and usefulness 25%; originality / needs Argon 15% (also: people stay in control of actions affecting external systems, money, private data); pitch clarity 10%. Format: 3-minute live demo + 2 min Q&A, **no slides**.
- **Avoid:** basic chat wrapper or Q&A bot over one PDF; static page with no autonomous reasoning/verification/multimodal flow; unverified medical, mental health or financial advice bots without human-in-the-loop.
- **Toolkit:** `gemini-4-argon` (lead model), `antigravity-preview-09-2026` (managed agent / Linux sandbox), `gemini-3.8-flash` and `gemini-3.5-flash-lite` (parallel subagents), `deep-research-preview-04-2026`, `gemini-3.8-live` family (voice/vision), `gemini-nano-banana-2.1` (images), `gemini-omni-1.1-flash` (video), `lyria-3.5` (music), `gemma-4-31b-it` (open model).
- **SDK/API:** Gemini SDK >= 2.3.0 (`pip install -U "google-genai>=2.3.0"` or `npm i @google/genai@latest`). Recommended endpoint: Interactions API (`client.interactions.create`).
- **Argon API rules:** use `thinking_level` ("low", "medium" default, "high"), not `thinking_budget`; drop `temperature`, `top_p`, `top_k` and explicit `cached_content`; set `background=True` to generate past 65,536 tokens (up to 1M).
- **Setup:** collect pre-provisioned credits from the DeepMind team at kickoff. Give the coding agent the skills: `npx skills add google-gemini/gemini-skills --skill gemini-api-dev` (and `gemini-live-api-dev`), or `agy plugin install https://github.com/google-gemini/gemini-skills` in Antigravity.
- **Mentors on site:** Amit Vadi, Geneviève Huskens (DeepMind booth). Feedback: gemini-developer-feedback@google.com.
- **Submission:** GitHub repo; 3-min demo video plus live demo; state which Gemini models/agents were used and how.

### 2. MongoDB: Build Anything, Change Everything with MongoDB Atlas — core target
- **Brief:** a real-world app that relies on MongoDB Atlas as its core backend data store.
- **Scoring:** must use at least one Atlas feature; more features = more points. Features: Atlas Search (text), Atlas Vector Search, Hybrid Search, Automated Embedding, Atlas Stream Processing, Voyage AI models.
- **Languages:** C, C++, C#, Go, Java, Kotlin, Node.js, PHP, Python, Ruby, Rust, Scala. Any AI tools allowed.
- **Prizes:** TBA.
- **Perk:** $100 Atlas credit per participant from the MongoDB booth (ground floor). Sign up and prepare a cluster beforehand.
- **Mentors:** Robin Varghese (Solutions Architect), Maja Brlek.
- **Submission:** GitHub repo; 3-min demo video showing the app working and MongoDB in use.

### 3. Saint: Best Use of Saint AI Agent (optional)
- Saint is a personal AI assistant that works in email, calendar, docs, browser and terminal (saint.work, built by Encode CEO Anthony Beaumont).
- **Brief:** put Saint to work on something real (give it a job, build a tool/integration for it, or deploy it for someone). Judged on working proof, real work with sensible recovery, human control, and "would still run on Monday".
- **Prize:** £200 cash (single prize), a Saint each for the winning team, 3 months free, set-up call.
- **Submission:** 2–4 min demo of Saint completing the task end to end, plus a short note on what it was asked and which tools/accounts it used.

### 4. Open challenge: The Real World — AI that understands the world around us — strong fit
- **Brief:** software that makes sense of the physical world using photos, audio, maps and open data (vision/audio/language models plus public datasets). Ideas listed include a **trip or hike conditions planner** (forecasts, daylight, terrain, trail reports, transport times: whether, when and how to go), wildlife/plant ID, accessibility guides, noise/air-quality maps, flood/heat risk.
- **Suggested data:** OpenStreetMap, TfL Unified API, London Datastore, Met Office, Open-Meteo, Breathe London / LAQN, Environment Agency flood API, iNaturalist, GBIF. Any other public data or phone sensors is fine.
- **Judging:** real-world usefulness; how well it reads the world (messy inputs, gaps); technical execution (working end-to-end demo with AI models plus real data); responsibility (privacy, honesty about uncertainty).
- **Submission:** working demo (web/mobile/hardware); repo with README and setup; 2–4 min demo video on real inputs; short note on models and data sources.

### 5. Open challenge: Agents That Ship — possible fit
- **Brief:** an AI agent that does a real job end to end, with real tools, error recovery and human approval of risky steps. Judged on completing the job, reliability, usefulness, technical depth (tools, memory, planning, evaluation), safety/control.
- **Submission:** working demo (live or recorded); repo with README; 2–4 min video; short description of tools, steps and where a human approves.

## Fit of the hiking buddy idea (first pass, to refine with the team)
- **Best matches:** Google DeepMind (Pathway 2, plus a verification loop), MongoDB, The Real World (explicitly lists a hike conditions planner). All three can take one project.
- **Watch-outs:**
  - Not a plain chat wrapper: needs autonomous reasoning, multimodal input and a verifiable check.
  - Must justify why it needs Argon specifically (long context, multimodal, orchestration).
  - Real named user and live demo on real inputs; 3 minutes, no slides.
  - Nothing coded before 23 Oct kickoff; log what is written when.
  - Real World also grades honesty about uncertainty and privacy (e.g. locations).
  - Any safety-relevant hiking advice should keep a human in the loop and flag uncertainty.
- **Open questions:** which MongoDB Atlas features (Vector/Hybrid Search, Voyage embeddings) are central; which data sources; team roles; demo script.

## Key deadlines checklist
- Before Fri: Atlas account and cluster ready; Discord connected; team created on the platform; Antigravity and Gemini SDK set up (code nothing yet).
- Fri 14:30–16:30: attend DeepMind and MongoDB workshops, claim credits and Atlas voucher; team formation done.
- Fri 17:00: start coding.
- Sun 12:00: submit (description, per-challenge explanation, repo, demo video). Then live demos and judging.
