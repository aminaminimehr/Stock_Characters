# `bm` and `bm_ia` — Line-by-Line Code Walkthrough

This document traces the construction of the two book-to-market characteristics
from the top-level wrapper down to the final panel merge. Read it top to bottom
and you will understand the whole structure.

The call chain is:

```
run_full_pipeline.py  (the wrapper / orchestrator)
  ├─ build_all_implemented_characters.py        (Green-style character batch)
  ├─ build_book_to_market.py                    (produces book_to_market.csv = "bm")
  ├─ build_bm_ia.py                             (produces bm_ia.csv = "bm_ia")
  │     └─ bm_ia_builder.py                      (WRDS-free demean logic)
  │           └─ timing.py :: expand_annual_file_june
  └─ build_all_character_panel.py              (merges every CSV into the signal panel)
```

Conventions used below:
- `bm` in datashare.csv == the repo column `book_to_market` (see `DATASHARE_PANEL_ALIAS`).
- `bm_ia` keeps its own name (no alias).
- "signal month" = the month the characteristic is *known* and used for sorting.
- "target month" = the month whose return the signal predicts (signal month + 1).

---

## 1. `Character_Panels/run_full_pipeline.py` — the wrapper

This is the only script you normally invoke. It builds every character CSV,
then assembles the monthly panels. Everything below is invoked (directly or via
`subprocess`) from here.

### 1.1 Module header and path setup

```1:11:Character_Panels/run_full_pipeline.py
"""Run character builds (resume-friendly) and rebuild monthly panels."""
import argparse
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
```

- Lines 2-6: standard library imports. `subprocess` is used because the
  individual character builders run as **separate Python processes** (so a
  crash in one builder cannot corrupt another, and each manages its own WRDS
  connection / memory).
- Line 8: `pandas` is only used here for the final summary column count.
- Lines 10-11: locate the repo root (one level up from `Character_Panels/`)
  and put it on `sys.path` so `output_paths` and `pipeline_config` import cleanly.

### 1.2 Output-path and config imports

```13:25:Character_Panels/run_full_pipeline.py
from output_paths import (  # noqa: E402
    CHARACTER_INDIVIDUAL_DIR,
    COMPLETE_ALL_PANEL_FILE,
    EXCESS_RETURNS_FILE,
    PIPELINE_LOG_FILE,
    RESEARCH_PANEL_FILE,
    SIGNAL_PANEL_FILE,
    character_csv_path,
    ensure_output_tree,
    iter_character_csv_paths,
    list_character_stems,
)
from pipeline_config import profile_help, resolve_config  # noqa: E402
```

- `CHARACTER_INDIVIDUAL_DIR` = `outputs/characteristics/individual/` — where every
  per-character CSV (including `book_to_market.csv` and `bm_ia.csv`) is written.
- `SIGNAL_PANEL_FILE` = `outputs/panels/all_character_signal_panel.csv` — the
  merged monthly panel that `bm`/`bm_ia` end up in.
- `resolve_config` turns a `--profile` (green/datashare/research) plus CLI flags
  into a single frozen `PipelineConfig` object (see §6).
- `# noqa: E402` silences the "import not at top of file" lint caused by the
  `sys.path` insertion above.

### 1.3 Metadata column set and the HXZ job list

```29:62:Character_Panels/run_full_pipeline.py
PANEL_META = {
    "permno",
    "permco",
    "gvkey",
    "date",
    "datadate",
    "source_date",
    "source_yyyymm",
    "signal_yyyymm",
    "target_yyyymm",
    "yyyymm",
    "sic",
    "exchcd",
    "shrcd",
    "fyear",
    "availability_date",
    "calendar_year",
    "excess_return",
    "ffi49",
}

HXZ_JOBS = [
    ("book_to_market", "Character_Builders/HXZ_BM_Generalized/build_book_to_market.py", []),
    (
        "operating_profitability",
        "Character_Builders/HXZ_OPE_Generalized/build_operating_profitability.py",
        [],
    ),
]

# Datashare mapping: HXZ/Green columns required for datashare profile.
DATASHARE_HXZ_STEMS = {"book_to_market", "operating_profitability", "bm_ia"}

BM_IA_SCRIPT = "Character_Builders/Datashare_BM_IA_Generalized/build_bm_ia.py"
```

- `PANEL_META` is the set of *non-character* columns. `print_summary` uses it
  (§1.8) to count how many real predictors the final panel contains.
- `HXZ_JOBS` lists the two "HXZ / Fama-French" annual builders run as standalone
  scripts. `book_to_market` is the first one — this is the source of the `bm`
  signal. The third list element (`[]`) is a slot for extra CLI args passed to
  that builder (unused for bm).
- `BM_IA_SCRIPT` is the path to the bm_ia builder, run separately because it
  depends on `book_to_market.csv` already existing.

### 1.4 `run()` helper

```65:67:Character_Panels/run_full_pipeline.py
def run(cmd):
    print("\n>>", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)
```

- Prints the command (so logs show exactly what ran), then executes it as a
  child process from the repo root. `check=True` makes any non-zero exit abort
  the whole pipeline immediately.

### 1.5 `build_all_characters()` — the Green batch

```75:110:Character_Panels/run_full_pipeline.py
def build_all_characters(
    wrds_user,
    cfg,
    skip_ibes=False,
    resume=False,
    workers=None,
):
    cmd = [
        PYTHON,
        "Character_Builders/build_all_implemented_characters.py",
        "--wrds-user",
        wrds_user,
        "--output-dir",
        str(CHARACTER_INDIVIDUAL_DIR),
    ]
    cmd.extend(["--ccm-linktypes", cfg.ccm_linktypes])
    cmd.extend(["--ccm-linkprim", cfg.ccm_linkprim])
    cmd.extend(["--crsp-shrcd", cfg.crsp_shrcd])
    cmd.extend(["--crsp-exchcd", cfg.crsp_exchcd])
    if skip_ibes:
        cmd.append("--skip-ibes")
    if resume:
        cmd.extend(["--skip-existing", "--skip-annual-monthly"])
    if cfg.sample_start:
        cmd.extend(["--sample-start", cfg.sample_start])
    if cfg.sample_end:
        cmd.extend(["--sample-end", cfg.sample_end])
    if cfg.profile:
        cmd.extend(["--profile", cfg.profile])
    if cfg.skip_special:
        cmd.append("--skip-special")
    if cfg.skip_daily:
        cmd.append("--skip-daily")
    if workers is not None:
        cmd.extend(["--workers", str(workers)])
    run(cmd)
```

- Assembles the command line for the Green-style batch builder (§2) by copying
  every resolved flag from `cfg` into argv. This is how the **single source of
  truth** (`PipelineConfig`) reaches the child process — no builder reads
  conventions from anywhere else.
- `--skip-existing --skip-annual-monthly` (resume mode) lets you restart after a
  crash without redoing finished CSVs.
- Note: this batch does **not** build `book_to_market` or `bm_ia`; those come
  from `build_hxz_characters()` next.

### 1.6 `build_hxz_characters()` and `build_datashare_bm_ia()`

```113:159:Character_Panels/run_full_pipeline.py
def build_hxz_characters(wrds_user, output_dir, cfg, profile="green"):
    jobs = HXZ_JOBS

    for stem, script, extra in jobs:
        out = output_dir / f"{stem}.csv"
        if out.exists():
            print(f"{stem}: skipped (already exists)")
            continue
        cmd = [
            PYTHON,
            script,
            "--wrds-user",
            wrds_user,
            "--output",
            str(out),
            "--ccm-linktypes",
            cfg.ccm_linktypes,
            "--ccm-linkprim",
            cfg.ccm_linkprim,
        ]
        cmd.extend(extra)
        run(cmd)

    # Datashare bm_ia depends on book_to_market.csv (WRDS-free demean).
    build_datashare_bm_ia(output_dir)


def build_datashare_bm_ia(output_dir):
    """Build SIC2 x month demeaned bm_ia after book_to_market exists."""
    bm_path = output_dir / "book_to_market.csv"
    out = output_dir / "bm_ia.csv"
    if out.exists():
        print("bm_ia: skipped (already exists)")
        return
    if not bm_path.exists():
        print("bm_ia: skipped (book_to_market.csv missing)")
        return
    run(
        [
            PYTHON,
            BM_IA_SCRIPT,
            "--bm-csv",
            str(bm_path),
            "--output",
            str(out),
        ]
    )
```

- `build_hxz_characters`: for each HXZ job, skip if the CSV already exists
  (idempotent), otherwise run the standalone builder with the resolved CCM
  flags. **This is where `book_to_market.csv` (= `bm`) is produced**, by
  `build_book_to_market.py` (§3).
- `build_datashare_bm_ia`: only runs **after** `book_to_market.csv` exists,
  because bm_ia is a pure post-processing demean of bm (no WRDS access needed).
  It calls `build_bm_ia.py` (§4). The skip-if-exists guard is the reason a stale
  `bm_ia.csv` survives partial rebuilds — delete it to force a refresh.

### 1.7 `build_panels()` — where bm/bm_ia enter the panel

```181:223:Character_Panels/run_full_pipeline.py
def build_panels(cfg):
    signal_cmd = [
        PYTHON,
        "Character_Panels/build_all_character_panel.py",
        "--input-dir",
        str(CHARACTER_INDIVIDUAL_DIR),
        "--output",
        str(SIGNAL_PANEL_FILE),
    ]
    if cfg.profile:
        signal_cmd.extend(["--profile", cfg.profile])
    if cfg.green_universe:
        signal_cmd.append("--green-universe")
    if cfg.green_winsor:
        signal_cmd.append("--green-winsor")
    run(signal_cmd)

    if not cfg.build_research_panel:
        print("Skipping prediction/research panels (profile setting).")
        return

    run(
        [
            PYTHON,
            "Character_Panels/build_complete_prediction_panel.py",
            "--characters",
            str(SIGNAL_PANEL_FILE),
            "--returns",
            str(EXCESS_RETURNS_FILE),
            "--output",
            str(COMPLETE_ALL_PANEL_FILE),
        ]
    )
    run(
        [
            PYTHON,
            "Character_Panels/build_research_panel_1957.py",
            "--input",
            str(COMPLETE_ALL_PANEL_FILE),
            "--output",
            str(RESEARCH_PANEL_FILE),
        ]
    )
```

- This runs `build_all_character_panel.py` (§7) over every CSV in
  `CHARACTER_INDIVIDUAL_DIR`, producing `SIGNAL_PANEL_FILE`. The datashare
  profile passes `--profile datashare` so only the 95 mapped columns merge.
- The two later `run()` calls build the prediction and research panels; the
  datashare profile sets `build_research_panel=False`, so those are skipped.

### 1.8 `print_summary()` and `main()`

```226:248:Character_Panels/run_full_pipeline.py
def print_summary(cfg):
    chars = list_character_stems()
    signal_cols = count_panel_characters(SIGNAL_PANEL_FILE)
    print("\n=== Pipeline summary ===")
    print(f"Profile: {cfg.profile}")
    print(f"Individual character CSV files: {len(chars)}")
    print(f"Signal panel: {SIGNAL_PANEL_FILE}")
    if cfg.build_research_panel:
        pred_cols = count_panel_characters(COMPLETE_ALL_PANEL_FILE)
        research_cols = count_panel_characters(RESEARCH_PANEL_FILE)
        print(f"Complete panel: {COMPLETE_ALL_PANEL_FILE}")
        print(f"Research panel: {RESEARCH_PANEL_FILE}")
        print(f"complete_all_character_prediction_panel predictors: {len(pred_cols)}")
        print(f"research_panel_1957_ranked predictors: {len(research_cols)}")
    print(f"all_character_signal_panel predictors: {len(signal_cols)}")
    if cfg.profile == "datashare":
        print("\nDatashare column mapping:")
        print("  bm -> book_to_market")
        print("  operprof -> operating_profitability")
        print("  cfp -> cfp (Green builder)")
        print("  bm_ia -> bm_ia (SIC2 x month demean of book_to_market)")
    print("\nPredictor columns in monthly signal panel:")
    print(", ".join(signal_cols))
```

- `count_panel_characters` (lines 70-72) reads only the CSV header and subtracts
  `PANEL_META` to count true predictors.
- The datashare block restates the alias mapping so the user sees that the panel
  column is `book_to_market` even though datashare.csv calls it `bm`.

`main()` (lines 251-387) parses all CLI flags, calls `resolve_config(...)` to
merge them with the chosen profile into `cfg`, runs `cfg.validate_required()`
(the five required flags must be set, directly or via profile), pushes them into
the environment with `cfg.apply_env()`, then dispatches:

```370:383:Character_Panels/run_full_pipeline.py
    if not args.skip_build:
        build_all_characters(
            args.wrds_user,
            cfg,
            skip_ibes=cfg.skip_ibes,
            resume=args.resume,
            workers=args.workers,
        )
        if cfg.build_hxz:
            build_hxz_characters(args.wrds_user, CHARACTER_INDIVIDUAL_DIR, cfg, profile=cfg.profile)
        build_excess_returns(args.wrds_user, cfg)

    build_panels(cfg)
    print_summary(cfg)
```

So the order is: Green batch → HXZ builders (incl. **book_to_market**) →
**bm_ia** → excess returns → panels. `--skip-build` jumps straight to panel
assembly from existing CSVs.

## 2. `Character_Builders/build_all_implemented_characters.py` — the Green batch

This builds all the Green-style annual/monthly/quarterly/special characters
(not bm/bm_ia, but it shares the same `--profile datashare` allowlist mechanism
that bm_ia relies on for being included in the panel).

### 2.1 Allowlist helpers

```53:70:Character_Builders/build_all_implemented_characters.py
def _output_allowlist(profile: str | None) -> frozenset[str] | None:
    """When profile is datashare, only write the 95 mapped output columns."""
    if profile == "datashare":
        return datashare_output_columns()
    return None


def _should_write(name: str, allowlist: frozenset[str] | None) -> bool:
    if allowlist is None:
        return True
    return name in allowlist


def _maybe_write_character(df, name: str, output_dir, allowlist: frozenset[str] | None):
    if not _should_write(name, allowlist):
        print(f"{name}: skipped (not in datashare output allowlist)")
        return
    write_character(df, name, output_dir)
```

- Under `--profile datashare`, only the 95 resolved datashare predictor names are
  written. `book_to_market` and `bm_ia` are both in that set (via the alias map),
  so they survive the allowlist. Everything else is skipped to keep the output
  folder clean and the panel narrow.
- `_maybe_write_character` is the single gate every builder passes through.

### 2.2 `main()` dispatch

```353:399:Character_Builders/build_all_implemented_characters.py
    db = connect_wrds(args.wrds_user)
    try:
        clear_monthly_crsp_cache()
        if not args.only_daily:
            if not args.skip_annual_monthly:
                build_annual_characters(
                    db,
                    output_dir,
                    args.ccm_linktypes,
                    args.ccm_linkprim,
                    skip_existing=args.skip_existing,
                    profile=profile,
                )
                build_monthly_characters(
                    db, output_dir, skip_existing=args.skip_existing, profile=profile
                )
            build_quarterly_characters(
                db,
                output_dir,
                args.ccm_linktypes,
                args.ccm_linkprim,
                skip_ibes=args.skip_ibes,
                skip_existing=args.skip_existing,
                profile=profile,
            )
            if not args.skip_special:
                build_special_characters(
                    db,
                    output_dir,
                    args.ccm_linktypes,
                    args.ccm_linkprim,
                    skip_ibes=args.skip_ibes,
                    skip_existing=args.skip_existing,
                    workers=args.workers,
                    profile=profile,
                )
        if args.only_daily or not args.skip_daily:
            build_daily_monthly_characters(
                db,
                output_dir,
                skip_existing=args.skip_existing,
                workers=args.workers,
                profile=profile,
            )
    finally:
        clear_monthly_crsp_cache()
        db.close()
```

- One WRDS connection is opened, reused across all builder blocks, then closed
  in `finally`. `clear_monthly_crsp_cache()` before/after prevents stale
  in-process caches leaking between runs.
- `build_annual_characters` (lines 73-94) loads Compustat once, attaches permnos
  via CCM, computes industry-adjusted annuals, and writes each annual character
  through the allowlist. `book_to_market` is **not** built here — it has its own
  standalone HXZ builder (§3) — but the same allowlist pattern applies.

---

## 3. `Character_Builders/HXZ_BM_Generalized/build_book_to_market.py` — builds `bm`

This standalone script produces `book_to_market.csv`. It is the HXZ/Fama-French
book-to-market: book equity from Compustat, market equity from CRSP December,
merged on `permco x calendar_year`, ratio taken on actual Compustat `datadate`
(no return-prediction shift — that shift happens later in the panel, §7).

### 3.1 Imports and constants

```1:17:Character_Builders/HXZ_BM_Generalized/build_book_to_market.py
import argparse
import sys
from pathlib import Path

import pandas as pd
import wrds

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared.ccm import add_ccm_arguments, attach_ccm_links, load_ccm_links
from output_paths import crsp_universe_filter, read_wrds_sql, resolve_output_path  # noqa: E402


WRDS_USER = None
OUTPUT_FILE = "book_to_market.csv"
```

- Two `sys.path` inserts: the repo root (for `output_paths`) and the
  `Character_Builders/` dir (for `_shared.ccm`).
- `add_ccm_arguments` adds `--ccm-linktypes` / `--ccm-linkprim` to this script's
  own parser, so the same CCM convention used everywhere else applies here too.
- `crsp_universe_filter` returns the SQL fragment enforcing shrcd/exchcd (§5.4).
- `read_wrds_sql` runs raw SQL via a DBAPI connection (works around a
  SQLAlchemy/wrds immutabledict incompatibility).

### 3.2 `load_compustat()` — book equity

```20:70:Character_Builders/HXZ_BM_Generalized/build_book_to_market.py
def load_compustat(db):
    comp = read_wrds_sql(db, """
        SELECT gvkey, datadate, fyear,
               seq, ceq, at, lt,
               pstk, pstkl, pstkrv,
               txditc
        FROM comp.funda
        WHERE indfmt = 'INDL'
          AND datafmt = 'STD'
          AND popsrc = 'D'
          AND consol = 'C'
    """)
    comp["datadate"] = pd.to_datetime(comp["datadate"])

    company = read_wrds_sql(db, """
        SELECT gvkey, sic
        FROM comp.company
    """)
    comp = comp.merge(company, on="gvkey", how="left")

    comp["preferred_stock"] = (
        comp["pstkrv"].fillna(comp["pstkl"]).fillna(comp["pstk"]).fillna(0)
    )
    comp["stockholders_equity"] = comp["seq"]
    comp.loc[comp["stockholders_equity"].isna(), "stockholders_equity"] = (
        comp["ceq"] + comp["preferred_stock"]
    )
    comp.loc[comp["stockholders_equity"].isna(), "stockholders_equity"] = (
        comp["at"] - comp["lt"]
    )

    comp["txditc"] = comp["txditc"].fillna(0)
    comp["book_equity"] = (
        comp["stockholders_equity"] + comp["txditc"] - comp["preferred_stock"]
    )
    comp = comp[comp["book_equity"] > 0].copy()
    comp["book_equity"] = comp["book_equity"] * 1000

    # This is the actual Compustat fiscal-year-end calendar year. The raw
    # output intentionally does not shift dates. For prediction or portfolio
    # formation, make this character available in June of calendar_year + 1.
    # Example: datadate in 2004 uses December 2004 market equity and is used
    # for June 2005 portfolios / July 2005-June 2006 returns.
    comp["calendar_year"] = comp["datadate"].dt.year

    # If a firm changes fiscal year end and has multiple records in the same
    # calendar year, keep the most recent report for that firm-year.
    return (
        comp.sort_values(["gvkey", "calendar_year", "datadate"])
        .drop_duplicates(["gvkey", "calendar_year"], keep="last")
    )
```

- The `WHERE` clause selects the standard annual fundamentals frame
  (industrial format, standardized, domestic, consolidated) — the canonical
  Compustat annual universe.
- `comp.company` is merged to attach `sic` (the **4-digit Compustat historical
  SIC**). This `sic` is what flows into `book_to_market.csv` and later into
  bm_ia's SIC2 grouping (§4.3).
- Preferred stock waterfall: `pstkrv` → `pstkl` → `pstk` → 0 (FF/Danielsen order).
- Stockholders' equity waterfall: `seq` → `ceq + preferred` → `at - lt`. This is
  the standard FF book-equity construction.
- `book_equity = stockholders_equity + txditc - preferred_stock` (add deferred
  taxes, subtract preferred). Rows with `book_equity <= 0` are dropped.
- `* 1000`: Compustat reports in millions; CRSP `shrout` is in thousands, so
  scaling book equity to dollars keeps the ratio dimensionless.
- `calendar_year = datadate.year` is the fiscal-year-end calendar year. The
  comment explains the June-availability convention is applied **later** in the
  panel, not here — the raw CSV keeps real datadates.
- The final sort + `drop_duplicates(keep="last")` handles firms that change
  fiscal-year-end and have two records in one calendar year: keep the latest.

### 3.3 `load_crsp_monthly()` — December market equity input

```73:99:Character_Builders/HXZ_BM_Generalized/build_book_to_market.py
def load_crsp_monthly(db, use_imputed_market_equity):
    crsp = read_wrds_sql(db, f"""
        SELECT m.permno, m.permco, m.date, m.prc, m.shrout,
               n.exchcd, n.shrcd
        FROM crsp.msf AS m
        JOIN crsp.msenames AS n
          ON m.permno = n.permno
         AND n.namedt <= m.date
         AND m.date <= COALESCE(n.nameendt, DATE '9999-12-31')
        WHERE {crsp_universe_filter("n")}
    """)
    crsp["date"] = pd.to_datetime(crsp["date"])
    crsp["year"] = crsp["date"].dt.year
    crsp["month"] = crsp["date"].dt.month
    crsp = crsp.sort_values(["permno", "date"])

    if use_imputed_market_equity:
        crsp[["price_for_me", "shrout_for_me"]] = (
            crsp.groupby("permno")[["prc", "shrout"]].ffill()
        )
    else:
        crsp["price_for_me"] = crsp["prc"]
        crsp["shrout_for_me"] = crsp["shrout"]

    crsp["market_equity"] = crsp["price_for_me"].abs() * crsp["shrout_for_me"]

    return crsp[crsp["market_equity"].notna() & (crsp["market_equity"] > 0)].copy()
```

- Pulls every monthly CRSP row with its then-current msenames record (the
  `namedt <= date <= nameendt` join attaches the correct share/exchange codes at
  the time of the observation).
- `crsp_universe_filter("n")` injects the shrcd/exchcd predicate from the
  resolved profile (datashare = shrcd ALL, so no share-code filter).
- `use_imputed_market_equity` (off by default) forward-fills price/shares within
  permno before computing market equity — useful to impute missing Decembers.
- `market_equity = |prc| * shrout` (absolute price handles CRSP's negative
  bid-ask midpoint convention). Zero/NaN market-equity rows are dropped.

### 3.4 `december_firm_market_equity()` — collapse to firm-year December ME

```102:111:Character_Builders/HXZ_BM_Generalized/build_book_to_market.py
def december_firm_market_equity(crsp):
    december = crsp[crsp["month"] == 12].copy()

    firm_me = (
        december.groupby(["permco", "year"], as_index=False)["market_equity"]
        .sum()
        .rename(columns={"year": "calendar_year"})
    )

    return firm_me
```

- Keep only December rows, then **sum market equity within `permco x year`**.
  `permco` is the company identifier (one company can have multiple permnos /
  share classes); summing across share classes gives the firm's total December
  market equity. The column is renamed `calendar_year` so it joins cleanly with
  Compustat (which keyed on `calendar_year` in §3.2).

### 3.5 `build_book_to_market()` — the ratio

```114:135:Character_Builders/HXZ_BM_Generalized/build_book_to_market.py
def build_book_to_market(comp, crsp_december_me, link):
    comp_linked = attach_ccm_links(comp, link)

    bm = comp_linked.merge(
        crsp_december_me,
        on=["permco", "calendar_year"],
        how="inner",
    )
    bm["book_to_market"] = bm["book_equity"] / bm["market_equity"]
    bm = bm[bm["book_to_market"] > 0].copy()

    bm = (
        bm.sort_values(
            ["permno", "datadate", "market_equity"],
            ascending=[True, True, False],
        )
        .drop_duplicates(["permno", "datadate"], keep="first")
    )

    return bm[
        ["permno", "permco", "gvkey", "datadate", "sic", "fyear", "book_to_market"]
    ]
```

- `attach_ccm_links` (§5.5) joins Compustat to CRSP permnos via the CCM link
  table, keeping one primary permno per `gvkey x datadate`.
- Inner-merge on `permco x calendar_year` pairs each fiscal year's book equity
  with that calendar year's December market equity. (December of the fiscal
  calendar year — the FF convention.)
- `book_to_market = book_equity / market_equity`. Negative/zero ratios dropped.
- Dedup: if a `permno x datadate` somehow maps to multiple firm-year ME rows,
  keep the one with the largest market equity (sort descending, keep first).
- Output columns: the annual ID set plus `book_to_market`. Note `datadate` is
  the **real** Compustat date — no June shift yet.

### 3.6 `main()` — orchestrate and write

```138:176:Character_Builders/HXZ_BM_Generalized/build_book_to_market.py
def main():
    parser = argparse.ArgumentParser(
        description="Build the book-to-market character using actual Compustat datadates."
    )
    parser.add_argument("--wrds-user", default=WRDS_USER)
    parser.add_argument("--output", default=OUTPUT_FILE)
    add_ccm_arguments(parser)
    parser.add_argument(
        "--use-imputed-market-equity",
        action="store_true",
        help=(
            "Forward-fill CRSP price and shares outstanding within permno before "
            "constructing December market equity."
        ),
    )
    args = parser.parse_args()

    db = (
        wrds.Connection(wrds_username=args.wrds_user)
        if args.wrds_user
        else wrds.Connection()
    )
    try:
        comp = load_compustat(db)
        crsp = load_crsp_monthly(db, args.use_imputed_market_equity)
        link = load_ccm_links(db, args.ccm_linktypes, args.ccm_linkprim)
    finally:
        db.close()

    bm = build_book_to_market(comp, december_firm_market_equity(crsp), link)
    output_path = resolve_output_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bm.to_csv(output_path, index=False)

    print(f"Saved book-to-market character to: {output_path.resolve()}")
    print(f"Rows: {len(bm):,}")
    print(f"Used imputed CRSP price/shareout: {args.use_imputed_market_equity}")
    print("datadate is the actual Compustat datadate; no return-prediction shift is applied.")
```

- Open one WRDS connection, load the three inputs (Compustat, CRSP monthly, CCM
  links), close it, then build and write. `resolve_output_path` sends a bare
  filename to `CHARACTER_INDIVIDUAL_DIR` (§5.2).
- The final print line is the key reminder: this CSV is **annual on real
  datadates**; the monthly June expansion happens in the panel stage (§7) and in
  the bm_ia builder (§4).

## 4. `Character_Builders/Datashare_BM_IA_Generalized/build_bm_ia.py` — builds `bm_ia`

A thin CLI wrapper around the shared demean logic. It is WRDS-free: it only
reads the already-built `book_to_market.csv`.

```1:34:Character_Builders/Datashare_BM_IA_Generalized/build_bm_ia.py
"""Build bm_ia: datashare-convention industry-adjusted book-to-market.

bm_ia = book_to_market - mean(book_to_market) over (SIC2, signal month),
with the equal-weight mean recomputed every month (see docs/gkx/
datashare_reverse_engineering.md, 2026-07-09/10 updates).

WRDS-free: reads the already-built book_to_market.csv from
outputs/characteristics/individual/ and writes a monthly-native CSV that
build_all_character_panel.py auto-merges. Run AFTER build_book_to_market.py.
"""
import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parents[2]))

from _shared.bm_ia_builder import build_bm_ia_character
from output_paths import CHARACTER_INDIVIDUAL_DIR, resolve_output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build bm_ia (SIC2 x month demeaned book-to-market, datashare convention)."
    )
    parser.add_argument(
        "--bm-csv",
        default=str(CHARACTER_INDIVIDUAL_DIR / "book_to_market.csv"),
        help="Path to the annual book_to_market.csv produced by build_book_to_market.py.",
    )
    parser.add_argument("--output", default="bm_ia.csv")
    parser.add_argument("--industry-digits", type=int, default=2)
    parser.add_argument("--stat", default="mean", choices=("mean", "median"))
    args = parser.parse_args()
```

- The module docstring states the formula and the reverse-engineering source.
- `--industry-digits` defaults to **2** (SIC2 = two-digit SIC), the datashare
  convention. `--stat` defaults to `mean` (equal-weight). Both are CLI flags, not
  hard-coded — per the repo rule that every convention is configurable.

```36:54:Character_Builders/Datashare_BM_IA_Generalized/build_bm_ia.py
    bm_csv = Path(args.bm_csv)
    if not bm_csv.exists():
        raise FileNotFoundError(
            f"{bm_csv} not found. Build it first with "
            "Character_Builders/HXZ_BM_Generalized/build_book_to_market.py."
        )

    out = build_bm_ia_character(
        bm_csv,
        industry_digits=args.industry_digits,
        stat=args.stat,
    )

    output_path = resolve_output_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    print(f"Saved bm_ia to: {output_path.resolve()}")
    print(f"Rows: {len(out):,}  permnos: {out['permno'].nunique():,}")
    print(f"non-null bm_ia: {out['bm_ia'].notna().sum():,}")
```

- The `FileNotFoundError` makes the ordering dependency explicit: bm_ia cannot
  run until `book_to_market.csv` exists.
- All real work is delegated to `build_bm_ia_character` (§4.2).

### 4.1 `Character_Builders/_shared/bm_ia_builder.py` — the demean engine

```22:41:Character_Builders/_shared/bm_ia_builder.py
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Character_Panels.timing import expand_annual_file_june  # noqa: E402

MONTHLY_OUTPUT_COLUMNS = [
    "permno",
    "signal_yyyymm",
    "target_yyyymm",
    "sic",
    "bm_ia",
]
```

- The module docstring (lines 1-21) is the authoritative description of the
  convention: the industry mean is **recomputed every month** over that month's
  universe, so bm_ia moves month-to-month from peer fiscal-year refreshes and
  membership churn — not from the firm's own bm.
- `expand_annual_file_june` (§5.1) is imported from the panel timing module so
  bm_ia uses the **exact same** June expansion the panel uses for
  `book_to_market`. This alignment is critical: bm_ia must be demeaned over the
  same (permno, signal_yyyymm) cells the panel will later expose.
- `MONTHLY_OUTPUT_COLUMNS` is the exact schema `build_all_character_panel.py`
  expects for a monthly-native CSV (§7.2): the three monthly keys + `sic` + the
  value column. Because these keys are present, the panel builder treats
  `bm_ia.csv` as already-monthly and merges it directly (no re-expansion).

### 4.2 `demean_by_industry_month()`

```44:65:Character_Builders/_shared/bm_ia_builder.py
def demean_by_industry_month(
    monthly: pd.DataFrame,
    *,
    value_column: str,
    industry_column: str = "sic",
    industry_digits: int = 2,
    time_column: str = "signal_yyyymm",
    stat: str = "mean",
    output_column: str = "bm_ia",
) -> pd.DataFrame:
    """Subtract the per-(industry, month) ``stat`` of ``value_column``.

    ``industry_digits`` truncates 4-digit SIC codes (2 -> two-digit SIC,
    matching the published datashare bm_ia convention). Rows with missing
    industry are demeaned in their own bucket (mirrors the GKX 'other' bucket).
    """
    monthly = monthly.copy()
    sic = pd.to_numeric(monthly[industry_column], errors="coerce")
    monthly["_industry"] = (sic // (10 ** (4 - industry_digits))).astype("Int64")
    grouped = monthly.groupby(["_industry", time_column], dropna=False)[value_column]
    monthly[output_column] = monthly[value_column] - grouped.transform(stat)
    return monthly.drop(columns=["_industry"])
```

- Every knob is a keyword argument: which column holds the value, which holds
  the industry code, how many digits to keep, which time key to group on, which
  statistic, and the output column name. Nothing is hard-coded.
- `sic // 10**(4 - industry_digits)`: with `industry_digits=2` this is
  `sic // 100`, i.e. integer-divide a 4-digit SIC by 100 to get the 2-digit SIC
  (e.g. 3812 -> 38). `.astype("Int64")` keeps nullable ints so missing SICs
  stay as `<NA>` rather than becoming 0.
- `groupby([_industry, signal_yyyymm], dropna=False)`: groups by (SIC2, month).
  `dropna=False` puts missing-industry rows in their own `<NA>` bucket — this
  mirrors the GKX "other" bucket so those firms are still demeaned against
  each other, not dropped.
- `grouped.transform(stat)`: computes the per-(SIC2,month) `mean` (or `median`)
  and broadcasts it back to every row, so the subtraction is vectorized.
- `bm_ia = bm - mean(bm) within (SIC2, month)`. The temporary `_industry`
  column is dropped before return.

### 4.3 `build_bm_ia_character()`

```68:89:Character_Builders/_shared/bm_ia_builder.py
def build_bm_ia_character(
    bm_csv_path: Path,
    *,
    bm_column: str = "book_to_market",
    industry_digits: int = 2,
    stat: str = "mean",
    output_column: str = "bm_ia",
) -> pd.DataFrame:
    """Monthly SIC2-demeaned book-to-market from an annual book_to_market CSV."""
    annual = pd.read_csv(bm_csv_path)
    monthly = expand_annual_file_june(annual, [bm_column])
    monthly = monthly[monthly[bm_column].notna()].copy()
    monthly = demean_by_industry_month(
        monthly,
        value_column=bm_column,
        industry_digits=industry_digits,
        stat=stat,
        output_column=output_column,
    )
    keep = [c if c != "bm_ia" else output_column for c in MONTHLY_OUTPUT_COLUMNS]
    return monthly[keep]
```

- Read the annual `book_to_market.csv` (one row per permno x datadate).
- `expand_annual_file_june` (§5.1) replicates each annual row across 12 signal
  months under the June convention, producing a monthly frame keyed by
  (permno, signal_yyyymm, target_yyyymm) with `sic` attached.
- Drop rows where bm is missing (cannot demean a missing value).
- Demean within (SIC2, signal month) via §4.2.
- Return exactly `MONTHLY_OUTPUT_COLUMNS` (the `keep` list comprehension just
  substitutes the configured output column name if it differs from `"bm_ia"`).
  This is the schema the panel builder auto-detects as monthly-native (§7.2).

## 5. Shared helpers used by bm / bm_ia

### 5.1 `Character_Panels/timing.py :: expand_annual_file_june()`

This is the heart of the June expansion used by both `book_to_market` (in the
panel) and `bm_ia` (in the builder).

```97:116:Character_Panels/timing.py
def expand_annual_file_june(df: pd.DataFrame, character_columns: Iterable[str]) -> pd.DataFrame:
    """HXZ / Fama-French June availability: FY ending calendar year y -> Jun y+1 .. May y+2."""
    df = df.copy()
    df["datadate"] = pd.to_datetime(df["datadate"])
    availability_year = df["datadate"].dt.year + 1

    repeated = df.loc[df.index.repeat(12), list(ANNUAL_ID_COLUMNS) + list(character_columns)].copy()
    month_offsets = np.tile(np.arange(12), len(df))
    first_signal_month = availability_year.to_numpy().repeat(12) * 12 + 5
    month_index = first_signal_month + month_offsets
    repeated["signal_yyyymm"] = (month_index // 12) * 100 + (month_index % 12 + 1)
    repeated["target_yyyymm"] = repeated["signal_yyyymm"].map(add_one_month)
    repeated = (
        repeated.sort_values(["permno", "signal_yyyymm", "datadate"])
        .drop_duplicates(["permno", "signal_yyyymm"], keep="last")
    )

    keep = MONTHLY_KEYS + ["permco", "gvkey", "sic"] + list(character_columns)
    return repeated[keep]
```

- **June convention**: a fiscal year ending in calendar year `y` becomes
  available in **June of y+1** and stays available through **May of y+2** — 12
  months. (So a Dec-2004 fiscal year feeds June-2005 … May-2006 signal months.)
- `availability_year = datadate.year + 1`.
- `df.index.repeat(12)`: each annual row is duplicated 12 times (one per month).
- `first_signal_month = availability_year * 12 + 5`: month index 0-based within
  the year; `+5` is June (Jan=0 … Jun=5). `month_offsets = 0..11` advances
  through the 12 availability months.
- `signal_yyyymm = (month_index // 12) * 100 + (month_index % 12 + 1)`: converts
  the linear month index back to a `YYYYMM` integer (handles the year rollover
  from December y+1 to January y+2 automatically).
- `target_yyyymm = add_one_month(signal_yyyymm)`: the return month the signal
  predicts (signal month + 1).
- Dedup on `(permno, signal_yyyymm)` keeping the **latest datadate**: if a firm
  has two fiscal years whose availability windows overlap a given signal month,
  the more recent fiscal year wins (point-in-time correctness).
- Returns the monthly keys + `permco, gvkey, sic` + the value columns. The `sic`
  carried here is the 4-digit Compustat SIC from `book_to_market.csv`, which
  bm_ia then truncates to SIC2 (§4.2).

Constants and `add_one_month`:

```19:24:Character_Panels/timing.py
MONTHLY_KEYS = ["permno", "signal_yyyymm", "target_yyyymm"]
ANNUAL_ID_COLUMNS = ["permno", "permco", "gvkey", "datadate", "sic", "fyear"]

# SAS Greens_code.sas L484, L505-L508
GREEN_ANNUAL_WINDOW_START_LAG_MONTHS = 7
GREEN_ANNUAL_WINDOW_END_LAG_MONTHS = 20  # exclusive upper bound in SAS join
```

```58:64:Character_Panels/timing.py
def add_one_month(yyyymm: int) -> int:
    year = yyyymm // 100
    month = yyyymm % 100
    next_month = month + 1
    next_year = year + (next_month == 13)
    next_month = 1 if next_month == 13 else next_month
    return next_year * 100 + next_month
```

- `MONTHLY_KEYS` is the universal join key for monthly-native CSVs — bm_ia and
  the panel both key on exactly these three columns.
- The Green constants (7/20-month window) define the *other* convention
  (`expand_annual_file_green`, used by Green annual chars, not by bm/bm_ia).

### 5.2 `output_paths.py :: resolve_output_path()`

```71:78:output_paths.py
def resolve_output_path(path, default_dir=CHARACTER_INDIVIDUAL_DIR):
    """Resolve a writer path; bare filenames go to default_dir (individual chars by default)."""
    path = Path(path)
    if path.is_absolute():
        return path
    if len(path.parts) == 1:
        return default_dir / path
    return PROJECT_ROOT / path
```

- A bare filename like `"book_to_market.csv"` or `"bm_ia.csv"` lands in
  `outputs/characteristics/individual/`. An absolute path or a relative path
  with subdirectories is honored as-is. This is why both builders default to
  writing into the individual-character directory.

### 5.3 `output_paths.py :: crsp_universe_filter()`

```164:172:output_paths.py
def crsp_universe_filter(table_alias: str = "n") -> str:
    """Return an SQL predicate fragment for the CRSP share/exchange code filters."""
    shrcd, exchcd = get_crsp_universe()
    parts = []
    if not _crsp_code_filter_disabled(shrcd):
        parts.append(f"{table_alias}.shrcd IN ({_sql_int_list(shrcd)})")
    if not _crsp_code_filter_disabled(exchcd):
        parts.append(f"{table_alias}.exchcd IN ({_sql_int_list(exchcd)})")
    return " AND ".join(parts) if parts else "TRUE"
```

- Reads `STOCK_CHARACTERS_CRSP_SHRCD` / `STOCK_CHARACTERS_CRSP_EXCHCD` (set by
  `cfg.apply_env()` from the profile). For datashare, shrcd is `ALL` → no
  share-code filter (only exchcd 1,2,3). For green, shrcd 10,11 + exchcd 1,2,3.
- `_crsp_code_filter_disabled` treats `ALL`/`*`/empty as "no filter".
- Returns a SQL fragment injected into the CRSP query in §3.3.

### 5.4 `Character_Builders/_shared/ccm.py :: load_ccm_links()` and `attach_ccm_links()`

```68:88:Character_Builders/_shared/ccm.py
def load_ccm_links(db, linktypes=None, linkprim=None):
    from _shared.green_builders import raw_sql_with_retry

    linkprim_clause = _linkprim_clause(linkprim)
    if _is_prefix_rule(linktypes):
        linktype_clause = "linktype LIKE 'L%'"
    else:
        codes = parse_ccm_codes(linktypes, DEFAULT_CCM_LINKTYPES)
        linktype_clause = f"linktype IN ({sql_code_list(codes)})"

    link = raw_sql_with_retry(db, f"""
        SELECT gvkey, lpermno AS permno, lpermco AS permco,
               linktype, linkprim, linkdt, linkenddt
        FROM crsp.ccmxpf_linktable
        WHERE {linktype_clause}
          {linkprim_clause}
          AND lpermno IS NOT NULL
    """)
    link["linkdt"] = pd.to_datetime(link["linkdt"])
    link["linkenddt"] = pd.to_datetime(link["linkenddt"])
    return link
```

- Pulls the CRSP-Compustat link table. `linktypes` is either an explicit code
  list (`LU,LC`) or the Dacheng prefix rule `L*` (datashare), which becomes
  `linktype LIKE 'L%'` — every linktype starting with L.
- `linkprim` (P,C / ALL) is added as an `AND linkprim IN (...)` clause, or
  omitted when ALL (no filter).
- Returns `gvkey -> permno/permco` with the link date window.

```165:179:Character_Builders/_shared/ccm.py
def attach_ccm_links(comp, link):
    linked = comp.merge(link, on="gvkey", how="inner")
    linked = linked[
        (linked["datadate"] >= linked["linkdt"])
        & ((linked["datadate"] <= linked["linkenddt"]) | linked["linkenddt"].isna())
    ].copy()

    linked["linkprim_priority"] = linked["linkprim"].map({"P": 0, "C": 1}).fillna(2)
    linked = linked.sort_values(
        ["gvkey", "datadate", "linkprim_priority", "permno", "linkdt"]
    )
    # Keep one permno per gvkey-datadate (primary link first), so HXZ builders stay
    # well-defined even when --ccm-linkprim=ALL admits multiple links per firm.
    linked = linked.drop_duplicates(["gvkey", "datadate"], keep="first")
    return linked.drop(columns=["linkdt", "linkenddt", "linkprim_priority"])
```

- Inner-merge Compustat with the link table on `gvkey`, then keep only rows
  whose `datadate` falls inside the link window (`linkdt <= datadate <= linkenddt`,
  with a missing `linkenddt` treated as open-ended).
- `linkprim_priority` ranks P (primary) before C before anything else, so when
  `--ccm-linkprim=ALL` admits multiple links per firm, the sort + dedup keeps the
  **primary** permno per `gvkey x datadate`. This is what makes `book_to_market`
  well-defined (one permno per firm-year) regardless of the linkprim setting.

---

## 6. `pipeline_config.py` — the single source of truth

This is where the five required flags get their per-profile values. The
datashare profile is the one relevant to bm/bm_ia matching datashare.csv.

### 6.1 The alias map (bm -> book_to_market)

```36:43:pipeline_config.py
DATASHARE_PANEL_ALIAS: dict[str, str] = {
    "bm": "book_to_market",
    "operprof": "operating_profitability",
    "mve_ia": "me_ia",
    "rd_mve": "rdm",
    "retvol": "rvar_mean",
    "ear": "abr",
}
```

- `bm` in datashare.csv maps to the repo column `book_to_market`. `bm_ia` is not
  in this map, so it keeps its own name. This map drives the datashare allowlist
  used by both the batch builder (§2.1) and the panel builder (§7).

### 6.2 The datashare profile

```234:251:pipeline_config.py
    if profile == "datashare":
        return PipelineConfig(
            profile="datashare",
            sample_start="1957-01-01",
            green_universe=False,
            skip_ibes=True,
            build_hxz=True,
            build_research_panel=False,
            skip_special=False,
            skip_daily=False,
            ccm_linktypes=DATASHARE_CCM_LINKTYPES,
            ccm_linkprim=DATASHARE_CCM_LINKPRIM,
            crsp_shrcd=DATASHARE_CRSP_SHRCD,
            crsp_exchcd=DEFAULT_CRSP_EXCHCD,
            industry_agg="post_ccm",
            sic_source="comp_company",
            datashare_columns=("bm", "operprof", "cfp"),
        )
```

- `ccm_linktypes="L*"` (Dacheng prefix rule), `ccm_linkprim="P,C"`,
  `crsp_shrcd="ALL"` (no share-code filter), `crsp_exchcd="1,2,3"`,
  `sample_start="1957-01-01"`, `industry_agg="post_ccm"` (benchmarks on the
  CRSP-investable panel, not full Compustat), `sic_source="comp_company"` (the
  4-digit Compustat SIC that flows into bm_ia's SIC2).
- `build_research_panel=False` → only the signal panel is built (§1.7).

### 6.3 `apply_env()` and `validate_required()`

```181:196:pipeline_config.py
    def apply_env(self) -> None:
        """Push sample bounds + CCM/CRSP filters into the environment for WRDS SQL."""
        for key, value in (
            ("STOCK_CHARACTERS_SAMPLE_START", self.sample_start),
            ("STOCK_CHARACTERS_SAMPLE_END", self.sample_end),
            ("STOCK_CHARACTERS_CCM_LINKTYPE", self.ccm_linktypes),
            ("STOCK_CHARACTERS_CCM_LINKPRIM", self.ccm_linkprim),
            ("STOCK_CHARACTERS_CRSP_SHRCD", self.crsp_shrcd),
            ("STOCK_CHARACTERS_CRSP_EXCHCD", self.crsp_exchcd),
            ("STOCK_CHARACTERS_INDUSTRY_AGG", self.industry_agg),
            ("STOCK_CHARACTERS_SIC_SOURCE", self.sic_source),
        ):
            if value:
                os.environ[key] = value
            else:
                os.environ.pop(key, None)
```

- `apply_env()` is the bridge from the frozen config to the environment variables
  that the WRDS-facing helpers read (`crsp_universe_filter`, CCM loaders, etc.).
  This is how a single `--profile datashare` propagates to every SQL query.

```198:214:pipeline_config.py
    def validate_required(self) -> None:
        """Ensure the five required global flags are set (directly or via a profile)."""
        required = {
            "--ccm-linktypes": self.ccm_linktypes,
            "--ccm-linkprim": self.ccm_linkprim,
            "--crsp-shrcd": self.crsp_shrcd,
            "--crsp-exchcd": self.crsp_exchcd,
            "--sample-start": self.sample_start,
        }
        missing = [flag for flag, value in required.items() if not value]
        if missing:
            raise ValueError(
                "Missing required pipeline flag(s): "
                + ", ".join(missing)
                + ". Pass them explicitly or use --profile green|datashare|research. "
                "See the 'Required flags & recipes' section in README.md / docs/CONFIGURATION.md."
            )
```

- Refuses to run unless all five required flags are set. This guarantees no
  build can accidentally use a silent default convention.

## 7. `Character_Panels/build_all_character_panel.py` — merging bm/bm_ia into the panel

This is the last step. It reads every per-character CSV (including
`book_to_market.csv` and `bm_ia.csv`), normalizes each to a monthly frame, and
outer-merges them all on `MONTHLY_KEYS`.

### 7.1 `classify_stem()` and `normalize_character_file()`

```185:193:Character_Panels/timing.py
def classify_stem(stem: str, columns: Iterable[str]) -> TimingConvention | None:
    """Infer how a CSV should be normalized from its stem and columns."""
    column_set = set(columns)
    if set(MONTHLY_KEYS).issubset(column_set):
        return TimingConvention.MONTHLY_NATIVE
    if {"permno", "datadate"}.issubset(column_set):
        return timing_convention_for_stem(stem)
    return None
```

- If a CSV already has the three `MONTHLY_KEYS` columns → `MONTHLY_NATIVE`
  (no expansion needed). **`bm_ia.csv` hits this branch** (§4.1 schema).
- If a CSV has `permno` + `datadate` (annual) → look up the stem's convention.
  `book_to_market` is in `HXZ_JUNE_STEMS` → `HXZ_JUNE` (§5.1 expansion).

```107:130:Character_Panels/build_all_character_panel.py
def normalize_character_file(path, crsp_month_index=None, force_june_annual=False):
    df = pd.read_csv(path)
    character_columns = infer_character_columns(df)
    if not character_columns:
        return None

    stem = Path(path).stem
    convention = classify_stem(stem, df.columns)
    if convention is None:
        return None

    if convention == TimingConvention.MONTHLY_NATIVE:
        keep = MONTHLY_KEYS + [
            column for column in ["permco", "gvkey", "sic"] if column in df.columns
        ] + character_columns
        return df[keep]

    if force_june_annual:
        return expand_annual_file_june(df, character_columns)

    if convention == TimingConvention.GREEN_ANNUAL_ROLLING:
        return expand_annual_file_green(df, character_columns, crsp_month_index=crsp_month_index)

    return expand_annual_file_june(df, character_columns)
```

- `infer_character_columns` (lines 98-104) keeps numeric columns that are not in
  `KNOWN_NON_CHARACTER_COLUMNS` — for `book_to_market.csv` that is just
  `book_to_market`; for `bm_ia.csv` that is just `bm_ia`.
- **bm_ia path**: `MONTHLY_NATIVE` → just select the keys + `sic` + `bm_ia`. No
  expansion, because bm_ia was already expanded and demeaned in §4.
- **book_to_market path**: `HXZ_JUNE` → `expand_annual_file_june` (§5.1) turns
  the annual rows into 12 monthly signal rows each. So `bm` enters the panel
  through the *same* June expansion that bm_ia used internally — the two are
  aligned cell-for-cell.

### 7.2 `merge_panels()` and `coalesce_metadata()`

```168:191:Character_Panels/build_all_character_panel.py
def merge_panels(panels):
    final = None
    for panel in panels:
        value_columns = [
            column
            for column in panel.columns
            if column not in set(MONTHLY_KEYS + ["permco", "gvkey", "sic"])
        ]
        panel = panel[MONTHLY_KEYS + value_columns].drop_duplicates(MONTHLY_KEYS)
        if final is None:
            final = panel
        else:
            # Drop columns already in final (except join keys) to prevent pandas 3.0
            # MergeError from duplicate non-key columns across files.
            dup_cols = [c for c in panel.columns if c in final.columns and c not in MONTHLY_KEYS]
            if dup_cols:
                panel = panel.drop(columns=dup_cols)
            final = final.merge(panel, on=MONTHLY_KEYS, how="outer")

    metadata = coalesce_metadata(panels)
    if metadata is not None:
        final = metadata.merge(final, on=MONTHLY_KEYS, how="right")

    return final
```

- Each panel is reduced to `MONTHLY_KEYS + value_columns` and deduped on the keys.
- Panels are outer-merged on `MONTHLY_KEYS`, so a (permno, signal month) present
  in any one CSV survives. `book_to_market` and `bm_ia` are joined here into one
  wide row per (permno, signal_yyyymm, target_yyyymm).
- The `dup_cols` guard drops any non-key column that already exists in `final`
  (e.g. `sic` appearing in multiple files) to avoid pandas 3.0 `MergeError`.
- `coalesce_metadata` (lines 133-165) then re-attaches `sic` by taking the first
  non-null value across all panels for each monthly key, and right-merges it
  back so every row carries an `sic` (the 4-digit Compustat SIC, later truncated
  to SIC2 wherever needed).

### 7.3 `build_all_character_panel()` and `main()`

```215:276:Character_Panels/build_all_character_panel.py
def build_all_character_panel(
    input_dir=None,
    force_june_annual=False,
    green_universe=False,
    green_winsor=False,
    profile=None,
):
    allowlist = datashare_output_columns() if profile == "datashare" else None
    if input_dir is None:
        paths = list(iter_character_csv_paths())
    else:
        input_dir = Path(input_dir)
        paths = sorted(input_dir.glob("*.csv"))
        if input_dir == CHARACTER_INDIVIDUAL_DIR and LEGACY_FLAT_OUTPUT_DIR.exists():
            legacy = {p.name for p in paths}
            for path in sorted(LEGACY_FLAT_OUTPUT_DIR.glob("*.csv")):
                if path.name not in legacy and path.name not in NON_CHARACTER_FILES:
                    paths.append(path)

    crsp_month_index = _load_crsp_month_index(paths)

    panels = []
    skipped = []
    for path in paths:
        if path.name in NON_CHARACTER_FILES:
            continue
        if allowlist is not None and path.stem not in allowlist:
            continue
        panel = normalize_character_file(
            path,
            crsp_month_index=crsp_month_index,
            force_june_annual=force_june_annual,
        )
        if panel is None:
            skipped.append(path.name)
            continue
        panels.append(panel)

    if not panels:
        raise FileNotFoundError(
            f"No compatible character CSV files found in {Path(input_dir).resolve()}."
        )

    panel = merge_panels(panels)
    if green_universe:
        before = len(panel)
        panel, resolved = apply_green_universe_screen(panel)
        print(
            f"Green universe screen on {resolved}: {before:,} -> {len(panel):,} rows "
            f"({len(panel) / before:.1%} retained)."
        )
    if green_winsor:
        import sys

        builders_root = PROJECT_ROOT / "Character_Builders"
        if str(builders_root) not in sys.path:
            sys.path.insert(0, str(builders_root))
        from _shared.green_winsor import apply_green_winsorization  # noqa: WPS433

        panel = apply_green_winsorization(panel, month_col="signal_yyyymm")
        print("Applied Green SAS monthly winsorization (p1/p99 or p99 by variable).")
    return panel, skipped
```

- `allowlist = datashare_output_columns()` for `--profile datashare` restricts
  the merge to the 95 mapped columns. `book_to_market` (alias of `bm`) and
  `bm_ia` are both in the allowlist, so both are included.
- `crsp_month_index` (from `me.csv`/`mvel1.csv`, §`_load_crsp_month_index`) is
  the CRSP month universe used to constrain Green rolling-annual expansion —
  not needed for the June-expanded `book_to_market` or the monthly-native
  `bm_ia`, but harmless.
- Each file is normalized (§7.1) and collected; incompatible files are skipped.
- `merge_panels` (§7.2) produces the wide panel.
- `green_universe` drops rows missing bm/mom1m/mve (Green's final screen) — off
  for datashare. `green_winsor` applies Green's monthly winsorization — also off
  for datashare, so bm/bm_ia reach the panel unwinsorized.

`main()` (lines 279-342) parses `--input-dir`, `--output`, the universe/winsor
flags, and `--profile`, calls `build_all_character_panel`, and writes the result
to `SIGNAL_PANEL_FILE`. The printed "Character columns" count excludes the
monthly keys and `sic`.

---

## 8. End-to-end recap (bm and bm_ia)

1. `run_full_pipeline.py --profile datashare` resolves the config and pushes
   the five flags into the environment (§1.9, §6.3).
2. `build_book_to_market.py` pulls Compustat + CRSP, builds book equity and
   December firm market equity, merges on `permco x calendar_year`, takes the
   ratio on real `datadate`, and writes `book_to_market.csv` (annual) (§3).
3. `build_bm_ia.py` reads that CSV, June-expands it to monthly, and demeans
   within (SIC2, signal month), writing `bm_ia.csv` (monthly-native) (§4).
4. `build_all_character_panel.py` reads both CSVs: it June-expands
   `book_to_market.csv` (same expansion bm_ia used) and takes `bm_ia.csv` as-is,
   then outer-merges everything on `(permno, signal_yyyymm, target_yyyymm)` into
   `all_character_signal_panel.csv` (§7).

Key alignment guarantees:
- bm and bm_ia share the **identical June expansion** (`expand_annual_file_june`),
  so they live on the same monthly cells.
- bm_ia's SIC2 is derived from the **same 4-digit Compustat `sic`** carried by
  `book_to_market.csv`, truncated to two digits inside the demean.
- The demean universe is recomputed **every signal month** over that month's
  expanded universe — this monthly churn, not the firm's own bm, drives the
  month-to-month movement of bm_ia.

<!-- END -->
