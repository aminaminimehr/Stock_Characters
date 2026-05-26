# Imputation Utilities

This folder is reserved for missing-value imputation and industry-classification
helpers.

## Fama-French Industry Codes

`industry_codes.py` adds Fama-French industry codes from a SIC column using
embedded SIC-range mappings in `industry_mappings.py`.

```python
from Imputation.industry_codes import add_fama_french_industry_codes

df = add_fama_french_industry_codes(
    df,
    sic_col="sic",
    schemes=(5, 10, 12, 17, 30, 38, 48, 49),
)
```

Included schemes:

```text
ffi5
ffi10
ffi12
ffi17
ffi30
ffi38
ffi48
ffi49
```

The following repository is a useful reference for Fama-French industry
classification files:

https://github.com/blairqin/Fama-French-Industry

The mappings are based on Fama-French industry classifications by SIC code. For
the original definitions, cite Kenneth French's data library / Fama-French
industry classification documentation. The Python implementation in this folder
is local to this repository; the underlying classification definitions are not
claimed as original work.

## Industry Median Imputation

`industry_median_imputation.py` fills missing values with time-by-industry
medians while preserving the original columns:

```python
from Imputation.industry_median_imputation import impute_by_industry_median

df = impute_by_industry_median(
    df,
    value_cols=["book_to_market", "operating_profitability"],
    industry_col="ffi49",
    time_col="yyyymm",
)
```
