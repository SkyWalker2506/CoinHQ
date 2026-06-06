# Lessons Learned — Run 5

**Date:** 2026-06-06

## What Worked
1. **Run-4's recommendations mapped cleanly to tasks again.** The waitlist backend (D004 reverse-trigger), OG metadata caching, OAuth entropy check, and dependabot triage all came straight from Run-4 lessons.
2. **Local controlled dep upgrade beat merging stale dependabot branches.** The Apr-5 dependabot PRs were ~9 commits behind and conflicted with each other (all touch the same ci.yml lines). Doing one batch branch — bump pyproject + `uv lock` + run tests + regenerate requirements.txt — was conflict-free and let `uv` reject the unsafe fastapi/pydantic cascade before it ever hit CI.
3. **`uv lock` surfaced the fastapi breakage instantly.** fastapi 0.135 → pydantic≥2.9 was caught by the resolver, not by a broken test run. Deferring it was a one-line revert.
4. **localStorage-as-fallback kept the waitlist CTA non-breaking** while still moving to a real backend — the form succeeds even if the API is down.

## What Failed / To Watch
1. **Worktree isolation did NOT give independent branches for parallel coders.** All three Wave-1 agents' commits piled onto one branch; the other two PRs were empty. Root cause likely: the shared object store + branch-ref races when the parent repo's `main` had an unpushed commit as the base. **Fix for next run:** either (a) push the base to origin BEFORE dispatching worktree agents so every worktree branches from a clean published main, or (b) run parallel coders sequentially / give each a distinct pre-created branch name and verify `git log origin/main..HEAD` per agent before opening its PR. Single in-repo agent (Wave 2) had zero issues.
2. **No live browser/e2e this run.** UI/Functional scores are test-derived only. A future run should stand up backend+frontend+a throwaway sqlite/redis and run a Playwright smoke of the waitlist POST + share page.
3. **fastapi/pydantic upgrade is now a known cascade** — schedule it as its own task alongside the pydantic v2.7→2.9 `class Config` → `ConfigDict` cleanup (the WaitlistOut schema also still uses the deprecated `class Config`).

## Recommendations for Run 6
1. **JWT localStorage → httpOnly cookie** — deferred 3× now (D003/D005). Highest-impact security item left; run as a SUPERVISED session with manual auth round-trip QA, not unattended forge.
2. **fastapi 0.135 + pydantic ≥2.9 migration** — single task: bump both, fix `class Config`→`ConfigDict` across schemas, run full suite. Clears 4 deprecation warnings + PR #5.
3. **Frontend major bumps (tailwind 3→4, recharts 2→3, eslint-config-next 14→15)** — one task with codemods + a Playwright visual sanity pass.
4. **Playwright smoke harness** so future runs can produce real UI/Functional scores instead of test-derived estimates.
5. **Codify the worktree fix** (push base first) into the forge dispatch step.
