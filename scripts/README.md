# Scripts

| Folder | When to use |
|---|---|
| **`validation/`** | Green SAS benchmark, datashare universe/correlation, output layout checks |
| **`rebuild/`** | Targeted rebuilds (e.g. `rebuild_green_cfp_full_history.py`) |
| **`audits/`** | One-off investigative audits (reference) |
| **`archive/`** | Superseded GKX phase scripts and scratch diagnostics |

## Primary validation commands

```bash
# Panel vs GKX datashare.csv (full period, all 95 predictors)
python scripts/validation/compare_panel_vs_gkx_datashare.py \
  --panel outputs/panels/all_character_signal_panel_for_GKX_comparison.csv \
  --datashare Supplementary_assistive_files/datashare.csv

# Green SAS output (full period, datashare columns)
python scripts/validation/compare_panel_final_vs_green.py

# Datashare universe + bm/operprof/cfp correlation
python scripts/validation/validate_datashare_universe.py

# Repo layout sanity check
python scripts/validation/validate_output_layout.py
```

See `docs/CONFIGURATION.md` for profiles and pipeline flags.
