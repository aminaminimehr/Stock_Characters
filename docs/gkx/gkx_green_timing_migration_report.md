# Green timing migration — final report

**Date:** 2026-05-29  
**Phase scope:** Timing conventions and formula-source policy only (no new GKX predictors).

---

## Summary

Green-derived **annual** characteristics now use **Green SAS rolling monthly timing** at panel merge instead of June flat expansion. HXZ/Fama-French standalone variables retain **June** timing. **No book-equity formula changes** were made in this phase.

---

## Variables by timing convention (after migration)

| Convention | Variables | Panel function |
|------------|-----------|----------------|
| **Green annual rolling** | 72 Green `ANNUAL_CHARACTER_INFO` names | `expand_annual_file_green` |
| **HXZ June** | `book_to_market`, `cash_flow_to_price`, `operating_profitability`, `bmj` | `expand_annual_file_june` |
| **Monthly native** | Quarterly (8), monthly CRSP (10), daily-rolled (7), beta/abr/re/rvar (6) | none (builder emits `signal_yyyymm`) |

Full list: `docs/gkx/gkx_green_timing_migration_audit.md`.

---

## Formula decisions (deferred)

| Variable | Decision |
|----------|----------|
| `bm`, `bm_ia`, `cfp`, `cfp_ia` | **Keep Green formulas** (`ceq/mve_f`, industry demean) |
| `book_to_market`, `cash_flow_to_price` | **Keep HXZ/FF** (parallel columns) |
| Book-equity fallback | **No change** — Green uses raw `ceq`; HXZ uses FF hierarchy in separate builders |

---

## Validation vs Green SAS (`201801–202312`)

Compared monthly `permno × DATE` on pre-winsor repo builders vs `Output_From_Greens_SAS_code.sas7bdat`:

| Variable | Green timing Spearman | June legacy Spearman | Paired (Green timing) |
|----------|----------------------:|---------------------:|----------------------:|
| chatoia | **0.9982** | 0.8278 | 183,084 |
| cfp_ia | **0.9853** | 0.9100 | 135,298 |
| bm | **0.9996** | 0.9748 | 183,938 |
| bm_ia | **0.9870** | 0.9140 | 183,938 |
| invest | **0.9977** | 0.8503 | 100,599 |
| age | **0.9998** | 0.9989 | 135,310 |
| absacc | **0.9999** | 0.9137 | 102,843 |
| orgcap | n/a | n/a | 0 (missing in Green window) |

Full metrics: `docs/gkx/gkx_green_timing_migration_validation.md`.

**GKX reconciliation:** Monthly alignment with Green SAS improves from ~0.83 (June) to ~0.99+ for representative `_ia` and level variables. Remaining gaps are primarily **Green post-merge winsorization** (not replicated in builders) and **quarterly `datadate` labeling** in Green output.

**Datashare:** Re-validate GKX datashare after panel rebuild; timing migration targets Green SAS, not datashare June convention.

---

## Infrastructure added

| File | Role |
|------|------|
| `Character_Panels/timing.py` | `TimingConvention`, `expand_annual_file_green`, `expand_annual_file_june` |
| `Character_Panels/build_all_character_panel.py` | Routes stems via `classify_stem`; `--legacy-june-annual` flag |
| `scripts/validate_green_timing_migration.py` | Green vs June comparison report |
| `tests/test_timing.py` | Unit tests for window bounds and dedupe |

---

## Legacy behavior

```bash
python Character_Panels/build_all_character_panel.py --legacy-june-annual
```

Restores June flat expansion for **all** annual CSVs (including Green annual).

---

## Risks / unresolved

1. Green quarterly timing in SAS (`date−10` … `date−5` months) ≠ repo quarterly `merge_asof` — not migrated.
2. Green SAS output winsorizes many variables monthly; repo builders do not.
3. `orgcap` not observable in Green SAS 2018–2023 window.
4. Panel rebuild required locally after pulling this change (`build_all_character_panel.py`).

---

## Commit

*To be filled after git push.*
