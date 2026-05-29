# Stock Characters

This repository builds stock-market characteristics in Python with explicit
definitions, identifiers, and timing. The first hand-built builders follow the
Hou-Xue-Zhang testing-portfolio documentation; the broader character set is
organized around Green-style SAS definitions.

---

## Table of Contents

- [License and Citation](#license-and-citation)
- [About / Contact](#about--contact)
- [Why This Repository Exists](#why-this-repository-exists)
- [Reference Documentation](#reference-documentation)
- [CRSP/Compustat Linking Policy](#crspcompustat-linking-policy)
- [WRDS Access](#wrds-access)
- [Requirements](#requirements)
- [Character Builders](#character-builders)
- [Book-To-Market Specifications](#book-to-market-specifications)
- [Construction Policy](#construction-policy)
- [Imputation Utilities](#imputation-utilities)
- [Panel Construction Workflow](#panel-construction-workflow)
- [Generated Outputs](#generated-outputs)

---

## License and Citation

This repository is released under the [MIT License](LICENSE).

If you use the code or the construction definitions in academic work, please cite the repository. A machine-readable record is provided in [CITATION.cff](CITATION.cff). A standard reference you can adapt in BibTeX is:

```bibtex
@software{aminimehr2026stockcharacters,
  author       = {Aminimehr, Amin},
  title        = {Stock Characters: Reproducible Python Builders for Green-Style and HXZ-Style Signals},
  year         = {2026},
  url          = {https://github.com/aminaminimehr/Stock_Characters},
  note         = {Construction definitions follow Green (2016) SAS programs and Hou-Xue-Zhang (2020) portfolio documentation.}
}
```

Empirical outputs also depend on licensed vendor data accessed through WRDS (CRSP, Compustat, IBES, and Fama-French factors). Follow each provider's terms of use in addition to citing this repository.

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

The book-to-market validation moments reference:

Fama and French, "Dissecting Anomalies"  
https://papers.ssrn.com/sol3/papers.cfm?abstract_id=911960

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
| Implemented through the shared Green annual builder | `acc`, `adm`, `agr`, `alm`, `ato`, `bm`, `bm_ia`, `cash`, `cashdebt`, `cfp`, `chcsho`, `chpm`, `depr`, `dy`, `ep`, `gma`, `grltnoa`, `herf`, `hire`, `lev`, `lgr`, `me_ia`, `noa`, `op`, `pctacc`, `pm`, `ps`, `rd_sale`, `rdm`, `roe`, `sgr`, `sp` |
| Implemented through the shared Green monthly builder | `dolvol`, `me`, `mom1m`, `mom6m`, `mom12m`, `mom36m`, `mom60m`, `mvel1`, `seas1a`, `turn` |
| Implemented through daily-CRSP monthly builders | `baspread`, `ill`, `maxret`, `rvar_mean`, `std_dolvol`, `std_turn`, `zerotrade` |
| Implemented through quarterly Compustat builders | `chtx`, `cinvest`, `ni`, `nincr`, `rna`, `roa1`, `rsup`, `sue` |
| Implemented with specialized factor / event / IBES builders | `abr`, `beta`, `re`, `rvar_capm`, `rvar_ff3` |

The full Green-style target list, descriptions, timing families, and folder
names are tracked in `Character_Builders/CHARACTER_CATALOG.md`.

---

## Book-To-Market Specifications

Book-to-market equity is a central asset-pricing characteristic. It is the
sorting variable behind the value factor in the Fama-French factor model, and
it is also used as a control or benchmark variable in many anomaly tests.
Because small timing or denominator choices can change both coverage and
replication moments, this repository keeps the alternative book-to-market
constructions separate instead of treating them as interchangeable.

The validation reference for the HXZ/Fama-French-style specification is Fama
and French, "Dissecting Anomalies." Their Table I reports annual descriptive
moments for log book-to-market by size group, using June size assignments and
book equity from the prior fiscal year.

The repository currently contains three book-to-market-style specifications:

| Specification | Output column | Builder | Book numerator | Market denominator | Timing interpretation | Primary use |
| --- | --- | --- | --- | --- | --- | --- |
| Green-style `bm` | `bm` | Shared Green builder, emitted by `Character_Builders/Green_BM_IA_Generalized` support code and `build_all_implemented_characters.py` | Compustat common equity, `ceq` | Compustat fiscal-year-end market equity, `prcc_f * csho` | Annual Compustat value later expanded to monthly signals using Green-style availability timing | Best for comparison to Green SAS outputs and Green-style characteristic panels |
| HXZ/Fama-French-style book-to-market equity | `book_to_market` | `Character_Builders/HXZ_BM_Generalized` | Book equity using the standard fallback hierarchy: stockholders' equity from `seq`, then `ceq + preferred stock`, then `at - lt`, plus deferred taxes, minus preferred stock | CRSP December firm market equity for the same calendar year as the fiscal year end | Fiscal year ending in calendar year `t-1` is used for June `t` portfolio formation and July `t` onward prediction windows | Preferred specification for Fama-French/HXZ-style book-to-market validation and benchmark comparisons |
| Book-to-June market equity | `bmj` | `Character_Builders/HXZ_BMJ_Generalized` | Book equity per share from the HXZ-style book-equity construction | CRSP June price/share information | Uses June market valuation rather than prior December market equity | A separate June-price variant; useful when the research design intentionally wants book scaled by the current June market value |

These variables are related, but they are not equivalent. Green `bm` and HXZ
`book_to_market` are conceptually closest because both measure book equity
relative to market equity, but they differ mechanically in both the book
numerator and the market denominator. The Green version is designed to track
Green's SAS convention; the HXZ version is designed to track the
Fama-French/HXZ portfolio-timing convention.

The `bmj` variable is a different timing choice rather than a drop-in
replacement. By using June market valuation, it can be more contemporaneous
with June portfolio formation, but it is not the same object as the standard
Fama-French book-to-market ratio based on December market equity.

For most benchmark work in this repository, use `book_to_market` when the
target is Fama-French or HXZ-style book-to-market equity, use Green `bm` when
the target is Green SAS comparability, and use `bmj` only when a June
market-equity denominator is part of the intended research design.

### Validation Against Fama-French Descriptive Moments

As a benchmark check, the HXZ/Fama-French-style `book_to_market` construction
was filtered to match the sample description in Fama and French's "Dissecting
Anomalies": June size groups based on NYSE 20th and 50th percentile market-cap
breakpoints; positive book equity; available June and prior-December market
equity; and the accounting variables required by the paper's appendix sample.
The reported characteristic is log book-to-market.

The table below compares repository moments to the published Table I moments.
Values are annual equal-weight cross-sectional averages over the benchmark
period, grouped by the paper's size categories.

| Size group | Repository avg firms | Paper avg firms | Repository avg log B/M | Paper avg log B/M | Repository avg cross-section SD | Paper avg cross-section SD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Market | 3143.67 | 3060 | -0.473 | -0.47 | 0.879 | 0.87 |
| Micro | 1910.98 | 1831 | -0.343 | -0.34 | 0.898 | 0.89 |
| Small | 622.86 | 603 | -0.572 | -0.59 | 0.793 | 0.77 |
| Big | 609.83 | 626 | -0.696 | -0.70 | 0.747 | 0.74 |
| All but Micro | 1232.69 | 1229 | -0.643 | -0.65 | 0.775 | 0.76 |

This validation is a sample-filter check only. It does not alter the raw
`book_to_market` builder, which remains a transparent firm-year construction.

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

### Duplicate Reports And Fiscal-Year Changes

Fiscal-year-end changes can create more than one Compustat annual report for
the same firm within a calendar year. After linking to CRSP, this can also
create duplicate or overlapping observations for the same `permno` and signal
month. This issue is rarely discussed explicitly in characteristic
documentation, but it affects reproducibility when annual accounting data are
expanded to monthly prediction panels.

The repository handles these cases explicitly:

- Annual builders keep the most recent Compustat `datadate` within each
  firm-calendar year when multiple annual reports map to the same calendar
  year.
- Generic annual character panel construction resolves duplicate
  `permno`/`signal_yyyymm` rows by keeping the observation with the latest
  underlying `datadate`.
- Raw character files retain `datadate` and `fyear` so these decisions remain
  auditable.

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

### Research-Ready 1957+ Panel

For empirical work that needs a clean machine-learning style panel, the
repository includes a final research-panel step. This step starts from the
complete all-character prediction panel and applies the following operations
only after raw construction and return alignment are complete:

1. Keep target return months from January 1957 onward.
2. Winsorize each characteristic cross-sectionally by `signal_yyyymm` at the
   monthly 1st and 99th percentiles.
3. Assign Fama-French 49-industry codes from SIC.
4. Impute missing characteristic values using `signal_yyyymm` by FF49 industry
   medians, with a same-month cross-sectional median fallback when the industry
   median is unavailable.
5. Cross-sectionally rank each characteristic period by period and map the
   ranks into the `[-1, 1]` interval, following the normalization convention
   used by Kelly, Pruitt, and Su (2019) and Freyberger, Neuhierl, and Weber
   (2020).

The rank transformation is applied separately to each characteristic in each
signal month:

```text
ranked_x = 2 * (rank(x) - 1) / (N - 1) - 1
```

where `N` is the number of nonmissing observations for that characteristic in
the month after winsorization and imputation. Ties receive average ranks. The
final panel therefore keeps the original timing columns and next-month
`excess_return`, while the characteristic columns are normalized predictors.
If an entire characteristic is unavailable in an early month, the final ranked
value is set to `0`, the neutral midpoint of the normalized interval. This keeps
the 1957+ matrix rectangular without pretending that an unavailable
cross-section had informative ranks.

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
are stored as `target_yyyymm = July y+1` through `June y+2`. For prediction,
keep the characteristic value fixed over its valid holding period and merge it
with the next-month return, so that `signal_yyyymm` always precedes
`target_yyyymm`. If fiscal-year-end changes cause overlapping annual signals
for the same `permno` and signal month, the panel keeps the latest available
Compustat `datadate`.

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

For the broad all-character panel, pass the all-character signal file
explicitly:

```powershell
python Character_Panels/build_complete_prediction_panel.py --characters outputs/all_character_signal_panel.csv --returns outputs/excess_returns.csv --output outputs/complete_all_character_prediction_panel.csv
```

### Step 7. Build The 1957+ Research Panel

After the broad prediction panel exists, create the winsorized, industry-median
imputed, rank-normalized research panel with:

```powershell
python Character_Panels/build_research_panel_1957.py
```

Output:

```text
outputs/research_panel_1957_ranked.csv
```

---

## Generated Outputs

The complete panel is saved to `outputs/complete_prediction_panel.csv`. It keeps
character timing untouched and merges returns on `permno` and `target_yyyymm`.

The broad research panel is saved to `outputs/research_panel_1957_ranked.csv`.
It starts in target month `195701`, includes next-month `excess_return`, and
stores each usable characteristic after monthly winsorization, FF49
industry-median imputation, and `[-1, 1]` rank normalization.

Generated files are written to the `outputs/` folder by default. The folder is
kept in the repository, but generated data files inside it are ignored by Git.
