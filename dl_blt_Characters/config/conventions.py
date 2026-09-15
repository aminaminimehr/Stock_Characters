"""Hardcoded datashare pipeline conventions for dl_blt_Characters."""
from __future__ import annotations

from pathlib import Path

# Root of this pipeline (dl_blt_Characters/).
PIPELINE_ROOT = Path(__file__).resolve().parents[1]

# WRDS sample window.
SAMPLE_START = "1950-01-01"
SAMPLE_END = None

# CRSP-Compustat link table filters.
CCM_LINKTYPES = "L*"
CCM_LINKPRIM = "P,C"

# CRSP universe: no share-code filter (ALL) is critical for bm_ia industry means.
CRSP_SHRCD = "ALL"
CRSP_EXCHCD = "1,2,3"

# Industry benchmarks computed after CRSP-Compustat merge.
INDUSTRY_AGG = "post_ccm"

# SIC metadata from Compustat comp.company.sic.
SIC_SOURCE = "comp_company"

# Green annual expansion: month lags after fiscal datadate.
ANNUAL_ROLLING_START_LAG = 7
ANNUAL_ROLLING_END_LAG = 20

# Green quarterly expansion window (months relative to monthly signal date).
QUARTERLY_MONTH_START_LAG = -10
QUARTERLY_MONTH_END_LAG = -5

# Output directories.
OUTPUT_ROOT = PIPELINE_ROOT / "outputs"
CACHE_DIR = OUTPUT_ROOT / "cache"
CHARACTERS_DIR = OUTPUT_ROOT / "characters"
PANEL_DIR = OUTPUT_ROOT / "panel"

# All 95 GKX datashare signal predictors (column names match datashare.csv).
DATASHARE_PREDICTORS = (
    "convind", "rd_sale", "rd_mve", "realestate", "dy", "dolvol", "saleinv", "mom1m",
    "secured", "depr", "beta", "betasq", "sp", "mvel1", "ill", "lev", "salecash", "roic",
    "cashpr", "ep", "baspread", "tang", "quick", "currat", "salerec", "zerotrade",
    "std_dolvol", "retvol", "std_turn", "securedind", "gma", "mom6m", "pctacc", "maxret",
    "mom12m", "acc", "absacc", "chmom", "mom36m", "cfp", "orgcap", "idiovol", "cashdebt",
    "chcsho", "sgr", "pchsale_pchxsga", "chinv", "pchsale_pchinvt", "pchsaleinv", "hire",
    "grltnoa", "lgr", "turn", "pchgm_pchsale", "egr", "pchquick", "pchcurrat", "pchdepr",
    "pchsale_pchrect", "invest", "divi", "stdcf", "stdacc", "divo", "cash", "grcapx", "rd",
    "sin", "sic2", "pricedelay", "tb", "chatoia", "age", "herf", "ps", "mve_ia", "roaq",
    "bm", "chempia", "rsup", "roeq", "operprof", "chtx", "nincr", "cinvest", "aeavol",
    "bm_ia", "ear", "chpmia", "cfp_ia", "roavol", "ms", "pchcapx_ia", "indmom", "agr",
)

DATASHARE_COLUMNS = frozenset(DATASHARE_PREDICTORS)

# Monthly identity columns written by category builders.
MONTHLY_ID_COLUMNS = [
    "permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "sic", "exchcd", "shrcd",
]

MONTHLY_MERGE_KEYS = ["permno", "signal_yyyymm", "target_yyyymm"]
