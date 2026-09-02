"""Green SAS constants (copied from green_builders)."""
from __future__ import annotations

ANNUAL_COMPUSTAT_WHERE = """
          f.indfmt = 'INDL'
          AND f.datafmt = 'STD'
          AND f.popsrc = 'D'
          AND f.consol = 'C'
          AND f.at IS NOT NULL
          AND f.prcc_f IS NOT NULL
          AND f.ni IS NOT NULL
"""

GREEN_SIN_NAICS = {
    "7132", "71312", "713210", "71329", "713290", "72112", "721120",
}

GREEN_CPI_BY_FYEAR = {
    1974: 49.3, 1975: 53.8, 1976: 56.9, 1977: 60.6, 1978: 65.2, 1979: 72.6,
    1980: 82.4, 1981: 90.9, 1982: 96.5, 1983: 99.6, 1984: 103.9, 1985: 107.6,
    1986: 109.6, 1987: 113.6, 1988: 118.3, 1989: 124.0, 1990: 130.7, 1991: 136.2,
    1992: 140.3, 1993: 144.5, 1994: 148.2, 1995: 152.4, 1996: 156.9, 1997: 160.5,
    1998: 163.0, 1999: 166.6, 2000: 172.2, 2001: 177.1, 2002: 179.88, 2003: 183.96,
    2004: 188.9, 2005: 195.3, 2006: 201.6, 2007: 207.342, 2008: 215.303, 2009: 214.537,
    2010: 218.056, 2011: 224.939, 2012: 229.594, 2013: 229.17, 2014: 229.91,
    2015: 236.53, 2016: 240.007, 2017: 245.120, 2018: 251.107, 2019: 255.657,
    2020: 258.811, 2021: 270.970, 2022: 292.655, 2023: 304.702,
}

GREEN_TAX_RATE_BY_FYEAR = {
    year: rate
    for year, rate in [
        *((y, 0.48) for y in range(1900, 1979)),
        *((y, 0.46) for y in range(1979, 1987)),
        (1987, 0.40),
        *((y, 0.34) for y in range(1988, 1993)),
        *((y, 0.35) for y in range(1993, 2100)),
    ]
}

ANNUAL_ID_COLUMNS = ["permno", "permco", "gvkey", "datadate", "sic", "fyear"]
MONTHLY_OUTPUT_COLUMNS = [
    "permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "sic", "exchcd", "shrcd",
]

QUARTERLY_MONTH_START_LAG = -10
QUARTERLY_MONTH_END_LAG = -5
