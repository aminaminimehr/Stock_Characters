# Reverse-engineering `datashare.csv` for `bm`, `bm_ia`, `operprof`, and `cfp`

Date: 2026-06-19

Goal: identify how the four public `datashare.csv` columns are constructed, using local builders and
WRDS-backed replications. The important result is that the first GKX/Xiu-style hypothesis was
tested and rejected for this local `datashare.csv`; three of the four columns are best explained by
existing repo-style builders.

## Executive Summary

| `datashare.csv` column | Best current explanation | Validation evidence | Status |
|---|---|---:|---|
| `bm` | HXZ/Fama-French annual book-to-market: book equity over December CRSP market equity, June availability | pooled rho 0.959, exact 64.1% | Mostly solved |
| `operprof` | HXZ operating profitability: `(revt - cogs - xsga0 - xint0) / book_equity`, June availability | pooled rho 0.952, exact 66.4% | Mostly solved |
| `cfp` | Green cash-flow-to-price: `oancf / mve_f`, with accrual fallback when `oancf` is missing | full-history scratch rebuild median rho 0.9988, pooled rho 0.9951, exact 97.9% | Solved |
| `bm_ia` | Not solved. It is not reproduced by the tested Xiu, HXZ, Green, FF, SIC, value-weighted, median, timing-offset, or monthly winsorized variants | best full-grid variant median rho 0.8321 | Unresolved |

## Rejected Initial Hypothesis

The earlier working hypothesis was:

1. port GKX/Xiu `accounting_60.py`,
2. use CRSP current-month market equity,
3. use annual accounting at `datadate + 4` months,
4. use quarterly accounting at `datadate + 3` months,
5. blend annual and quarterly values by most recent `datadate`,
6. compute `bm_ia` by FF49 industry demeaning.

That builder was implemented in `Character_Builders/GKX_datashare/build_datashare_chars.py` and
validated against the local `Supplementary_assistive_files/datashare.csv`. It does not match:

| Column | Median monthly rho | Pooled rho | Exact <= 1e-4 | Paired obs |
|---|---:|---:|---:|---:|
| `bm` | 0.8169 | 0.7971 | 0.14% | 2,536,031 |
| `bm_ia` | 0.3069 | 0.2474 | 0.01% | 2,515,849 |
| `operprof` | 0.8734 | 0.8571 | 20.53% | 2,321,033 |
| `cfp` | 0.1120 | -0.0177 | 0.07% | 2,355,019 |

The poor `cfp` result is especially decisive: public `datashare.csv` behaves like the repo's Green
`cfp`, not like `(ib + dp) / current CRSP me`.

## Column Findings

### `bm`

The public `bm` column is best explained by the repo's HXZ/Fama-French-style `book_to_market`.

Formula family:

```text
ps = first nonmissing of pstkrv, pstkl, pstk, else 0
stockholders_equity = seq, else ceq + ps, else at - lt
book_equity = stockholders_equity + txditc0 - ps
bm = (book_equity * 1000) / December CRSP permco market equity
```

Timing:

```text
Fiscal year ending in calendar year y is used from June y+1 through May y+2.
```

Evidence:

- `book_to_market` vs public `bm`: pooled Spearman 0.959337, exact match 64.12%.
- For checked examples, public `bm` is held constant across the June/July-to-next-May window, which
  rejects the current-month market-equity hypothesis.
- Example: `permno = 25160` has public `bm = 1.303222` from 1962-07 through 1963-06, matching the
  repo's annual `book_to_market`, not the current-month CRSP-ME GKX port.

Residual differences are likely from link-history, universe, delisting/security filters, or small
definition differences around legacy Compustat/CRSP records.

### `operprof`

The public `operprof` column is best explained by the repo's HXZ-style
`operating_profitability`.

Formula family:

```text
ps = first nonmissing of pstkrv, pstkl, pstk, else 0
stockholders_equity = seq, else ceq + ps, else at - lt
book_equity = stockholders_equity + txditc0 - ps
operprof = (revt - cogs - xsga0 - xint0) / book_equity
```

Timing:

```text
Fiscal year ending in calendar year y is used from June y+1 through May y+2.
```

Evidence:

- `operating_profitability` vs public `operprof`: pooled Spearman 0.951927, exact match 66.39%.
- Example: `permno = 25160` public `operprof = 0.149212` in 1963-07, exactly matching the repo's
  annual `operating_profitability` for that signal month.
- The first-pass GKX/Xiu annual-quarterly blend is directionally related but materially worse.

### `cfp`

The public `cfp` column is best explained by the repo's Green-style `cfp`, not HXZ
`cash_flow_to_price` and not the GKX/Xiu `(ib + dp) / me` candidate.

Formula family used by the Green builder:

```text
mve_f = prcc_f * csho
cfp = oancf / mve_f, when oancf is available
cfp = (ib - working_capital_accrual) / mve_f, otherwise
```

Evidence over the repo's available `cfp` history:

- repo/Green `cfp` vs public `cfp`: pooled Spearman 0.998197, exact match 98.17%.
- HXZ `cash_flow_to_price` vs public `cfp`: pooled Spearman about 0.187, rejected.
- GKX/Xiu `(ib + dp) / current CRSP me`: pooled Spearman -0.0177, rejected.

Note: the current local Green `cfp.csv` starts in 1975 because the Green Compustat query uses a
1975 start date. Public `datashare.csv` has earlier `cfp` values. Extending the Green query backward
should be the first thing to try if full-history `cfp` replication is needed.

2026-06-20 update: this was tested with
`scripts/rebuild/rebuild_green_cfp_full_history.py`, changing only the Compustat start date to
1959-01-01 and keeping the Green `cfp` formula unchanged. Scratch outputs:

- `outputs/characteristics/datashare_style/green_cfp_full_history_annual.csv`
- `outputs/characteristics/datashare_style/green_cfp_full_history.csv`
- `outputs/diagnostics/cfp_full_history_validation.txt`

Best alignment is `signal_yyyymm` with no shift:

| Metric | Value |
|---|---:|
| Median monthly Spearman | 0.998770 |
| Pooled Spearman | 0.995132 |
| Exact <= 1e-4 | 97.92% |
| Paired observations | 2,690,126 |
| Pre-1975 paired observations gained | 109,388 |

The existing `outputs/characteristics/individual/cfp.csv` was left untouched.

### `bm_ia`

`bm_ia` is unresolved.

Rejected variants include:

| Candidate | Result |
|---|---|
| First-pass GKX/Xiu `bm_ia` by FF49 and annual/quarterly blend | median monthly rho 0.3069 |
| HXZ `book_to_market` demeaned by month and SIC2 | median monthly rho about 0.416 |
| HXZ `book_to_market` demeaned by annual date and SIC2 | median monthly rho about 0.416 |
| HXZ `book_to_market` demeaned by FF49 | median monthly rho about 0.36-0.38 |
| Exact SIC and SIC3 demeaning variants | poor, below the solved columns by a wide margin |
| Green `bm_ia` | poor against public `datashare.csv`, despite matching Green SAS |
| Public `bm - mean(public bm)` by `DATE x SIC2` | pooled rho about 0.796, exact 17.8%; not enough |

2026-06-20 update: a logged grid was run with
`scripts/experiments/run_bm_ia_experiments.py --full-grid`. Results were written to:

- `outputs/diagnostics/bm_ia_experiments/results.csv`
- `outputs/diagnostics/bm_ia_experiments/best_per_decade.csv`
- `outputs/characteristics/datashare_style/bm_ia_best_candidate.csv`

The grid covered 364 candidates across:

- input: public `bm`, repo `book_to_market` with June timing, repo `book_to_market` with Green rolling
  timing, raw annual repo `book_to_market`;
- grouping time: monthly, June cohort, annual datadate year;
- industry: SIC2, SIC3, FF12, FF17, FF30, FF48, FF49;
- statistic: mean and median;
- weighting: equal and value-weighted where weights were available;
- monthly benchmark offsets: -1, 0, +1.

Best candidate:

```text
bm_ia_hat = public bm - mean(public bm) by month x SIC2
universe = published datashare rows
stat = equal-weight mean
month shift = 0
```

Best metrics:

| Metric | Value |
|---|---:|
| Median monthly Spearman | 0.832090 |
| Pooled Spearman | 0.790613 |
| Exact <= 1e-4 | 8.03% |
| Paired observations | 3,042,589 |
| Median absolute difference | 0.172042 |
| 95th percentile absolute difference | 8.604244 |

Per-decade median monthly Spearman for the best candidate:

| Decade | Median rho |
|---|---:|
| 1960s | 0.8404 |
| 1970s | 0.8617 |
| 1980s | 0.6371 |
| 1990s | 0.7193 |
| 2000s | 0.8238 |
| 2010s | 0.9016 |
| 2020s | 0.9291 |

Additional checks:

- Direct public datashare `bm_ia` vs Green SAS `bm_ia` is poor: median monthly Spearman about 0.244
  in `Supplementary_assistive_files/green_vs_gkx_comparison/csv/characteristic_comparison_summary.csv`.
- Monthly 1/99 winsorization of the best candidate does not improve it materially.
- Green `bm_ia` with Green timing and monthly 1/99 winsorization remains poor against public
  datashare (`~0.23` median monthly Spearman).
- Grep found only the known Green SAS and GKX/Xiu generators. Green uses SIC2 x fyear mean
  demeaning followed by monthly winsorization; GKX/Xiu uses FF49 x datadate demeaning. Both are
  rejected for this public `datashare.csv`.

Important diagnostic:

- For `permno = 25160`, public `bm` is constant across the annual holding window, but implied
  industry benchmark `bm - bm_ia` changes inside that window. This means public `bm_ia` is not a
  simple annual fixed demeaning of the public `bm` column.

Current inference:

`bm_ia` probably uses an industry benchmark built from a different intermediate universe, industry
classification, or timing convention than the published `bm` values. It should not be treated as
solved by applying a simple industry mean to the public `bm`.

2026-07-09 update: RESOLVED via the implied-adjustment diagnostic (Dr. Qin's suggestion).
Scripts: `scripts/audits/audit_bmia_implied_adjustment.py`,
`audit_bmia_industry_fingerprint.py`, `audit_bmia_benchmark_recovery.py`,
`audit_bmia_reconstruction_check.py`. Outputs in `outputs/diagnostics/bmia_*`.

Method: define `implied := bm - bm_ia` (the industry benchmark each firm actually received).
If `bm_ia = bm - mean(bm)` over some grouping, `implied` must be identical for all firms in a cell.

Findings:

1. Grouping is **SIC2 x calendar month** (monthly recomputation), not FF49 x datadate:
   - within (month, sic2): 44.4% of cells exactly constant (<1e-6), cell-mean R^2 = 0.958;
   - within (year, sic2): 1.2% constant, R^2 = 0.698 -> annual cohorts rejected;
   - month-only / year-only: R^2 < 0.08 -> rejected;
   - ~62-66 distinct benchmark values per month (SIC2 granularity; FF49 would give <= 49;
     FF12/17/30/38/48/49 ambiguity fingerprints all fail, agreement <= 59%).
2. The benchmark is the **equal-weight mean of the published bm itself**: in cells with no
   misassigned firms the recovered benchmark equals the in-cell mean of published `bm`
   exactly (45.2% of cells; median benchmark/mean ratio = 1.000 in every decade).
3. **97.09% of firm-months sit exactly on their cell's modal benchmark.** The remaining 2.91%
   carry a different benchmark; ~19.5% of those exactly match ANOTHER sic2's benchmark the same
   month -> their construction-time SIC differs from the published `sic2` (SIC vintage issue).
4. The monthly-CRSP-ME mechanism from `accounting_60.py` (`bm_ia_t = be/me_t - const`) is
   rejected: within constant-`bm` windows, `bm_ia` is NOT linear in 1/mvel1 (median R^2 ~ 0.21-0.25).
5. Reconstruction check (five-metric):
   - `bm - mean(published bm)` by (sic2, month): median monthly Spearman 0.8323, exact 17.5%;
   - `bm - modal implied benchmark` by (sic2, month): **median monthly Spearman 0.9921, pooled
     0.9938, exact 97.1%**, paired N 3,030,618, permnos 23,448.

Conclusion: published `bm_ia` = published `bm` minus the equal-weight mean of `bm` over
(SIC2 x month), with the mean recomputed EVERY MONTH over that month's universe. `bm` itself
keeps its annual holding convention; the monthly movement of `bm_ia` comes entirely from
monthly benchmark recomputation (membership churn + staggered fiscal-year refreshes of peers).
The residual gap vs the naive mean reconstruction is the ~3% of firms whose construction-time
SIC assignment differs from the published `sic2`, plus possible benchmark-universe firms that
were screened out of the published rows.

2026-07-10 update: remaining blocker tests (`scripts/audits/audit_bmia_remaining_blockers.py`):

- **Why a monthly mean moves when every firm's bm is annual** (falsification test): over
  41,118 consecutive-month (sic2, month) cell pairs, the benchmark moved in 99.0-99.9% of
  pairs with membership churn, 78.4% of pairs where some member refreshed its bm (staggered
  fiscal year-ends), and only **1.4%** of pairs with neither. Monthly movement is fully
  explained by peer refreshes + membership churn; the grouping needs no other mechanism.
- **Benchmark timing**: recovered benchmark(t) matches the in-cell mean at k=0 (45.2% exact)
  vs 21% at k=+/-1 and 12% at k=+/-2 -> same-month benchmark, no shift.
- **Benchmark universe**: no bm/bm_ia null asymmetry (0 rows either way); winsorized (1/99 by
  month) and trimmed (1/99 by cell) means explain none of the mismatch cells. In cells where
  the benchmark equals the plain mean, reconstruction is pooled rho 1.0000 / exact 99.9%;
  mismatch cells are contaminated by the ~3% construction-SIC-vintage firms (one such firm
  shifts its entire cell's mean).

Builder implemented from these findings: `bm_ia`
(`Character_Builders/_shared/bm_ia_builder.py` +
`Character_Builders/Datashare_BM_IA_Generalized/build_bm_ia.py`), WRDS-free:
June-expands `book_to_market.csv` monthly and demeans by (SIC2, signal month).
Formula validation on datashare's own bm/sic2 inputs
(`scripts/validation/validate_bmia_formula.py`): median monthly Spearman **0.8357**,
pooled 0.7955, exact 17.8%, paired N 3,042,589, permnos 23,489. This is the replication
ceiling without the original construction universe/SIC vintage; a WRDS rebuild inherits our
`book_to_market` quality (rho 0.971) on top. Green SIC2×fyear and FF49×datadate variants
were removed; the panel column is `bm_ia` (identity mapping vs datashare).

## Practical Mapping For Now

For reproducing the public file as closely as the current evidence supports:

| Public column | Use this repo column/builder |
|---|---|
| `bm` | `book_to_market` |
| `operprof` | `operating_profitability` |
| `cfp` | full-history Green `cfp`; scratch rebuild validates cleanly and can replace the shorter local history after review |
| `bm_ia` | solved 2026-07-09: `bm - mean(bm)` by (SIC2 x month), monthly recomputation; see update above |

## Remaining Blocker For `bm_ia`

The available local formulas do not identify public `bm_ia`. The remaining useful tests are narrower:

1. Rebuild industry-adjusted BM using the exact public-file universe for each month, but with
   historical SIC/NAICS/FF mappings from the same CRSP/Compustat vintage used by `datashare.csv`.
2. Test whether the industry benchmark is built from all Compustat firms rather than only the final
   CRSP-linked panel.
3. Test whether the benchmark uses a different month than the reported signal month.
4. Locate the exact original public generation script for this `datashare.csv`; the column is too
   inconsistent with simple public-`bm` demeaning to infer safely from formulas alone.
