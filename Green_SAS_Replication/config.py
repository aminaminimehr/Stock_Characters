"""Configuration for isolated Green SAS replication (Greens_code.sas)."""
from __future__ import annotations

from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = MODULE_ROOT.parent
GREEN_SAS_PATH = REPO_ROOT / "Supplementary_assistive_files" / "SAS_codes" / "Greens_code.sas"
GREEN_BENCHMARK_PATH = REPO_ROOT / "Supplementary_assistive_files" / "Output_From_Greens_SAS_code.sas7bdat"

OUTPUT_DIR = MODULE_ROOT / "outputs"
CHECKPOINT_DIR = OUTPUT_DIR / "checkpoints"
DIAGNOSTICS_DIR = MODULE_ROOT / "diagnostics"
DOCS_DIR = MODULE_ROOT / "docs"

FINAL_OUTPUT_PARQUET = OUTPUT_DIR / "rpsdata_green_replication.parquet"
FINAL_OUTPUT_CSV = OUTPUT_DIR / "rpsdata_green_replication.csv"

# Default limited validation window (not full 1975 sample).
DEFAULT_SAMPLE_START = "2018-01-01"
DEFAULT_SAMPLE_END = "2023-12-31"

# SAS Greens_code.sas L411-412
GREEN_CCM_LINKTYPES = ("LU", "LC", "LD", "LF", "LN", "LO", "LS", "LX")

# SAS annual timing L484
GREEN_ANNUAL_START_LAG_MONTHS = 7
GREEN_ANNUAL_END_LAG_MONTHS = 20  # exclusive upper bound

# SAS quarterly-to-monthly L768
QUARTERLY_MONTH_START_LAG = -10
QUARTERLY_MONTH_END_LAG = -5  # intnx(MONTH, date, -5, 'beg')

# SAS IBES monthly merge L902 (excluded; documented only)
IBES_MONTH_START_LAG = -4
IBES_MONTH_END_LAG = -1

# CPI table embedded in SAS L299-345
CPI_BY_YEAR: dict[int, float] = {
    1974: 49.3,
    1975: 53.8,
    1976: 56.9,
    1977: 60.6,
    1978: 65.2,
    1979: 72.6,
    1980: 82.4,
    1981: 90.9,
    1982: 96.5,
    1983: 99.6,
    1984: 103.9,
    1985: 107.6,
    1986: 109.6,
    1987: 113.6,
    1988: 118.3,
    1989: 124.0,
    1990: 130.7,
    1991: 136.2,
    1992: 140.3,
    1993: 144.5,
    1994: 148.2,
    1995: 152.4,
    1996: 156.9,
    1997: 160.5,
    1998: 163.0,
    1999: 166.6,
    2000: 172.2,
    2001: 177.1,
    2002: 179.88,
    2003: 183.96,
    2004: 188.9,
    2005: 195.3,
    2006: 201.6,
    2007: 207.342,
    2008: 215.303,
    2009: 214.537,
    2010: 218.056,
    2011: 224.939,
    2012: 229.594,
    2013: 229.17,
    2014: 229.91,
    2015: 236.53,
}

# SAS L461-470 annual keep list
ANNUAL_OUTPUT_COLS = [
    "gvkey", "permno", "exchcd", "datadate", "fyear", "sic2",
    "bm", "cfp", "ep", "cashpr", "dy", "lev", "sp", "roic", "rd_sale", "rd_mve", "chadv",
    "agr", "invest", "gma", "chcsho", "lgr", "egr", "chpm", "chato", "chinv", "hire", "cf",
    "acc", "pctacc", "absacc", "age", "spii", "spi", "sgr", "pchsale_pchinvt", "pchsale_pchrect",
    "pchgm_pchsale", "pchsale_pchxsga", "pchcapx", "ps", "divi", "divo", "obklg", "chobklg",
    "securedind", "secured", "convind", "conv", "grltnoa", "chdrc", "rd", "rdbias", "chpmia",
    "chatoia", "chempia", "bm_ia", "pchcapx_ia", "tb", "cfp_ia", "mve_ia", "herf", "credrat",
    "credrat_dwn", "orgcap", "m1", "m2", "m3", "m4", "m5", "m6", "grcapx", "depr", "pchdepr",
    "grGW", "tang", "woGW", "sin", "mve_f", "currat", "pchcurrat", "quick", "pchquick",
    "salecash", "salerec", "saleinv", "pchsaleinv", "cashdebt", "realestate", "roe", "operprof",
]

# SAS L750-752 quarterly keep
QUARTERLY_OUTPUT_COLS = [
    "gvkey", "permno", "datadate", "rdq", "chtx", "roaq", "rsup", "stdacc", "stdcf", "sgrvol",
    "roavol", "cash", "cinvest", "nincr", "sue", "aeavol", "ear", "m7", "m8", "prccq", "roeq",
    "che", "mveq",
]

# IBES-related columns kept as NaN (schema match)
IBES_COLUMNS = [
    "disp", "chfeps", "fgr5yr", "meanrec", "chrec", "nanalyst", "sfe", "meanest", "ltg", "chnanalyst",
]

# SAS L1161-1185 winsorization lists (names as in SAS macro)
HITRIM_VARS = [
    "betasq", "mve", "dy", "lev", "baspread", "depr", "sp", "turn", "dolvol", "std_dolvol",
    "std_turn", "disp", "idiovol", "obklg", "roavol", "ill", "age", "rd_sale", "rd_mve", "retvol",
    "zerotrade", "stdcf", "tang", "absacc", "stdacc", "cash", "orgcap", "salecash", "salerec",
    "saleinv", "pchsaleinv", "cashdebt", "realestate", "secured",
]

HILOTRIM_VARS = [
    "beta", "ep", "fgr5yr", "mom12m", "mom1m", "mom6m", "mom36m", "indmom", "sue", "agr", "maxret",
    "chfeps", "bm", "currat", "pchcurrat", "quick", "pchquick", "pchdepr", "sgr", "chempia", "acc",
    "pchsale_pchinvt", "pchsale_pchrect", "pchcapx_ia", "pchgm_pchsale", "pchsale_pchxsga", "mve_ia",
    "cfp_ia", "bm_ia", "sfe", "chinv", "grltnoa", "cinvest", "tb", "cfp", "lgr", "egr", "pricedelay",
    "grcapx", "chmom", "roic", "aeavol", "chcsho", "chpmia", "chatoia", "grGW", "ear", "rsup", "spi",
    "hire", "chadv", "cashpr", "roaq", "roe", "roeq", "invest", "chtx", "pctacc", "gma", "operprof",
]

WINSOR_DUMMY_EXCLUDE = {
    "rd", "eamonth", "ipo", "divi", "divo", "securedind", "convind", "ltg", "credrat_dwn", "wogw",
    "sin", "retcons_pos", "retcons_neg",
}

PIPELINE_STAGES = [
    "annual_compustat",
    "ccm_annual",
    "annual_monthly",
    "quarterly_compustat",
    "merge_quarterly",
    "ibes_stubs",
    "crsp_monthly",
    "crsp_daily",
    "final_filters",
    "winsorize",
]
