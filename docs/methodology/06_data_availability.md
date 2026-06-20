# Data Availability Rules

Lag requirements, minimum-history requirements, lookback windows, missing-value handling, and
truncation effects. Source: `Greens_code.sas`, `Character_Builders/_shared/green_builders.py`,
`_shared/quarterly_builders.py`, `_shared/beta_builder.py`, `_shared/sas_stats.py`.

## Lag requirements (publication delay)

| Data type | Lag before a fundamental is usable | Code |
|---|---|---|
| Green annual | 7 months after `datadate` (window months 7–19, SAS `7 <= … < 20`) | `timing.py` L22-24, L118-154 |
| Green quarterly | quarterly availability lag then monthly expansion | `quarterly_builders.py` |
| HXZ / FF June | June `y+1` for FY ending in year `y` (≈ 6-month minimum) | `timing.py` L97-115 |
| Datashare annual | `datadate + 4 months` | `accounting_60.py` L204 |
| Datashare quarterly | `datadate + 3 months` | `accounting_60.py` L633 |
| Monthly characteristics | lagged 1 month into the signal month (`shift(1)`) | `green_builders.py` L886-888 |

## Minimum-history / first-observation rules

Many Green annual characteristics need 1–2 prior fiscal years and are set missing until enough
history exists:

```600:621:Character_Builders/_shared/green_builders.py
comp.loc[comp.groupby("gvkey").cumcount() < 2, ["chato", "chatoia"]] = np.nan
comp.loc[comp.groupby("gvkey").cumcount() == 0, [ ... first-year change vars ... ]] = np.nan
comp.loc[comp.groupby("gvkey").cumcount() < 2, "grcapx"] = np.nan
```

| Rule | Effect |
|---|---|
| `cumcount() == 0` | first fiscal year: all year-over-year **change** variables (`agr`, `egr`, `lgr`, `chcsho`, `chinv`, `pchsale_*`, `pchcapx`, `divi`, `divo`, `rd`, `chpmia`, `chempia`, `pchcapx_ia`, `ps`, …) set missing |
| `cumcount() < 2` | needs 2 years of history: `chato`/`chatoia`, `grcapx` (3-year capex growth context) set missing |
| `age = cumcount() + 1` | firm age in fiscal years since first appearance (`green_builders.py` L312, L626) |
| `orgcap` | accumulated; first year set missing (L330-332, L614-621) |

## Lookback / rolling windows

| Characteristic(s) | Window | Code |
|---|---|---|
| `mom1m` | 1-month return (lagged) | `green_builders.py` L888 |
| `mom6m` | months 2–6 | momentum block |
| `mom12m` | months 2–12 | momentum block |
| `mom36m` | months 13–36 | momentum block |
| `mom60m` | months 13–60 | momentum block |
| `chmom` | change in 6-month momentum | momentum block |
| `seas1a` | return 11 months prior | L894 |
| `turn`, `std_turn`, `std_dolvol` | 3-month rolling | L902-905 |
| `beta`, `betasq`, `idiovol`, `pricedelay` | rolling daily/weekly window | `beta_builder.py` |
| `baspread`, `ill`, `maxret`, `rvar_mean`, `zerotrade` | within-month daily aggregates | `DAILY_MONTHLY` path |
| `stdacc`, `stdcf`, `roavol` | 16-quarter rolling std (≥ N quarters) | `quarterly_builders.py` + `sas_stats.py` |
| `nincr` | consecutive earnings-increase streak | `quarterly_builders.py` |

Rolling windows require a minimum number of valid observations; insufficient history yields missing
values (matching SAS, via `sas_stats.py` row-wise std that mirrors SAS `std()` minimum-count behavior).

## Missing-value handling conventions

- **`*0` fields:** several Compustat inputs are coalesced to 0 when missing (`xsga0`, `xint0`,
  `cogs0`, etc.) per Green/Dacheng, but only where the SAS code does so — not universally.
- **`ps`** (preferred stock) = `coalesce(pstkrv, pstkl, pstk, 0)`.
- **`txditc`** filled 0 in book-equity computations.
- **SAS `+` operator semantics:** Green's `ms = m1+...+m8` propagates missingness (any missing → total
  missing). The repo replicates this with `sum(axis=1, min_count=len(M_COLUMNS))` (`ms_builder.py`).
- **SAS `lag()` semantics:** SAS `lag()` is *not* BY-group-aware; Green's `pchcapx_ia` output is
  corrupted by this. The repo computes BY-group-correct shifts (`green_builders.py` L172
  `groupby("gvkey").shift`), so it diverges from Green's (buggy) output by design.

## Truncation / winsorization effects

- Green winsorizes a defined list of continuous variables monthly (`hitrim` one-sided,
  `hilotrim` two-sided) — `Greens_code.sas` L1175-1182. The repository applies winsorization only in
  the **research panel** step (1%/99% by month), leaving the raw signal panel unwinsorized.
- Datashare values are **raw** (no winsorization, no rank-standardization); rank-standardization is a
  downstream user step (`impute_rank_output_bchmk_60.py`).
- The final `mve/mom1m/bm` non-missing screen (Green) truncates the sample to firms with those three
  present; off by default in the repo (`--green-universe` to enable).
