# Codex Task — Next Tests for `datashare.csv` (`cfp` history + `bm_ia`)

Audience: an autonomous coding agent (codex) with WRDS access on the server.
Prereq reading: `docs/gkx/datashare_reverse_engineering.md` (your prior findings).

## 0. Context (do not re-litigate)

Your prior reverse engineering established, empirically, against the **local**
`Supplementary_assistive_files/datashare.csv`:

| Public column | Best repo match | Evidence | Status |
|---|---|---|---|
| `bm` | repo `book_to_market` (HXZ/FF June; ME = Dec CRSP permco; `be = seq` else `ceq+ps` else `at−lt`, `+txditc0−ps`) | pooled ρ 0.959, exact 64% | mostly solved |
| `operprof` | repo `operating_profitability` (HXZ June; `(revt−cogs−xsga0−xint0)/be`) | pooled ρ 0.952, exact 66% | mostly solved |
| `cfp` | repo **Green** `cfp` (`oancf/mve_f`, accrual fallback) | pooled ρ 0.998, exact 98% **over 1975+** | solved where history exists |
| `bm_ia` | none | best tested ≈ 0.42 | **UNSOLVED** |

Conclusion already reached: this `datashare.csv` follows **Green/HXZ** definitions, **not** Dacheng's
`accounting_60.py`. The pure-Dacheng port in `Character_Builders/Dacheng_datashare/build_datashare_chars.py`
(`be/me`, `(ib+dp)/me`, FF49 demean) is the wrong model for this file (`cfp` ρ ≈ −0.02). Treat it as a
rejected experiment; do **not** use it as the panel source.

## Objectives (in priority order)

0. **Match the datashare stock universe (permno set + missingness), not just the formula.** See
   `docs/gkx/datashare_universe_comparison.md`. This is the user's primary concern and gates the rest.
1. **Extend `cfp` history backward** so Green `cfp` covers the full `datashare.csv` period, then
   re-validate.
2. **Solve `bm_ia`** (the one open column) via a systematic, logged experiment grid.
3. (Optional) Tighten `bm`/`operprof` residuals (push exact-match above ~65%).

Hard constraints:
- Do **not** modify Green builders' formulas. For `cfp` history, change only the Compustat query
  **start date**, not the formula.
- Write all experimental outputs under `outputs/characteristics/datashare_style/` or a new
  `outputs/diagnostics/bm_ia_experiments/`. Do not overwrite Green/HXZ individual CSVs.
- Log every experiment (config + metrics) to a results table; never silently discard a run.

---

## Task 0 — Universe / permno matching (DO FIRST; gates Tasks 1–3)

Measured facts (`docs/gkx/datashare_universe_comparison.md`):
- datashare: **32,793** permnos, **195701–202112**, sparse panel (`bm` non-null in only 3.04M of
  4.12M rows; `bm` over 23,489 permnos).
- Green output: 18,702 permnos, 198001+; **Green ⊆ datashare** (green-only = 0; datashare-only = 14,091).
- Gap drivers: (1) datashare starts 1957 vs Green 1980; (2) datashare is sparse / keeps rows Green's
  joint `mve & mom1m & bm` screen drops; (3) link/security handling.

**What you must do:**
1. For each repo builder you intend to map to a datashare column (`book_to_market`,
   `operating_profitability`, Green `cfp`), produce its output over the **full datashare period
   (1957+)** with **no Green final screen**, so the universe is comparable.
2. Compute and report a **coverage report** vs datashare for each char (not just correlation):
   `keys_datashare, keys_repo, keys_both, datashare_only, repo_only,
    permno_datashare, permno_repo, permno_both`, where a "key" is a `(permno, month)` with the char
   non-null. Use the next-month `DATE` alignment that datashare uses (datashare `DATE` is the return
   month; the predictor month is the prior month-end).
3. Diagnose the residual `repo_only` / `datashare_only` permnos: are they pre-1957/post-2021, missing
   CRSP link, wrong share class, delisted, or dropped by a filter the repo applies but datashare does
   not (or vice versa)? Tabulate the cause breakdown.
4. **Acceptance:** `datashare_only` and `repo_only` permno-month counts each < ~5% of `keys_both`
   for `bm`/`operprof`/`cfp` once period and screen are aligned. If not reachable, document the exact
   filter responsible.

Only after the universe is aligned do the Spearman/exact comparisons in Tasks 1–3 become meaningful
(they must be computed on `keys_both`).

---

## Task 1 — Extend `cfp` history and re-validate

**Why:** local Green `cfp.csv` starts in 1975 because the Green Compustat query uses a 1975 start
date; public `datashare.csv` has earlier `cfp`. (See reverse-engineering report, `cfp` note.)

**Steps:**
1. Find the Green annual Compustat query start date. Search `Character_Builders/_shared/green_builders.py`
   and any annual loader for `1975` / `datadate >=` / `'01JAN1975'`. (Greens_code.sas L69 uses
   `datadate >= '01JAN1975'd`.)
2. Add a configurable start (e.g. `--annual-start 1959-01-01`, default unchanged) OR a one-off rebuild
   script under `scripts/rebuild/` that pulls `comp.funda` from 1959 and recomputes **only** `cfp`
   with the existing Green formula (`oancf/mve_f`, fallback `(ib − wc_accrual)/mve_f`).
3. Rebuild `cfp` over full history; write to a scratch CSV (do not clobber `individual/cfp.csv` unless
   the full-period rebuild validates cleanly).
4. Validate full-overlap `cfp` vs public `datashare.csv` `cfp`.

**Acceptance:** pooled Spearman ≥ 0.99 and median monthly Spearman ≥ 0.99 over the **full** overlap
(including pre-1975). Report paired-obs gained pre-1975.

---

## Task 2 — Solve `bm_ia` (the open column)

**Critical diagnostic from your report:** for `permno = 25160`, public `bm` is **constant** across its
annual June→May holding window, but the **implied** industry benchmark `bm − bm_ia` **changes within
that window**. Therefore `bm_ia` is **not** a fixed annual demeaning of the public `bm` column. The
industry benchmark updates more often than annually (likely monthly) and/or is built from a different
universe/industry/timing than the published `bm`.

Already rejected (do not repeat): Dacheng FF49 annual demean (0.31); public `bm` demeaned by
month×SIC2 (0.42); annual-date×SIC2 (0.42); FF49 month (0.36–0.38); SIC/SIC3 exact; Green `bm_ia`.

### Run a logged experiment grid

For each candidate, construct an industry benchmark `bench[i,t]`, set
`bm_ia_hat[i,t] = bm_pub[i,t] − bench[i,t]`, and validate vs public `bm_ia`. Use the **public `bm`**
column itself as the input where the hypothesis demeans the published value, and use the repo's
`book_to_market` (which best reproduces public `bm`) where the hypothesis rebuilds the benchmark from
an intermediate universe.

Vary these axes (full factorial where feasible):

| Axis | Values to try |
|---|---|
| Benchmark input | (a) public `bm` forward-filled to monthly; (b) repo `book_to_market` monthly; (c) raw annual `book_equity/Dec-ME` at datadate |
| Grouping time | monthly cross-section (`signal_yyyymm`); annual `datadate`-year; June-formation cohort |
| Industry scheme | SIC2, SIC3, FF12, FF17, FF30, FF48, FF49 (use repo `Imputation/industry_codes.py`) |
| Statistic | **mean** and **median** |
| Weighting | equal-weight and value-weight (by ME) |
| Benchmark universe | (i) final published panel rows; (ii) **all CRSP-linked common stock** (shrcd 10/11, exchcd 1–3); (iii) **all Compustat firms with bm** regardless of CRSP link/share-code; (iv) include financials/microcaps |

Highest-prior hypotheses to try first (they explain the within-window variation):
- **H-A:** monthly cross-sectional **mean** of `book_to_market` by **SIC2**, universe = all CRSP-linked
  common stock present that month (not just the published-bm rows). Monthly membership changes →
  benchmark varies within a firm's annual window. ✅ explains the diagnostic.
- **H-B:** same as H-A but **median**, and FF48/FF49.
- **H-C:** benchmark = mean over **all Compustat firms with a valid annual bm** (broader than the
  CRSP-linked panel), assigned monthly via forward-fill.
- **H-D:** benchmark month offset differs from the signal month (e.g., industry mean as of June
  formation, or as of the prior month).

### Discriminating test (cheap, do before the full grid)
Re-run the `permno = 25160` window: for each candidate, check whether `bench[25160, t]` reproduces the
**within-window movement** of public `bm − bm_ia`. Discard candidates whose benchmark is flat within
the window. This kills most variants in seconds before paying for a full-panel Spearman.

### If the grid fails
Locate the **exact original generation script** for this `datashare.csv`. Search:
- `Supplementary_assistive_files/Python_codes/Dacheng_Xiu_or_Xin_he/` (already-known Dacheng code) —
  but note this gives the rejected 0.31, so look for a **different** generator.
- Any SAS/Python that produces a `bm_ia` matching public values. Grep the repo and
  `Supplementary_assistive_files/` for `bm_ia`, `bmia`, `industry`, `_ia`.
- The GKX appendix definition of `bm_ia` (industry-adjusted book-to-market) and whether it cites a
  specific industry scheme.

**Acceptance:** median monthly Spearman ≥ 0.95 vs public `bm_ia`. If unreachable, deliver a written
conclusion stating the best achievable mapping and why exact replication is not possible from the
available evidence.

---

## Task 3 (optional) — Tighten `bm` / `operprof` residuals

Current ρ ≈ 0.95–0.96, exact ≈ 65%. Investigate residual drivers:
- link-history / multiple-share-class handling,
- delisting & security filters,
- legacy Compustat/CRSP vintage differences,
- December-ME permco aggregation edge cases.
Report which factor moves exact-match most. Do not change Green builders; experiment in scratch.

---

## Validation harness (use/extend, don't reinvent)

- Primary comparison target: `Supplementary_assistive_files/datashare.csv` (raw, not rank-standardized).
- Reuse `Character_Builders/Dacheng_datashare/validate_against_datashare.py` and
  `scripts/compare_panel_final_vs_green.py` patterns:
  - join on the correct month key (test both `signal_yyyymm` and the next-month `DATE` alignment —
    datashare stamps the return month);
  - compute **median monthly Spearman**, **pooled Spearman**, **exact-match (abs 1e-4)**, and
    **paired-obs**;
  - report per-decade as well as full-period.
- For `bm_ia` experiments, emit one results row per config to
  `outputs/diagnostics/bm_ia_experiments/results.csv` with columns:
  `input, group_time, industry, stat, weight, universe, median_rho, pooled_rho, exact, paired_obs`.

## Deliverables

1. Updated `cfp` history (script + validation numbers).
2. `bm_ia` experiment results table + the winning config (or a documented negative result).
3. An updated section appended to `docs/gkx/datashare_reverse_engineering.md` with final mappings.
4. Confirmation of the recommended panel mapping:
   `datashare bm → book_to_market`, `operprof → operating_profitability`, `cfp → Green cfp`,
   `bm_ia → <result>`.

## Notes for whoever wires the panel afterward (not codex's job here)
- Because `bm`/`operprof`/`cfp` are already in the panel via `book_to_market`,
  `operating_profitability`, and Green `cfp`, **no new `_dc` columns are needed for those three**.
  Only a solved `bm_ia` warrants a new column (e.g. `bm_ia_dc`).
- The pure-Dacheng port `Character_Builders/Dacheng_datashare/build_datashare_chars.py` should be
  retained as a documented experiment, not used as the datashare source.
