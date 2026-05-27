from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
GREEN_FILE = PROJECT_ROOT / "Supplementary_assistive_files" / "Output_From_Greens_SAS_code.sas7bdat"
REPORT_MD = OUTPUT_DIR / "green_sas_validation_report.md"
DETAIL_CSV = OUTPUT_DIR / "green_sas_validation_summary.csv"


ANNUAL_MAP = {
    "acc": "acc",
    "agr": "agr",
    "bm": "bm",
    "bm_ia": "bm_ia",
    "cash": "cash",
    "cashdebt": "cashdebt",
    "cfp": "cfp",
    "chcsho": "chcsho",
    "chpm": "chpmia",
    "depr": "depr",
    "ep": "ep",
    "gma": "gma",
    "grltnoa": "grltnoa",
    "herf": "herf",
    "hire": "hire",
    "lev": "lev",
    "lgr": "lgr",
    "me_ia": "mve_ia",
    "op": "operprof",
    "pctacc": "pctacc",
    "ps": "ps",
    "rd_sale": "rd_sale",
    "rdm": "rd_mve",
    "roe": "roe",
    "sgr": "sgr",
    "sp": "sp",
}

MONTHLY_MAP = {
    "baspread": "baspread",
    "dolvol": "dolvol",
    "ill": "ill",
    "maxret": "maxret",
    "me": "mve",
    "mom1m": "mom1m",
    "mom6m": "mom6m",
    "mom12m": "mom12m",
    "mom36m": "mom36m",
    "mom60m": "mom60m",
    "mvel1": "mve",
    "rvar_mean": "retvol",
    "std_dolvol": "std_dolvol",
    "std_turn": "std_turn",
    "turn": "turn",
    "zerotrade": "zerotrade",
}

KNOWN_UNMAPPED = {
    "adm": "No `adm` column is present in the supplied Green SAS output.",
    "alm": "No `alm` column is present in the supplied Green SAS output.",
    "ato": "No direct `ato` column is present; Green output contains `chato` and `chatoia` instead.",
    "noa": "No `noa` column is present in the supplied Green SAS output.",
    "pm": "No `pm` column is present in the supplied Green SAS output.",
}


def yyyymm_from_date(series):
    dt = pd.to_datetime(series)
    return dt.dt.year * 100 + dt.dt.month


def read_green(usecols):
    df, _ = pyreadstat.read_sas7bdat(str(GREEN_FILE), usecols=sorted(usecols))
    return df


def exact_match_rates(left, right):
    out = {}
    for decimals in (4, 3, 2):
        lround = left.round(decimals)
        rround = right.round(decimals)
        out[f"exact_{decimals}dp"] = float((lround == rround).mean()) if len(left) else np.nan
    return out


def grouped_correlation(df, group_col):
    corrs = []
    for _, group in df.groupby(group_col):
        pair = group[["python_value", "green_value"]].dropna()
        if len(pair) >= 5 and pair["python_value"].nunique() > 1 and pair["green_value"].nunique() > 1:
            corrs.append(pair["python_value"].corr(pair["green_value"]))
    if not corrs:
        return {
            "mean_xs_corr": np.nan,
            "median_xs_corr": np.nan,
            "min_xs_corr": np.nan,
            "xs_periods": 0,
        }
    corrs = pd.Series(corrs, dtype="float64")
    return {
        "mean_xs_corr": float(corrs.mean()),
        "median_xs_corr": float(corrs.median()),
        "min_xs_corr": float(corrs.min()),
        "xs_periods": int(corrs.notna().sum()),
    }


def summarize_match(character, green_col, family, merged, group_col):
    pair = merged[["python_value", "green_value"]].replace([np.inf, -np.inf], np.nan).dropna()
    row = {
        "character": character,
        "green_column": green_col,
        "family": family,
        "python_rows": int(merged["python_present"].sum()),
        "green_rows_on_keys": int(merged["green_present"].sum()),
        "matched_nonmissing_pairs": int(len(pair)),
        "overall_corr": float(pair["python_value"].corr(pair["green_value"])) if len(pair) >= 2 else np.nan,
        "mean_abs_diff": float((pair["python_value"] - pair["green_value"]).abs().mean()) if len(pair) else np.nan,
    }
    row.update(grouped_correlation(pair.assign(**{group_col: merged.loc[pair.index, group_col]}), group_col))
    row.update(exact_match_rates(pair["python_value"], pair["green_value"]))
    return row


def compare_annual(green):
    green = green.copy()
    green["permno"] = pd.to_numeric(green["permno"], errors="coerce")
    green["gvkey"] = green["gvkey"].astype(str).str.extract(r"(\d+)")[0].str.zfill(6)
    green["fyear"] = pd.to_numeric(green["fyear"], errors="coerce")
    results = []

    for character, green_col in ANNUAL_MAP.items():
        path = OUTPUT_DIR / f"{character}.csv"
        if not path.exists() or green_col not in green.columns:
            continue

        py = pd.read_csv(path)
        py = py[["permno", "gvkey", "fyear", character]].copy()
        py["permno"] = pd.to_numeric(py["permno"], errors="coerce")
        py["gvkey"] = py["gvkey"].astype(str).str.extract(r"(\d+)")[0].str.zfill(6)
        py["fyear"] = pd.to_numeric(py["fyear"], errors="coerce")
        py = py.rename(columns={character: "python_value"})
        key = ["permno", "gvkey", "fyear"]
        py = py.drop_duplicates(key, keep="last")
        py["python_present"] = True

        gr = green[key + [green_col]].rename(columns={green_col: "green_value"})
        gr = gr.dropna(subset=key)
        gr = gr.drop_duplicates(key + ["green_value"])
        gr = gr.groupby(key, as_index=False)["green_value"].last()
        gr["green_present"] = True

        merged = py.merge(gr, on=key, how="inner")
        merged["python_present"] = merged["python_present"].fillna(False)
        merged["green_present"] = merged["green_present"].fillna(False)
        results.append(summarize_match(character, green_col, "annual", merged, "fyear"))

    return results


def compare_monthly(green):
    green = green.copy()
    green["permno"] = pd.to_numeric(green["permno"], errors="coerce")
    green["signal_yyyymm"] = yyyymm_from_date(green["DATE"])
    results = []

    for character, green_col in MONTHLY_MAP.items():
        path = OUTPUT_DIR / f"{character}.csv"
        if not path.exists() or green_col not in green.columns:
            continue

        py = pd.read_csv(path)
        if "signal_yyyymm" not in py.columns:
            continue
        py = py[["permno", "signal_yyyymm", character]].copy()
        py["permno"] = pd.to_numeric(py["permno"], errors="coerce")
        py = py.rename(columns={character: "python_value"})
        py = py.drop_duplicates(["permno", "signal_yyyymm"], keep="last")
        py["python_present"] = True

        gr = green[["permno", "signal_yyyymm", green_col]].rename(columns={green_col: "green_value"})
        gr = gr.dropna(subset=["permno", "signal_yyyymm"])
        gr = gr.drop_duplicates(["permno", "signal_yyyymm", "green_value"])
        gr = gr.groupby(["permno", "signal_yyyymm"], as_index=False)["green_value"].last()
        gr["green_present"] = True

        merged = py.merge(gr, on=["permno", "signal_yyyymm"], how="inner")
        merged["python_present"] = merged["python_present"].fillna(False)
        merged["green_present"] = merged["green_present"].fillna(False)
        results.append(summarize_match(character, green_col, "monthly", merged, "signal_yyyymm"))

    return results


def format_pct(x):
    return "" if pd.isna(x) else f"{100 * x:.2f}%"


def format_num(x):
    return "" if pd.isna(x) else f"{x:.6f}"


def write_report(summary):
    summary = summary.sort_values(["family", "character"]).reset_index(drop=True)
    summary.to_csv(DETAIL_CSV, index=False)

    display = summary.copy()
    for col in ["overall_corr", "mean_xs_corr", "median_xs_corr", "min_xs_corr", "mean_abs_diff"]:
        display[col] = display[col].map(format_num)
    for col in ["exact_4dp", "exact_3dp", "exact_2dp"]:
        display[col] = display[col].map(format_pct)

    columns = [
        "character",
        "green_column",
        "family",
        "matched_nonmissing_pairs",
        "overall_corr",
        "mean_xs_corr",
        "median_xs_corr",
        "exact_4dp",
        "exact_3dp",
        "exact_2dp",
        "mean_abs_diff",
    ]

    lines = [
        "# Green SAS Validation Report",
        "",
        "This report compares the repository's generated character CSV files in `outputs/`",
        "against `Supplementary_assistive_files/Output_From_Greens_SAS_code.sas7bdat`.",
        "",
        "Annual variables are matched on `permno`, `gvkey`, and `fyear`. Monthly variables are matched",
        "on `permno` and `signal_yyyymm`, where `signal_yyyymm` is derived from Green's `DATE`.",
        "Cross-sectional correlations are computed within each fiscal year or month and then",
        "summarized across periods.",
        "",
        "## Summary",
        "",
        display[columns].to_markdown(index=False),
        "",
        "## Variables Not Compared",
        "",
    ]
    for character, reason in KNOWN_UNMAPPED.items():
        if (OUTPUT_DIR / f"{character}.csv").exists():
            lines.append(f"- `{character}`: {reason}")
    lines.extend(
        [
            "",
            "## Name Mappings Used",
            "",
            "- `chpm` was compared to Green's `chpmia` because this repository's `chpm` builder stores the industry-adjusted value.",
            "- `rdm` was compared to Green's `rd_mve`.",
            "- `me_ia` was compared to Green's `mve_ia`.",
            "- `op` was compared to Green's `operprof`.",
            "- `me` and `mvel1` were compared to Green's `mve`; inspect these carefully because Green's SAS output labels current monthly size as `mve`, while this repository's monthly size builders use an explicit lagged-size convention.",
            "- `rvar_mean` was compared to Green's `retvol`, the available realized-return-volatility column in the supplied SAS output.",
            "",
        ]
    )
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main():
    if not GREEN_FILE.exists():
        raise FileNotFoundError(GREEN_FILE)

    annual_cols = {"permno", "gvkey", "fyear", *ANNUAL_MAP.values()}
    monthly_cols = {"permno", "DATE", *MONTHLY_MAP.values()}

    print("Reading selected annual Green SAS columns...")
    green_annual = read_green(annual_cols)
    print("Reading selected monthly Green SAS columns...")
    green_monthly = read_green(monthly_cols)

    rows = compare_annual(green_annual) + compare_monthly(green_monthly)
    summary = pd.DataFrame(rows)
    write_report(summary)
    print(f"Wrote {REPORT_MD}")
    print(f"Wrote {DETAIL_CSV}")


if __name__ == "__main__":
    main()
