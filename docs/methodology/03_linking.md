# CRSP–Compustat (CCM) Linking

Source: `Character_Builders/_shared/ccm.py`, `Greens_code.sas` L410-417, GKX `accounting_60.py`
L184-235.

## Link tables and filters

| | Link types | Link primaries | Date rule | Source |
|---|---|---|---|---|
| **Repo default (HXZ)** | `LU, LC` | `P, C` | `linkdt ≤ datadate ≤ linkenddt` (open-ended `linkenddt` allowed) | `ccm.py` L6-7, L100-105 |
| **Repo Green** (`load_ccm_links_green`) | `LU, LC, LD, LF, LN, LO, LS, LX` | **none** | `(year(linkdt) ≤ 2015 or null)` and `(year(linkenddt) ≥ 1950 or null)`; open-ended dates treated as missing | `ccm.py` L9, L69-97 |
| **Green SAS** | `LU, LC, LD, LF, LN, LO, LS, LX` | **none** | same as above | `Greens_code.sas` L411-416 |
| **GKX** | `substr(linktype,1,1)='L'` (all `L*`) | `C, P` | `linkdt ≤ jdate ≤ linkenddt` (missing `linkenddt` → today) | `accounting_60.py` L184-207 |

## Key code

```6:9:Character_Builders/_shared/ccm.py
DEFAULT_CCM_LINKTYPES = ("LU", "LC")
DEFAULT_CCM_LINKPRIM = ("P", "C")
# Green SAS L410-412 (broader linktype set, no linkprim filter).
GREEN_CCM_LINKTYPES = ("LU", "LC", "LD", "LF", "LN", "LO", "LS", "LX")
```

```100:111:Character_Builders/_shared/ccm.py
def attach_ccm_links(comp, link):
    linked = comp.merge(link, on="gvkey", how="inner")
    linked = linked[(linked["datadate"] >= linked["linkdt"]) & (...)]
    linked["linkprim_priority"] = linked["linkprim"].map({"P": 0, "C": 1}).fillna(2)
    ...
```

## Handling of multiple securities / share classes

- **Repo default (`attach_ccm_links`):** when a gvkey links to several permnos, rows are ordered by
  `linkprim_priority` (P before C before other) then `linkdt`, and the first is kept per
  `(gvkey, datadate)` downstream. This favors the CRSP/Compustat **primary** security.
- **Repo Green (`attach_ccm_links_green`):** no linkprim filter; date-validity only (matches Green SAS,
  which relies on `LC/LU/...` link types without a linkprim screen). Duplicate `(gvkey, datadate)`
  resolved by the SAS `nodupkey` sort.
- **GKX:** keeps `linkprim in (C,P)`; dedupes by `(datadate, permno, linkprim)` then
  `(permno, yearend, datadate)`; **firm-level (permco) market equity** is aggregated across share
  classes and assigned to the largest-ME permno (`accounting_60.py` L160-177) — i.e., multiple share
  classes are summed into one firm market cap.
- **HXZ builders** aggregate December market equity by **permco** as well
  (`HXZ_*_Generalized/*.py` `december_firm_market_equity`).

## What the repository uses

- The **canonical Green panel** uses the **Green CCM rule** when run with `--green-universe` /
  `load_ccm_links_green`; otherwise the default `LU,LC` + `P,C` rule. The residual permno surplus over
  Green's output is attributable to the linkprim difference and the final `mve/mom1m/bm` screen, not
  the share-code filter (see `04_filters_and_universe.md` and
  `docs/gkx/green_universe_and_mismatch_audit.md`).
- The **GKX-exact layer** (`GKX_datashare/build_datashare_chars.py`) reproduces GKX's
  `L*` + `(C,P)` rule, permco ME aggregation, and dedupe order exactly.
