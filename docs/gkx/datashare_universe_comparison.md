# Datashare vs Green/Repo — Stock Universe (permno) Comparison

Measured locally (`scripts/_tmp_universe_probe.py`, since removed) on
`Supplementary_assistive_files/datashare.csv` and `Output_From_Greens_SAS_code.sas7bdat`.

## Headline numbers

| | `datashare.csv` | Green SAS output |
|---|---:|---:|
| Rows | 4,117,300 | 2,273,186 |
| Unique permno | **32,793** | 18,702 |
| Date range | **195701 → 202112** | 198001 → 202412 |
| Unique months | 780 | — |
| `bm` non-null rows / permno | 3,042,589 / 23,489 | — |
| `operprof` non-null rows / permno | 2,721,953 / 21,516 | — |
| `cfp` non-null rows / permno | 2,768,521 / 22,134 | — |

**permno set overlap:** datashare 32,793; green 18,702; **in both 18,702; green-only 0;
datashare-only 14,091.** → Green's universe is a **strict subset** of datashare's.

## Unique permno per decade

| Decade | datashare (any row) | datashare (bm non-null) | Green |
|---|---:|---:|---:|
| 1950 | 1,153 | — | — |
| 1960 | 3,122 | 1,629 | — |
| 1970 | 7,129 | 4,591 | — |
| 1980 | 11,837 | 8,962 | 8,301 |
| 1990 | 15,188 | 12,740 | 11,063 |
| 2000 | 12,719 | 10,725 | 8,743 |
| 2010 | 9,374 | 7,368 | 5,226 |
| 2020 | 7,565 | 4,179 | 2,766 |

## Why datashare has more permnos (the filtering differences)

1. **Period.** datashare starts **1957**; Green's published output starts **1980**
   (`Greens_code.sas` final step keeps `year(date) >= 1980`). All pre-1980 permnos are
   datashare-only.
2. **Sparse vs screened panel.** datashare is a *sparse wide panel* — a `(permno, DATE)` row exists
   whenever *any* characteristic is available, so many rows have missing `bm`/`operprof`/`cfp`
   (`bm` is non-null in only 3.04M of 4.12M rows). Green applies a **joint** final screen
   (`not missing(mve) and not missing(mom1m) and not missing(bm)`, `Greens_code.sas` L1149) that
   drops rows datashare keeps. This explains most of the within-decade gap (1980s: datashare bm
   8,962 vs Green 8,301).
3. **Link / security handling.** Residual differences from CCM linkprim, multiple share classes
   (permco aggregation), and delisting/security filters.

Share-code/exchange filters are **not** the cause: datashare's ~32.8k common-stock permnos over
1957–2021 are consistent with `shrcd 10,11` / `exchcd 1–3` (same as Green/HXZ/repo).

## Implication for reproducing the 4 datashare characters with HXZ/Green builders

A high rank-correlation on the *intersection* is necessary but **not sufficient**. To reproduce
datashare we must also match its **universe and missing-data handling**:

- **Build period must cover 1957+** (the HXZ/Green annual builders must not start at 1975/1980 for
  this purpose — cf. the `cfp` 1975 start issue).
- **Do not apply Green's joint `mve & mom1m & bm` final screen** when targeting datashare; datashare
  keeps a per-characteristic sparse panel.
- **Keep each characteristic's own missingness** (a permno-month with `bm` but no `operprof` should
  still appear).
- **Match link handling** (linkprim, permco share-class aggregation) to datashare's.

### Required validation metrics (in addition to Spearman)
For every candidate builder vs datashare, report **coverage**, not just correlation:
- `keys_datashare` = count of `(permno, month)` with the char non-null in datashare,
- `keys_repo` = same for the repo builder,
- `keys_both`, `datashare_only`, `repo_only`,
- `permno_datashare`, `permno_repo`, `permno_both`,
- then Spearman/exact **on `keys_both`**.

A good reproduction needs `repo_only` and `datashare_only` both small (universe match) **and** high
Spearman on the intersection (formula match).
