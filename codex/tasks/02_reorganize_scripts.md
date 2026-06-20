# Task 02 — Reorganize `scripts/` with path fixes

**Priority:** Medium  
**Run on:** Local  
**Depends on:** Task 01 optional  

## Objective

Reorganize the flat `scripts/` folder into subfolders and fix `PROJECT_ROOT = Path(__file__).parents[1]`
so scripts still resolve the repo root (must become `parents[2]` when one level deeper).

## Target layout

See `docs/RESTRUCTURING_PLAN.md` §3:

- `scripts/validation/` — keep running these
- `scripts/audits/` — reference only
- `scripts/rebuild/` — maintenance
- `scripts/archive/` — phase validators, scratch diagnostics

## Critical constraint

Every moved script that uses `Path(__file__).resolve().parents[1]` for repo root must use
`parents[2]` after the move. Scripts that import siblings must stay in the **same** subfolder or
imports must be updated.

## Do NOT

- Change validation logic or formulas.
- Delete scripts (except `_diag_datashare_focus.py` only if user explicitly approves — skip delete for now).

## Acceptance checks

```bash
python scripts/validation/validate_output_layout.py
python scripts/validation/compare_panel_final_vs_green.py --help
# Both should start without ImportError
```

Update `README.md` validation section paths if script locations changed.

## Codex prompt

```
Read codex/tasks/02_reorganize_scripts.md and docs/RESTRUCTURING_PLAN.md section 3.

Reorganize scripts/ into validation/, audits/, rebuild/, archive/ as specified.
Fix PROJECT_ROOT path depth (parents[1] -> parents[2]) in every moved file.
Fix any broken sibling imports.
Update README.md paths for validation commands.

Do NOT change validation algorithms or Green builder formulas.
Run acceptance checks and fix any ImportError.
```
