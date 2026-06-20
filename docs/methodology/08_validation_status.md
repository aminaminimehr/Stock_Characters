# Validation Status — Every `datashare.csv` Variable

Benchmark = **Green SAS output** (`Output_From_Greens_SAS_code.sas7bdat`), full period (540 monthly
cross-sections). Metric = **median monthly Spearman rank correlation** between the repository panel
(`outputs/panels/all_character_signal_panel_final.csv`) and Green. Underlying data:
`docs/gkx/panel_final_vs_green_full_comparison.csv` (95 datashare columns; 2 of `datashare.csv`'s 97
columns are identifiers).

> Note on exact-match rates: several variables with ρ ≈ 1.0 have low *exact* match rates (e.g.
> `std_dolvol`, `beta`, `betasq`, `idiovol`, `herf`) due to floating-point scale/precision, not
> methodology — they are rank-identical. ρ is the authoritative measure.

## A. Excellent — median monthly ρ ≥ 0.999 (≈64 variables)

`convind, divo, securedind, sin, rd, divi, age, nincr, depr, realestate, sp, orgcap, tang, lev,
salerec, pchsaleinv, saleinv, roavol, salecash, rd_mve(→rdm), secured, rd_sale, cash, dy, std_turn,
ill, std_dolvol, cashdebt, absacc, retvol(→rvar_mean), baspread, zerotrade, currat, quick, pchquick,
ep, sgr, hire, bm, cfp, agr, grltnoa, pchdepr, pchsale_pchxsga, pchsale_pchrect, lgr, egr, chcsho,
pchsale_pchinvt, chinv, roic, pchgm_pchsale, cashpr, gma, rsup, roeq, roaq, chtx, acc, pctacc,
pchcurrat, mom1m, maxret, mvel1(→mve), aeavol, ear, dolvol, invest`

**Status: validated.** Green replication is exact or near-exact.

## B. Strong — 0.99 ≤ ρ < 0.999 (≈21 variables)

| Variable | ρ (median monthly) | Note |
|---|---|---|
| turn | 0.9988 | rolling-window precision |
| chatoia | 0.9986 | industry-adjusted (SIC2 mean); low exact-match (0.63) but rank-aligned |
| beta, betasq, idiovol | 0.998 | daily-regression precision |
| stdcf, stdacc | 0.998 | 16-quarter rolling std |
| bm_ia | 0.9976 | industry-adjusted; sensitive (see datashare note below) |
| mve_ia (→me_ia) | 0.9975 | industry-adjusted size |
| sic2 | 0.9970 | mapping near-identity |
| herf | 0.9967 | industry concentration |
| mom6m, mom12m, mom36m | 0.992–0.996 | momentum windows |
| grcapx | 0.9959 | 2-year capex history |
| tb | 0.9954 | tax-based; low exact-match |
| chempia | 0.9947 | industry-adjusted employment |
| cfp_ia | 0.9936 | industry-adjusted (note pooled ρ lower, 0.86, due to tails) |
| chmom | 0.9934 | momentum change |
| chpmia | 0.9927 | industry-adjusted profit margin |
| cinvest | 0.9897 | quarterly investment |

**Status: validated** (rank-aligned; residual gaps are window/precision/industry-mean sensitivity).

## C. Acceptable — 0.95 ≤ ρ < 0.99 (2 variables)

| Variable | ρ | Cause |
|---|---|---|
| ps | 0.979 | Mohanram/Piotroski-style discrete score; low exact-match (0.11) from discrete ties |
| indmom | 0.960 | industry momentum; SIC2×month mean; discrete-ish, sensitive to industry membership |

**Status: acceptable**, monitor.

## D. Borderline — 0.90 ≤ ρ < 0.95 (1 variable)

| Variable | ρ | Cause |
|---|---|---|
| pricedelay | 0.939 | weekly-lag regression R² differences; known sensitivity |

**Status: borderline.** Candidate for a focused review.

## E. Divergent — ρ < 0.75 (3 variables)

| Variable | ρ | Cause | Resolution |
|---|---|---|---|
| pchcapx_ia | 0.729 | Green SAS `lag()` is not BY-group-aware → Green's **output** is corrupted | Repo is **correct**; divergence is by design (matches Green code, not buggy output) |
| ms | 0.580 | Mohanram 8-signal score; quarterly alignment / signal-threshold differences | **Unresolved** — open item |
| operprof | 0.573 | Green **output** omits `xsga0` (SAS typo); repo follows Green **code** | Repo is **correct**; divergence by design |

**Status:** `pchcapx_ia` and `operprof` are *intentional* (code > output). `ms` is the one genuinely
**open** Green-replication item.

## F. Dacheng (datashare) layer — divergence from `datashare.csv`

For the four characteristics Dacheng constructs differently, validation is against `datashare.csv`
directly. Best-matching repo column (median monthly Spearman):

| datashare var | Green col (ρ vs datashare) | HXZ col (ρ vs datashare) | Dacheng-exact `_dc` | Best |
|---|---|---|---|---|
| `bm` | `bm` ≈ 0.925 | `book_to_market` ≈ **0.969** | `bm_dc` (pending WRDS run) | HXZ June best so far |
| `operprof` | `operprof` ≈ 0.909 | `operating_profitability` ≈ **0.956** | `operprof_dc` (pending) | HXZ June best so far |
| `cfp` | `cfp` ≈ **0.999** (rank), level differs | `cash_flow_to_price` | `cfp_dc` (pending) | Green rank-identical |
| `bm_ia` | `bm_ia` ≈ 0.27 | — | `bm_ia_dc` (pending) | needs `_dc` |

**Status:** The HXZ June layer already provides strong datashare matches for `bm`/`operprof`. The
Dacheng-exact `_dc` builder (`Character_Builders/Dacheng_datashare/`) is implemented but **not yet
run on WRDS / wired into the panel** — this is the main remaining Dacheng-layer task, especially for
`bm_ia` (the weakest datashare match).

## Headline

- **92 / 95** datashare variables replicate Green at median monthly ρ ≥ 0.95.
- **2** intentional divergences (`operprof`, `pchcapx_ia`) — repo follows Green's code over its
  buggy output.
- **1** open item: `ms`.
- **Dacheng layer:** HXZ variants cover `bm`/`operprof`/`cfp` well; `_dc` exact builder pending run,
  needed primarily for `bm_ia`.
