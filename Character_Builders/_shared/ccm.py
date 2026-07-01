import re

import pandas as pd


DEFAULT_CCM_LINKTYPES = ("LU", "LC")
DEFAULT_CCM_LINKPRIM = ("P", "C")
# Green SAS L410-412 (broader linktype set, no linkprim filter).
GREEN_CCM_LINKTYPES = ("LU", "LC", "LD", "LF", "LN", "LO", "LS", "LX")


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


def add_ccm_arguments(parser):
    parser.add_argument(
        "--ccm-linktypes",
        default=",".join(DEFAULT_CCM_LINKTYPES),
        help=(
            "Comma-separated CCM linktype filter. Default is LU,LC: link used "
            "and research-complete links."
        ),
    )
    parser.add_argument(
        "--ccm-linkprim",
        default=",".join(DEFAULT_CCM_LINKPRIM),
        help=(
            "Comma-separated CCM linkprim filter. Default is P,C: Compustat "
            "primary and CRSP primary links."
        ),
    )


def load_ccm_links(db, linktypes=None, linkprim=None):
    from _shared.green_builders import raw_sql_with_retry

    linktypes = parse_ccm_codes(linktypes, DEFAULT_CCM_LINKTYPES)
    linkprim_clause = _linkprim_clause(linkprim)

    link = raw_sql_with_retry(db, f"""
        SELECT gvkey, lpermno AS permno, lpermco AS permco,
               linktype, linkprim, linkdt, linkenddt
        FROM crsp.ccmxpf_linktable
        WHERE linktype IN ({sql_code_list(linktypes)})
          {linkprim_clause}
          AND lpermno IS NOT NULL
    """)
    link["linkdt"] = pd.to_datetime(link["linkdt"])
    link["linkenddt"] = pd.to_datetime(link["linkenddt"])
    return link


def _linkprim_clause(linkprim):
    """Return 'AND linkprim IN (...)' or '' when linkprim is ALL/empty (no filter).

    ``None`` falls back to the STOCK_CHARACTERS_CCM_LINKPRIM env var (default ALL).
    """
    import os
    if linkprim is None:
        linkprim = os.environ.get("STOCK_CHARACTERS_CCM_LINKPRIM", "ALL")
    if str(linkprim).strip().upper() in ("", "ALL", "*"):
        return ""
    codes = parse_ccm_codes(linkprim, ())
    return f" AND linkprim IN ({sql_code_list(codes)})"


def _resolve_linktypes(linktypes):
    """Resolve linktypes: explicit value > STOCK_CHARACTERS_CCM_LINKTYPES env > Green recipe."""
    import os
    if linktypes is None or not str(linktypes).strip():
        linktypes = os.environ.get("STOCK_CHARACTERS_CCM_LINKTYPES") or GREEN_CCM_LINKTYPES
    if str(linktypes).strip().upper() in ("ALL", "*"):
        raise ValueError("linktypes 'ALL' is not valid; specify explicit CCM linktype codes.")
    return parse_ccm_codes(linktypes, GREEN_CCM_LINKTYPES)


def load_ccm_links_green(db, linktypes=None, linkprim=None):
    """Green-family CCM link table filter.

    ``linktypes``/``linkprim`` fall back to the STOCK_CHARACTERS_CCM_LINKTYPES /
    STOCK_CHARACTERS_CCM_LINKPRIM environment variables (set by run_full_pipeline),
    then to the Green SAS recipe (broad linktypes, no linkprim filter). Pass
    ``linkprim='ALL'`` (or '') to disable the linkprim filter. The legacy Green SAS
    2015/1950 link-date cap has been removed, so links starting in any year are kept.
    """
    from _shared.green_builders import raw_sql_with_retry

    codes = sql_code_list(_resolve_linktypes(linktypes))
    linkprim_clause = _linkprim_clause(linkprim)
    link = raw_sql_with_retry(db, f"""
        SELECT gvkey, lpermno AS permno, lpermco AS permco, linkdt, linkenddt, linktype
        FROM crsp.ccmxpf_linktable
        WHERE linktype IN ({codes})
          {linkprim_clause}
          AND lpermno IS NOT NULL
    """)
    link["linkdt"] = pd.to_datetime(link["linkdt"])
    link["linkenddt"] = pd.to_datetime(link["linkenddt"])
    link["permno"] = pd.to_numeric(link["permno"], errors="coerce").astype("Int64")
    return link.sort_values(["gvkey", "linkdt"])


def attach_ccm_links_green(comp, link):
    """Green SAS L414-417: open-ended link dates treated as missing."""
    merged = comp.merge(link, on="gvkey", how="inner")
    linkdt_ok = merged["linkdt"].isna() | (merged["linkdt"] <= merged["datadate"])
    linkend_ok = merged["linkenddt"].isna() | (merged["datadate"] <= merged["linkenddt"])
    out = merged[linkdt_ok & linkend_ok & merged["permno"].notna()].copy()
    out["permno"] = pd.to_numeric(out["permno"], errors="coerce").astype("int64")
    if "permco" in out.columns:
        out["permco"] = pd.to_numeric(out["permco"], errors="coerce").astype("Int64")
    return out.drop(columns=["linkdt", "linkenddt", "linktype"], errors="ignore")


def attach_ccm_links(comp, link):
    linked = comp.merge(link, on="gvkey", how="inner")
    linked = linked[
        (linked["datadate"] >= linked["linkdt"])
        & ((linked["datadate"] <= linked["linkenddt"]) | linked["linkenddt"].isna())
    ].copy()

    linked["linkprim_priority"] = linked["linkprim"].map({"P": 0, "C": 1}).fillna(2)
    linked = linked.sort_values(
        ["gvkey", "datadate", "linkprim_priority", "permno", "linkdt"]
    )
    # Keep one permno per gvkey-datadate (primary link first), so HXZ builders stay
    # well-defined even when --ccm-linkprim=ALL admits multiple links per firm.
    linked = linked.drop_duplicates(["gvkey", "datadate"], keep="first")
    return linked.drop(columns=["linkdt", "linkenddt", "linkprim_priority"])
