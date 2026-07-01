# Stock Characteristics — Green Replication + GKX-Compatible Library

A transparent, auditable implementation of monthly U.S. equity characteristics built from CRSP,
Compustat, and (optionally) IBES via WRDS.

## Repository mission

**Primary — replicate Green's character library as closely as possible.** The benchmark for
correctness is Jeremiah Green's SAS program (`Supplementary_assistive_files/SAS_codes/Greens_code.sas`)
and its output (`Supplementary_assistive_files/Output_From_Greens_SAS_code.sas7bdat`). All Green-layer
validation is performed against that SAS output. When Green's *code* and *output* disagree (known SAS
bugs), the **code** is authoritative and the divergence is documented.

**Secondary — match `datashare.csv` where it differs from Green**, using existing HXZ/Green builders
with configurable universe and timing (`--profile datashare`). **`bm_ia` is not replicated.**

## Character layers

| Layer | Naming | Example | Role |
|---|---|---|---|
| **Green** (canonical) | short names | `bm`, `operprof`, `cfp` | Replicate Green SAS; benchmark vs `Output_From_Greens_SAS_code.sas7bdat` |
| **HXZ / FF June** | descriptive | `book_to_market`, `operating_profitability` | Datashare mapping for `bm` and `operprof` |

Datashare mapping (empirically validated): `bm` → `book_to_market`, `operprof` → `operating_profitability`,
`cfp` → Green `cfp`. See `docs/gkx/datashare_reverse_engineering.md`.

## Data sources

- **CRSP** — monthly & daily stock files (returns, prices, volume, shares, exchange/share codes),
  delisting returns, `mseall`/`msenames` for the universe screen.
- **Compustat** — `funda` (annual) and `fundq` (quarterly) fundamentals.
- **CRSP–Compustat Merged (CCM)** — `crsp.ccmxpf_linktable` for `gvkey ↔ permno` linking.
- **Green SAS output** — `Output_From_Greens_SAS_code.sas7bdat` (validation benchmark).
- **Datashare** — `Supplementary_assistive_files/datashare.csv` (GKX variable list / target).
- **Optional** — IBES (analyst data) for `re` and a few IBES-dependent fields (skippable with
  `--skip-ibes`); Fama-French factors / risk-free rate for excess returns.

## Pipeline architecture

```
Character builders ──► outputs/characteristics/individual/*.csv
  • Green engine:      Character_Builders/build_all_implemented_characters.py
                       (annual, monthly, daily→monthly, quarterly, special)
  • HXZ June layer:    Character_Builders/HXZ_*_Generalized/build_*.py  (datashare bm/operprof)
        │
        ▼
Signal panel          Character_Panels/build_all_character_panel.py
                      → outputs/panels/all_character_signal_panel.csv   (wide outer merge)
        │
Excess returns        Return_Builders/build_excess_returns.py
                      → outputs/panels/excess_returns.csv
        │
        ▼
Prediction panel      Character_Panels/build_complete_prediction_panel.py
                      → outputs/panels/complete_all_character_prediction_panel.csv
        │
        ▼
Research panel        Character_Panels/build_research_panel_1957.py
                      → outputs/panels/research_panel_1957_ranked.csv
                        (winsorize → FF49 median impute → rank to [-1, 1])
```

- **Builders** compute one (or a few) characteristics each and write a CSV keyed by
  `(permno, datadate)` (fundamentals) or `(permno, signal_yyyymm, target_yyyymm)` (monthly).
- **Panels** merge builders into a wide monthly panel, attach returns, and produce a research-ready
  ranked panel.
- **Validation scripts** (`scripts/validation/`) compare the panel to Green SAS and to `datashare.csv`.
- **Profiles** (`pipeline_config.py`): `--profile green|datashare|research` — see [Configuration](#configuration).

See `docs/methodology/` for formulas, timing, linking, filters, validation status.
See `docs/CONFIGURATION.md` for every flag.

## Configuration

Behavior is controlled by **profiles** (not hard-coded). Override any default with CLI flags.

| Profile | Use when |
|---|---|
| `green` (default) | Replicating Green SAS output |
| `datashare` | Matching `datashare.csv` universe (1957+, sparse panel, no joint screen) for bm/operprof/cfp |
| `research` | Full pipeline through ranked 1957+ research panel |

```bash
# Green replication
python Character_Panels/run_full_pipeline.py --wrds-user "$WRDS_USER" --profile green

# Datashare-like (1957+, no Green joint universe screen)
export STOCK_CHARACTERS_PROFILE=datashare
bash run_full_pipeline.sh

# Optional: exact Green final sample (drops rows missing bm, mom1m, mve)
python Character_Panels/run_full_pipeline.py --wrds-user "$WRDS_USER" --profile green --green-universe
```

Full flag reference: **`docs/CONFIGURATION.md`** (CCM link types, sample dates, `--skip-ibes`, `--resume`, env vars).

## Validation philosophy

1. **Green SAS output is the benchmark.** Correctness = agreement with `Output_From_Greens_SAS_code.sas7bdat`.
2. **`datashare.csv` determines which variables matter** (the GKX-relevant set) but is **not** the
   ground-truth implementation.
3. **Code over output** when Green's SAS has a known bug (`operprof`, `pchcapx_ia`).
4. Metric: **median monthly Spearman** rank correlation across all monthly cross-sections.
5. Current status: 92/95 datashare variables at median monthly ρ ≥ 0.95; see
   `docs/methodology/08_validation_status.md`.

## Stock universe

Common stock on major exchanges: `exchcd ∈ {1,2,3}`, `shrcd ∈ {10,11}`. **No** price floor, **no**
financial-firm exclusion, **no** microcap exclusion — matching both Green's SAS and GKX's
`accounting_60.py`. The Green final-sample screen (`mve`, `mom1m`, `bm` non-missing) is reproduced by
the `--green-universe` flag (off by default). Full details and the GKX paper-vs-code discrepancy:
`docs/methodology/04_filters_and_universe.md`.

## How to run (fresh machine)

### 1. Environment

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. WRDS access

Set credentials via environment + `.pgpass` (no credentials are stored in the repo):

```bash
export WRDS_USER=your_wrds_username
export PGPASSFILE=~/.pgpass        # contains: wrds-pgdata.wharton.upenn.edu:9737:wrds:USER:PASSWORD
```

### 3. Run the full pipeline

```bash
export STOCK_CHARACTERS_WORKERS=8   # parallel daily windows; tune to your machine
# export RESUME=1                   # skip characters already built (rebuild only missing)
# export GREEN_UNIVERSE=1           # restrict panel to Green's exact final sample
bash run_full_pipeline.sh           # Windows: ./run_full_pipeline.ps1
```

This builds all individual characteristics, then the signal / prediction / research panels into
`outputs/`. Expect a multi-hour run on full history; 64 GB RAM recommended.

Build a single characteristic (optional CLIs):

```bash
python Character_Builders/Green_ACC_Generalized/build_acc.py --wrds-user "$WRDS_USER"
```

### 4. Validation

```bash
# Green SAS benchmark (datashare columns)
python scripts/validation/compare_panel_final_vs_green.py

# Datashare universe + bm/operprof/cfp correlation (requires built panel)
python scripts/validation/validate_datashare_universe.py
```

## Outputs

```
outputs/
  characteristics/individual/*.csv     one file per characteristic
  panels/
    all_character_signal_panel.csv
    excess_returns.csv
    complete_all_character_prediction_panel.csv
    research_panel_1957_ranked.csv
  logs/  diagnostics/
```

## Documentation map

| Location | Contents |
|---|---|
| **`docs/CONFIGURATION.md`** | **Profiles, CLI flags, environment variables** |
| `docs/methodology/` | Authoritative methodology (00–09) |
| `docs/gkx/` | Active datashare/Green comparison reports (+ `archive/` for history) |
| `scripts/README.md` | Validation vs audit script layout |
| `codex/` | Optional task pack for delegating future work to Codex |
| `Green_SAS_Replication/docs/` | SAS→Python reference cross-check |

## License & citation

See `LICENSE` and `CITATION.cff`. WRDS data is subject to your institution's WRDS license; no raw
WRDS data is redistributed in this repository.
