# Task 03 — Pipeline presets module (configurable, not hard-coded)

**Priority:** High  
**Run on:** Local  
**Depends on:** nothing  

## Objective

Add a single configuration module so users pick a **profile** instead of memorizing many flags.
Datashare-like behavior must be a preset, not baked into builders.

## Create

New file: `pipeline_config.py` (repo root, next to `output_paths.py`) or `Character_Panels/pipeline_config.py`.

Define dataclass or dict **profiles**:

### `--profile green` (default for Green replication)

- CCM: Green linktypes (`LU,LC,LD,LF,LN,LO,LS,LX`), no linkprim filter (match `load_ccm_links_green`)
- Annual timing: Green rolling (existing `timing.py`)
- Quarterly timing: Green (existing `quarterly_builders.py`)
- Panel universe screen: optional `--green-universe` (joint bm, mom1m, mve)
- Sample: allow full history; Green SAS output comparison often 1980+
- Build: all Green characters + optional HXZ (document as separate columns)

### `--profile datashare`

- Same formulas as today; mapping for comparison:
  - datashare `bm` ↔ repo `book_to_market`
  - datashare `operprof` ↔ repo `operating_profitability`
  - datashare `cfp` ↔ repo Green `cfp`
- CCM: document default (LU,LC + P,C) unless evidence says otherwise; expose overrides
- Annual timing: FF-June for HXZ stems (already in `timing.py`)
- **No** Green joint universe screen on panel
- **Sparse panel** behavior: outer merge keeps rows even when one char missing
- Sample start: **1957-01-01** (or earliest CRSP) for WRDS pulls where supported
- Do **not** build or require `bm_ia`

### `--profile research`

- Existing research panel path: winsorize, FF49 impute, rank to [-1,1]
- Document in config only; wiring in task 04

Expose function: `resolve_config(profile: str, cli_overrides: dict) -> PipelineConfig`

CLI overrides must still work: `--ccm-linktypes`, `--ccm-linkprim`, `--green-universe`,
`--sample-start`, `--sample-end`, `--skip-ibes`, `--workers`.

## Do NOT

- Change formulas inside `green_builders.py` / HXZ builders.
- Hard-code datashare filters inside builder math.

## Acceptance checks

```bash
python -c "from pipeline_config import resolve_config; c=resolve_config('datashare',{}); print(c)"
python -c "from pipeline_config import resolve_config; c=resolve_config('green',{}); print(c)"
```

## Codex prompt

```
Read codex/tasks/03_pipeline_presets.md and docs/methodology/00_overview.md.

Implement pipeline_config.py with profiles: green, datashare, research.
Each profile sets CCM defaults, timing notes, universe screen behavior, sample start,
and which HXZ/Green outputs matter for datashare (bm, operprof, cfp only; bm_ia out of scope).

Allow CLI overrides to merge on top of the profile.
Do NOT modify character formulas in green_builders.py or HXZ builders.
Add minimal unit test or import smoke test.
Document profile fields in module docstring.
```
