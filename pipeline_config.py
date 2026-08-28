"""Hardcoded datashare pipeline conventions.

This module is the single source of truth for WRDS filters, sample bounds,
industry aggregation, and the 95 GKX datashare predictor column names.
There are no profiles, flags, or environment-variable overrides for these values.
"""
from __future__ import annotations

# WRDS sample window (formerly --profile datashare --sample-start 1950-01-01).
SAMPLE_START = "1950-01-01"
SAMPLE_END = None

# CRSP-Compustat link table: Dacheng/datashare recipe (L* prefix + primary links).
CCM_LINKTYPES = "L*"
CCM_LINKPRIM = "P,C"

# CRSP universe: no share-code filter (ALL) is critical for bm_ia industry means.
CRSP_SHRCD = "ALL"
CRSP_EXCHCD = "1,2,3"

# Industry benchmarks computed after CRSP-Compustat merge (CRSP-investable only).
INDUSTRY_AGG = "post_ccm"

# SIC metadata from Compustat comp.company.sic.
SIC_SOURCE = "comp_company"

# IBES tables are not used; re/sue use Compustat-only surprise where applicable.
SKIP_IBES = True

# All 95 GKX datashare signal predictors (excl. permno, DATE). Column names match datashare.csv.
DATASHARE_PREDICTORS: tuple[str, ...] = (
    "convind",
    "rd_sale",
    "rd_mve",
    "realestate",
    "dy",
    "dolvol",
    "saleinv",
    "mom1m",
    "secured",
    "depr",
    "beta",
    "betasq",
    "sp",
    "mvel1",
    "ill",
    "lev",
    "salecash",
    "roic",
    "cashpr",
    "ep",
    "baspread",
    "tang",
    "quick",
    "currat",
    "salerec",
    "zerotrade",
    "std_dolvol",
    "retvol",
    "std_turn",
    "securedind",
    "gma",
    "mom6m",
    "pctacc",
    "maxret",
    "mom12m",
    "acc",
    "absacc",
    "chmom",
    "mom36m",
    "cfp",
    "orgcap",
    "idiovol",
    "cashdebt",
    "chcsho",
    "sgr",
    "pchsale_pchxsga",
    "chinv",
    "pchsale_pchinvt",
    "pchsaleinv",
    "hire",
    "grltnoa",
    "lgr",
    "turn",
    "pchgm_pchsale",
    "egr",
    "pchquick",
    "pchcurrat",
    "pchdepr",
    "pchsale_pchrect",
    "invest",
    "divi",
    "stdcf",
    "stdacc",
    "divo",
    "cash",
    "grcapx",
    "rd",
    "sin",
    "sic2",
    "pricedelay",
    "tb",
    "chatoia",
    "age",
    "herf",
    "ps",
    "mve_ia",
    "roaq",
    "bm",
    "chempia",
    "rsup",
    "roeq",
    "operprof",
    "chtx",
    "nincr",
    "cinvest",
    "aeavol",
    "bm_ia",
    "ear",
    "chpmia",
    "cfp_ia",
    "roavol",
    "ms",
    "pchcapx_ia",
    "indmom",
    "agr",
)

# Frozenset of the 95 predictor names for allowlist checks during build/merge.
DATASHARE_COLUMNS = frozenset(DATASHARE_PREDICTORS)
