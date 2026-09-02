"""SQL templates: same JOIN/WHERE as production; SELECT lists come from each builder."""
from __future__ import annotations

from constants import ANNUAL_COMPUSTAT_WHERE
from wrds_io import crsp_universe_filter, sql_date_filter


def _funda_select_list(items: tuple[str, ...]) -> str:
    parts = ["c.gvkey", "f.datadate", "f.fyear", "c.sic"]
    for item in items:
        if item == "prcc_f":
            parts.append("ABS(f.prcc_f) AS prcc_f")
        elif item == "prccq":
            parts.append("ABS(f.prccq) AS prccq")
        else:
            parts.append(f"f.{item}")
    return ", ".join(parts)


def green_funda_sql(items: tuple[str, ...], *, include_naics: bool = False) -> str:
    naics_col = ", c.naics" if include_naics else ""
    return f"""
        SELECT {_funda_select_list(items)}{naics_col}
        FROM comp.company AS c
        JOIN comp.funda AS f ON c.gvkey = f.gvkey
        WHERE {ANNUAL_COMPUSTAT_WHERE}
          AND {sql_date_filter("f.datadate")}
    """


def green_funda_full_history_sql(items: tuple[str, ...]) -> str:
    return f"""
        SELECT {_funda_select_list(items)}
        FROM comp.company AS c
        JOIN comp.funda AS f ON c.gvkey = f.gvkey
        WHERE {ANNUAL_COMPUSTAT_WHERE}
    """


def green_age_lookup_sql() -> str:
    return f"""
        SELECT c.gvkey, f.datadate
        FROM comp.company AS c
        JOIN comp.funda AS f ON c.gvkey = f.gvkey
        WHERE {ANNUAL_COMPUSTAT_WHERE}
    """


def green_ccm_sql() -> str:
    return """
        SELECT gvkey, lpermno AS permno, lpermco AS permco, linkdt, linkenddt, linktype
        FROM crsp.ccmxpf_linktable
        WHERE linktype LIKE 'L%'
          AND linkprim IN ('P', 'C')
          AND lpermno IS NOT NULL
    """


def hxz_ccm_sql() -> str:
    return """
        SELECT gvkey, lpermno AS permno, lpermco AS permco,
               linktype, linkprim, linkdt, linkenddt
        FROM crsp.ccmxpf_linktable
        WHERE linktype LIKE 'L%'
          AND linkprim IN ('P', 'C')
          AND lpermno IS NOT NULL
    """


def crsp_msf_sql(items: tuple[str, ...]) -> str:
    msf_cols = ", ".join(f"m.{c}" for c in items)
    return f"""
        SELECT {msf_cols}, n.exchcd, n.shrcd
        FROM crsp.msf AS m
        JOIN crsp.msenames AS n
          ON m.permno = n.permno
         AND n.namedt <= m.date
         AND m.date <= COALESCE(n.nameendt, DATE '9999-12-31')
        WHERE {crsp_universe_filter("n")}
          AND {sql_date_filter("date", "m")}
    """


def hxz_funda_bm_sql() -> str:
    return """
        SELECT gvkey, datadate, fyear, seq, ceq, at, lt, pstk, pstkl, pstkrv, txditc
        FROM comp.funda
        WHERE indfmt = 'INDL' AND datafmt = 'STD' AND popsrc = 'D' AND consol = 'C'
    """


def hxz_funda_operprof_sql() -> str:
    return """
        SELECT gvkey, datadate, fyear, revt, cogs, xsga, xint,
               seq, ceq, at, lt, pstk, pstkl, pstkrv, txditc
        FROM comp.funda
        WHERE indfmt = 'INDL' AND datafmt = 'STD' AND popsrc = 'D' AND consol = 'C'
    """


def company_sic_sql() -> str:
    return "SELECT gvkey, sic FROM comp.company"


def fundq_sql(items: tuple[str, ...]) -> str:
    base = [
        "c.gvkey",
        "SUBSTR(REPLACE(f.cusip, ' ', ''), 1, 6) AS cusip6",
        "f.datadate", "f.fyearq", "f.fqtr", "f.rdq",
        "SUBSTR(c.sic, 1, 2) AS sic2", "c.sic",
    ]
    for item in items:
        if item in ("prccq",):
            base.append(f"ABS(f.{item}) AS {item}")
        elif item == "mveq":
            base.append("ABS(f.prccq) * f.cshoq AS mveq")
        else:
            base.append(f"f.{item}")
    cols = ", ".join(base)
    return f"""
        SELECT {cols}
        FROM comp.company AS c
        JOIN comp.fundq AS f ON c.gvkey = f.gvkey
        WHERE f.indfmt = 'INDL' AND f.datafmt = 'STD' AND f.popsrc = 'D' AND f.consol = 'C'
          AND f.ibq IS NOT NULL
          AND f.datadate >= DATE '1975-01-01'
          AND {sql_date_filter("f.datadate")}
    """
