# Green timing validation debug (2010–2015)

Diagnostics for variables with 0 valid months in the main validation report.

## Summary

Date conversion (`signal_yyyymm`, Green SAS `DATE` → month, datashare `DATE` // 100), `permno` alignment (both coerced to `Int64` in the validation loader), and Green column names all check out. Variables with 72 valid months (`bm`, `bm_ia`, `chatoia`) confirm the merge and Spearman path work in this window.

For variables with 0 valid months, the repo panel has **zero non-null values** in 201001–201512 because the underlying individual character CSVs only contain fiscal rows from 2018–2019 onward (see source CSV ranges below). Green SAS has full coverage; inner `permno×month` overlap exists, but every merged row has a missing repo value.

Lowering the per-month pair threshold to 10 does **not** produce valid Spearman months when `repo_non_null = 0`.

| Variable | Bench col | Repo non-null | Green non-null | Overlap rows | Paired | Months ≥1 | Months ≥10 | Months ≥50 | Spearman months (≥50 pairs) | Spearman months (≥10 pairs) | Reason |
|----------|-----------|--------------:|---------------:|-------------:|-------:|----------:|-----------:|-----------:|----------------------------:|----------------------------:|--------|
| age | age | 0 | 254,419 | 254,229 | 0 | 0 | 0 | 0 | 0 | 0 | overlap exists but all paired values missing |
| absacc | absacc | 0 | 247,243 | 254,229 | 0 | 0 | 0 | 0 | 0 | 0 | overlap exists but all paired values missing |
| invest | invest | 0 | 241,279 | 254,229 | 0 | 0 | 0 | 0 | 0 | 0 | overlap exists but all paired values missing |
| cfp_ia | cfp_ia | 0 | 254,377 | 254,229 | 0 | 0 | 0 | 0 | 0 | 0 | overlap exists but all paired values missing |
| bm | bm | 254,199 | 254,419 | 254,229 | 248,722 | 72 | 72 | 72 | 72 | 72 |  |
| bm_ia | bm_ia | 254,199 | 254,419 | 254,229 | 248,722 | 72 | 72 | 72 | 72 | 72 |  |
| chatoia | chatoia | 238,900 | 240,102 | 254,229 | 234,660 | 72 | 72 | 72 | 72 | 72 |  |
| cashpr | cashpr | 0 | 252,578 | 254,229 | 0 | 0 | 0 | 0 | 0 | 0 | overlap exists but all paired values missing |
| egr | egr | 0 | 247,320 | 254,229 | 0 | 0 | 0 | 0 | 0 | 0 | overlap exists but all paired values missing |
| orgcap | orgcap | 0 | 190,635 | 254,229 | 0 | 0 | 0 | 0 | 0 | 0 | overlap exists but all paired values missing |

## Individual builder CSV date ranges

- `age.csv`: 30,851 fiscal rows, `2018-01-31` – `2023-12-31`
- `absacc.csv`: 24,177 fiscal rows, `2018-10-31` – `2023-12-31`
- `invest.csv`: 23,077 fiscal rows, `2019-01-31` – `2023-12-31`
- `cfp_ia.csv`: 30,775 fiscal rows, `2018-01-31` – `2023-12-31`
- `bm.csv`: 279,607 fiscal rows, `1975-01-31` – `2026-04-30`
- `bm_ia.csv`: 279,607 fiscal rows, `1975-01-31` – `2026-04-30`
- `chatoia.csv`: 233,644 fiscal rows, `1976-12-31` – `2026-04-30`
- `cashpr.csv`: 30,712 fiscal rows, `2018-01-31` – `2023-12-31`
- `egr.csv`: 24,166 fiscal rows, `2018-10-31` – `2023-12-31`
- `orgcap.csv`: 20,391 fiscal rows, `2018-10-31` – `2023-12-31`
