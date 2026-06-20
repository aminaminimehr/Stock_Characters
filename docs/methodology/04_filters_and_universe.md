# Exchange / Share-Code Filters and the Stock-Universe Audit

This document covers (a) the exchange/share-code/price/financial/microcap filters and (b) the
detailed stock-universe investigation requested: what GKX applies, what Green applies, what the
repository applies, whether they match, and whether discrepancies materially affect characters.

## 1. Filter comparison

| Filter | Green SAS | GKX (`accounting_60.py`) | Repository | Match? |
|---|---|---|---|---|
| **Exchange** | `exchcd in (1,2,3)` (NYSE/AMEX/NASDAQ) | `exchcd 1–3` | `exchcd 1,2,3` | ✅ all agree |
| **Share code** | `shrcd in (10,11)` (12 considered then dropped) | `shrcd 10,11` | `shrcd 10,11` | ✅ all agree |
| **Price < $5** | none | none | none | ✅ none excludes |
| **Financial firms** | not excluded | not excluded | not excluded | ✅ none excludes |
| **Microcap** | not excluded | not excluded | not excluded | ✅ none excludes |
| **Annual data screen** | `at, prcc_f, ni` non-missing; `datadate ≥ 1975` | non-missing key fields | built full history; screened at panel | partial (timing) |
| **Final sample screen** | `mve, mom1m, bm` all non-missing | (n/a — datashare keeps raw) | `--green-universe` replicates it | optional flag |

### Code evidence

**Green SAS** (`Greens_code.sas`):

```427:445:Supplementary_assistive_files/SAS_codes/Greens_code.sas
*----------------------screen for only NYSE, AMEX, NASDAQ, and common stock-------------;
proc sort data=crsp.mseall(keep=date permno exchcd shrcd siccd) out=mseall nodupkey;
    where exchcd in (1,2,3) or shrcd in (10,11,12);
    ...
data temp;
    set temp;
    where exchcd in (1,2,3) and shrcd in /*(10,11,12)*/ (10,11) and not missing(permno);
```

```1147:1152:Supplementary_assistive_files/SAS_codes/Greens_code.sas
data temp;
    set temp7;
    where not missing(mve) and not missing(mom1m) and not missing(bm);
```

**Repository** Green universe screen (`Character_Panels/build_all_character_panel.py`):

```63:92:Character_Panels/build_all_character_panel.py
# Green SAS final sample screen (Greens_code.sas L1147-1152):
#   where not missing(mve) and not missing(mom1m) and not missing(bm)
GREEN_UNIVERSE_REQUIRED = ("bm", "mom1m", "mve")
GREEN_UNIVERSE_ALIASES = {"mve": ("mve", "mvel1", "me")}
```

Activated by `--green-universe` (CLI), `GREEN_UNIVERSE=1` (shell), or `run_full_pipeline.py`. Off by
default (full CRSP spine retained).

## 2. Stock-universe investigation (the GKX paper claim)

**Paper quote:** *"We include stocks with prices below \$5, share codes beyond 10 and 11, and
financial firms."*

**Finding — paper vs code discrepancy inside GKX itself:**

1. **Price < \$5:** Neither Green, GKX's code, nor the repo applies a price filter. The paper's
   statement that low-price stocks are *included* is consistent with all three. ✅
2. **Financial firms:** No SIC-based financial exclusion anywhere. The paper's claim holds. ✅
3. **"Share codes beyond 10 and 11":** This is the one place the **paper text and GKX's own
   `accounting_60.py` disagree.** The code restricts to `shrcd in (10,11)` (common stock). Green does
   the same. The repository matches the **code**, not the literal paper text.

**Interpretation:** the GKX text describes their philosophy of *not adding* the usual anomaly-study
exclusions (no \$5 floor, no financial-firm drop). But their construction code — and the published
`datashare.csv` — still rests on the common-stock / major-exchange CRSP base (`shrcd 10,11`,
`exchcd 1–3`). The repository is therefore **consistent with the code that produced `datashare.csv`**,
which is the artifact we validate against.

## 3. Does the repository match either approach?

- **Exchange + share code:** the repo matches **both** Green and GKX exactly (`exchcd 1–3`,
  `shrcd 10,11`).
- **CCM linkprim:** default repo (`P,C`) differs from Green (none); `--green-universe` switches to
  Green's broader link-type set. GKX uses `(C,P)` like the repo default.
- **Final screen:** off by default; `--green-universe` reproduces Green's `mve/mom1m/bm` non-missing
  screen.

## 4. Material effect on character construction

- **Share-code / exchange / price / financial filters:** identical across all three → **no material
  effect**; these are not the source of the permno-count surplus over Green's output.
- **CCM linkprim + final screen:** these *do* change the row count (the repo retains more permnos than
  Green's output unless `--green-universe` is set). They affect **coverage**, not the **formula** of a
  character. Industry-adjusted variables are mildly sensitive because the industry mean is computed
  over whatever cross-section survives the screen (see `05_industry_definitions.md`).
- **Documented in:** `docs/gkx/green_universe_and_mismatch_audit.md`.

## 5. Recommended configuration to match Green exactly

```
--green-universe            # final mve/mom1m/bm screen + Green CCM link rule
```
Run without the flag for the broad research universe (default), with it for Green-exact validation.
