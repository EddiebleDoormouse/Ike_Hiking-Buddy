# START HERE: Hiking Buddy @ Encode London 2026

Read this first in every new session. It says where things stand, who is on the team, where the repo is, and how to work with us. Last updated: Fri 23 Oct 2026, 19:55 (London).

## Doc index
| Doc | What it holds | Update when |
|---|---|---|
| `docs/00-start-here.md` | Status, repo, team, vision, conventions, open items, log | Any status change; add a log line every session |
| `docs/hiking-buddy-plan.md` | The plan: decisions, scope (Must/Should/Could/Won't), architecture, data model, demo script, timeline, risks, submission checklist | A decision or scope change |
| `docs/build-spec.md` | **How we build:** repo layout, service interfaces, API contract, work packages (WP0–WP11) with executors and acceptance tests, AGENTS.md content, overnight prompt template, morning review protocol | Work packages change or get done |
| `docs/antigravity-setup.md` | **Antigravity setup:** credit/quota pools, per-laptop checklist, permission lists, AGENTS.md additions, `docs/hackathon-spec.md` rubric digest, MongoDB MCP config, the three check skills, treg verdict | Antigravity settings or rules change |
| `docs/encode-london-2026-context.md` | Hackathon rules, schedule, all 5 challenge briefs, Gemini 4 Argon toolkit and API rules | Encode changes the page (e.g. MongoDB prizes announced) |
| `docs/research-notes.md` | Verified technical facts (MongoDB Automated Embedding, Voyage, BirdNET, Strava exports…) with sources, plus what is still unverified | New research findings |
| `claude/friend-outreach.md` | Message templates for hiking friends, the follow-up, and the data and consent tracker. **Private: Project only, never mirrored to the repo.** | Data arrives or someone replies |

## Repo (GitHub)
- **URL:** https://github.com/EddiebleDoormouse/Ike_Hiking-Buddy (**public**; owner Edouard's account `EddiebleDoormouse`; default branch `main`).
- **State at Fri 19:55:** `README.md`, `docs/` (mirror of the planning docs), `CLAUDE.md`, `.agents/skills/` (three check skills). **No app code pushed yet.** The WP0 scaffold and `AGENTS.md` are still to come from Edouard's local work; don't create them from a Claude session (it would clash with his push).
- **Attaching it in a Claude session:** call `add_repo` (owner `EddiebleDoormouse`, repo `Ike_Hiking-Buddy`, access `push`), then ONE shallow clone into `/home/claude/ike_hiking-buddy` with a long timeout (≈10 min), then `register_repo_root`. If that folder already exists, check `git -C /home/claude/ike_hiking-buddy rev-parse HEAD` before touching it. Use `list_repos` with query `hiking` if the name is in doubt.
- **Source of truth:** planning docs are edited **in this Project** (`claude/…`). The repo's `docs/` is a **read-only mirror** for the coding agents (Antigravity, Devin). After changing a Project doc, re-sync it:
  1. Copy the file to `docs/<same name>`.
  2. Rewrite the doc paths (`claude/<file>.md` becomes `docs/<file>.md`), and replace the experienced friend's first name with `[friend]` until she has agreed to be named.
  3. Skip `friend-outreach.md`.
  4. Commit `docs: sync from Claude Project` and push straight to `main`. Docs-only syncs are the only direct pushes to `main`.
- **Everything else goes through branches and PRs:** one branch per task (`wp2-tracks`), small commits, PR into `main`, never force-push `main`. Agents follow `AGENTS.md` (once it exists) and `CLAUDE.md`.
- **Public repo, so never commit:** `.env`, API keys, connection strings, friends' GPX/FIT/photos/audio/notes, or anyone's raw data. Friends' real data stays outside the repo (see Privacy below).
- **Hackathon rule:** the demo must show only code written after Fri 23 Oct 17:00. Docs, workflows and README are fine; don't paste in code from before kickoff.

## Key dates (London time)
- **Fri 23 Oct:** doors open 12:00; kickoff 14:00; workshops 14:30 (DeepMind), 15:30 (MongoDB); **hacking began 17:00**.
- **Sat 24 Oct:** full building day. Demo rehearsal #1 at 18:00.
- **Sun 25 Oct:** feature freeze 09:00 (our own deadline); dress rehearsal 10:30; **submissions close 12:00**; then live demos and judging.
- Venue: Encode Hub, 41 Pitfield St, Shoreditch. No sleeping on site.

## Current status
- **Phase:** hacking underway (since Fri 17:00). Whether the WP0 scaffold exists locally is not recorded here; ask Edouard.
- Plan v1 agreed (22 Oct). Build spec v1 written (23 Oct 16:15).
- Friend data: GPX requested from friends. Follow-up asking for Export Original (FIT), photos, audio and notes is pending. Tracked in `friend-outreach.md` (Project only).
- Antigravity: installed on Edouard's laptop; MongoDB agent skills and the treg CLI installed; free quota; Edouard expects hackathon-provided credits (whether they cover Antigravity quota is unconfirmed: ask the DeepMind booth). Setup is in `antigravity-setup.md`. **Antigravity workflows were retired (19 Oct per the official docs); our `/ship-check`, `/spec-check`, `/demo-check` are now skills in `.agents/skills/`.**
- Agents: we plan to run overnight streams (max 3): Antigravity agents for WP3/WP4 (and maybe WP6), and **Devin** (Edouard has some Devin credit left from a previous hackathon) for WP2. See the build spec.
- MongoDB Atlas setup: separate session; status not recorded.

## Team
- **Edouard** (Imperial College London student): team lead, owns architecture, backend, integration and the morning PR review. Python is the only language he is properly comfortable with. Uses Apple Watch + Strava. Couldn't do a hike before the event (uni and labs).
- **Teammate A:** friend with minimal coding background. Does frontend (WP6) with the coding agent's help.
- **Teammate B:** friend who is a complete beginner. Does data organisation, accuracy labels, prompt testing in AI Studio, the demo script and video, README and submission text, and the pitch. Writes no code.
- Teammates' names: not recorded yet. Add them here.
- **Named user:** Edouard (a less experienced hiker planning a trail), plus an experienced hiking friend, **[friend]** (to be confirmed: she still needs to be asked about the interview and use of her name).
- Both teammates are eager to learn. Explanations for them should be simple and step by step.

## Product vision (the original idea, in full)
"Hiking buddy": one app covering a hike from planning to post-hike documentation. The unique angle is automated planning from real environmental data combined with multimodal flora and fauna tracking.
- **Planning:** the user names a trail. The AI pulls weather, hazards, permits and closures, and suggests the best dates, safety precautions, kit and duration. Output is a concise "prep report" (markdown) for each hike.
- **During the hike:**
  - Stats: distance, time, elevation, plus heart rate and calories, imported from GPX/FIT files (not live watch sync).
  - Comparisons across hikes, and light gamification.
  - Flora and fauna identification from photos and audio (e.g. birdsong), logged as sightings.
- **After the hike:**
  - Each hike is a folder in a Notion-style gallery holding photos, videos, audio, notes and sightings.
  - The AI tags and organises everything so it's searchable (e.g. "show all fox sightings").
- **Optional:** opt-in sharing of observations with conservation groups (a CSV export, under Could).
- The scoped version is in the plan doc. Live watch sync, a native app and offline mode were cut.

## Why these tracks
- **The Real World** (primary interest): software that understands the physical world through photos, audio, maps and data. It lists "trip or hike conditions planner" and "wildlife ID" as example ideas.
- **Google DeepMind Gemini 4 Argon:** the multimodal ID, planning and long-context recap all run on Gemini. The verification loops are our answer to the judges' "real verification loop" requirement.
- **MongoDB Atlas:** a flexible schema for mixed media, and many Atlas features to score points (Vector Search with Automated Embedding, Atlas Search, Hybrid, geo).
- **Not Saint:** its demo requires a specific interaction with a Saint that doesn't fit the concept.
- **Not Agents That Ship:** a narrow agent built quickly would be less polished, and would lose to the many existing, heavily engineered agents. The team had no unique twist, and conventional app development suits us better.

## How Claude should work with us
- **Style:** concise and clear, no fluff, but complete. Feel free to read and explore without asking.
- **Coding** is done mostly by coding agents: Gemini in **Antigravity**, plus Devin for isolated tickets. Claude's role: planning, architecture, prompts for the coding agents, PR review against `build-spec.md`, debugging, explaining things to the beginners, test design, and the pitch, video and submission text. When Claude writes code, use Python for the backend.
- **Respect the rules:** the demo shows only code written after 17:00 Fri; one project per team.
- **Use the latest Gemini API conventions** (in the context doc and AGENTS.md): Interactions API; `thinking_level`, not `thinking_budget`; no `temperature`, `top_p` or `top_k`; `background=True` for long outputs.
- **Privacy:** never put friends' raw GPX files, photos or personal data in the public repo, and never give them to Devin or other cloud agents. Keep them outside the repo folder (e.g. `~/hb-data`, read via `HB_DATA_DIR`) so Antigravity agents don't read them either (see `antigravity-setup.md` §2). Blur faces. Don't publish routes that start from someone's home. Don't name friends in the public repo until they agree.
- **Keep the docs current:** decisions go in the plan doc, work-package status in the build spec, findings in research notes, and status changes plus a log line go here. Then re-sync the repo mirror (see Repo above).
- **Time awareness:** always weigh suggestions against the Sun 12:00 deadline and the Must/Should/Could tiers. Push back on scope creep and on running more agent streams than Edouard can review.

## Open items
- [x] GitHub repo created (`EddiebleDoormouse/Ike_Hiking-Buddy`); docs, `CLAUDE.md` and the check skills pushed 23 Oct evening.
- [ ] Each laptop: pull the repo so `.agents/skills/` and `docs/` arrive; type `/ship-check` in Antigravity to confirm the skills are picked up. If a skill doesn't appear, restart Antigravity and check it opened the repo root as the workspace.
- [ ] All three laptops: Antigravity updated, own Google account, `gemini-api-dev` skill installed (`npx skills add google-gemini/gemini-skills --skill gemini-api-dev -a antigravity`), and the skill test passed (`antigravity-setup.md` §2).
- [ ] Permissions set (allow/deny lists, non-workspace file access = Deny); MongoDB MCP (read-only) on Edouard's laptop only.
- [ ] Decide on the build-spec change: friend data lives outside the repo (`HB_DATA_DIR`), not `data/` inside it. Update WP9 and the repo layout if agreed.
- [ ] Ask DeepMind booth whether hackathon credits can raise Antigravity quota; check gemini.google.com/students with Imperial emails.
- [ ] MongoDB Atlas upgraded to M10 with the credit, DB user created, network access set, connection string saved (not committed).
- [ ] Claim the Gemini credits (DeepMind booth) and the Atlas credit (MongoDB booth, ground floor), if not done yet.
- [ ] Edouard: push the WP0 scaffold plus `AGENTS.md` (content in the build spec, plus the additions in `antigravity-setup.md` §4). Rebase on `main` first: it now has `docs/`, `CLAUDE.md` and `.agents/`.
- [ ] ~21:30: decide stream count from quota; fill in the overnight prompts from the template; launch at most 3 streams by 22:30. Dry-run one task first so the allow list is complete.
- [ ] Friends: follow up asking for Export Original (FIT), original photos, audio and notes, plus consent.
- [ ] Ask [friend] for the interview and permission to use her name; then drop the `[friend]` redaction in the repo mirror.
- [ ] Choose the demo trail once data arrives.
- [ ] Confirm hybrid search (`$rankFusion`) and Automated Embedding details (MongoDB workshop or docs).
- [ ] Measure Argon latency once WP1 runs.
- [ ] Teammate B: ~20-item labelled accuracy set.
- [ ] Register the team on the Encode platform and connect Discord.

## Session log
- **Thu 22 Oct (AM):** Read the Encode page, including the FAQs, and saved the context doc.
- **Thu 22 Oct (PM):**
  - Agreed the tracks, the UK region, and the Python FastAPI + React + Atlas stack.
  - Wrote the plan doc.
  - Drafted messages to friends.
  - Decided to use friends' past hikes as the demo data.
- **Fri 23 Oct (AM):** GPX requested from friends. Added the start-here doc, the research notes and the outreach tracker.
- **Fri 23 Oct (16:15):** Wrote `build-spec.md`: work packages, interfaces, AGENTS.md, the overnight prompt template and the review protocol. Decided Devin takes isolated overnight tickets (WP2 first), with at most 3 agent streams in total.
- **Fri 23 Oct (16:30):** Researched Antigravity (quota, permissions, rules, skills, workflows, MCP) and wrote `antigravity-setup.md`. Findings: Antigravity quota is per Google account and separate from the Gemini API credits; free tier is weekly-limited and may stall overnight streams; treg's docs say $1 free credit (not $20) and adds little for us, so don't run `treg mcp install`.
- **Fri 23 Oct (19:55):** Attached the GitHub repo to the Project. Found that Antigravity workflows were retired (official docs: stopped working 19 Oct 2026; replaced by skills in `.agents/skills/<name>/SKILL.md`), so converted our three workflows into skills and fixed the `/demo-check` path (the demo script is in the plan doc, not the build spec). Pushed `docs/` (mirror; `friend-outreach.md` withheld, friend's name shown as `[friend]`), `CLAUDE.md` and the skills. Updated `antigravity-setup.md` §2, §4, §7.
