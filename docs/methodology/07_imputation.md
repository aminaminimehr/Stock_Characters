# Imputation

Authoritative reference for imputation logic. Source: `Imputation/` and
`Character_Panels/build_research_panel_1957.py`.

## Current state: TWO implementations (to be unified)

The repository currently has **two** imputation code paths, which is exactly the duplication to
collapse into a single authoritative source:

| Path | Statistic | Grouping | Columns | Wired into pipeline? |
|---|---|---|---|---|
| `Imputation/industry_median_imputation.py` (`impute_by_industry_median`) | median | `time × industry` | creates **new** `{col}_ind_median_imputed` columns, leaves originals | **No** — standalone, zero imports elsewhere |
| `Character_Panels/build_research_panel_1957.py` (`impute_by_month_industry`) | median, with monthly-median fallback | `signal_yyyymm × ffi49` | **overwrites in place** | **Yes** — production research panel |

The FF industry-code assignment (`Imputation/industry_codes.py` /
`add_fama_french_industry_code`) **is** shared and used by the research panel.

## What the production pipeline does (`build_research_panel_1957.py`)

```84:93:Character_Panels/build_research_panel_1957.py
def impute_by_month_industry(df, character_cols, time_col, industry_col):
    out = df.copy()
    monthly_groups = out.groupby(time_col, sort=False)
    industry_groups = out.groupby([time_col, industry_col], sort=False, dropna=False)
    for column in character_cols:
        industry_median = industry_groups[column].transform("median")
        monthly_median = monthly_groups[column].transform("median")
        out[column] = out[column].fillna(industry_median).fillna(monthly_median)
    return out
```

Sequence (research panel, 1957+): **FF49 assignment → monthly 1%/99% winsorize → FF49×month median
impute (monthly-median fallback) → cross-sectional rank to [-1, 1] (residual gaps → 0).** This is the
Fama-French-style cross-sectional industry imputation the project standardizes on.

## Standalone utility (`Imputation/industry_median_imputation.py`)

```4:25:Imputation/industry_median_imputation.py
def impute_by_industry_median(df, value_cols, industry_col, time_col="yyyymm", suffix="_ind_median_imputed"):
    out = df.copy()
    group_cols = [time_col, industry_col]
    for col in value_cols:
        out[f"{col}{suffix}"] = out[col].fillna(out.groupby(group_cols)[col].transform("median"))
    return out
```

Identical core (FF industry × time median) but **non-destructive** (new columns) and **no** monthly
fallback.

## FF industry-code assignment (shared, keep)

```12:58:Imputation/industry_codes.py
def add_fama_french_industry_code(df, scheme, sic_col="sic", output_col=None, unmatched_value=pd.NA): ...
def add_fama_french_industry_codes(df, sic_col="sic", schemes=SUPPORTED_SCHEMES): ...
```

Backed by embedded SIC-range tables for FF 5/10/12/17/30/38/48/49 in
`Imputation/industry_mappings.py`.

## Unification plan (proposed — not yet implemented)

1. Make `Imputation/` the **single source of truth**: add a `monthly_industry_median` mode (with
   monthly fallback) to `industry_median_imputation.py` so it matches the research-panel behavior.
2. Have `build_research_panel_1957.py` **import** that function instead of re-implementing
   `impute_by_month_industry` inline.
3. Keep FF code assignment in `Imputation/industry_codes.py` (already shared).
4. Do **not** add any new Fama-French-style imputation elsewhere; route all imputation through
   `Imputation/`.

(Implementation deferred until the documentation/architecture is approved.)
