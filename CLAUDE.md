# Hiking Buddy: instructions for Claude sessions

Hackathon app for Encode London 2026 (23–25 Oct). **Submissions close Sun 25 Oct 12:00 London.** Repo: https://github.com/EddiebleDoormouse/Ike_Hiking-Buddy (**public**).

1. **Read `docs/00-start-here.md` first** (status, team, conventions, open items), then the doc for your task: `docs/build-spec.md` for work packages and interfaces, `docs/hiking-buddy-plan.md` for scope and the demo script, `docs/hackathon-spec.md` for the judging rubric.
2. **`AGENTS.md`** (once it exists) applies to you as it does to the Antigravity and Devin agents. Follow its working rules and Gemini API rules.
3. **`docs/*.md` planning files are a read-only mirror** of the team's Claude Project "Encode Club Hackathon". Don't edit them here. If something in them is wrong, say so in `NOTES.md` or in the PR, and the Project copy gets fixed and re-synced. Repo-native docs you may edit: `NOTES.md`, `docs/MODELS.md`, `README.md`.
4. **Git.** One branch per task (`wp2-tracks`), small commits, PR into `main`. Never force-push `main`. Only docs syncs go straight to `main`.
5. **Public repo, so never commit** `.env`, API keys, connection strings, or friends' data (GPX/FIT, photos, audio, notes). Real data stays outside the repo. Use synthetic fixtures in tests. Don't put friends' names in the repo; the mirror shows the experienced friend as `[friend]` until she agrees.
6. **Hackathon rule:** the demo may show only code written after Fri 23 Oct 17:00. Don't paste in code from before kickoff.
7. **Checks:** `/ship-check` before every merge, `/spec-check` for a rubric audit, `/demo-check` before rehearsals (skills in `.agents/skills/`).
8. Keep answers concise and clear; the team includes beginners, so explain simply when asked.
