import pandas as pd


def impute_by_industry_median(
    df,
    value_cols,
    industry_col,
    time_col="yyyymm",
    suffix="_ind_median_imputed",
):
    """Fill missing values with time-by-industry medians.

    This keeps the original columns unchanged and creates new imputed columns.
    For example, imputing ``book_to_market`` creates
    ``book_to_market_ind_median_imputed`` by default.
    """
    out = df.copy()
    group_cols = [time_col, industry_col]

    for col in value_cols:
        imputed_col = f"{col}{suffix}"
        medians = out.groupby(group_cols)[col].transform("median")
        out[imputed_col] = out[col].fillna(medians)

    return out
