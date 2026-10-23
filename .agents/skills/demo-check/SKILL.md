---
name: demo-check
description: Walks steps 2 to 4 of the Hiking Buddy demo script in the browser agent at phone width and reports what breaks or looks unfinished, without fixing anything. Run only when the user types /demo-check or asks for a demo rehearsal check.
---

# /demo-check

Check only. Do not fix anything.

1. Read the **Demo script** section of `docs/hiking-buddy-plan.md` (steps 2 to 4: plan, hike folder with a live photo upload, search and recap).
2. Make sure the backend and the frontend are running. If they are not, start them with the commands in `README.md`; if the README has none yet, say so and stop.
3. Use the browser agent (`/browser`) at a **390 px wide** viewport. Follow each step of the script on the app's real data, in order. Take a screenshot at every step.
4. For each step report **OK**, **BROKEN** (what happened, and any console or network error) or **UNFINISHED** (missing UI or placeholder text). Also note anything that would not fit in the 3-minute time budget, such as a call that takes more than a few seconds.
5. Finish with the three most damaging problems for a live demo, most serious first.
