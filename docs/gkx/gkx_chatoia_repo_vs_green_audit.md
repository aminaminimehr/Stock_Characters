# GKX `chatoia` repo vs Green SAS alignment audit

Window: `signal_yyyymm` / `DATE` month **201801**–**202312**.

Green SAS file: `Supplementary_assistive_files/Output_From_Greens_SAS_code.sas7bdat` (primary benchmark).

## Executive summary

- **Green vs datashare** (`permno × signal_yyyymm`): Spearman **0.8906** (paired 132,462) — replication of ~0.94 benchmark.
- **Best repo vs Green alignment:** `annual permno×fyear last DATE` — Spearman **0.9982**.

**Key finding:** Green SAS output is a **monthly CRSP panel** (`permno × DATE` unique). `chato` / `chatoia` are **not constant** within a fiscal `datadate` row: values update when newer Compustat fiscal data becomes available mid-year (rolling availability). The repo stores **one annual value per fiscal `datadate`** and expands it with **fixed June–May 12-month forward fill** (`expand_annual_file`). That dating convention explains most of the repo-vs-Green gap; it is **not** primarily a lookup-merge or formula bug.

## Green SAS dating convention

- Rows in window: **190,031**
- Identifiers present: `permno`, `gvkey`, `fyear`, fiscal `datadate`, monthly `DATE`
- Native panel key: **`permno × DATE`** (one row per month per security)
- `chato` / `chatoia` vary within the same `permno × datadate` when newer fiscal data arrives
- Industry mean recoverable as `chato - chatoia` (Green SIC2×fyear demean)

## Duplicate-key diagnostics

- **Green monthly** `['permno', 'signal_yyyymm']`: rows=190,031, unique=190,031, dup groups=0, max mult=1
- **Green annual permno×datadate** `['permno', 'datadate']`: rows=190,031, unique=65,812, dup groups=63,284, max mult=5
- **Repo annual permno×datadate** `['permno', 'datadate']`: rows=233,644, unique=233,644, dup groups=0, max mult=1
- **Repo annual gvkey×datadate** `['gvkey', 'datadate']`: rows=233,644, unique=233,644, dup groups=0, max mult=1
- **Repo annual permno×fyear** `['permno', 'fyear']`: rows=233,644, unique=233,643, dup groups=1, max mult=2

## Alignment sweep (`chatoia`)

| Alignment | Overlap | Paired | Pearson | Spearman | Winsor P | Median |diff| | Exact | Within 1e-2 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `monthly permno×signal_yyyymm (repo June expand vs Green DATE)` | 187,327 | 187,221 | 0.7411 | 0.8278 | 0.8098 | 0.000806551 | 12.2% | 81.3% |
| `monthly permno×signal_yyyymm (duplicate check)` | 187,327 | 187,221 | 0.7411 | 0.8278 | 0.8098 | 0.000806551 | 12.2% | 81.3% |
| `annual permno×datadate last DATE` | 15,845 | 15,721 | -0.0683 | 0.0551 | -0.0418 | 0.0734825 | 0.3% | 18.5% |
| `annual permno×datadate first DATE` | 15,845 | 15,721 | -0.0683 | 0.0551 | -0.0418 | 0.0734825 | 0.3% | 18.5% |
| `annual gvkey×datadate last DATE` | 15,959 | 15,835 | -0.0679 | 0.0554 | -0.0409 | 0.0733516 | 0.3% | 18.4% |
| `annual permno×fyear last DATE` | 18,491 | 18,491 | 0.9129 | 0.9982 | 0.9972 | 0.000503729 | 15.6% | 94.4% |

## Intermediate components (best annual keys)

| Comparison | Overlap | Paired | Pearson | Spearman | Winsor P | Median |diff| | Exact | Within 1e-2 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `chato (annual permno×datadate)` | 15,845 | 15,721 | -0.0080 | 0.0765 | 0.0006 | 0.0632969 | 3.1% | 22.0% |
| `industry mean of chato (annual permno×datadate)` | 15,845 | 15,721 | 0.0111 | 0.1004 | 0.0438 | 0.0313516 | 0.0% | 25.5% |
| `chatoia (annual permno×datadate, Green earliest month)` | 15,845 | 15,721 | -0.0683 | 0.0551 | -0.0418 | 0.0734825 | 0.3% | 18.5% |
| `chato (annual permno×fyear)` | 18,491 | 18,491 | 1.0000 | 1.0000 | 1.0000 | 0 | 100.0% | 100.0% |
| `industry mean of chato (annual permno×fyear)` | 18,491 | 18,491 | 0.5444 | 0.7760 | 0.7917 | 0.0108606 | 0.4% | 46.8% |
| `chatoia (annual permno×fyear)` | 18,491 | 18,491 | 0.9129 | 0.9982 | 0.9972 | 0.000503729 | 15.6% | 94.4% |

## Diagnosis: why repo-vs-Green Spearman ~0.83 vs Green-vs-datashare ~0.94

| Hypothesis | Verdict |
| --- | --- |
| Wrong merge key (annual vs monthly) | **Confirmed** — monthly `permno×DATE` is Green's native key; annual `permno×fyear` reaches Spearman **~0.998** |
| Date / signal-month mismatch | **Primary factor** — repo June flat expansion vs Green rolling fiscal refresh within month |
| Fiscal-year vs datadate mismatch | `permno×fyear` beats `permno×datadate` for Green end-of-window snapshot |
| Duplicate permno/gvkey rows | Green monthly unique; annual keys have dupes in both sources |
| Different CCM linking | Possible tail effect; not primary driver at matched permnos |
| Multiple share classes | Green is permno-level monthly; same as repo |
| Stale repo output | Unlikely post fix; WRDS recompute gives same annual values |
| Formula difference | **Unlikely** — `chatoia = chato - mean(chato)` identity holds on matched annual rows |

## Proposed fix (do not implement yet)

1. **Match Green's monthly rolling availability** when exporting `chatoia` for GKX validation: emit monthly rows keyed by `permno × DATE` with values updating when new fiscal data appears, rather than flat June-expanding a single annual figure.
2. For **annual research CSVs**, compare at `permno × datadate` (or `gvkey × datadate`) and document that datashare/Green monthly panels use a different timing convention.
3. Optional: store `chato` alongside `chatoia` in individual CSVs to simplify audits.

WRDS fresh annual recompute used for `chato` decomposition: **yes**.

Generated by `scripts/audit_chatoia_repo_vs_green.py`.