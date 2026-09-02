"""Catalog of all 95 datashare predictors: family, expansion, funda items."""
from __future__ import annotations

from config import DATASHARE_PREDICTORS

GREEN_ANNUAL_STEMS = frozenset({
    "absacc", "acc", "age", "agr", "cashdebt", "cashpr", "cfp", "cfp_ia", "chcsho", "chinv",
    "chatoia", "chempia", "convind", "currat", "depr", "dy", "divi", "divo", "egr", "ep",
    "gma", "grcapx", "grltnoa", "herf", "hire", "invest", "lev", "lgr", "mve_ia", "orgcap",
    "pctacc", "pchcurrat", "pchdepr", "pchcapx_ia", "pchgm_pchsale", "pchquick",
    "pchsale_pchinvt", "pchsale_pchrect", "pchsale_pchxsga", "pchsaleinv", "ps", "quick",
    "rd", "rd_sale", "rd_mve", "realestate", "roic", "sgr", "salecash", "saleinv", "salerec",
    "secured", "securedind", "sic2", "sin", "sp", "tb", "tang", "chpmia",
})

MONTHLY_CRSP_STEMS = frozenset({
    "chmom", "dolvol", "indmom", "mvel1", "mom1m", "mom6m", "mom12m", "mom36m", "turn",
})

DAILY_MONTHLY_STEMS = frozenset({
    "baspread", "ill", "maxret", "retvol", "std_dolvol", "std_turn", "zerotrade",
})

QUARTERLY_STEMS = frozenset({
    "chtx", "cinvest", "nincr", "roaq", "roeq", "rsup", "cash", "stdacc", "stdcf", "roavol",
})

HXZ_STEMS = frozenset({"bm", "operprof"})
SPECIAL_STEMS = frozenset({"beta", "betasq", "idiovol", "pricedelay", "ear", "aeavol", "ms"})
NO_WRDS_STEMS = frozenset({"bm_ia"})

# Per-stem Compustat annual items (minimal for SQL SELECT; universe WHERE unchanged).
ANNUAL_FUNDA_ITEMS: dict[str, tuple[str, ...]] = {
    "ep": ("ib", "prcc_f", "csho"),
    "rd_mve": ("xrd", "prcc_f", "csho"),
    "lev": ("lt", "prcc_f", "csho"),
    "dy": ("dvt", "prcc_f", "csho"),
    "sp": ("sale", "prcc_f", "csho"),
    "rd_sale": ("xrd", "sale"),
    "agr": ("at",),
    "gma": ("revt", "cogs", "at"),
    "chcsho": ("csho",),
    "lgr": ("lt",),
    "acc": ("ib", "oancf", "at", "act", "che", "lct", "dlc", "txp", "dp"),
    "pctacc": ("ib", "oancf", "at", "act", "che", "lct", "dlc", "txp", "dp"),
    "absacc": ("ib", "oancf", "at", "act", "che", "lct", "dlc", "txp", "dp"),
    "cfp": ("ib", "oancf", "at", "act", "che", "lct", "dlc", "txp", "dp", "prcc_f", "csho"),
    "cfp_ia": ("ib", "oancf", "at", "act", "che", "lct", "dlc", "txp", "dp", "prcc_f", "csho"),
    "hire": ("emp",),
    "sgr": ("sale",),
    "depr": ("dp", "ppent"),
    "pchdepr": ("dp", "ppent"),
    "cashdebt": ("ib", "dp", "lt"),
    "cashpr": ("prcc_f", "csho", "dltt", "at", "che"),
    "invest": ("ppegt", "ppent", "invt", "at"),
    "egr": ("ceq",),
    "chinv": ("invt", "at"),
    "pchcurrat": ("act", "lct"),
    "grcapx": ("capx", "ppent"),
    "currat": ("act", "lct", "che", "rect", "invt", "ap"),
    "quick": ("act", "lct", "che", "rect", "invt", "ap"),
    "pchquick": ("act", "lct", "che", "rect", "invt", "ap"),
    "pchsaleinv": ("sale", "invt"),
    "salecash": ("sale", "che"),
    "saleinv": ("sale", "invt"),
    "salerec": ("sale", "rect"),
    "tang": ("che", "rect", "invt", "ppent", "at"),
    "roic": ("ebit", "nopi", "ceq", "lt", "che"),
    "pchsale_pchinvt": ("sale", "invt"),
    "pchsale_pchrect": ("sale", "rect"),
    "pchgm_pchsale": ("sale", "cogs"),
    "pchsale_pchxsga": ("sale", "xsga"),
    "divi": ("dvt",),
    "divo": ("dvt",),
    "rd": ("xrd", "at"),
    "convind": ("dcvt", "dcpstk", "pstk", "cshrc"),
    "secured": ("dm", "dltt"),
    "securedind": ("dm",),
    "sin": (),
    "realestate": ("fatb", "fatl", "ppegt", "ppent"),
    "grltnoa": ("rect", "invt", "ppent", "aco", "intan", "ao", "ap", "lco", "lo", "dp", "at"),
    "orgcap": ("xsga", "at"),
    "age": (),
    "ps": ("ni", "oancf", "at", "dltt", "act", "lct", "sale", "cogs", "scstkc"),
    "sic2": (),
    "chatoia": ("sale", "at"),
    "chempia": ("emp",),
    "chpmia": ("ib", "sale"),
    "pchcapx_ia": ("capx", "ppent"),
    "mve_ia": ("prcc_f", "csho"),
    "tb": ("txfo", "txfed", "txt", "txdi", "ib"),
    "herf": ("sale",),
}

QUARTERLY_FUNDA_ITEMS: dict[str, tuple[str, ...]] = {
    "chtx": ("txtq", "atq", "ibq", "rdq"),
    "cinvest": ("ppentq", "saleq", "ibq", "rdq"),
    "nincr": ("ibq", "rdq"),
    "roaq": ("ibq", "atq", "rdq"),
    "roeq": ("ibq", "seqq", "ceqq", "pstkq", "pstkrq", "ltq", "atq", "dlcq", "dlttq", "rdq"),
    "rsup": ("saleq", "mveq", "ibq", "rdq"),
    "cash": ("cheq", "atq", "ibq", "rdq"),
    "stdacc": ("actq", "cheq", "lctq", "dlcq", "saleq", "ibq", "rdq"),
    "stdcf": ("ibq", "saleq", "actq", "cheq", "lctq", "dlcq", "rdq"),
    "roavol": ("ibq", "atq", "saleq", "mveq", "oiadpq", "ceqq", "seqq", "pstkq", "pstkrq", "ltq", "dlcq", "dlttq", "cheq", "rdq", "actq", "lctq"),
}

BUILD_ORDER = [
    # Green annual firm-level
    *[s for s in GREEN_ANNUAL_STEMS if s not in {
        "cfp_ia", "chatoia", "chempia", "chpmia", "pchcapx_ia", "mve_ia", "tb", "herf",
        "age", "orgcap", "ps", "sin", "sic2", "absacc",
    }],
    "absacc",
    "age", "orgcap", "ps", "sin", "sic2",
    "cfp_ia", "chatoia", "chempia", "chpmia", "pchcapx_ia", "mve_ia", "tb", "herf",
    "bm", "operprof", "bm_ia",
    *sorted(MONTHLY_CRSP_STEMS),
    *sorted(DAILY_MONTHLY_STEMS),
    *sorted(QUARTERLY_STEMS),
    "beta", "betasq", "idiovol", "pricedelay", "ear", "aeavol", "ms",
]

assert set(DATASHARE_PREDICTORS) == (
    GREEN_ANNUAL_STEMS | MONTHLY_CRSP_STEMS | DAILY_MONTHLY_STEMS
    | QUARTERLY_STEMS | HXZ_STEMS | SPECIAL_STEMS | NO_WRDS_STEMS
)
