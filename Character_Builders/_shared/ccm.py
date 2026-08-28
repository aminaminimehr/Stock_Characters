"""CRSP-Compustat Merged (CCM) link table loading and attachment."""
import re

import pandas as pd

from pipeline_config import CCM_LINKPRIM, CCM_LINKTYPES


def parse_ccm_codes(value, default):
    if value is None:
        return tuple(default)
    if isinstance(value, str):
        codes = [code.strip().upper() for code in re.split(r"[, ]+", value) if code.strip()]
    else:
        codes = [str(code).strip().upper() for code in value if str(code).strip()]
    if not codes:
        raise ValueError("At least one CCM code must be supplied.")
    invalid = [code for code in codes if not re.fullmatch(r"[A-Z0-9]+", code)]
    if invalid:
        raise ValueError(f"Invalid CCM code(s): {invalid}")
    return tuple(dict.fromkeys(codes))


def sql_code_list(codes):
    return ", ".join(f"'{code}'" for code in codes)


def _is_prefix_rule(linktypes):
    """True when linktypes is the Dacheng 'any L-prefixed code' rule (L*)."""
    if linktypes is None:
        return False
    if isinstance(linktypes, str):
        return linktypes.strip().upper() in ("L*", "L")
    return any(str(c).strip().upper() == "L*" for c in linktypes)


def load_ccm_links(db, linktypes=None, linkprim=None):
    """Load CCM links using hardcoded pipeline_config defaults unless overridden."""
    from _shared.green_builders import raw_sql_with_retry

    if linktypes is None:
        linktypes = CCM_LINKTYPES
    if linkprim is None:
        linkprim = CCM_LINKPRIM

    linkprim_clause = _linkprim_clause(linkprim)
    if _is_prefix_rule(linktypes):
        linktype_clause = "linktype LIKE 'L%'"
    else:
        codes = parse_ccm_codes(linktypes, ("LU", "LC"))
        linktype_clause = f"linktype IN ({sql_code_list(codes)})"

    link = raw_sql_with_retry(db, f"""
        SELECT gvkey, lpermno AS permno, lpermco AS permco,
               linktype, linkprim, linkdt, linkenddt
        FROM crsp.ccmxpf_linktable
        WHERE {linktype_clause}
          {linkprim_clause}
          AND lpermno IS NOT NULL
    """)
    link["linkdt"] = pd.to_datetime(link["linkdt"])
    link["linkenddt"] = pd.to_datetime(link["linkenddt"])
    return link


def _linkprim_clause(linkprim):
    """Return 'AND linkprim IN (...)' or '' when linkprim is ALL/empty."""
    if str(linkprim).strip().upper() in ("", "ALL", "*"):
        return ""
    codes = parse_ccm_codes(linkprim, ())
    return f" AND linkprim IN ({sql_code_list(codes)})"


def load_ccm_links_green(db, linktypes=None, linkprim=None):
    """Load CCM links for Green-style annual builders (same datashare recipe)."""
    from _shared.green_builders import raw_sql_with_retry

    if linktypes is None:
        linktypes = CCM_LINKTYPES
    if linkprim is None:
        linkprim = CCM_LINKPRIM

    if _is_prefix_rule(linktypes):
        linktype_clause = "linktype LIKE 'L%'"
    else:
        codes = parse_ccm_codes(linktypes, ("LU", "LC"))
        linktype_clause = f"linktype IN ({sql_code_list(codes)})"
    linkprim_clause = _linkprim_clause(linkprim)
    link = raw_sql_with_retry(db, f"""
        SELECT gvkey, lpermno AS permno, lpermco AS permco, linkdt, linkenddt, linktype
        FROM crsp.ccmxpf_linktable
        WHERE {linktype_clause}
          {linkprim_clause}
          AND lpermno IS NOT NULL
    """)
    link["linkdt"] = pd.to_datetime(link["linkdt"])
    link["linkenddt"] = pd.to_datetime(link["linkenddt"])
    link["permno"] = pd.to_numeric(link["permno"], errors="coerce").astype("Int64")
    return link.sort_values(["gvkey", "linkdt"])


def attach_ccm_links_green(comp, link):
    """Attach CCM links; open-ended link dates treated as missing (Green SAS L414-417)."""
    merged = comp.merge(link, on="gvkey", how="inner")
    linkdt_ok = merged["linkdt"].isna() | (merged["linkdt"] <= merged["datadate"])
    linkend_ok = merged["linkenddt"].isna() | (merged["datadate"] <= merged["linkenddt"])
    out = merged[linkdt_ok & linkend_ok & merged["permno"].notna()].copy()
    out["permno"] = pd.to_numeric(out["permno"], errors="coerce").astype("int64")
    if "permco" in out.columns:
        out["permco"] = pd.to_numeric(out["permco"], errors="coerce").astype("Int64")
    return out.drop(columns=["linkdt", "linkenddt", "linktype"], errors="ignore")


def attach_ccm_links(comp, link):
    """Attach CCM links for HXZ builders; keep primary link per gvkey-datadate."""
    linked = comp.merge(link, on="gvkey", how="inner")
    linked = linked[
        (linked["datadate"] >= linked["linkdt"])
        & ((linked["datadate"] <= linked["linkenddt"]) | linked["linkenddt"].isna())
    ].copy()

    linked["linkprim_priority"] = linked["linkprim"].map({"P": 0, "C": 1}).fillna(2)
    linked = linked.sort_values(
        ["gvkey", "datadate", "linkprim_priority", "permno", "linkdt"]
    )
    linked = linked.drop_duplicates(["gvkey", "datadate"], keep="first")
    return linked.drop(columns=["linkdt", "linkenddt", "linkprim_priority"])
