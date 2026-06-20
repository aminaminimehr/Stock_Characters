# Task 10 — Push to remote and release notes

**Priority:** Final  
**Run on:** Local (git)  
**Depends on:** Task 09 (or explicit sign-off if server run pending)  

## Objective

Update the online GitHub repo with a clean, documented state.

## Steps

1. Review `git status` — no secrets, no huge outputs committed (`outputs/` should stay gitignored).
2. Commit message style: one sentence **why** (e.g. "Add datashare profile and archive audit docs").
3. Push branch or main per team practice.
4. Add `docs/RELEASE_NOTES.md` (or section in 09_final_report) listing:
   - Profiles added
   - Docs archived
   - bm_ia out of scope
   - How to validate datashare universe

## Do NOT

- `git push --force` to main
- Commit `datashare.csv` or WRDS outputs if not already tracked

## Acceptance checks

```bash
git status
git log -1 --oneline
# Remote updated: git pull on server succeeds
```

## Codex prompt

```
Read codex/tasks/10_push_and_release.md.

Prepare docs/RELEASE_NOTES.md summarizing this restructuring wave.
List files changed by category. Do NOT run git push unless the user explicitly asks.
Provide exact git commands for the user to run.
```
