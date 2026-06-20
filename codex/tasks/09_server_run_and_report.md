# Task 09 — Server full run + validation report

**Priority:** High  
**Run on:** **Linux server (WRDS)**  
**Depends on:** Tasks 04, 06, 07  

## Objective

One clean end-to-end run with `--profile datashare`, then document results.

## Server steps (you or Codex on server)

```bash
cd ~/work/Equity_chars_Amins_repo/Stock_Characters
git pull

export WRDS_USER=aminaminimehr
export PGPASSFILE=~/.pgpass
export STOCK_CHARACTERS_WORKERS=8
export STOCK_CHARACTERS_PROFILE=datashare

# Fresh build (no RESUME) if validating universe from scratch:
# rm -rf outputs/characteristics/individual/*.csv outputs/panels/*.csv  # CAREFUL

bash run_full_pipeline.sh
# Or:
python Character_Panels/run_full_pipeline.py --wrds-user "$WRDS_USER" --profile datashare
```

After build:

```bash
python scripts/validation/validate_datashare_universe.py \
  --datashare Supplementary_assistive_files/datashare.csv \
  --panel outputs/panels/all_character_signal_panel.csv

python scripts/validation/compare_panel_final_vs_green.py \
  # Green benchmark optional; use green profile run separately
```

## Deliverable

Append results to `docs/methodology/09_final_report.md`:

- Run date, profile, git commit
- Universe metrics for bm, operprof, cfp
- Spearman on keys_both
- Known gaps and whether acceptable

Copy panel to local if needed: `all_character_signal_panel.csv`

## Success criteria (pragmatic)

- `datashare_only` + `repo_only` each < 10% of `keys_both` for bm (tune after first run)
- Spearman on keys_both: bm ≥ 0.95, operprof ≥ 0.95, cfp ≥ 0.99

## Codex prompt

```
Read codex/tasks/09_server_run_and_report.md.

If running on server with WRDS: execute datashare profile pipeline and validation scripts.
If running locally without WRDS: write a shell script scripts/server_run_datashare.sh
with exact commands and update 09_final_report.md with a "pending server run" checklist.

Do not change formulas. Report universe metrics before correlation.
```
