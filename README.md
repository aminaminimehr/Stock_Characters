# Stock Characters

This repository builds stock-market characteristics in Python with explicit
definitions, identifiers, and timing. The first hand-built builders follow the
Hou-Xue-Zhang testing-portfolio documentation; the broader character set is
organized around Green-style SAS definitions.

---

## Table of Contents

- [About / Contact](#about--contact)
- [Why This Repository Exists](#why-this-repository-exists)
- [Reference Documentation](#reference-documentation)
- [CRSP/Compustat Linking Policy](#crspcompustat-linking-policy)
- [WRDS Access](#wrds-access)
- [Requirements](#requirements)
- [Character Builders](#character-builders)
- [Construction Policy](#construction-policy)
- [Imputation Utilities](#imputation-utilities)
- [Panel Construction Workflow](#panel-construction-workflow)
- [Generated Outputs](#generated-outputs)

---

## About / Contact

This project is maintained by Amin Aminimehr. Suggestions, corrections, and
replication notes are welcome. Please open a GitHub issue or contact me at
`aminiman@mail.uc.edu`.

---

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

---

## Reference Documentation

The characteristic definitions and June portfolio timing follow:

Hou, Xue, and Zhang, "Technical Document: Testing Portfolios"  
https://global-q.org/uploads/1/2/2/6/122679606/portfoliostd_2020june.pdf

Green-style character definitions are based on Jeremiah Green's public
empirical asset pricing resources:

- Jeremiah Green's website: https://sites.google.com/site/jeremiahrgreenacctg/home
- Green SAS code: https://drive.google.com/file/d/0BwwEXkCgXEdRQWZreUpKOHBXOUU/view?resourcekey=0-1xjZ8fAc0sTybVC6RADDCA

---

## CRSP/Compustat Linking Policy

Accounting characteristics require a CRSP/Compustat Merged link from `gvkey` to
`permno`/`permco`. This repository makes that choice explicit because the CCM
filter is rarely discussed in signal documentation, but it changes coverage and
occasionally changes the matched security.

This choice directly affects the number of unique `permno` identifiers that
survive into the final dataset. Broader filters can add firms and share classes,
while stricter filters can reduce coverage. The tradeoff is not only about row
count: CCM link types differ in how WRDS classifies the validity and role of the
link, so the filter is also a data-quality and replication choice.

### Default Rule

The default rule is conservative:

```text
linktype in ('LU', 'LC')
linkprim in ('P', 'C')
```

This keeps WRDS link-used/research-complete links and accepts both Compustat
primary (`P`) and CRSP primary (`C`) cases. It is also the default in modern
teaching/tooling examples such as Kai Chen's WRDS linking note and the
`tidyfinance` WRDS CCM helper. The code keeps `P` ahead of `C` when duplicate
links must be ordered.

### Linking Conventions

The table below summarizes the relevant conventions and why this repository
makes the choice configurable.

| Source or codebase | CCM choice visible in the referenced code/documentation | What that choice does | How this repo can match it |
| --- | --- | --- | --- |
| This repository | `linktype in ('LU', 'LC')`; `linkprim in ('P', 'C')` | Uses link-used and research-complete CCM links, while allowing both Compustat-primary and CRSP-primary matches. This is the default conservative rule used by the builders. | Default behavior. No extra flags needed. |
| WRDS/Kai Chen-style examples and `tidyfinance` helpers | Commonly use `LC/LU` with `P/C` | A conservative, teachable default that avoids many stale or secondary historical links while preserving CRSP-primary cases. | Default behavior. |
| Fama-French public portfolio descriptions | Usually state the CRSP and Compustat inputs, but not the exact CCM `linktype`/`linkprim` filters | Replication must choose and report a CCM rule; the public descriptions alone do not fully determine the link table filter. | Start from the default, then validate against Fama-French benchmark moments. |
| Green public SAS code | Uses `crsp.ccmxpf_linktable`; in the visible linking step, an explicit `linktype`/`linkprim` filter is not always shown before the date-valid CCM merge | Broader linking can increase coverage, but may include links that a conservative `LC/LU` filter would drop. | Pass a broader explicit list with `--ccm-linktypes`. |
| Gu-Kelly-Xiu / Xin He style assistive code | Keeps linktypes whose first letter is `L` and `linkprim in ('P', 'C')` | Broadly accepts WRDS link-family records while still restricting to primary Compustat/CRSP link flags. | Use `--ccm-linktypes LU,LC,LD,LF,LN,LO,LS,LX --ccm-linkprim P,C`. |
| Chen-Zimmermann Open Source Asset Pricing | Provides open signal code and downloadable data; the exact applicable linking rule should be checked in the current preparation scripts for the release being compared | Their project is designed for broad reproducible signal coverage, so comparisons should use the release-specific construction code rather than infer the rule from final data files. | Use this repo's CCM flags to run a conservative or broader variant, then compare against the chosen Open Source Asset Pricing release. |

### Builder Flags

Accounting builders expose these choices:

```powershell
python Character_Builders/HXZ_BM_Generalized/build_book_to_market.py --wrds-user YOUR_WRDS_USERNAME --ccm-linktypes LU,LC --ccm-linkprim P,C
```

To reproduce a broader `L*` style link rule, pass the explicit WRDS codes you
want to allow, for example:

```powershell
python Character_Builders/build_all_implemented_characters.py --wrds-user YOUR_WRDS_USERNAME --ccm-linktypes LU,LC,LD,LF,LN,LO,LS,LX --ccm-linkprim P,C
```

---

## WRDS Access

The code does not store WRDS credentials. Use one of the standard local WRDS
authentication methods:

- a local `.pgpass` file,
- WRDS/PostgreSQL environment variables,
- or the optional `--wrds-user` argument where supported.

Do not commit usernames, passwords, `.pgpass` files, downloaded WRDS data, or
generated output CSVs to a public repository.

---

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

---

## Character Builders

### HXZ-Specific Builders

| Acronym | Character | Output column | Folder |
| --- | --- | --- | --- |
| `bm` | Book-to-market | `book_to_market` | `Character_Builders/HXZ_BM_Generalized` |
| `bmj` | Book-to-June-end market equity | `bmj` | `Character_Builders/HXZ_BMJ_Generalized` |
| `op` | Operating profitability to equity | `operating_profitability` | `Character_Builders/HXZ_OPE_Generalized` |
| `cfp` | Cash-flow-to-price | `cash_flow_to_price` | `Character_Builders/HXZ_CFP_Generalized` |

### Green-Style Builders

| Status | Acronyms |
| --- | --- |
| Implemented through the shared Green SAS builder | `acc`, `adm`, `agr`, `alm`, `ato`, `baspread`, `bm_ia`, `cash`, `cashdebt`, `chcsho`, `chpm`, `depr`, `dolvol`, `ep`, `gma`, `grltnoa`, `herf`, `hire`, `ill`, `lev`, `lgr`, `maxret`, `me`, `me_ia`, `mom1m`, `mom6m`, `mom12m`, `mom36m`, `mom60m`, `mvel1`, `noa`, `pctacc`, `pm`, `ps`, `rd_sale`, `rdm`, `roe`, `rvar_mean`, `sgr`, `sp`, `std_dolvol`, `std_turn`, `turn`, `zerotrade` |
| Scaffolded; needs specialized event, IBES, quarterly, or factor-estimation code | `abr`, `beta`, `chtx`, `cinvest`, `dy`, `ni`, `nincr`, `re`, `rna`, `Roa1`, `rsup`, `rvar_capm`, `rvar_ff3`, `seas1a`, `sue` |

The full Green-style target list, descriptions, timing families, and folder
names are tracked in `Character_Builders/CHARACTER_CATALOG.md`.

---

## Construction Policy

The repository separates raw characteristic construction from later panel
operations. Individual character builders write transparent source-level
outputs and keep identifiers such as `permno`, `permco`, `gvkey`, `datadate`,
`fyear`, and `sic` where applicable. Panel builders then assign prediction
months, merge returns, and apply any broader sample rules.

CRSP-based builders restrict the stock universe to common shares on NYSE, AMEX,
and NASDAQ where monthly CRSP data are queried:

```text
shrcd in (10, 11)
exchcd in (1, 2, 3)
```

Monthly return-history characteristics use lagged returns so the signal month
does not include the return being predicted. For example, `mom1m` uses the
previous month's return, `mom6m` uses lags 2 through 6, `mom12m` uses lags 2
through 12, and `mom36m` uses lags 13 through 36. Monthly size variables such
as `me` and `mvel1` use lagged market equity.

Daily CRSP-based monthly characteristics are computed from daily data within a
source month and then placed on the following monthly signal. This keeps daily
statistics such as maximum daily return, bid-ask spread, turnover volatility,
and return volatility out of the contemporaneous return month being predicted.

Annual accounting builders preserve the actual Compustat `datadate` in their
raw files. The monthly prediction panel applies the repository's public June
availability convention: fiscal-year information ending in calendar year `y`
is used from June `y+1` through May `y+2`, with `target_yyyymm` identifying the
next return month.

Return-side files include delisting returns when available. The excess-return
builder also exposes an optional distress-delisting convention:

```powershell
python Return_Builders/build_excess_returns.py --wrds-user YOUR_WRDS_USERNAME --green-delisting-fill
```

This fills selected missing distress delisting returns with `-35%` for
NYSE/AMEX and `-55%` for NASDAQ before computing adjusted returns. This is a
return adjustment, not winsorization.

Winsorization is not applied by the individual character builders. Raw
character CSVs and the default prediction panels are intentionally unwinsorized.
If a research design requires outlier treatment, apply it as a separate,
documented panel step, preferably cross-sectionally by signal month. A common
choice is monthly 1st/99th percentile capping for two-sided variables and
monthly 99th percentile capping for variables that are only high-tail trimmed.

---

## Imputation Utilities

`Imputation` contains early utilities for Fama-French industry-code
assignment and time-by-industry median imputation. This folder is intended to
grow as missing-value handling becomes part of the public workflow.

Included Fama-French industry mapping schemes are 5, 10, 12, 17, 30, 38, 48,
and 49 industries.

---

## Panel Construction Workflow

The raw character builders keep the actual Compustat `datadate`. Monthly
prediction files can be created with
`Character_Panels/build_monthly_character_panel.py`, which assigns each row
an explicit predictor month, `signal_yyyymm`, and a next-month return marker,
`target_yyyymm`.

Annual accounting characteristics are observable at the end of June after the
fiscal-year calendar year. A fiscal year ending in calendar year `y` is repeated
from `signal_yyyymm = June y+1` through `May y+2`; the matching return months
are stored as `target_yyyymm = July y+1` through `June y+2`. For prediction, keep the characteristic value fixed over its valid holding period and merge it with the next-month return, so that signal_yyyymm always precedes target_yyyymm.

### Step 1. Build Individual Character Files

First build the individual character files:

```powershell
python Character_Builders/HXZ_BM_Generalized/build_book_to_market.py --wrds-user YOUR_WRDS_USERNAME
python Character_Builders/HXZ_BMJ_Generalized/build_book_to_june_market_equity.py --wrds-user YOUR_WRDS_USERNAME
python Character_Builders/HXZ_OPE_Generalized/build_operating_profitability.py --wrds-user YOUR_WRDS_USERNAME
python Character_Builders/HXZ_CFP_Generalized/build_cash_flow_to_price.py --wrds-user YOUR_WRDS_USERNAME --use-imputed-market-equity
python Character_Builders/Green_MVEL1_Generalized/build_mvel1.py --wrds-user YOUR_WRDS_USERNAME
```

### Step 2. Build Monthly Excess Returns

Then build monthly excess returns:

```powershell
python Return_Builders/build_excess_returns.py --wrds-user YOUR_WRDS_USERNAME
```

### Step 3. Create The Annual Raw Panel

Then create the annual raw panel with:

```powershell
python Character_Panels/build_annual_character_panel.py
```

### Step 4. Create The Monthly Prediction Panel

Then create the monthly prediction panel with:

```powershell
python Character_Panels/build_monthly_character_panel.py
```

### Step 5. Combine Compatible Character CSV Files

Or combine all compatible generated character CSV files with:

```powershell
python Character_Panels/build_all_character_panel.py
```

### Step 6. Merge Characters With Next-Month Excess Returns

Finally, merge the monthly character panel to next-month excess returns:

```powershell
python Character_Panels/build_complete_prediction_panel.py
```

---

## Generated Outputs

The complete panel is saved to `outputs/complete_prediction_panel.csv`. It keeps
character timing untouched and merges returns on `permno` and `target_yyyymm`.

Generated files are written to the `outputs/` folder by default. The folder is
kept in the repository, but generated data files inside it are ignored by Git.
