# Task 08 — Demote experimental paths and sync docs

**Priority:** Medium  
**Run on:** Local  
**Depends on:** Tasks 01, 05  

## Objective

Mark rejected or reference-only code clearly so the repo mission is obvious.

## Actions

1. **`Character_Builders/Dacheng_datashare/`** — update README: "Experimental; wrong model for this
   datashare.csv per datashare_reverse_engineering.md. Not used in pipeline."
2. **`docs/methodology/01_formula_differences.md`** — update datashare section: empirical mapping
   is HXZ/Green for bm/operprof/cfp; Dacheng accounting_60 port rejected; **bm_ia abandoned**.
3. **`docs/methodology/08_validation_status.md`** — note bm_ia out of scope.
4. **`Character_Builders/CHARACTER_CATALOG.md`** — remove or demote `_dc` as primary; list datashare
   mapping to existing columns.
5. **`Green_SAS_Replication/README.md`** — one line: reference cross-check, not production path.

## Do NOT

- Delete Dacheng_datashare folder (keep as experiment).
- Delete Green_SAS_Replication.

## Acceptance checks

Grep docs for contradictory "use bm_dc" as primary — should be gone.

## Codex prompt

```
Read codex/tasks/08_cleanup_experimental_paths.md and docs/gkx/datashare_reverse_engineering.md.

Update docs and READMEs to state:
- datashare bm/operprof/cfp map to book_to_market, operating_profitability, Green cfp
- Dacheng_datashare builder is experimental/rejected for this file
- bm_ia is out of scope

Do not delete folders. Do not change builder formulas.
```
