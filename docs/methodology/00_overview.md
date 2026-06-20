# Methodology Documentation — Overview & Architecture

This `docs/methodology/` set is the **authoritative** methodological reference for the repository.
It supersedes the fragmented phase-by-phase notes under `docs/gkx/` (retained as a historical audit trail).

## Repository mission

1. **Primary — Green replication layer.** Replicate Jeremiah Green's SAS character library
   (`Supplementary_assistive_files/SAS_codes/Greens_code.sas`). Benchmark:
   `Output_From_Greens_SAS_code.sas7bdat`. When Green's *code* and *output* disagree (known SAS bugs),
   the **code** is authoritative and the divergence is documented.
2. **Secondary — datashare alignment (configurable).** Match `datashare.csv` for **`bm`, `operprof`,
   `cfp`** via `--profile datashare` — not by hard-coding datashare formulas. See
   `docs/CONFIGURATION.md`.
3. **`bm_ia` is out of scope** (no reliable replication found).

## Character layers

| Layer | Purpose | Builder |
|---|---|---|
| **Green** (canonical) | Replicate Green SAS | `Character_Builders/_shared/` + `Green_*_Generalized/` |
| **HXZ / FF June** | June-timed variants for datashare `bm`/`operprof` | `HXZ_*_Generalized/` |
| **Experimental `_dc`** | GKX `accounting_60.py` port | `GKX_datashare/` — **rejected** for this datashare.csv |

**Datashare column mapping (empirical):**

| datashare | repo column |
|---|---|
| `bm` | `book_to_market` |
| `operprof` | `operating_profitability` |
| `cfp` | Green `cfp` |

Profiles (`pipeline_config.py`): `green` (default), `datashare` (1957+, sparse panel), `research`.

## Canonical vs reference Green implementations

- **Canonical:** `green_builders.py` + `build_all_implemented_characters.py` → production panel.
- **Reference:** `Green_SAS_Replication/` — cross-check only, not wired into production.

## Where each topic is documented

| File | Topic |
|---|---|
| `01_formula_differences.md` | Green vs datashare vs repo formulas |
| `02_timing.md` | Annual/quarterly/June/FF/HXZ timing |
| `03_linking.md` | CCM link types and share classes |
| `04_filters_and_universe.md` | Exchange/share-code filters + universe audit |
| `05_industry_definitions.md` | SIC / FF industry codes |
| `06_data_availability.md` | Lags, lookbacks, missing handling |
| `07_imputation.md` | Imputation reference and unification plan |
| `08_validation_status.md` | Validation vs Green and datashare |
| `09_final_report.md` | Restructuring status and open items |

## Pipeline architecture (current)

```
pipeline_config.py  (--profile green | datashare | research)
        |
        v
Character_Panels/run_full_pipeline.py
        |
        +-- build_all_implemented_characters.py   (Green: annual/monthly/daily/quarterly/special)
        +-- HXZ_*_Generalized/build_*.py          (datashare profile: book_to_market, operating_profitability only)
        +-- Return_Builders/build_excess_returns.py
        |
        v   outputs/characteristics/individual/*.csv
Character_Panels/build_all_character_panel.py     -> all_character_signal_panel.csv
Character_Panels/build_complete_prediction_panel.py -> complete_all_character_prediction_panel.csv
Character_Panels/build_research_panel_1957.py     -> research_panel_1957_ranked.csv  (research profile only)
```

`GKX_datashare/` is **not** in the production path.
