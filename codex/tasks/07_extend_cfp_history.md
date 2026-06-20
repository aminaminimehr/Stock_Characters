# Task 07 — Extend Green `cfp` history to 1957+

**Priority:** Medium  
**Run on:** **Server with WRDS**  
**Depends on:** nothing (can parallel task 03–04)  

## Objective

Green `cfp` matches datashare at ρ≈0.998 but local output may start 1975 due to Compustat query
start date. Extend **query window only**, not the formula.

Reference: `docs/gkx/datashare_reverse_engineering.md` (cfp section).

## Scope

- Find Compustat annual start filter in `_shared/green_builders.py` (or env `STOCK_CHARACTERS_SAMPLE_START`).
- Ensure `--profile datashare` / `--sample-start 1957-01-01` pulls funda from 1957.
- If `scripts/rebuild/rebuild_green_cfp_full_history.py` exists, verify or fix it.
- Rebuild **only** `cfp.csv` to scratch or individual dir; validate vs datashare pre-1975.

## Do NOT

- Change cfp formula (`oancf/mve_f`, accrual fallback).

## Acceptance checks (server)

```bash
export WRDS_USER=...
export PGPASSFILE=~/.pgpass
python Character_Builders/build_all_implemented_characters.py \
  --wrds-user "$WRDS_USER" \
  --output-dir outputs/characteristics/individual \
  --sample-start 1957-01-01 \
  # rebuild cfp only if skip-existing allows, or use dedicated rebuild script

python scripts/validation/validate_datashare_universe.py ...  # cfp row pre-1975 paired obs > 0
```

## Codex prompt

```
Read codex/tasks/07_extend_cfp_history.md and docs/gkx/datashare_reverse_engineering.md.

Extend Green cfp Compustat history to 1957+ by sample-start / query date only.
Do NOT change cfp formula. Provide a rebuild command for the server.
If rebuild script exists under scripts/rebuild/, use or fix it.

Document server steps in docs/CONFIGURATION.md under datashare profile.
```
