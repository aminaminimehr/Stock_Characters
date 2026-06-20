# Task 01 — Archive historical audit documentation

**Priority:** High (reduces clutter, no behavior change)  
**Run on:** Local machine  
**Depends on:** nothing  

## Objective

Move phase-by-phase GKX audit markdown out of the main `docs/gkx/` view into an archive subfolder,
without deleting history. Update indexes so new users find `docs/methodology/` first.

## Scope

- Create `docs/gkx/archive/` and move **historical** files there (phase validations, one-off audits,
  debug notes). Keep these **in repo root of gkx** (not archived):
  - `datashare_reverse_engineering.md`
  - `datashare_universe_comparison.md`
  - `panel_final_vs_green_full_comparison.md` (+ `.csv` if present)
  - `codex_task_datashare_next_tests.md`
- Add `docs/gkx/README.md`: "Historical audit trail; current methodology is in `docs/methodology/`."
- Update `docs/README.md` if paths change.
- Move `agents review/` → `docs/archive/agents_review/` (4 handoff files).

## Do NOT

- Delete any markdown files.
- Change Python code or builders.
- Edit `docs/methodology/` content except adding a one-line pointer to `docs/gkx/archive/`.

## Acceptance checks

```bash
# From repo root
test -d docs/gkx/archive
test -f docs/gkx/README.md
test -f docs/gkx/datashare_universe_comparison.md
# agents review folder should be gone from top level
test ! -d "agents review"
test -d docs/archive/agents_review
```

## Codex prompt (copy everything below this line)

```
You are working in the Stock_Characters repository.

Read codex/tasks/01_archive_docs.md and implement it exactly.

Goals:
1. Create docs/gkx/archive/ and move historical GKX phase/audit markdown there.
2. Keep datashare_reverse_engineering.md, datashare_universe_comparison.md,
   panel_final_vs_green_full_comparison.md, codex_task_datashare_next_tests.md in docs/gkx/.
3. Add docs/gkx/README.md explaining the archive.
4. Move "agents review/" to docs/archive/agents_review/.
5. Update docs/README.md links if needed.

Do NOT delete files. Do NOT change character builder code or formulas.
Run the acceptance checks in the task file and report results.
```
