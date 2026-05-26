# Stock Characters

This repository builds stock-market characteristics in Python with explicit
definitions, identifiers, and timing. The first hand-built builders follow the
Hou-Xue-Zhang testing-portfolio documentation; the broader character set is
organized around Green-style SAS definitions.

## Why This Repository Exists

There are excellent public resources for empirical asset pricing data, including
large predictor libraries and ready-to-use monthly signal files such as those
used in the Gu-Kelly-Xiu and Chen-Zimmermann/Open Source Asset Pricing projects.
This repository is meant to complement those resources rather than replace them.

The focus here is transparency in construction. Finished characteristic datasets
are very useful, but they do not always expose implementation choices that
matter for research: the exact accounting definition, the CRSP/Compustat link
rule, the market-equity date, fiscal-year timing, treatment of multiple share
classes, and which identifiers or industry codes are preserved for later
imputation or industry adjustment.

For example, some public datasets prioritize broad coverage and final cleaned
signals, while this project keeps intermediate identifiers such as `gvkey`,
`permno`, `permco`, `datadate`, `fyear`, and `sic` in the raw character files.
That makes it easier to audit the construction and to build later steps such as
industry adjustments, missing-value imputations, and return alignment.

This is especially useful when documentation layers emphasize different
conventions, such as citing an original source paper in one place and describing
an adapted construction elsewhere. In those cases, this repo aims to make the
implemented choice explicit and reproducible.

The goal is a small, inspectable codebase where each characteristic states its
definition, timing convention, and data-cleaning choices directly in code and
documentation.

## Reference Documentation

The characteristic definitions and June portfolio timing follow:

Hou, Xue, and Zhang, "Technical Document: Testing Portfolios"  
https://global-q.org/uploads/1/2/2/6/122679606/portfoliostd_2020june.pdf

The broader Green-style character scaffolds and shared builder are based on the
local Green SAS reference file in the private supplementary folder. That folder
is ignored by Git and is not part of the public repository.

## WRDS Access

The code does not store WRDS credentials. Use one of the standard local WRDS
authentication methods:

- a local `.pgpass` file,
- WRDS/PostgreSQL environment variables,
- or the optional `--wrds-user` argument where supported.

Do not commit usernames, passwords, `.pgpass` files, downloaded WRDS data, or
generated output CSVs to a public repository.

## Requirements

The project was developed with the following package versions:

```text
pandas==2.3.3
numpy==2.4.1
wrds==3.4.0
```

Install them with:

```powershell
pip install -r requirements.txt
```

## Generalized Characters

| Character | Source label | Output column | Folder | Definition summary |
| --- | --- | --- | --- | --- |
| Book-to-market | HXZ | `book_to_market` | `Character_Builders/HXZ_BM_Generalized` | Book equity divided by December market equity. |
| Book-to-June-end market equity | HXZ | `bmj` | `Character_Builders/HXZ_BMJ_Generalized` | Split-adjusted book equity per share divided by June-end CRSP price. |
| Operating profitability to equity | HXZ | `operating_profitability` | `Character_Builders/HXZ_OPE_Generalized` | `REVT - COGS - XSGA - XINT`, scaled by current book equity. |
| Cash-flow-to-price | HXZ | `cash_flow_to_price` | `Character_Builders/HXZ_CFP_Generalized` | `IB + DP`, scaled by December market equity. |
| Size | Green SAS / Banz | `mvel1` | `Character_Builders/Green_MVEL1_Generalized` | Monthly log lagged CRSP market equity. |

The full Green-style target list and implementation status are tracked in
`Character_Builders/CHARACTER_CATALOG.md`.

## Imputation Utilities

`Imputation` contains early utilities for Fama-French industry-code
assignment and time-by-industry median imputation. This folder is intended to
grow as missing-value handling becomes part of the public workflow.

Included Fama-French industry mapping schemes are 5, 10, 12, 17, 30, 38, 48,
and 49 industries.

The raw character builders keep the actual Compustat `datadate`. Monthly
prediction files can be created with
`Character_Panels/build_monthly_character_panel.py`, which assigns each row
an explicit predictor month, `signal_yyyymm`, and a next-month return marker,
`target_yyyymm`.

Annual accounting characteristics are observable at the end of June after the
fiscal-year calendar year. A fiscal year ending in calendar year `y` is repeated
from `signal_yyyymm = June y+1` through `May y+2`; the matching return months
are stored as `target_yyyymm = July y+1` through `June y+2`. For prediction, keep
the characteristics fixed and align or lead the return by one month.

First build the individual character files:

```powershell
python Character_Builders/HXZ_BM_Generalized/build_book_to_market.py --wrds-user YOUR_WRDS_USERNAME
python Character_Builders/HXZ_BMJ_Generalized/build_book_to_june_market_equity.py --wrds-user YOUR_WRDS_USERNAME
python Character_Builders/HXZ_OPE_Generalized/build_operating_profitability.py --wrds-user YOUR_WRDS_USERNAME
python Character_Builders/HXZ_CFP_Generalized/build_cash_flow_to_price.py --wrds-user YOUR_WRDS_USERNAME --use-imputed-market-equity
python Character_Builders/Green_MVEL1_Generalized/build_mvel1.py --wrds-user YOUR_WRDS_USERNAME
```

Then create the annual raw panel with:

```powershell
python Character_Panels/build_annual_character_panel.py
```

Then create the monthly prediction panel with:

```powershell
python Character_Panels/build_monthly_character_panel.py
```

Or combine all compatible generated character CSV files with:

```powershell
python Character_Panels/build_all_character_panel.py
```

Generated files are written to the `outputs/` folder by default. The folder is
kept in the repository, but generated data files inside it are ignored by Git.
