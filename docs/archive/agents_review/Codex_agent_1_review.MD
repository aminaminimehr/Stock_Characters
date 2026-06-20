# Codex Agent 1 Review

This review was prepared as a read-only repository inspection. No code, documentation, generated outputs, or configuration files were modified during the review itself.

## Purpose Of This Report

The goal of this report is to help a future agent or developer understand the current repository state and correct structural, documentation, portability, and implementation issues in a way that supports the main project goal:

1. First obtain an exact replication of Green's SAS output.
2. Use that exact Green replication as the validated baseline.
3. Then compare and modify toward GKX `datashare.csv`, treating GKX primarily as the target column universe and later as a comparison target.

## What Was Inspected

The inspection covered the repository structure, Git state, ignore rules, README, requirements, output path logic, core builders, panel timing logic, pipeline runner, tests, audit scripts/docs, and the isolated `Green_SAS_Replication` subtree.

Key files and areas inspected included:

- `README.md`
- `.gitignore`
- `requirements.txt`
- `output_paths.py`
- `run_full_pipeline.sh`
- `run_full_pipeline.ps1`
- `Character_Builders/`
- `Character_Builders/_shared/green_builders.py`
- `Character_Builders/_shared/ccm.py`
- `Character_Builders/_shared/beta_builder.py`
- `Character_Panels/`
- `Character_Panels/timing.py`
- `Character_Panels/build_all_character_panel.py`
- `Character_Panels/run_full_pipeline.py`
- `tests/test_timing.py`
- `docs/gkx/`
- `scripts/`
- `Green_SAS_Replication/`
- local ignored generated outputs under `outputs/`
- local ignored supplementary/reference files under `Supplementary_assistive_files/`

## Repository Understanding

The repository is intended to build WRDS-based asset-pricing characteristics for return prediction.

The current root pipeline is a broad production/research pipeline. It builds Green-style characteristics, adds HXZ/Fama-French-style variants, merges monthly signal panels, attaches future returns, and can create a ranked 1957+ research panel.

The current stated strategic goal is narrower and more sequential:

1. Replicate Green SAS exactly first.
2. Validate against Green's provided `.sas7bdat` output.
3. Only after that, modify and compare toward GKX `datashare.csv`.

There is also a newer `Green_SAS_Replication/` folder. It is structurally coherent and appears designed as an isolated direct Green SAS replication. However, the user-provided context says this folder was recently created, may be out of scope, and may be deleted. If retained, it should be treated deliberately as the authoritative Green-replication path rather than as a side experiment.

## Extra, Temporary, Duplicated, Or Out-Of-Scope Files

### Large Ignored Local Outputs

The working tree contains many large generated files that are ignored by Git but take substantial disk space and make local inspection noisy.

Examples:

- `outputs/panels/all_character_signal_panel.csv`: about 4.6 GB
- `outputs/panels/research_panel_1957_ranked.csv`: about 4.0 GB
- `outputs/panels/complete_all_character_prediction_panel.csv`: about 3.5 GB
- `outputs/diagnostics/green_comparable_temp.csv`: about 2.5 GB
- `outputs/diagnostics/green_comparable_temp2_winsorized.csv`: about 2.4 GB
- `outputs/diagnostics/green_vs_gkx/gkx_panel_cache.pkl`: about 2.5 GB
- `outputs/diagnostics/green_vs_gkx/green_panel_cache.pkl`: about 1.7 GB
- many `outputs/characteristics/individual/*.csv` files over 100 MB

These are mostly correctly ignored by `.gitignore`, but a future cleanup pass should decide what to archive externally and what can be safely regenerated.

### Python Caches

There are many `__pycache__/` folders across:

- repository root
- `Character_Builders/`
- `Character_Panels/`
- `Green_SAS_Replication/`
- `Imputation/`
- `Return_Builders/`
- `scripts/`
- `tests/`

They are ignored and should not be committed.

### Green_SAS_Replication Generated Files

`Green_SAS_Replication/outputs/` contains local parquet outputs and checkpoints, including:

- `Green_SAS_Replication/outputs/rpsdata_green_replication.parquet`
- `Green_SAS_Replication/outputs/checkpoints/*.parquet`

These are ignored by `Green_SAS_Replication/.gitignore`, but they are still local generated artifacts.

### Untracked But Potentially Important Files

There are 13 untracked but not ignored files. They appear important and should not be dismissed as junk without review:

- `docs/gkx/datashare_columns_green_benchmark_mapping.md`
- `docs/gkx/datashare_columns_green_validation.md`
- `docs/gkx/gkx_chatoia_repo_vs_green_audit.md`
- `docs/gkx/green_timing_validation_2010_2015.md`
- `docs/gkx/green_timing_validation_2010_2015_debug.md`
- `scripts/audit_chatoia_repo_vs_green.py`
- `scripts/build_datashare_green_mapping.py`
- `scripts/compare_green_vs_gkx_datashare.py`
- `scripts/debug_green_timing_validation.py`
- `scripts/rebuild_full_history_annual_csvs.py`
- `scripts/rebuild_green_formula_fixes.py`
- `scripts/rebuild_quarterly_special_formula_fixes.py`
- `scripts/validate_green_timing_2010_2015.py`

These files seem more aligned with the current Green-first policy than some older tracked docs. A future agent should decide whether to commit them, move them to an archive, or consolidate them into a cleaner audit system.

## Main Issues And Risks

### 1. Root Pipeline Does Not Default To Exact Green

The README states that exact Green SAS replication is the primary setup, but the root pipeline defaults are not exact Green.

In `Character_Builders/_shared/ccm.py`, the default CCM rule is:

```text
DEFAULT_CCM_LINKTYPES = ("LU", "LC")
DEFAULT_CCM_LINKPRIM = ("P", "C")
```

Green SAS uses a broader set:

```text
LU, LC, LD, LF, LN, LO, LS, LX
```

The README documents how to approximate Green by passing flags, but this means exact Green is optional rather than the default. That conflicts with the current strategy of exact Green first.

### 2. Isolated Green Validation Report Is Not Currently Meaningful

`Green_SAS_Replication/diagnostics/green_replication_validation.md` reports:

```text
paired_panel_rows = 0
python_rows = 36943
green_rows = 0
merged_keys = 0
```

Every variable-level comparison is effectively `nan`.

This report cannot support any claim of successful Green replication. It suggests that the validation window, benchmark loading, date filtering, or benchmark coverage logic needs immediate attention.

### 3. Validation Code Has A Fragility / Bug

In `Green_SAS_Replication/modules/validation.py`, `run_validation()` references `green.columns` while constructing `compare_cols`, before `green` is loaded.

Problematic logic:

```python
and (pd.api.types.is_numeric_dtype(py[c]) or c in green.columns)
```

This may be masked for numeric columns because of Python short-circuiting, but it is still unsafe and can fail if nonnumeric compared columns appear.

### 4. IBES Unavailability Prevents Exact Green For Some Variables

The isolated Green replication explicitly says direct IBES WRDS tables are not used and IBES columns are retained as missing or stubbed.

This is appropriate given current IBES access limitations, but it means the project should not claim full exact Green replication for IBES-dependent variables. Instead, those variables should be separated into:

- Green-exact where possible without IBES
- Green schema-compatible but value-missing
- Compustat fallback/proxy
- unavailable until IBES access is restored

### 5. Documentation And Implementation Disagree On Some Daily Variables

`Character_Builders/CHARACTER_CATALOG.md` describes several daily-CRSP variables as rolling 3-month measures.

Examples:

- `baspread`: rolling 3 months
- `ill`: rolling 3 months
- `maxret`: rolling 3 months
- `std_dolvol`: rolling 3 months
- `std_turn`: rolling 3 months
- `zerotrade`: rolling 3 months

But `Character_Builders/_shared/green_builders.py` describes and computes them as rolling/current calendar-month aggregates:

```python
DATE_TRUNC('month', date)::date AS month_start
GROUP BY permno, DATE_TRUNC('month', date)::date
```

This may be correct for some Green definitions, but the docs and code should agree. A future agent should verify against `Greens_code.sas` before changing code.

### 6. Output Path Documentation Is Inconsistent

The newer code uses organized output paths:

```text
outputs/characteristics/individual/
outputs/panels/
outputs/logs/
outputs/diagnostics/
```

But some docs still refer to older flat paths:

```text
outputs/book_to_market.csv
outputs/mvel1.csv
outputs/all_character_signal_panel.csv
outputs/research_panel_1957_ranked.csv
outputs/complete_prediction_panel.csv
```

Examples appear in:

- `Character_Panels/README.md`
- individual HXZ builder READMEs
- some sections of root `README.md`

This can break reproducibility for a fresh clone because users may run commands that write to or expect the old layout.

### 7. Dependency Reproducibility Is Incomplete

Root `requirements.txt` contains:

```text
pandas==2.3.3
numpy==2.4.1
wrds==3.4.0
tqdm==4.67.1
```

But multiple root scripts import `pyreadstat`, and some reports use `to_markdown`, which requires `tabulate`.

The isolated `Green_SAS_Replication/requirements.txt` includes:

```text
pyreadstat
pyarrow
tabulate
```

This split means a fresh clone using only root `requirements.txt` may fail when running validation/audit scripts.

There is also a documentation conflict: root README says not to pin `wrds`, while root `requirements.txt` pins `wrds==3.4.0`.

### 8. Datashare Target Universe Is Not Fully Implemented

The newer untracked validation doc reports that several datashare predictors are missing from the repo:

- `aeavol`
- `chmom`
- `idiovol`
- `indmom`
- `ms`
- `pricedelay`
- `roavol`
- `roeq`
- `sic2`
- `stdacc`
- `stdcf`

The same doc flags below-threshold Green validation for:

- `ear`
- `beta`
- `betasq`
- `operprof`
- `pchcapx_ia`
- `nincr`

This is not necessarily bad, but it should be made explicit in the main status docs.

### 9. Some Builder READMEs Say "Scaffolded" Despite Implementations Existing Elsewhere

Several individual `Green_*_Generalized/README.md` files still say:

```text
Status: Scaffolded; this character requires a specialized event, IBES, quarterly, or factor-estimation routine before it can be used.
```

Some of these variables are now implemented through shared builders or specialized modules. The documentation status is stale in places.

Examples to check carefully:

- quarterly builders such as `chtx`, `cinvest`, `nincr`, `roa1`, `rsup`, `sue`
- special builders such as `beta`, `rvar_capm`, `rvar_ff3`, `re`
- monthly builders such as `seas1a`

### 10. Encoding / Mojibake In Documentation

Several Markdown files contain mojibake such as:

```text
Ã¢â‚¬â€
Ã¢â€ â€™
Ã¢â€°Â¥
ÃÂ
Ãƒâ€”
```

This affects readability and makes reports look less reliable. It appears in root README and multiple docs under `docs/gkx/`.

### 11. Test Coverage Is Narrow

Current tests focus mainly on annual timing in `tests/test_timing.py`.

Missing test coverage includes:

- Green benchmark loading
- validation merge keys
- output schema checks
- datashare alias mapping
- CCM default/profile checks
- Green exact profile behavior
- formula spot checks
- generated panel column counts
- missing variable inventory

## Conflicts With The Main Goal

The biggest conflict is conceptual:

- The root pipeline is a broad research panel builder.
- The current project priority is exact Green SAS replication first.
- `Green_SAS_Replication/` appears closer to that priority, but its validation is currently not functioning.
- The root pipeline can approximate Green in many places, but defaults and docs still mix Green, HXZ, GKX, conservative CCM, research ranking, and legacy workflows.

For the current goal, this repo should have a clear Green-first path that is separate from:

- HXZ/Fama-French variants
- GKX/datashare comparison
- final ranked machine-learning panel construction
- exploratory diagnostics
- legacy flat-output workflows

## Recommended Next Actions

### Priority 1: Decide The Authoritative Green Path

Decide whether exact Green replication should live in:

1. `Green_SAS_Replication/`, or
2. the root `Character_Builders` / `Character_Panels` pipeline with a `--profile green_exact` style configuration.

Avoid maintaining two competing Green pipelines unless their responsibilities are very clearly separated.

### Priority 2: Fix Green Validation Before More Formula Work

The Green validation report currently has zero Green rows and zero paired rows. Fix this first.

Recommended checks:

- confirm the benchmark `.sas7bdat` date range
- confirm date type and date filtering
- confirm `permno x date` merge keys
- fix the `green.columns` pre-definition bug
- generate a small validation window with nonzero Green and Python rows
- require validation summary to fail loudly when benchmark rows are zero

### Priority 3: Define A Green-Exact Profile

A Green-exact profile should explicitly control:

- CCM linktypes
- share/exchange filters
- Compustat annual filters
- quarterly timing
- annual rolling timing
- daily/monthly calculation windows
- winsorization
- IBES policy
- final filter rules
- output schema and names

This should be runnable with one obvious command.

### Priority 4: Separate Benchmark Policy From Production Policy

Recommended policy:

- Green `.sas7bdat`: primary value/timing benchmark
- GKX `datashare.csv`: target export column universe and later comparison target
- HXZ/Fama-French: separate alternate convention family

This policy is already present in some newer untracked docs and should be made the central repo narrative.

### Priority 5: Clean Documentation

Documentation cleanup should address:

- old flat output paths
- stale "scaffolded" statuses
- mojibake
- unclear Green vs GKX vs HXZ scope
- inconsistent dependency instructions
- unclear status of `Green_SAS_Replication/`

### Priority 6: Rationalize Untracked Files

The 13 untracked scripts/docs appear useful. Decide whether to:

- commit them as current audit infrastructure,
- consolidate them into fewer scripts,
- move exploratory ones to an archive folder,
- or delete them after extracting useful findings.

### Priority 7: Add Minimal Reproducibility Tests

Add tests that do not require full WRDS downloads:

- output path resolution
- annual timing windows
- Green benchmark loader on metadata or small row sample
- datashare-to-Green alias mapping
- required dependency imports
- validation behavior when benchmark rows are zero
- profile/default configuration checks

### Priority 8: Clean Local Generated Artifacts After Review

Only after preserving anything needed, consider cleaning:

- `outputs/diagnostics/*temp*`
- large panel CSVs
- pickle caches
- parquet checkpoints
- `__pycache__/`

Do not delete reference files under `Supplementary_assistive_files/` unless the user explicitly confirms.

## Suggested Handoff For The Next Agent

Start with the Green validation failure. Do not begin by rewriting formulas. The repository already has many formulas that validate well in newer docs, but the isolated Green validation report is broken and the project needs a trustworthy benchmark loop.

Recommended first concrete task:

1. Inspect `Green_SAS_Replication/modules/validation.py`.
2. Fix the premature `green.columns` reference.
3. Verify the benchmark `.sas7bdat` date range and column names.
4. Run a tiny validation window known to overlap Green output.
5. Ensure the report fails clearly if `green_rows == 0`.
6. Only then compare variable-level results and prioritize formulas.

After that, decide whether `Green_SAS_Replication/` should be kept and promoted, or removed in favor of a Green-exact root profile.

