# Share Code Flag Pipeline Design Review

Date: 2026-06-17

This review is for a later agent who will design repository-level support for configurable CRSP share-code filters. No code has been changed by this review.

## Purpose

The current repository mostly assumes the common-stock CRSP universe:

```text
shrcd in (10, 11)
```

That convention is appropriate for many classic asset-pricing panels, but it should not be hard-coded everywhere if the repository is intended to support multiple replication targets. Later users may need to:

- keep only common shares: `10,11`,
- include additional share classes,
- replicate GKX-style broader coverage,
- run sensitivity checks with narrower or broader CRSP universes,
- or explicitly document the exact CRSP share-code universe used in a run.

The pipeline should therefore allow the user to specify share codes at run time.

## Current Situation

The repository documents that monthly CRSP data are queried with:

```text
shrcd in (10, 11)
exchcd in (1, 2, 3)
```

This appears in the main README under the construction policy.

The implementation also has hard-coded share-code filters in multiple places. Important examples include:

- `Character_Builders/_shared/green_builders.py`
- `Return_Builders/build_excess_returns.py`
- HXZ builders such as:
  - `Character_Builders/HXZ_BM_Generalized/build_book_to_market.py`
  - `Character_Builders/HXZ_BMJ_Generalized/build_book_to_june_market_equity.py`
  - `Character_Builders/HXZ_CFP_Generalized/build_cash_flow_to_price.py`
- IBES/monthly matching support code such as:
  - `Character_Builders/_shared/ibes_builders.py`

The current top-level pipeline does not expose a share-code flag. A user running:

```text
python Character_Panels/run_full_pipeline.py ...
```

cannot currently specify a different `shrcd` universe from the top-level command.

## Why This Matters

Share-code filtering is not a cosmetic option. It changes:

- CRSP monthly coverage,
- CRSP daily coverage if the daily builders are aligned to the monthly universe,
- excess-return availability,
- final prediction-panel rows,
- market equity and momentum histories,
- industry adjustment coverage,
- missingness patterns,
- validation correlations versus Green SAS and GKX `datashare.csv`.

If the repository goal is:

1. exact Green SAS replication first,
2. then comparison/modification toward GKX `datashare.csv`,

then share-code conventions must be explicit and reproducible.

Green-style replication and GKX-style datashare comparison may not use the same stock universe assumptions. The repo should make that choice visible rather than burying it inside SQL strings.

## Recommended User Interface

Add a share-code argument to the relevant command-line entry points.

Recommended flag:

```text
--share-codes 10,11
```

Recommended default:

```text
10,11
```

Possible examples:

```text
python Character_Panels/run_full_pipeline.py --wrds-user USER --share-codes 10,11

python Character_Panels/run_full_pipeline.py --wrds-user USER --share-codes 10,11,12

python Character_Panels/run_full_pipeline.py --wrds-user USER --share-codes 10,11,12,18
```

The exact broader GKX share-code list should be verified against the intended source before hard-coding any named GKX profile.

## Recommended Internal Design

The later agent should avoid copy-pasting parsing logic into every builder. Instead, add one shared helper, probably in a shared module such as:

```text
Character_Builders/_shared/crsp_filters.py
```

or an equivalent existing shared location.

The helper should provide:

```text
DEFAULT_SHARE_CODES = (10, 11)
parse_share_codes(value)
sql_int_list(values)
add_crsp_filter_arguments(parser)
```

The parser should accept comma-separated values and possibly whitespace-separated values:

```text
10,11
10, 11
10 11
```

It should validate that all supplied codes are integers. Invalid values should raise a clear error before WRDS queries are run.

## Pipeline Propagation

The flag must be available at the highest-level pipeline command:

```text
Character_Panels/run_full_pipeline.py
```

That top-level script should pass the parsed share-code setting into:

- `Character_Builders/build_all_implemented_characters.py`,
- HXZ standalone builders,
- `Return_Builders/build_excess_returns.py`,
- any panel or research-panel step that directly reloads CRSP.

The bulk builder should then pass it into all loaders that query CRSP monthly or CRSP daily data.

At minimum, the later agent should audit and update these areas:

- monthly CRSP loader in `Character_Builders/_shared/green_builders.py`,
- daily/monthly alignment logic in `green_builders.py`,
- quarterly builders if they build a CRSP monthly alignment frame,
- event builders if they depend on the monthly CRSP universe,
- beta, idiovol, pricedelay, and residual-variance builders if they query CRSP daily independently,
- return builder in `Return_Builders/build_excess_returns.py`,
- HXZ builders that query CRSP monthly directly,
- IBES builders that join IBES events to CRSP names or CRSP monthly securities.

## Important Design Rule

The same share-code convention should be used consistently across:

- character construction,
- excess-return construction,
- final panel merge,
- validation scripts.

It is dangerous to build characteristics with one share-code universe and returns with another. That can silently alter coverage and make validation failures look like formula problems.

## Interaction With Exchange Codes

This review focuses on share codes, but the same design issue exists for exchange codes:

```text
exchcd in (1, 2, 3)
```

The later agent should consider implementing share-code and exchange-code flags together, for example:

```text
--share-codes 10,11
--exchange-codes 1,2,3
```

However, if the work must be staged, share codes should be implemented first because the user explicitly needs configurable share-code coverage.

## Interaction With Profiles

Eventually, the repository would benefit from named convention profiles:

```text
--profile green_exact
--profile repo_default
--profile gkx_datashare
```

These profiles should set share codes along with:

- CCM linktype/linkprim rules,
- timing rules,
- exchange-code rules,
- delisting-return rules,
- IBES inclusion/exclusion,
- winsorization and ranking rules.

Even if profiles are added later, explicit flags such as `--share-codes` should still be allowed. If both are supplied, the command should clearly document whether explicit flags override the profile.

## Documentation Requirement

The later agent must also update the main repository README.

The README should include:

- the default share-code rule,
- how to override it from the top-level pipeline,
- examples of narrower and broader runs,
- a warning that changing share codes changes the security universe and can change validation against Green SAS or GKX datashare,
- a note that the same share-code rule should be used for both characteristics and returns.

Suggested README section title:

```text
CRSP Share-Code And Exchange-Code Policy
```

or, if profiles are implemented:

```text
Pipeline Convention Profiles
```

## Validation Checklist For The Later Agent

After implementing share-code configurability, validate the following:

1. Running with no flag reproduces the current default behavior: `10,11`.
2. Running with `--share-codes 10` produces only `shrcd == 10` rows where `shrcd` is retained.
3. Running with a broader list increases or preserves CRSP coverage relative to `10,11`.
4. Character builders and return builders use the same share-code list.
5. The top-level pipeline logs or prints the active share-code convention.
6. Validation scripts record the share-code convention used.
7. README examples match the actual CLI.

## Bottom Line

The repository currently documents the `10,11` common-share convention but does not expose share-code selection as a first-class pipeline option. A later agent should centralize CRSP universe filtering, add a top-level `--share-codes` flag, propagate it through all CRSP loaders, and document the convention clearly in the main README.
