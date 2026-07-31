# Stock Characteristics — A Transparent Framework for Empirical Asset Pricing

A transparent, auditable implementation of monthly U.S. equity characteristics built from CRSP,
Compustat, and (optionally) IBES via WRDS.

---

## Table of Contents

- [Citation & License](#citation--license)
- [Introduction](#introduction)
- [Construction decision points](#construction-decision-points)
- [Repository architecture](#repository-architecture)
- [Configuration](#configuration)
- [How to run (fresh machine)](#how-to-run-fresh-machine)
- [Validation philosophy](#validation-philosophy)
- [Reference documentation](#reference-documentation)

---

## Citation & License

This repository is released under the [MIT License](LICENSE).

If you use the code or the construction definitions in academic work, please cite the repository. A
machine-readable record is provided in [CITATION.cff](CITATION.cff). A standard reference you can adapt
in BibTeX is:

```bibtex
@software{aminimehr2026stockcharacters,
  author       = {Aminimehr, Amin},
  title        = {Stock Characters: Reproducible Python Builders for Green-Style and HXZ-Style Signals},
  year         = {2026},
  url          = {https://github.com/aminaminimehr/Stock_Characters}
}
```

Empirical outputs also depend on licensed vendor data accessed through WRDS (CRSP, Compustat, IBES,
and Fama-French factors). Follow each provider's terms of use in addition to citing this repository.
No raw WRDS data is redistributed in this repository.

**Contact:** Amin Aminimehr — `aminiman@mail.uc.edu` (GitHub issues welcome).

---

## Introduction

### What this repository builds

This repository constructs monthly U.S. equity characteristics — the firm-level signals used in return
prediction, portfolio optimization, and machine-learning asset pricing. It pulls data from CRSP,
Compustat, and (optionally) IBES through WRDS, links firms to securities, applies timing and
universe conventions, and assembles the results into prediction-ready panels.

### Why this matters

Replication in empirical asset pricing has historically been treated as largely automatic. Authors of
renowned papers shared their code — or, in many cases, only summary documentation — with little
explanation of the construction details that sit behind the published numbers. Researchers could
download a finished panel and run their models without ever seeing how that panel was assembled.

But building a characteristic dataset for prediction and portfolio optimization is more than the
characteristic formula and the timing convention. Many silent decisions — CRSP/Compustat linking rules,
share-code and exchange filters, industry averaging order, SIC code source, fiscal-year timing,
delisting return handling, imputation, winsorization, and cross-sectional ranking — each push the
final panel in a different direction. Two implementations can use the same published formula and still
produce materially different cross-sections, especially for industry-adjusted variables and for
post-2000 samples where Compustat coverage exceeds CRSP-investable coverage.

We believe this is a genuinely important issue. This repository therefore contributes in two ways:

1. **Reproducibility** — it reproduces two published datasets (Jeremiah Green's SAS character library
   as the validated baseline, and Gu-Kelly-Xiu's `datashare.csv` as the empirical target) by
   identifying every implementation convention that separates them.
2. **Transparency and teaching** — it documents *how* characteristics are built and *where* the
   **construction decision points** live, so that researchers can understand, audit, and reconfigure
   the pipeline rather than treating replication as a black box.

### What this repository is not

This is not a project to produce matching numbers by any means necessary. Every discrepancy between
implementations must be explained by a named, configurable parameter. Convention changes and formula
changes are tracked separately. The Green baseline replication must remain reproducible at all times.

See `docs/agent/CONVENTIONS_REGISTRY.yaml` for the authoritative record of confirmed conventions and
`docs/agent/AGENT_RULES.md` for the investigation protocol.

### Character layers

| Layer | Naming | Example | Role |
|---|---|---|---|
| **Green** (canonical) | short names | `bm`, `operprof`, `cfp` | Replicate Green SAS; benchmark vs `Output_From_Greens_SAS_code.sas7bdat` |
| **HXZ / FF June** | descriptive | `book_to_market`, `operating_profitability` | Fama-French June timing for price-ratio characteristics |
| **GKX-exact** | `_dc` suffix | `bm_dc`, `operprof_dc`, `bm_ia_dc` | Datashare timing and industry conventions |

Datashare mapping (empirically validated): `bm` → `book_to_market`, `operprof` → `operating_profitability`,
`cfp` → Green `cfp`. See `docs/gkx/datashare_reverse_engineering.md`.

### Data sources

- **CRSP** — monthly and daily stock files (returns, prices, volume, shares, exchange/share codes),
  delisting returns, `mseall`/`msenames` for the universe screen.
- **Compustat** — `funda` (annual) and `fundq` (quarterly) fundamentals.
- **CRSP–Compustat Merged (CCM)** — `crsp.ccmxpf_linktable` for `gvkey ↔ permno` linking.
- **Green SAS output** — `Output_From_Greens_SAS_code.sas7bdat` (validation benchmark).
- **Datashare** — `Supplementary_assistive_files/datashare.csv` (GKX variable list / target).
- **Optional** — IBES (analyst data) for `re` and a few IBES-dependent fields (skippable with
  `--skip-ibes`); Fama-French factors / risk-free rate for excess returns.

---

## Construction decision points

A **construction decision point** is any implementation choice that changes the final panel but is
not the characteristic formula itself. The same formula applied under different conventions can
produce different cross-sections, different sample sizes, and different rank correlations against a
published dataset.

This repository makes each decision point a configurable parameter (CLI flag or profile). Below is
every decision point we have encountered during the construction of this codebase, with the options
seen in the literature, what this repository does, and why it matters.

### a. Annual fiscal-year timing

How fiscal-year accounting data is assigned to calendar months is one of the most consequential
decisions in the pipeline. Three conventions appear in the literature and in this repository:

| Convention | Rule | Used by | Characteristics affected |
|---|---|---|---|
| **Fama-French / HXZ June** | Fiscal year ending in calendar year `y` → available **June `y+1` … May `y+2`** | HXZ builders (`book_to_market`, `operating_profitability`, `cash_flow_to_price`, `bmj`) | Price-ratio characteristics with December ME |
| **Green rolling window** | Fundamentals from fiscal-year-end `datadate` available in months **`datadate + 7` … `datadate + 19`** | Green SAS and all repo Green annual characteristics | All annual accounting variables (`bm`, `acc`, `agr`, `ep`, …) |
| **GKX datashare lag** | `jdate = datadate + 4 months`; forward-filled monthly until next report | GKX `accounting_60.py` and repo `_dc` layer | `bm_dc`, `operprof_dc`, `cfp_dc`, `bm_ia_dc` |

**Why it matters:** These conventions are not equivalent. For a firm with a non-December fiscal year
end, the Green rolling window and the FF June convention assign the same fiscal report to different
calendar months. Industry-adjusted annual characteristics (`bm_ia`, `cfp_ia`, `me_ia`, `pchcapx_ia`)
are especially sensitive because the industry mean is computed over a different firm-year cross-section
depending on which timing convention is active.

See `docs/methodology/02_timing.md` for code references and per-variable routing.

### b. Quarterly timing

Quarterly accounting data introduces a second timing layer:

| Convention | Rule | Used by |
|---|---|---|
| **Green quarterly window** | Data from a quarter ending on `datadate` is available in calendar months **`datadate − 10 months` … `datadate − 5 months`** | Green SAS and repo Green quarterly characteristics |
| **GKX quarterly lag** | `jdate = datadate + 3 months` (month-end); forward-filled via `merge_asof` | GKX `accounting_60.py` and repo `_gkx` variants |

This difference is **confirmed** in `docs/agent/CONVENTIONS_REGISTRY.yaml`. Quarterly characteristics
affected include `chtx`, `cinvest`, `nincr`, `roaq`, `roeq`, `rsup`, `stdacc`, and `stdcf`.

The Green window reflects a fixed availability schedule tied to the quarter end. The GKX lag reflects
SEC filing deadlines (10-Q/10-K with common 45-day extensions). Both are defensible; they produce
different monthly cross-sections for the same underlying quarterly report.

### c. Industry averaging order (pre- vs post-CCM merge)

Industry-adjusted characteristics subtract an industry mean (or median) from a firm-level value. The
**order of operations** — when that industry statistic is computed relative to the CRSP merge — is
expected to be the single largest source of discrepancy for industry-related variables, especially
post-2000.

| Option | Definition | Used by |
|---|---|---|
| **`pre_ccm`** | Compute industry averages from the **full Compustat universe**, then merge with CRSP | Green SAS (default `--profile green`) |
| **`post_ccm`** | Merge with CRSP first, keep only matched firms, **then** compute industry averages | GKX / Dacheng EAPVML SAS (`--profile datashare`) |

**Why it matters:** Many Compustat firms lose their CRSP match over time (delistings, link breaks,
non-investable share classes). Pre-CCM industry means include these firms in the benchmark;
post-CCM means exclude them. The gap widens after 2000 when Compustat coverage exceeds
CRSP-investable coverage. This affects all annual industry benchmarks (`bm_ia`, `cfp_ia`, `me_ia`,
`herf`, Mohanram `m1`–`m6`, and related variables).

Controlled by `--industry-agg pre_ccm|post_ccm`. Quarterly Mohanram `m7`/`m8` and `indmom` are
unaffected (always computed on quarterly Compustat / monthly CRSP respectively).

### d. Industry classification scheme

Which industry buckets are used to compute means, medians, and imputations:

| Scheme | Definition | Where used |
|---|---|---|
| **SIC2** | First two digits of SIC | Green industry-adjusted characteristics (`*_ia`), `indmom`, Mohanram `ms` |
| **FF49** | Fama-French 49-industry SIC-range groupings | GKX `bm_ia_dc`, research-panel imputation |
| **FF12 / FF17 / FF30 / FF38 / FF48** | Other Fama-French mappings | Available in `Imputation/industry_mappings.py`; not wired into production builders |

| Operation | Statistic | Industry scheme |
|---|---|---|
| Green industry-adjusted characteristics (`*_ia`, `indmom`) | **mean** | SIC2 |
| Green Mohanram (`ms`) industry signals | **median** | SIC2 |
| GKX industry-adjusted (`bm_ia_dc`) | **mean** | FF49 |
| Research-panel imputation | **median** | FF49 |

Green's SIC2 grouping vs GKX's FF49 grouping is the primary structural difference for
industry-adjusted variables beyond the pre/post-CCM order question.

See `docs/methodology/05_industry_definitions.md`.

### e. Share-code and exchange-code universe filters

Which CRSP securities enter the stock universe:

| Filter | Green SAS | GKX (`accounting_60.py`) | Repo default (`--profile green`) | Repo datashare (`--profile datashare`) |
|---|---|---|---|---|
| **Exchange** | `exchcd in (1,2,3)` | `exchcd 1–3` | `1,2,3` | `1,2,3` |
| **Share code** | `shrcd in (10,11)` | `shrcd 10,11` | `10,11` | `ALL` (no filter) |

**GKX paper vs code discrepancy:** The GKX paper states *"We include stocks with prices below $5,
share codes beyond 10 and 11, and financial firms."* That describes a philosophy of not adding the
usual anomaly-study exclusions. But GKX's own `accounting_60.py` (L214–215) — and the published
`datashare.csv` — restrict to `shrcd in (10,11)` and `exchcd in (1,2,3)`.

**How this repository handles it:** The **Green profile** matches GKX code's share-code filter
(`shrcd 10,11`; see `pipeline_config.py`). The **datashare profile** uses `shrcd=ALL` (no
share-code SQL filter) as an empirically tested hypothesis that **deviates** from GKX's own
`accounting_60.py`. The validation target is `datashare.csv` the artifact, not GKX's code line
for line — the datashare profile tests whether relaxing the share-code screen improves coverage
against that published file.

### f. Price, financial-firm, and microcap screens

| Filter | Green SAS | GKX code | Repository |
|---|---|---|---|
| Price < $5 | none | none | none |
| Financial firms (SIC) | not excluded | not excluded | not excluded |
| Microcap | not excluded | not excluded | not excluded |

All three implementations agree: no price floor, no financial-firm exclusion, no microcap exclusion.
These filters are **not** the source of permno-count differences between implementations.

See `docs/methodology/04_filters_and_universe.md`.

### g. CCM linktype and linkprim filters

Accounting characteristics require a CRSP/Compustat Merged link from `gvkey` to `permno`. The CCM
filter is rarely discussed in signal documentation, but it changes coverage and occasionally changes
the matched security.

| Source | Link types | Link primaries | Date rule |
|---|---|---|---|
| **Repo default (HXZ)** | `LU, LC` | `P, C` | `linkdt ≤ datadate ≤ linkenddt` |
| **Green SAS** | `LU, LC, LD, LF, LN, LO, LS, LX` | **none** | `(year(linkdt) ≤ 2015 or null)` and `(year(linkenddt) ≥ 1950 or null)` |
| **GKX / Dacheng** | all `L*` (prefix rule) | `C, P` | `linkdt ≤ jdate ≤ linkenddt` (missing `linkenddt` → today) |
| **Chen-Zimmermann / Open Source Asset Pricing** | `LC, LU` | `P, C` | standard date validity |

**Multiple share classes:** HXZ and GKX aggregate December market equity by **permco** (summing across
share classes, assigning to the largest-ME permno). The repo default resolves duplicates by
`linkprim_priority` (P before C before other). These choices affect price-ratio characteristics and
firm-level size measures.

The legacy Green SAS **2015 link-date cap** (`linkdt` year ≤ 2015) has been **removed** in this
repository; links starting in any year are kept.

See `docs/methodology/03_linking.md` and `Character_Builders/_shared/ccm.py`.

### h. SIC code source and look-ahead-bias note

SIC codes classify firms into industries. Both CRSP (`msenames.siccd`) and Compustat
(`comp.company.sic`) provide SIC codes, but they are not always identical and they behave
differently over time:

| Source | Behavior | Used by |
|---|---|---|
| **`comp.company.sic`** | Constant per `gvkey` (current Compustat classification) | Green SAS, GKX, repo default (`sic_source=comp_company`) |
| **CRSP `msenames.siccd`** | Time-varying per `permno` | Legacy repo behavior (now deprecated) |

**Look-ahead-bias caveat:** `comp.company.sic` reflects the firm's *current* SIC classification,
which can incorporate later reclassifications not known at the historical signal date. This is a
known trade-off. We accept it because:

1. It matches Green and GKX, the two datasets we replicate.
2. SIC2 industry buckets are coarse and relatively stable over time.
3. The alternative (time-varying `siccd`) introduces a different kind of noise and does not match
   either published dataset.

This convention is **confirmed** in `docs/agent/CONVENTIONS_REGISTRY.yaml` (839,494 sic2 mismatches
were diagnosed when CRSP SIC was used instead of Compustat SIC).

### i. Duplicate fiscal reports and fiscal-year-end changes

Fiscal-year-end changes can create more than one Compustat annual report for the same firm within a
calendar year. After linking to CRSP, this can produce duplicate or overlapping observations for the
same `permno` and signal month.

The repository handles these cases explicitly:

- Annual builders keep the **most recent Compustat `datadate`** within each firm-calendar year when
  multiple annual reports map to the same calendar year.
- Panel construction resolves duplicate `(permno, signal_yyyymm)` rows by keeping the observation
  with the latest underlying `datadate`.
- Raw character files retain `datadate` and `fyear` so these decisions remain auditable.

### j. Delisting return handling

Return-side files include delisting returns when available from CRSP (`dlret`). The excess-return
builder also exposes an optional distress-delisting convention:

```bash
python Return_Builders/build_excess_returns.py --wrds-user "$WRDS_USER" --green-delisting-fill
```

This fills selected missing distress delisting returns with **−35%** for NYSE/AMEX and **−55%** for
NASDAQ before computing adjusted returns. This is a return adjustment, not winsorization.

Delisting return handling primarily affects momentum and return-based characteristics (`mom*`,
`maxret`, `rvar_*`).

### k. Return lagging for monthly momentum and size

Monthly return-history characteristics use lagged returns so the signal month does not include the
return being predicted:

| Variable | Lag structure |
|---|---|
| `mom1m` | previous month's return (lag 1) |
| `mom6m` | lags 2 through 6 |
| `mom12m` | lags 2 through 12 |
| `mom36m` | lags 13 through 36 |
| `me`, `mvel1` | lagged market equity |

This prevents look-ahead bias in the predictor–return alignment.

### l. Daily-CRSP monthly placement

Daily CRSP-based monthly characteristics (`maxret`, `baspread`, `ill`, `std_dolvol`, `std_turn`,
`zerotrade`, `dolvol`, `turn`) are computed from daily data within a source month and then placed on
the **following** monthly signal. This keeps daily statistics out of the contemporaneous return month
being predicted.

### m. Sign conventions (formula-direction decisions)

Some characteristics differ between implementations not in the formula itself but in the **direction**
of the signal:

| Characteristic | Green | GKX datashare |
|---|---|---|
| `agr` (asset growth) | raw: `(AT_t − AT_{t−1}) / AT_{t−1}` (positive = growing) | negated for ML convention (higher value → higher predicted return) |

These are logged as `FORMULA_ONLY` in the discrepancy table — a deliberate formula-direction choice,
not a computation error. See `docs/agent/CONVENTIONS_REGISTRY.yaml` (confirmed: Spearman(panel vs
datashare) = −0.997; Spearman(−panel vs datashare) = +0.997).

Convention changes and formula changes must never be conflated. See `docs/agent/AGENT_RULES.md`.

### n. Imputation (research panel)

For the research-ready 1957+ panel, missing characteristic values are imputed after raw construction
and return alignment:

1. Assign Fama-French 49-industry codes from SIC.
2. Impute missing values using `(signal_yyyymm, FF49)` **industry medians**.
3. Fall back to the same-month cross-sectional median when the industry median is unavailable.

See `docs/methodology/07_imputation.md`.

### o. Winsorization and ranking

**Individual character builders do not winsorize.** Raw character CSVs and the default prediction
panels are intentionally unwinsorized. If a research design requires outlier treatment, apply it as a
separate, documented panel step.

The research panel (`build_research_panel_1957.py`) applies:

1. Cross-sectional winsorization at the monthly 1st and 99th percentiles (by `signal_yyyymm`).
2. Cross-sectional ranking to the **[-1, 1]** interval:

```text
ranked_x = 2 * (rank(x) - 1) / (N - 1) - 1
```

where `N` is the number of nonmissing observations for that characteristic in the month after
winsorization and imputation. Ties receive average ranks. If an entire characteristic is unavailable
in an early month, the final ranked value is set to **0** (the neutral midpoint), following the GKX
convention for keeping the 1957+ matrix rectangular.

### p. Sample window and Green final-sample screen

| Parameter | Green profile | Datashare profile |
|---|---|---|
| **`--sample-start`** | `1975-01-01` | `1957-01-01` |
| **`--green-universe`** | optional: drops rows missing `bm`, `mom1m`, `mve` | off by default |

Green SAS applies a final sample screen requiring non-missing `mve`, `mom1m`, and `bm`. The
repository reproduces this with `--green-universe` (off by default so the full CRSP spine is retained
for research use).

### q. Lookback buffer for history-dependent characteristics

`--sample-start` is the WRDS **download lower bound**, applied as a hard SQL predicate
(`date >= start`) via `output_paths.sql_date_filter()`. The repository does **not** automatically
extend the download window backward to warm up history-dependent characteristics.

**Why it matters:** Many characteristics need months or quarters of prior data before they can be
computed. With no lookback buffer, they are **missing (NaN)** for the first N periods after
`sample_start`. The builders handle this correctly — they null values when history is insufficient
rather than emitting wrong numbers (e.g. `green_builders.py` nulls momentum when
`return_count` is too low; `quarterly_builders.py` nulls `stdacc`/`stdcf` when `count < 17`).

| Characteristic | Warmup needed | Notes |
|---|---|---|
| `mom6m` | 6 months | lags 2–6 |
| `mom12m`, `chmom`, `indmom` | 12 months | lags 2–12 |
| `seas1a` | 11 months | lag 11 |
| `mom36m` | 36 months | lags 13–36 |
| `mom60m` | 60 months | lags 13–60 |
| `rvar_mean`, `rvar_capm`, `rvar_ff3` | 60 months of daily data | daily regression windows |
| `stdacc`, `stdcf` | 16 quarters (~4 years) | rolling quarterly std |
| `sgrvol`, `roavol` | 8 quarters (~2 years) | rolling quarterly std |
| `nincr` | 8 quarters | consecutive earnings increases |
| `cinvest`, `ni`, `rna`, `sue`, `che` | 4–5 quarters | quarter-over-quarter lags |

**Exceptions — full history already pulled:** `age` and `orgcap` load the full annual Compustat
history regardless of `--sample-start` (`green_builders.py`: "sample window ignored").

**Practical guidance:** To have long-history characteristics available from a desired panel start
date, set `--sample-start` **earlier** than that date by at least the longest warmup. Examples:

- For full `mom60m` / `rvar_*` coverage from January 1975, download from roughly **1970** or
  earlier (`--sample-start 1970-01-01`).
- For a 1957 research panel with full long-history coverage, download from roughly **1950** or
  earlier.

**Research-profile implication:** `--profile research` uses `sample_start=1975-01-01` for WRDS
downloads, while the research **panel** keeps target return months from January 1957 onward
(`build_research_panel_1957.py`). Long-history characteristics therefore only populate from roughly
**1980 onward** in the default research profile; earlier panel months have them as NaN, then the
research-panel step imputes (FF49 median) and ranks missing values to **0**.

---

## Repository architecture

```
Character builders ──► outputs/characteristics/individual/*.csv
  • Green engine:      Character_Builders/build_all_implemented_characters.py
                       (annual, monthly, daily→monthly, quarterly, special)
  • HXZ June layer:    Character_Builders/HXZ_*_Generalized/build_*.py
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

### Outputs

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

### Documentation map

| Location | Contents |
|---|---|
| **`docs/CONFIGURATION.md`** | Profiles, CLI flags, environment variables |
| `docs/methodology/` | Authoritative methodology (00–09): timing, linking, filters, industry, imputation |
| `docs/gkx/` | Active datashare/Green comparison reports |
| `docs/agent/` | Conventions registry, discrepancy table, investigation protocol |
| `scripts/README.md` | Validation vs audit script layout |

See `docs/methodology/` for formulas, timing, linking, filters, and validation status.

---

## Configuration

Behavior is controlled by **profiles** (not hard-coded). Override any default with CLI flags.

| Profile | Use when |
|---|---|
| `green` (default) | Replicating Green SAS output |
| `datashare` | Matching `datashare.csv` universe (1957+, sparse panel, no joint screen) |
| `research` | Full pipeline through ranked 1957+ research panel |

### Required flags and recipes

`run_full_pipeline.py` has **no silent defaults** for the universe/link/window filters. Pass a
profile (which fills all required flags) or pass them explicitly. Resolved values are printed at
startup for transparency.

| Flag | Meaning | Green recipe (`--profile green`) | Datashare recipe (`--profile datashare`) |
|---|---|---|---|
| `--ccm-linktypes` | CCM linktype filter. `L*` = every linktype starting with L. | `LU,LC,LD,LF,LN,LO,LS,LX` | `L*` |
| `--ccm-linkprim` | CCM linkprim filter; `ALL` = no filter | `ALL` | `P,C` |
| `--crsp-shrcd` | CRSP share-code filter; `ALL` = no filter | `10,11` | `ALL` |
| `--crsp-exchcd` | CRSP exchange-code filter | `1,2,3` | `1,2,3` |
| `--sample-start` | WRDS download window start | `1975-01-01` | `1957-01-01` |
| `--industry-agg` | When to compute annual industry benchmarks | `pre_ccm` | `post_ccm` |

`--sample-end` is optional (open-ended = latest available).

**These flags are global — one set applies to every builder (Green and HXZ).** Because
`--ccm-linkprim` is a single global choice, the recipes force a trade-off:

- `--profile green` uses `linkprim=ALL` (no primary filter), so HXZ `bm`/`operprof`/`cfp` differ
  from a strict Fama-French primary-link build.
- `--profile datashare` uses the Dacheng convention: `linktypes=L*`, `linkprim=P,C`, and
  `--industry-agg post_ccm`.

```bash
# Green replication
python Character_Panels/run_full_pipeline.py --wrds-user "$WRDS_USER" --profile green

# Datashare-like (1957+, no Green joint universe screen)
python Character_Panels/run_full_pipeline.py --wrds-user "$WRDS_USER" --profile datashare

# Optional: exact Green final sample (drops rows missing bm, mom1m, mve)
python Character_Panels/run_full_pipeline.py --wrds-user "$WRDS_USER" --profile green --green-universe

# Explicit flags (no profile)
python Character_Panels/run_full_pipeline.py --wrds-user "$WRDS_USER" \
  --ccm-linktypes LU,LC,LD,LF,LN,LO,LS,LX --ccm-linkprim ALL \
  --crsp-shrcd 10,11 --crsp-exchcd 1,2,3 --sample-start 1975-01-01 --industry-agg pre_ccm
```

Full flag reference: **`docs/CONFIGURATION.md`** (CCM link types, sample dates, `--skip-ibes`,
`--resume`, environment variables).

---

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

Do not commit usernames, passwords, `.pgpass` files, downloaded WRDS data, or generated output CSVs
to a public repository.

### 3. Run the full pipeline

```bash
export STOCK_CHARACTERS_WORKERS=8   # parallel daily windows; tune to your machine
# export RESUME=1                   # skip characters already built (rebuild only missing)
# export GREEN_UNIVERSE=1           # restrict panel to Green's exact final sample
bash run_full_pipeline.sh           # Windows: ./run_full_pipeline.ps1
```

This builds all individual characteristics, then the signal / prediction / research panels into
`outputs/`. Expect a multi-hour run on full history; 64 GB RAM recommended.

Build a single characteristic (optional):

```bash
python Character_Builders/Green_ACC_Generalized/build_acc.py --wrds-user "$WRDS_USER"
```

Resume after interruption:

```bash
RESUME=1 bash run_full_pipeline.sh
# or
python Character_Panels/run_full_pipeline.py --wrds-user "$WRDS_USER" --resume
```

Rebuild panels only from existing CSVs (no WRDS queries):

```bash
python Character_Panels/run_full_pipeline.py --wrds-user "$WRDS_USER" --skip-build
```

### 4. Validation

```bash
# Green SAS benchmark (datashare columns)
python scripts/validation/compare_panel_final_vs_green.py

# Datashare universe + bm/operprof/cfp correlation (requires built panel)
python scripts/validation/validate_datashare_universe.py
```

Every validation must report **Spearman correlation, sample N, and unique permnos** — Spearman alone
is never sufficient to claim a match.

---

## Validation philosophy

1. **Green SAS output is the benchmark.** Correctness = agreement with
   `Output_From_Greens_SAS_code.sas7bdat`.
2. **`datashare.csv` determines which variables matter** (the GKX-relevant set) but is **not** the
   ground-truth implementation.
3. **Code over output** when Green's SAS has a known bug (`operprof`, `pchcapx_ia`).
4. **Metric:** median monthly Spearman rank correlation across all monthly cross-sections, plus
   sample N and unique permno count (both must align within 2%).
5. **Current status:** 92/95 datashare variables at median monthly ρ ≥ 0.95; see
   `docs/methodology/08_validation_status.md`.

A characteristic is considered matched only when all three conditions hold simultaneously:

- Cross-sectional Spearman vs GKX datashare.csv > 0.95
- Sample N within 2% of the GKX sample N
- Unique permno count within 2% of the GKX unique permno count

---

## Reference documentation

**Characteristic definitions and June portfolio timing:**

Hou, Xue, and Zhang, *Technical Document: Testing Portfolios*  
https://global-q.org/uploads/1/2/2/6/122679606/portfoliostd_2020june.pdf

**Book-to-market validation moments:**

Fama and French, *Dissecting Anomalies*  
https://papers.ssrn.com/sol3/papers.cfm?abstract_id=911960

**Green-style character definitions:**

- Jeremiah Green's website: https://sites.google.com/site/jeremiahrgreenacctg/home
- Green SAS code: https://drive.google.com/file/d/0BwwEXkCgXEdRQWZreUpKOHBXOUU/view?resourcekey=0-1xjZ8fAc0sTybVC6RADDCA

**CCM linking references:**

- Kai Chen's WRDS linking note and the `tidyfinance` WRDS CCM helper (conservative `LC/LU` + `P/C` default)
- WRDS CRSP/Compustat Merged Database documentation

**Related public datasets:**

- Gu, Kelly, and Xiu — machine-learning asset pricing (`datashare.csv`)
- Chen and Zimmermann — Open Source Asset Pricing
- Hou, Xue, and Zhang — global factor data and testing portfolios
