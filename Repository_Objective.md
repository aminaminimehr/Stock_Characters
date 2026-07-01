# Repository Objective

> Organized reference version of `Repository Objective.txt`. This document is **internal** to the
> project and the agent working on it; it is **not** part of the public-facing repository.
> The public-facing description of the project lives in `README.md`.

## 1. Mission

Build a **completely transparent and configurable framework** for constructing empirical
asset-pricing characteristics from WRDS data.

Unlike existing repositories, this project is **not** intended to simply reproduce one specific
dataset. Instead, it exposes **every important implementation decision ("convention")** used
during character construction, so users understand exactly *why* different implementations
produce different results.

Ultimately, users should be able to generate **any** asset-pricing characteristic under **any**
desired configuration, while understanding **every assumption** made during construction.

## 2. Success criteria

The objective of the framework is assessed on two dimensions:

1. **Cross-sectional Spearman correlation** between the framework's output and the reference
   dataset is close to 1 — roughly **≥ 95%** (median monthly Spearman).
2. **The stock universe matches** — not only timing and formula, but also the universe for which
   characters are built: the survived permnos, the number of samples, and the count of unique
   permnos.

The universe match becomes especially important for characters that contain
**industry-related components**, because those cause significant divergence in values.

## 3. Immediate priority

Although the repository is designed as a general framework, the **highest priority** is:

> **Recover the complete logic that generated GKX's `datashare.csv`.**

The repository should eventually be capable of reproducing `datashare.csv` by explicitly
specifying every implementation convention used during its construction.

Because the published GKX code is incomplete and its behavior is not fully understood,
reproducing `datashare.csv` **cannot be attempted directly**. Instead, the repository follows a
**staged reconstruction process**.

> The immediate-priority and reconstruction-strategy sections below are **not** part of the public
> `README.md`. They describe the internal process the agent follows, which has proven useful
> during recent developments. We are not starting from scratch — many steps are already done with
> only minimal issues.

## 4. Reconstruction strategy

The reconstruction proceeds in two major stages.

### Stage 1 — Replicate Green's SAS implementation

Completely replicate Green's SAS implementation and verify that our implementation reproduces
Green's published output.

This serves as the **stable baseline** because:

- Green's SAS code is available.
- Green's published output is available.
- Every implementation decision can therefore be verified directly.

**Only after** Green's implementation has been faithfully reproduced should the project proceed
to Stage 2.

### Stage 2 — Reconcile Green's output with GKX's `datashare.csv`

Starting from the validated Green replication, systematically identify **every difference**
between Green's output and GKX's `datashare.csv`.

Each discrepancy should be **explained by uncovering the implementation convention responsible**
for it.

The objective is **not** merely to force the outputs to match. The objective is to **discover the
exact sequence of implementation decisions that transforms Green's output into GKX's
`datashare.csv`**.

## 5. Sources of information

The repository relies on three major sources.

### 5.1 GKX repository (Dacheng Xiu)

Contains:

- Python code (written by Xin He)
- SAS code
- a published version of `datashare.csv`

It is currently **unclear** whether either the Python or the SAS implementation actually produces
the released `datashare.csv`. Therefore these codes **cannot currently be treated as ground
truth**. They should be viewed as **valuable but uncertain references**.

### 5.2 Green's SAS code (primary reconstruction source)

Considered the **most reliable** reconstruction source because:

- the complete SAS code is available, and
- the corresponding output is available.

This allows direct verification that our replication is correct. Green therefore serves as the
**baseline implementation** from which all later modifications are studied.

### 5.3 HXZ documentation (authoritative formula reference)

Provides highly reliable documentation describing the construction of the characteristics.

One important lesson learned so far: many discrepancies between Green and GKX arise simply
because they use **different characteristic definitions**. Therefore HXZ documentation is treated
as the **authoritative reference for characteristic formulas**, even though implementation
conventions may still differ.

> Note: HXZ's documentation strictly follows the *Dissecting Anomalies* paper by Fama and French.

## 6. Philosophy of the repository

The repository is intended to **maximize transparency**.

Rather than hiding implementation choices, **every important convention should be made explicit**.
Different conventions should simply correspond to **different parameter choices**.

The repository should therefore become capable of **reproducing multiple published datasets by
changing configuration parameters rather than rewriting code**.

## 7. Important implementation conventions

A major objective is to **identify and parameterize every implementation convention** that
affects the final characteristics.

### 7.1 CRSP filtering

- Which share codes are included?
- Which exchange codes are included?
- Are low-price stocks excluded? If so, what price threshold is used?

> **Hypothesis:** Green excludes very low-price securities whereas GKX includes them, consistent
> with statements in the paper.

### 7.2 Linking CRSP and Compustat

Different implementations may use different CCM linking rules. Configurable choices include:

- `linktype`
- `linkprim`

These choices should be **explicit repository parameters**.

### 7.3 Delisting returns

Different implementations handle delisting returns differently. The repository should **expose**
the exact convention being used rather than embedding it inside the code.

### 7.4 Fiscal-year changes

The handling of firms that change fiscal year is another important implementation detail.
Different implementations may process these firms differently.

### 7.5 Industry aggregation and imputation (a key discovery)

One of the most important discoveries concerns industry-level calculations. When computing
industry averages or performing industry imputation, the **order of operations matters
substantially**.

Should industry averages be computed:

- **before** merging with CRSP, or
- **after** merging with CRSP?

These approaches can produce materially different results because many firms lose their CRSP
match (particularly after around 2000).

> **Current evidence — the correct workflow appears to be:**
> 1. Merge with CRSP first.
> 2. Retain only firms that successfully match.
> 3. Perform industry averaging and industry imputation afterward.
>
> This appears to be one of the **largest sources of discrepancy** discovered so far.

### 7.6 Industry classification

Industry aggregation may use different classification systems. Possible choices include:

- SIC two-digit industries
- Fama-French industry classifications
- other supported industry mappings

These should all be **configurable**.

### 7.7 Timing conventions

Timing conventions are another major source of disagreement.

For example, **HXZ follows the traditional Fama-French convention**: in June of year *t*, every
firm uses accounting information from fiscal year *t−1*, regardless of when that fiscal year
ended.

Current evidence suggests **Green and/or GKX may instead use a rolling six-month reporting lag**
based on the firm's own reporting date. The same issue may also arise for quarterly accounting
variables.

Determining these timing conventions is therefore a **major research objective**.

## 8. Current understanding: formula vs. convention

Disagreements between published datasets often arise for **two completely different reasons**:

1. **Different characteristic formulas.**
2. **Different implementation conventions.**

The repository must **carefully distinguish** between these two sources of disagreement. Changing
the formula is fundamentally different from changing the implementation convention, and **both**
should remain explicit throughout the project.

## 9. File locations and disposition

This section is a complete inventory: **what** each item is, **where** it lives, and its
**disposition** — whether it belongs in the public repo, is internal-only, is gitignored, or is
flagged for deletion.

### 9.1 Disposition key

| Tag | Meaning |
|---|---|
| **PUBLIC** | Part of the released public repository (source code + user-facing docs). |
| **INTERNAL** | Kept for the project / agent; **must NOT** appear in the public repo. |
| **GITIGNORED** | Not tracked by git — generated data, outputs, caches, credentials, or third-party reference data. Never distributed. |
| **DELETE** | Redundant or obsolete; flagged for removal. |

> **Git-tracking note.** `.gitignore` already excludes `Supplementary_assistive_files/`,
> `outputs/**`, `*.csv`, `*.parquet`, `*.log`, `*.pkl`, `*.xlsx`, and `__pycache__/`.
> Items marked **INTERNAL** that are `.md` or `.py` (e.g. `docs/gkx/*.md`, `docs/agent/*.md`,
> `scripts/*.py`) are **currently still tracked by git** and must be explicitly excluded (via a
> gitignore rule or by removal/move) before a public release. The `.csv`/`.parquet` INTERNAL
> files are already auto-ignored.

### 9.2 Top-level files

| File | What it is | Disposition |
|---|---|---|
| `README.md` | Public-facing description (must explain reproducibility & transparency). | **PUBLIC** |
| `LICENSE` | License terms. | **PUBLIC** |
| `CITATION.cff` | Citation metadata. | **PUBLIC** |
| `requirements.txt` | Python dependencies. | **PUBLIC** |
| `output_paths.py` | Central output-path configuration used by builders/panels. | **PUBLIC** |
| `pipeline_config.py` | Profile / configuration layer (`green|datashare|research`). | **PUBLIC** |
| `run_full_pipeline.sh` / `.ps1` | OS launcher scripts (referenced by README). | **PUBLIC** |
| `.gitignore` | Git ignore rules. | **PUBLIC** |
| `.cursorrules` | Cursor IDE agent rules — references internal `docs/agent/` protocol. | **INTERNAL** |
| `Repository Objective.txt` | Original objective (prose). Superseded by this file. | **INTERNAL** (then **DELETE** once `.md` is confirmed) |
| `Repository_Objective.md` | This organized objective reference (internal process doc). | **INTERNAL** |

### 9.3 Top-level directories (summary)

| Directory | What it is | Disposition |
|---|---|---|
| `Character_Builders/` | All character builders (Green / HXZ / GKX / shared). | **PUBLIC** |
| `Character_Panels/` | Panel assembly + pipeline entry point. | **PUBLIC** |
| `Return_Builders/` | Excess-returns builder. | **PUBLIC** |
| `Imputation/` | Fama-French industry mappings + imputation. | **PUBLIC** |
| `tests/` | Unit tests. | **PUBLIC** |
| `docs/` | Documentation (mixed — see §9.6). | **MIXED** |
| `scripts/` | Validation / audit / rebuild tooling (past validations). | **INTERNAL** (exclude from public) |
| `codex/` | AI task-delegation pack. | **INTERNAL** |
| `Green_SAS_Replication/` | Duplicate, isolated Green SAS replication (not wired in). | **DELETE** (after confirming not useful) |
| `graphify-out/` | Code-graph tool output (AST cache, HTML/JSON reports). | **DELETE** / GITIGNORED |
| `outputs/` | Generated outputs (CSVs, panels, logs, diagnostics). | **GITIGNORED** |
| `Supplementary_assistive_files/` | Third-party reference data + SAS code/outputs. | **GITIGNORED** (not redistributed) |
| `__pycache__/` | Python bytecode caches (throughout tree). | **GITIGNORED** |

### 9.4 Reference / source-of-information files (the original objective list)

These are the inputs the objective points to. All live under `Supplementary_assistive_files/`
and are **gitignored** (subject to WRDS / publisher licenses; no raw data redistributed).

| Item | Path | Disposition |
|---|---|---|
| `datashare.csv` (GKX target) | `Supplementary_assistive_files/datashare.csv` | **GITIGNORED** |
| Python code (Xin He) | `Supplementary_assistive_files/Python_codes/Dacheng_Xiu_or_Xin_he` | **GITIGNORED** |
| Dacheng Xiu's SAS code | `Supplementary_assistive_files/SAS_codes/Related_to_Dachengs_EAPVML_paper.sas` | **GITIGNORED** |
| Green's SAS code | `Supplementary_assistive_files/SAS_codes/Greens_code.sas` | **GITIGNORED** |
| Green's SAS output (benchmark) | `Supplementary_assistive_files/Output_From_Greens_SAS_code.sas7bdat` | **GITIGNORED** |
| HXZ documentation | `Supplementary_assistive_files/MarkItDown_outputs/Technical_Document_Factors_HXZ.md` | **GITIGNORED** |

Additional items inside `Supplementary_assistive_files/` beyond the objective's list
(all **GITIGNORED**; several are candidates for **DELETE** as redundant artifacts):

| Item | Disposition |
|---|---|
| `green_vs_gkx_comparison/` (cache, csv, figures, report) | **GITIGNORED** — past comparison artifacts; consider **DELETE** |
| `BM_validation_private/` (private BM validation CSVs/reports) | **GITIGNORED** — private; consider **DELETE** |
| `validate_against_green_sas.py`, `validate_hxz_bm_against_dissecting_anomalies*.py` | **GITIGNORED** — one-off validation scripts |
| `PDF_ready_for_MarkItDown/` | **GITIGNORED** — doc-conversion source |
| `Chars60_*.csv`, `chars60_summary.csv`, `GKX_characters.txt` | **GITIGNORED** — reference summaries |
| `Repository_map.jpg`, `README_revision_notes.md` | **GITIGNORED** |

### 9.5 Framework source code (PUBLIC)

| Path | What it is |
|---|---|
| `Character_Builders/build_all_implemented_characters.py` | Orchestrator for all Green-style characters. |
| `Character_Builders/CHARACTER_CATALOG.md` | Catalog of implemented characters. |
| `Character_Builders/_shared/` | Shared engine: `green_builders`, `quarterly_builders`, `ms_builder`, `beta_builder`, `rvar_factor_builders`, `event_builders`, `ibes_builders`, `ccm`, `parallel_daily_windows`, `wrds_chunk_download`, `sas_stats`, `green_winsor`. |
| `Character_Builders/Green_*_Generalized/` | One builder per Green character. |
| `Character_Builders/HXZ_*_Generalized/` | HXZ June-layer builders (`book_to_market`, `book_to_june_market_equity`, `operating_profitability`, `cash_flow_to_price`). |
| `Character_Builders/README.md` | Builder-layer docs. |
| `Character_Panels/` | `run_full_pipeline.py`, `build_all_character_panel.py`, `build_complete_prediction_panel.py`, `build_research_panel_1957.py`, `build_monthly_character_panel.py`, `build_annual_character_panel.py`, `build_green_comparable_panel.py`, `compare_green_comparable_panel.py`, `timing.py`, `README.md`. |
| `Return_Builders/` | `build_excess_returns.py`, `README.md`. |
| `Imputation/` | `industry_codes.py`, `industry_mappings.py`, `industry_median_imputation.py`, `README.md`. |
| `tests/` | `test_timing.py` (+ expand over time). |

### 9.6 Documentation (`docs/` — MIXED)

| Path | What it is | Disposition |
|---|---|---|
| `docs/README.md` | Documentation index. | **PUBLIC** |
| `docs/CONFIGURATION.md` | Authoritative profiles/flags/env-var reference. | **PUBLIC** |
| `docs/methodology/` (00–09) | Authoritative methodology (formulas, timing, linking, filters, imputation, validation). | **PUBLIC** |
| `docs/RELEASE_NOTES.md` | Current restructuring release notes. | **PUBLIC** |
| `docs/RESTRUCTURING_PLAN.md` | Historical restructuring plan (mostly implemented). | **INTERNAL** |
| `docs/gkx/` (active reports) | Active datashare/Green comparison reports + diagnosis MDs. | **INTERNAL** (exclude from public) |
| `docs/gkx/archive/` | Historical validation reports (phase1–7, timing/industry/ms/chatoia audits). | **INTERNAL** (consider **DELETE**) |
| `docs/agent/` | Agent protocol: `AGENT_RULES.md`, `INVESTIGATION_PROTOCOL.md`, `CONVENTIONS_REGISTRY.yaml`, `DISCREPANCY_TABLE.csv`, `SESSION_LOG.md`, `FORMULA_DIFFERENCES.yaml`. | **INTERNAL** — must not be public |
| `docs/archive/agents_review/` | Prior agent handoff notes. | **INTERNAL** |

### 9.7 Validation & investigation tooling (INTERNAL — exclude from public)

| Path | What it is | Disposition |
|---|---|---|
| `scripts/README.md` | Scripts index. | **INTERNAL** |
| `scripts/validation/` | Validation scripts incl. `compare_panel_vs_gkx_datashare.py`, `compare_panel_final_vs_green.py`, `debug_*.py`, `validate_*.py`, `green_sas_io.py`. | **INTERNAL** |
| `scripts/audits/` | One-off audit scripts (`audit_gkx_*.py`, `audit_character_inventory.py`, etc.). | **INTERNAL** |
| `scripts/rebuild/` | One-off rebuild/migration scripts. | **INTERNAL** |
| `scripts/archive/` | Archived phase1–7 validation scripts. | **INTERNAL** (consider **DELETE**) |
| `scripts/experiments/` | Experimental scripts (currently empty besides `__pycache__`). | **INTERNAL** (consider **DELETE**) |
| `codex/` | AI task-delegation pack (`GETTING_STARTED.md`, `PROMPT_TIPS.md`, `TASK_INDEX.md`, `tasks/01–10_*.md`). | **INTERNAL** |

### 9.8 Generated artifacts (GITIGNORED)

| Path | What it is | Disposition |
|---|---|---|
| `outputs/characteristics/individual/*.csv` | One CSV per built character. | **GITIGNORED** (regenerated by pipeline) |
| `outputs/panels/` | Signal / prediction / research panels (+ `legacy/`, dated snapshots). | **GITIGNORED** |
| `outputs/diagnostics/` | Audit MDs, temp CSVs, validation dumps. | **GITIGNORED** (consider **DELETE** of stale temp files) |
| `outputs/logs/` | Build logs, server log (`Latest_log_on_the_server.txt`). | **GITIGNORED** |
| `outputs/**/.gitkeep` | Directory placeholders. | **PUBLIC** (kept so tree exists) |
| `graphify-out/` | Code-graph tool output (HTML/JSON/AST cache). | **DELETE** / GITIGNORED |
| `__pycache__/` | Python bytecode (throughout tree). | **GITIGNORED** |

### 9.9 Items explicitly flagged for deletion

Per the objective and the redundancy audit:

| Item | Reason | Action |
|---|---|---|
| `Green_SAS_Replication/` | Duplicate, isolated replication; **not wired** into `Character_Builders/` or `Character_Panels/`; the main `_shared` engine already replicates Green SAS. | **Verify not useful → DELETE** (objective §10) |
| `Repository Objective.txt` | Superseded by `Repository_Objective.md`. | **DELETE** after `.md` confirmed |
| `graphify-out/` | Code-graph tool artifact, unrelated to character construction. | **DELETE** (or gitignore) |
| `docs/gkx/archive/`, `scripts/archive/`, `scripts/experiments/` | Historical/obsolete validation artifacts. | **DELETE** or move to an internal archive outside the public repo |
| `outputs/diagnostics/` stale temp files (`green_comparable_temp*.csv`, `_audit_tmp.txt`, etc.) | Throwaway diagnostics. | **DELETE** (regenerated as needed) |
| `Supplementary_assistive_files/green_vs_gkx_comparison/`, `BM_validation_private/` | Past/private comparison artifacts. | **DELETE** (already gitignored) |

### 9.10 Public-release checklist (derived from the above)

Before publishing the repository:

1. **Keep PUBLIC**: `Character_Builders/`, `Character_Panels/`, `Return_Builders/`,
   `Imputation/`, `tests/`, `output_paths.py`, `pipeline_config.py`, `README.md`, `LICENSE`,
   `CITATION.cff`, `requirements.txt`, `run_full_pipeline.sh/.ps1`, `.gitignore`,
   `docs/{README.md, CONFIGURATION.md, methodology/, RELEASE_NOTES.md}`.
2. **Exclude (INTERNAL)**: `docs/agent/`, `docs/gkx/`, `docs/RESTRUCTURING_PLAN.md`,
   `docs/archive/`, `scripts/`, `codex/`, `.cursorrules`, `Repository_Objective.md`,
   `Repository Objective.txt`. Add a gitignore rule or move these out of the public tree.
3. **Delete**: `Green_SAS_Replication/`, `graphify-out/`, and the stale archives/temp files
   listed in §9.9.
4. **Update `README.md`** to (a) state reproducibility & transparency as the target, and
   (b) keep the `bm_ia` "not replicated" note accurate (the `_dc` GKX port has been removed).
5. **Verify** `.gitignore` continues to exclude `Supplementary_assistive_files/`, `outputs/**`,
   and all data/cache formats so no raw WRDS data or generated outputs leak into the public repo.

## 10. Repository housekeeping (internal)

- **`docs/`** — contains many extra files from past validations across different constructions.
  They can be used if necessary, but **should be excluded from the public repo**.
- **`scripts/`** — the codes used to calculate validations and tests through the process.
  These are **also to be excluded from the public repo**.
- **`Green_SAS_Replication/`** — constructed separately. **Verify it is not useful, then delete it.**

## 11. README requirement

The public `README.md` of the repository must:

1. Clearly state that the target of this repo is **reproducibility and transparency**.
2. Document **every flag** accepted by the pipeline and **every way the pipeline can be used**
   (full run, resume, profiles, panels-only, single-character, daily-only, parallelism, date
   windowing, launcher scripts), plus the **environment variables** that control behavior.
3. Point to `docs/CONFIGURATION.md` as the authoritative, exhaustive flag reference and to
   `docs/methodology/` for the formulas/conventions behind each flag.

The reference content below is what the README should convey (mirrors the actual CLI surfaces in
`run_full_pipeline.py`, `build_all_implemented_characters.py`, the per-character builders, the
panel/return builders, `pipeline_config.py`, and the launcher scripts).

### 11.1 Top-level entry point — `Character_Panels/run_full_pipeline.py`

| Flag | Purpose |
|---|---|
| `--wrds-user` *(required)* | WRDS PostgreSQL username. |
| `--profile {green\|datashare\|research}` | Pipeline preset (default `green`; also via `STOCK_CHARACTERS_PROFILE`). |
| `--resume` | Resume a partial build — skips characters whose CSV already exists. |
| `--skip-build` | Only rebuild panels from existing character CSVs (no WRDS pulls). |
| `--skip-ibes` | Skip IBES tables (`re` omitted; `sue` uses Compustat-only surprise). |
| `--sample-start`, `--sample-end` *(YYYY-MM-DD)* | WRDS date bounds for pulls. |
| `--workers N` | Parallel CPU workers for `beta`, `rvar_*`, `abr`, `ear` (default `min(cpu,8)`). |
| `--green-universe` / `--no-green-universe` | Apply Green's final sample screen (`bm`, `mom1m`, `mve` non-missing). |
| `--green-winsor` / `--no-green-winsor` | Apply Green's monthly winsorization to the signal panel. |
| `--ccm-linktypes`, `--ccm-linkprim` | Override CCM linking rules (applies to Green **and** HXZ builders). |
| `--skip-special` | Skip `beta`/`rvar`/`ear`/`ms` and other special builders (debug). |
| `--skip-daily` | Skip daily-CRSP-based monthly characters (debug). |

### 11.2 Profiles (`pipeline_config.py`)

| Profile | Behavior |
|---|---|
| `green` *(default)* | Replicate Green SAS library; annual start 1975; winsor on; builds research panel. |
| `datashare` | 1957+ start; sparse panel (no Green joint screen); HXZ `bm`/`operprof`; no research panel. |
| `research` | Full pipeline through the ranked 1957+ research panel. |

CCM defaults: Green = `LU,LC,LD,LF,LN,LO,LS,LX` (no `linkprim`); HXZ = `LU,LC` with `linkprim P,C`.

### 11.3 Character orchestrator — `Character_Builders/build_all_implemented_characters.py`

Invoked internally by the pipeline; also runnable standalone:

`--wrds-user`, `--output-dir`, `--ccm-linktypes`, `--ccm-linkprim`,
`--skip-daily`, `--only-daily` *(build only daily-CRSP monthly chars)*,
`--skip-special`, `--skip-annual-monthly` *(skip annual+monthly blocks after a partial run)*,
`--skip-ibes`, `--skip-existing`, `--sample-start`, `--sample-end`, `--workers`.

### 11.4 Per-character builder CLIs

Common to most builders: `--wrds-user`, `--output`, and (HXZ + several Green) `--ccm-linktypes`,
`--ccm-linkprim`.

Notable per-builder flags:

| Builder | Extra flag | Purpose |
|---|---|---|
| `HXZ_BM`, `HXZ_CFP`, `Green_MVEL1` | `--use-imputed-market-equity` | Forward-fill CRSP price/shares within permno before computing market equity. |

> Example single-character build:
> `python Character_Builders/Green_ACC_Generalized/build_acc.py --wrds-user "$WRDS_USER"`

### 11.5 Panel & return builders (run internally by the pipeline)

| Script | Flags |
|---|---|
| `build_all_character_panel.py` | `--input-dir`, `--output`, `--legacy-june-annual` *(force June flat expansion)*, `--green-universe`, `--green-winsor`. |
| `build_complete_prediction_panel.py` | `--characters`, `--returns`, `--output`, `--legacy-narrow-panel` *(deprecated)*. |
| `build_research_panel_1957.py` | `--input`, `--output`, `--start-target-yyyymm` *(default 195701)*, `--industry-scheme` *(default 49)*, `--winsor-lower` *(0.01)*, `--winsor-upper` *(0.99)*. |
| `build_monthly_character_panel.py` / `build_annual_character_panel.py` | `--output`. |
| `Return_Builders/build_excess_returns.py` | `--wrds-user`, `--output`, `--sample-start`, `--sample-end`, `--green-delisting-fill` *(fill missing distress delisting returns)*. |

### 11.6 Environment variables

| Variable | Purpose |
|---|---|
| `WRDS_USER` / `WRDS_USERNAME` / `WRDS_PASSWORD` | WRDS credentials (never stored in the repo; use `.pgpass`). |
| `PGPASSFILE` | Path to `.pgpass` for non-interactive auth. |
| `STOCK_CHARACTERS_PROFILE` | Select profile (`green\|datashare\|research`). |
| `STOCK_CHARACTERS_WORKERS` | Parallel CPU workers (used if `--workers` omitted). |
| `STOCK_CHARACTERS_SAMPLE_START` / `STOCK_CHARACTERS_SAMPLE_END` | WRDS date bounds. |
| `STOCK_CHARACTERS_DEFAULT_ANNUAL_START` | Annual pull floor (default `1975-01-01`). |
| `STOCK_CHARACTERS_WRDS_DOWNLOAD_WORKERS` | Parallel WRDS download threads (default 4, capped 16). |
| `STOCK_CHARACTERS_WRDS_PERMNO_CHUNK` | Permno batch size for `crsp.dsf` downloads (default 400). |
| `STOCK_CHARACTERS_PYTHON` | Python interpreter for launcher scripts. |
| Launcher conveniences (`.sh`/`.ps1`) | `RESUME`, `SKIP_IBES`, `SAMPLE_START`, `SAMPLE_END`, `GREEN_UNIVERSE`. |

### 11.7 Ways to run the pipeline

```bash
# Full Green replication (default profile)
python Character_Panels/run_full_pipeline.py --wrds-user "$WRDS_USER"

# Resume a partial build (skip already-built characters)
python Character_Panels/run_full_pipeline.py --wrds-user "$WRDS_USER" --resume

# Datashare-style universe (1957+, sparse panel, HXZ bm/operprof)
python Character_Panels/run_full_pipeline.py --wrds-user "$WRDS_USER" --profile datashare
#   or:  export STOCK_CHARACTERS_PROFILE=datashare && bash run_full_pipeline.sh

# Full pipeline through ranked research panel
python Character_Panels/run_full_pipeline.py --wrds-user "$WRDS_USER" --profile research

# Green's exact final sample (drops rows missing bm/mom1m/mve)
python Character_Panels/run_full_pipeline.py --wrds-user "$WRDS_USER" --profile green --green-universe

# Panels only — no WRDS pulls, merge existing character CSVs
python Character_Panels/run_full_pipeline.py --wrds-user "$WRDS_USER" --skip-build

# Tune parallelism and date window
python Character_Panels/run_full_pipeline.py --wrds-user "$WRDS_USER" --workers 25 \
    --sample-start 2000-01-01 --sample-end 2023-12-31

# Single character
python Character_Builders/Green_ACC_Generalized/build_acc.py --wrds-user "$WRDS_USER"

# Launcher scripts (read the env vars in §11.6)
bash run_full_pipeline.sh        # Linux/macOS
./run_full_pipeline.ps1          # Windows
```

### 11.8 README housekeeping

The README should also keep the documented flag set in sync with the actual `argparse` definitions
(the source of truth) whenever new flags are added, and keep the `bm_ia` "not replicated" note
accurate (the experimental `_dc` GKX port has been removed from the repo).
