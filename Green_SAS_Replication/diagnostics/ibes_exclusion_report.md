# IBES Exclusion Report

Direct IBES WRDS access is unavailable for this replication. IBES-dependent
variables are retained in the output schema as missing (or Compustat fallback for `sue`).

| Variable | SAS lines | IBES table | Status | Fallback | Output treatment |
|----------|-----------|------------|--------|----------|------------------|
| sue | 684-686 | ibes.statsum_epsus (fpi=6) | Partial | che/mveq when IBES missing | Compustat-only `che/mveq` always |
| disp | 830-831 | ibes.statsum_epsus (fpi=1) | Excluded | None | Column present, NaN |
| chfeps | 832-833 | ibes.statsum_epsus (fpi=1) | Excluded | None | Column present, NaN |
| fgr5yr | 836-856 | ibes.statsum_epsus (fpi=0) | Excluded | None | Column present, NaN |
| meanrec | 858-867 | ibes.recdsum | Excluded | None | Column present, NaN |
| chrec | 872-879 | ibes.recdsum | Excluded | None | Column present, NaN |
| nanalyst | 897-923 | ibes.statsum_epsus | Excluded | Set to 0 post-1989 in SAS cleanup | NaN then 0 post-1989 per SAS cleanup |
| sfe | 899 | ibes.statsum_epsus | Excluded | None | Column present, NaN |
| meanest | 899 | ibes.statsum_epsus | Excluded | None | Column present, NaN |
| ltg | 914-915 | Derived from fgr5yr | Excluded | 0/1 indicator from fgr5yr | 0 post-1989 when fgr5yr missing |
| chnanalyst | 960 | nanalyst lag | Excluded | Depends on nanalyst | NaN / rule-based on stub nanalyst |

## SUE divergence note

Green SAS sets `sue = (actual - medest) / abs(prccq)` when IBES forecast and actual
are available; otherwise `sue = che/mveq`. This replication always uses `che/mveq`,
so agreement with Green SAS will be imperfect wherever IBES was used in the benchmark.