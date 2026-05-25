import pandas as pd

try:
    from .industry_mappings import FF_INDUSTRY_MAPPINGS, MAPPING_COLUMNS
except ImportError:
    from industry_mappings import FF_INDUSTRY_MAPPINGS, MAPPING_COLUMNS


SUPPORTED_SCHEMES = tuple(sorted(FF_INDUSTRY_MAPPINGS))


def load_industry_mapping(scheme):
    """Load one embedded Fama-French industry SIC-range mapping table."""
    if scheme not in SUPPORTED_SCHEMES:
        raise ValueError(
            f"Unsupported Fama-French industry scheme: {scheme}. "
            f"Supported schemes are {SUPPORTED_SCHEMES}."
        )

    return pd.DataFrame(FF_INDUSTRY_MAPPINGS[scheme], columns=MAPPING_COLUMNS)


def add_fama_french_industry_code(
    df,
    scheme,
    sic_col="sic",
    output_col=None,
    unmatched_value=pd.NA,
):
    """Add one Fama-French industry code column based on SIC."""
    mapping = load_industry_mapping(scheme)
    output_col = output_col or f"ffi{scheme}"

    out = df.copy()
    sic = pd.to_numeric(out[sic_col], errors="coerce")
    out[output_col] = unmatched_value

    for row in mapping.itertuples(index=False):
        mask = sic.between(row.sic_s, row.sic_e)
        out.loc[mask, output_col] = row.ffi

    out[output_col] = out[output_col].astype("Int64")
    return out


def add_fama_french_industry_codes(df, sic_col="sic", schemes=SUPPORTED_SCHEMES):
    """Add one or more Fama-French industry code columns based on SIC."""
    out = df.copy()

    for scheme in schemes:
        out = add_fama_french_industry_code(
            out,
            scheme=scheme,
            sic_col=sic_col,
            output_col=f"ffi{scheme}",
        )

    return out
