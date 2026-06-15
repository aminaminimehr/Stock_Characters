# Green SAS Replication

Isolated Python replication of Green, Hand, and Zhang’s SAS signal construction program (`Supplementary_assistive_files/SAS_codes/Greens_code.sas`).

This module is **not** wired into `Character_Builders/` or `Character_Panels/`. It answers:

> What does Green’s SAS code produce if implemented in Python?

## Requirements

- WRDS account (for data pulls)
- Python 3.10+
- Install deps:

```bash
pip install -r Green_SAS_Replication/requirements.txt
```

## Quick start (limited sample)

Default sample window: `2018-01-01` to `2023-12-31`.

```bash
cd Green_SAS_Replication
python green_replication_pipeline.py --sample-start 2018-01-01 --sample-end 2023-12-31
```

Outputs:

- `outputs/checkpoints/*.parquet` — stage checkpoints
- `outputs/rpsdata_green_replication.parquet` — final winsorized panel
- `diagnostics/green_replication_validation.{md,csv}`
- `diagnostics/ibes_exclusion_report.md`

## CLI flags

| Flag | Description |
|------|-------------|
| `--sample-start` / `--sample-end` | Restrict WRDS pulls and validation window |
| `--stage` | Run a single stage (see `config.PIPELINE_STAGES`) |
| `--from-checkpoint` | Reuse prior checkpoints where possible |
| `--validate-only` | Compare existing output to Green SAS `.sas7bdat` |
| `--no-wrds` | Skip WRDS (requires checkpoints / final output) |
| `--wrds-user` | Optional WRDS username |

## Pipeline stages

1. `annual_compustat` — annual Compustat extraction and characteristics
2. `ccm_annual` — CCM link + exchange/share screen
3. `annual_monthly` — Green timing `intnx(MONTH, datadate, 7) <= date < intnx(MONTH, datadate, 20)`
4. `quarterly_compustat` — quarterly characteristics + `aeavol` / `ear`
5. `merge_quarterly` — quarterly-to-monthly alignment + `ms`
6. `ibes_stubs` — IBES columns as NaN (+ SAS cleanup rules)
7. `crsp_monthly` — momentum, turnover, `indmom`
8. `crsp_daily` — daily aggregates, beta, `idiovol`, `pricedelay`
9. `final_filters` — nonmissing `mve`, `mom1m`, `bm`
10. `winsorize` — monthly `hitrim` / `hilotrim`

## IBES exclusion

Direct IBES WRDS tables are **not** used. IBES columns remain in the schema as missing (see `diagnostics/ibes_exclusion_report.md`).

`sue` uses the Compustat fallback from Green SAS when IBES is unavailable:

```text
sue = che / mveq
```

This will diverge from the benchmark wherever Green SAS used IBES actual/forecast values.

## Benchmark

Primary validation file:

`Supplementary_assistive_files/Output_From_Greens_SAS_code.sas7bdat`

Merge key: `permno` × `date` (month-end).

## Full sample

The code supports pulls from 1975 onward. Do **not** run the full sample until the limited window validates and resource usage is acceptable:

```bash
python green_replication_pipeline.py --sample-start 1975-01-01 --sample-end 2024-12-31
```

## Documentation

- `docs/sas_pipeline_map.md` — structured SAS-to-Python map
- `diagnostics/ibes_exclusion_report.md` — IBES variables and fallbacks
