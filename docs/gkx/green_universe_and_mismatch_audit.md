# Green SAS universe & remaining-mismatch audit

Reference SAS: `Supplementary_assistive_files/SAS_codes/Greens_code.sas`
Benchmark output: `Supplementary_assistive_files/Output_From_Greens_SAS_code.sas7bdat`
Panel audited: `outputs/panels/all_character_signal_panel_06182026.csv`
Overlap window: **1980-01 .. 2024-12** (Green's date range).

---

## 1. Why the repo panel has more permnos than Green

### Counts (1980–2024 overlap)

| | Rows (permno-month) | Unique permnos |
|---|---:|---:|
| Repo panel (raw) | 3,414,083 | 27,593 |
| Repo panel + Green screen | 2,313,204 | **19,069** |
| Green SAS output | 2,273,186 | **18,702** |

### Root cause

Green's pipeline starts from **Compustat annual** (`comp.funda`, `Greens_code.sas` L39–72),
links to CRSP via CCM (L410–417), screens to common stocks on NYSE/AMEX/NASDAQ
(`shrcd in (10,11)`, `exchcd in (1,2,3)`, L428–445), and then applies a **final
sample screen** before saving (L1147–1152):

```sas
data temp;
    set temp7;
    where not missing(mve) and not missing(mom1m) and not missing(bm);
    ...
```

Because `bm = ceq / mve_f` (L125) requires a linked **Compustat** record, this screen
makes Green's universe effectively *CRSP common stocks that also have linked Compustat
annual data with non-missing book equity, plus ≥13 months of return history for
`mom1m`/`mom12m`*.

The repo, by contrast, builds every characteristic off the **pure-CRSP monthly spine**
(`load_crsp_monthly`, `green_builders.py` L802–828), which already filters
`shrcd in (10,11)` and `exchcd in (1,2,3)` but does **not** require a Compustat match.
Pure-CRSP characteristics (momentum, volatility, turnover, …) therefore exist for
CRSP common stocks that never matched Compustat, adding ~8,900 extra permnos.

### Empirical confirmation

Applying Green's exact screen (`bm`, `mom1m`, `mve` all non-missing) to the repo panel
reduces it from **27,593 → 19,069 permnos** and **3.41M → 2.31M rows**, essentially
matching Green's **18,702 permnos / 2.27M rows**. The screen accounts for **~96%** of
the permno gap and **~97%** of the row gap.

### Residual difference (19,069 vs 18,702 permnos; ~1.7% of rows)

Secondary, second-order timing/definition differences (not the universe driver):

- **`bm` availability timing.** Green merges annual data to months `datadate+7 .. datadate+19`
  (L480–484) and drops the first monthly observation per permno (`if first.permno then delete`, L522).
- **CCM link set.** Green uses linktypes `LU LC LD LF LN LO LS LX` with
  `year(LINKDT) <= 2015` and `year(LINKENDDT) >= 1950` (L411–412). The repo mirrors this
  in `load_green_ccm_links`, but small link-window differences shift a few hundred permnos.
- **`mve` definition.** Green uses `mve = log(mve_m)` with `mve_m = abs(lag(prc))*lag(shrout)`
  (L516–519); the repo uses `me = log(lagged market_equity)` — equivalent, but edge cases
  (missing lagged price/shares) differ slightly.

## 2. Configuration flag to match Green's universe

A `--green-universe` flag now applies Green's final screen at panel-build time.

- `Character_Panels/build_all_character_panel.py`: `--green-universe`
  (function `apply_green_universe_screen`, keeps rows with non-missing `bm`, `mom1m`, `mve/mvel1`).
- `Character_Panels/run_full_pipeline.py`: `--green-universe`.
- `run_full_pipeline.sh` / `run_full_pipeline.ps1`: env var `GREEN_UNIVERSE=1`.

Example:

```bash
GREEN_UNIVERSE=1 bash run_full_pipeline.sh
# or, on an existing build:
python Character_Panels/build_all_character_panel.py \
  --input-dir outputs/characteristics/individual \
  --output outputs/panels/all_character_signal_panel_green_universe.csv \
  --green-universe
```

The flag is **off by default** so the superset panel is preserved; enable it to
reproduce Green's exact sample.

---

## 3. Remaining character mismatches (median monthly Spearman vs Green, full period)

| Char | ρ before | Status | Root cause |
|------|---------:|--------|------------|
| `indmom` | −0.03 | **FIXED in code** | Repo computed `mom12m - industry_mean` (deviation). Green (L992–997) is `mean(mom12m)` by `sic2 × date` broadcast to every firm. Changed `transform(lambda s: s - s.mean())` → `transform("mean")` in `green_builders.py` and `Green_SAS_Replication/modules/crsp_monthly.py`. Reconstruction from Green's own `mom12m` confirms ρ ≈ 0.97. |
| `operprof` | 0.57 | **repo correct — Green output is a typo** | **Code-vs-output discrepancy in Green's own program.** The published SAS (L206) writes `operprof=(revt-cogs-xsga0-xint0)/lag(ceq)`, and the repo faithfully implements that. The published benchmark output (`Output_From_Greens_SAS_code.sas7bdat`) instead computes **`(revt-cogs-xint0)/lag(ceq)`** — it subtracts `xint0` but drops `xsga0`. Verified to the 5th decimal across 20 firms × 5 fiscal years via raw `comp.funda` (matched on `roe`): `(revt-cogs-xint0)/lag_ceq` reproduced Green's output on **72/72 rows (mean abs err 0.0000)**, while the SAS-code formula `(revt-cogs-xsga0-xint0)` matched 2/72. **Per the data owner, the dropped `xsga0` is a typo in Green's run; the SAS code is authoritative.** The repo therefore keeps the full `-xsga0-xint0` formula and intentionally diverges from Green's `operprof` output column. |
| `pchcapx_ia` | 0.65 | **repo correct — Green output corrupted by SAS `lag()` bug** | `pchcapx_ia = pchcapx − mean(pchcapx)` by `sic2 × fyear` (L246), and the mean is extremely outlier-sensitive. Decomposing against Green's output (mean = `pchcapx − pchcapx_ia`): the **input `pchcapx` matches Green at ρ = 0.997 / 94.8% exact**, but the backed-out industry **mean matches only at ρ = 0.55** — most `sic2×month` cells are identical, a minority are shifted. The shift traces to the `capx` fallback `if missing(capx) and count>=2 then capx=ppent-lag(ppent)` (L168). In SAS, `lag(ppent)` **inside a conditional is not BY-group aware**, so it returns the `ppent` of whatever *different* firm last triggered the branch. Confirmed on permno 91274 / gvkey 152049, FY2009: raw `capx` missing, repo imputes `capx = ppent − lag_ppent = 14.279 − 15.279 = −1.0` → `pchcapx = −3.008` (correct, within-firm); Green's output gives `pchcapx = −8256`, implying imputed `capx ≈ −4111 = 14.279 − ~4125`, i.e. another firm's `ppent`. These garbage extremes (only 0.2% of rows, but |pchcapx| up to 8256) dominate their industry-year mean and shift `pchcapx_ia` for the whole cell. Same class as `operprof`: the repo implements the intended within-firm calculation; Green's output carries a SAS artifact we deliberately do not reproduce. |
| `ms` | 0.57 | **FIXED in code** | `ms = m1+...+m8` (L799) uses SAS's `+` operator, which yields **missing if ANY component is missing** — so Green keeps a score only where a firm-month has both the annual block (m1–m6) and a matched quarterly block (m7,m8). The repo (`ms_builder.py`) instead `fillna(0)`-ed every component before summing, fabricating **1,510,204 spurious `ms=0` rows** (vs Green's 35,427) and biasing `ms` low wherever a component failed to merge. Fix: build `ms` with `sum(axis=1, min_count=8)` so missingness propagates (matches SAS). Component formulas (m1–m6 `green_builders.py` L640–657; m7,m8 quarterly medians by `fyearq×fqtr×sic2`, `quarterly_builders.py` L438–446) already match Green (L257–285, L620–642). |
| `pricedelay` | 0.94 | marginal | `1 - adjR²_single / adjR²_multi` (L1124–1128). Repo (`beta_builder.py` L131–135) matches structurally; ρ already 0.94 and is dominated by the `np.roll` lag construction wrapping at series start and adj-R² edge cases. Small calibration gap. |

Winsorization (Green L1160–1237) was ruled out as a cause: re-winsorizing the repo
values at per-month p1/p99 leaves the Spearman unchanged (rank correlation is invariant
to monotone tail-clamping).
