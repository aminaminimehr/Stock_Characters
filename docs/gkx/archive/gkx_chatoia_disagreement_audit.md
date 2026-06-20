# GKX `chatoia` disagreement audit

Window: `signal_yyyymm` **201801**–**202312**.

Goal: explain near-zero on-disk repo vs datashare agreement despite large paired coverage.

**No formula changes made in this audit.**

## Executive summary

| Finding | Detail |
| --- | --- |
| Formula | Green `chatoia = chato - mean(chato)` by **SIC2×fyear** is **correct** |
| Datashare match (fresh compute) | Spearman **0.775**, winsor Pearson **0.713**, median \|diff\| **0.017** |
| On-disk `chatoia.csv` match | Spearman **0.060**, median \|diff\| **924** |
| Root cause | **`age_lookup` / `orgcap_lookup` merges** in `build_character()` corrupt values before industry demean |
| Alternative definitions | None beat Green `chatoia` once build path is clean; not a GKX-vs-Green naming issue |

---

## Datashare column identity

- GKX datashare exposes **`chatoia` only** (no `chato` or `ato` columns).
- Description: *Industry-adjusted change in asset turnover* (`docs/gkx/datashare_inventory.md`).
- Green SAS: `chatoia = chato - mean(chato)` by **`sic2, fyear`** after `count<3` nulling.
- Dacheng/Xiu exports **`chato`** (permno lags) but **not `chatoia`** (Phase 7 audit).

### Datashare scale (201801–202312)

| Stat | Value |
| --- | ---: |
| Non-null | 190,718 |
| Median | 0.00137 |
| Mean | 0.00418 |
| P95 \|value\| | 0.337 |

Scale mismatch (×100 / ×1000) does **not** explain disagreement — Spearman is scale-invariant.

---

## Decomposition: `chato`, industry mean, `chatoia`

Fresh WRDS compute **without** age/orgcap lookups, June expansion vs datashare:

| Component | Repo monthly non-null | Paired | Pearson | Spearman | Winsor P | Median \|diff\| |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `chato` (raw Green) | 189,754 | 185,679 | 0.214 | 0.633 | 0.737 | 0.027 |
| `chato` industry mean | 217,537 | 187,742 | −0.131 | −0.189 | −0.146 | 0.073 |
| `chatoia` (fresh compute) | 194,208 | 187,198 | 0.235 | **0.775** | 0.713 | **0.017** |
| `chatoia` (**on-disk CSV**) | 282,410 | 169,375 | 0.008 | **0.060** | 0.012 | **924** |

Identity check: `chatoia = chato - mean(chato)` holds exactly (max \|diff\| = 0).

---

## Ranked candidate definitions (June expansion, scale=1)

Fresh compute path (no lookup corruption):

| Rank | Candidate | Paired | Pearson | Spearman | Winsor P | Median \|diff\| |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | `chato_permno_ia_sic2_fyear` | 185,502 | 0.230 | 0.825 | 0.825 | 0.006 |
| 2 | `chatoia_green_pre_mask` | 185,679 | 0.235 | 0.777 | 0.717 | 0.017 |
| 3 | `ato_diff_ia_sic2_fyear` | 185,679 | 0.235 | 0.777 | 0.717 | 0.017 |
| 4 | **`chatoia_repo_official`** | 187,198 | 0.235 | **0.775** | **0.713** | **0.017** |
| 5 | `chatoia_ff49_datadate` | 185,679 | 0.224 | 0.694 | 0.682 | 0.025 |
| 6 | `ato_diff_gvkey` (simple Δato) | 186,803 | 0.215 | 0.633 | 0.737 | 0.027 |
| 7 | `chato_green` (raw) | 185,679 | 0.214 | 0.633 | 0.737 | 0.027 |
| 8 | `ato_pct_gvkey` (%Δato) | 180,517 | 0.016 | 0.572 | 0.384 | 0.072 |
| 9 | `ato_ia_sic2_fyear` (level) | 187,697 | 0.020 | 0.011 | 0.017 | 0.263 |
| — | **`chatoia_on_disk_csv`** | 169,375 | 0.008 | **0.060** | 0.012 | **924** |

**Conclusion:** Green `chatoia` matches datashare well. Simple `ato_t − ato_{t-1}`, percent change, FF49×datadate demean, and permno-lag variants do **not** materially outperform Green once the build path is clean. The on-disk CSV is the outlier.

---

## Root cause: lookup merge corrupts `chatoia`

`build_character('chatoia')` calls `compute_annual_characters()` with:

- `age_lookup=load_annual_age_lookup(db)` — full-history age
- `orgcap_lookup=load_annual_orgcap_lookup(db)` — full-history orgcap

Those tables merge on `(gvkey, datadate)` **before** the `chato` / `chatoia` industry-demean block (L551–580 in `green_builders.py`), misaligning fiscal rows.

| Build path | Annual `chatoia` median | Max \|value\| | vs datashare Spearman |
| --- | ---: | ---: | ---: |
| No lookups | **0.0015** | ~189 | **0.775** |
| With age lookup only | −105 | ~46M | corrupted |
| With orgcap lookup only | −105 | ~46M | corrupted |
| `build_character` (both) | −115 | ~23M | **0.060** (on-disk) |

On-disk `chatoia.csv` (213,837 rows) was produced through the corrupted path. Correlation between on-disk and fresh compute on matching keys: **ρ ≈ 0**.

This is an **implementation / build-path bug**, not a Green formula bug.

---

## Timing conventions

June expansion (current) is correct. Shifts degrade agreement except small +1 month (Spearman 0.814). `datadate+4` forward-fill is slightly weaker (Spearman 0.754).

| Timing | Spearman (`chatoia` fresh) |
| --- | ---: |
| June expand (baseline) | 0.775 |
| datadate + 4mo ffill | 0.754 |
| June shift +1 month | 0.814 |
| June shift −12 months | 0.121 |

---

## Scale / denominator diagnostics

- Datashare median **0.0014** aligns with fresh Green `chatoia` median **0.0012**.
- On-disk median **−99** and 38k rows with \|value\| > 1000 are **inconsistent** with industry-adjusted turnover.
- Near-zero denominators affect tails but winsorized Pearson (0.713 fresh vs 0.012 on-disk) confirms the on-disk file is wrong, not merely outlier-prone.

---

## Recommendation

1. **Keep** the Green `chatoia` formula — it matches GKX datashare when built correctly.
2. **Fix** the `age_lookup` / `orgcap_lookup` merge bug (move merges after industry chars, or dedupe lookups) and **rebuild** `chatoia.csv` + panels — **separate fix, not in this commit**.
3. **Do not** add an optional GKX-aligned variant; no evidence datashare uses a different definition.
4. **Do not** implement new GKX predictors until `chatoia` rebuild is corrected.

---

## Resolution (2026-06-15)

**Fix commit:** `4a3fd82` — moved `orgcap_lookup` / `age_lookup` merges and `ps` **after** the SIC2×fyear industry-demean block in `compute_annual_characters()`.

**Rebuild:** `chatoia.csv` (233,644 annual rows, median **0.0012**) and both panels refreshed.

| Benchmark | Before (corrupted on-disk) | After fix |
| --- | ---: | ---: |
| vs datashare Spearman (201801–202312) | **0.060** | **0.775** |
| vs datashare median \|diff\| | **924** | **0.017** |
| vs Green SAS Spearman | n/a | **0.828** |
| vs Green SAS median \|diff\| | n/a | **0.00081** |
| With-lookup vs no-lookup (annual) | ~0 | **1.0** |

Only `chato` / `chatoia` were corrupted on the old path; other Phase 7 `_ia` variables and lookup-sourced `age` / `orgcap` / `ps` were unaffected.

Full validation: `docs/gkx/gkx_chatoia_lookup_fix_validation.md` (`scripts/validate_chatoia_lookup_fix.py`).

---

Generated by `scripts/audit_gkx_chatoia_disagreement.py`.
