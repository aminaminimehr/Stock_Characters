# Task 06 — Datashare universe validation (permno + coverage)

**Priority:** Critical (user's main concern)  
**Run on:** Local script; **run against data on server or local** if panel CSVs exist  
**Depends on:** Task 04 recommended  

## Objective

One script that reports **universe match**, not just Spearman, for datashare columns
`bm`, `operprof`, `cfp` vs repo builders:

| datashare | repo column |
|---|---|
| bm | book_to_market |
| operprof | operating_profitability |
| cfp | cfp (Green) |

Reference: `docs/gkx/datashare_universe_comparison.md`

## Create

`scripts/validation/validate_datashare_universe.py` (or keep flat `scripts/` if task 02 not done)

For each character, report:

- `keys_datashare`, `keys_repo`, `keys_both`, `datashare_only`, `repo_only`
- `permno_datashare`, `permno_repo`, `permno_both`
- median monthly Spearman and exact match on **`keys_both` only**
- optional decade breakdown

Month alignment: datashare `DATE` is return month; predictor month = prior month-end
(test both if ambiguous; document which wins).

Inputs (CLI args):

- `--datashare` path to datashare.csv
- `--panel` path to signal panel OR individual CSVs for the three repo columns

Output: `docs/gkx/datashare_universe_validation_report.md` + CSV summary

## Do NOT

- Include `bm_ia`.
- Change builder formulas in this task.

## Acceptance checks

```bash
python scripts/validation/validate_datashare_universe.py --help
# If local panel exists:
python scripts/validation/validate_datashare_universe.py \
  --datashare Supplementary_assistive_files/datashare.csv \
  --panel outputs/panels/all_character_signal_panel.csv
```

## Codex prompt

```
Read codex/tasks/06_datashare_universe_validation.md and docs/gkx/datashare_universe_comparison.md.

Implement validate_datashare_universe.py comparing datashare bm/operprof/cfp to
book_to_market, operating_profitability, and Green cfp.

Report coverage metrics (keys_both, datashare_only, repo_only, permno counts) BEFORE correlation.
Write markdown report to docs/gkx/datashare_universe_validation_report.md.

Exclude bm_ia. Do not change builder formulas.
```
