import re

import pandas as pd


DEFAULT_CCM_LINKTYPES = ("LU", "LC")
DEFAULT_CCM_LINKPRIM = ("P", "C")


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
    linktypes = parse_ccm_codes(linktypes, DEFAULT_CCM_LINKTYPES)
    linkprim = parse_ccm_codes(linkprim, DEFAULT_CCM_LINKPRIM)

    link = db.raw_sql(f"""
        SELECT gvkey, lpermno AS permno, lpermco AS permco,
               linktype, linkprim, linkdt, linkenddt
        FROM crsp.ccmxpf_linktable
        WHERE linktype IN ({sql_code_list(linktypes)})
          AND linkprim IN ({sql_code_list(linkprim)})
          AND lpermno IS NOT NULL
    """)
    link["linkdt"] = pd.to_datetime(link["linkdt"])
    link["linkenddt"] = pd.to_datetime(link["linkenddt"])
    return link


def attach_ccm_links(comp, link):
    linked = comp.merge(link, on="gvkey", how="inner")
    linked = linked[
        (linked["datadate"] >= linked["linkdt"])
        & ((linked["datadate"] <= linked["linkenddt"]) | linked["linkenddt"].isna())
    ].copy()

    linked["linkprim_priority"] = linked["linkprim"].map({"P": 0, "C": 1}).fillna(2)
    linked = linked.sort_values(
        ["gvkey", "datadate", "permno", "linkprim_priority", "linkdt"]
    )
    return linked.drop(columns=["linkdt", "linkenddt", "linkprim_priority"])
