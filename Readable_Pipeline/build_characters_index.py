"""Build characters_index.xlsx: one row per GKX datashare predictor (94 stems, excl. sic2)."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parent
DEFS = ROOT / "01_definitions"
STOCK = ROOT.parent
SHARED = STOCK / "Character_Builders" / "_shared"

if str(DEFS) not in sys.path:
    sys.path.insert(0, str(DEFS))

from catalog import (  # noqa: E402
    ANNUAL_FUNDA_ITEMS,
    BUILD_ORDER,
    DAILY_MONTHLY_STEMS,
    GREEN_ANNUAL_STEMS,
    HXZ_STEMS,
    MONTHLY_CRSP_STEMS,
    NO_WRDS_STEMS,
    QUARTERLY_FUNDA_ITEMS,
    QUARTERLY_STEMS,
    SPECIAL_STEMS,
)
from config import DATASHARE_PREDICTORS  # noqa: E402

OUTPUT = ROOT / "characters_index.xlsx"

# WRDS table sets by builder family
TABLES_ANNUAL = "comp.funda, comp.company, crsp.ccmxpf_linktable, crsp.msf, crsp.msenames"
TABLES_MONTHLY = "crsp.msf, crsp.msenames, comp.funda, comp.company, crsp.ccmxpf_linktable"
TABLES_DAILY_MONTHLY = "crsp.dsf, crsp.msf, crsp.msenames"
TABLES_QUARTERLY = "comp.fundq, comp.company, crsp.ccmxpf_linktable, crsp.msf, crsp.msenames"
TABLES_HXZ = "comp.funda, comp.company, crsp.ccmxpf_linktable, crsp.msf, crsp.msenames"
TABLES_BETA = "crsp.dsf, crsp.msf, crsp.msenames"
TABLES_EVENT = "comp.fundq, comp.company, crsp.ccmxpf_linktable, crsp.dsf, crsp.msf, crsp.msenames"
TABLES_MS = "comp.funda, comp.fundq, comp.company, crsp.ccmxpf_linktable, crsp.msf, crsp.msenames"
TABLES_BM_IA = "none (reads bm parquet)"

MSF_ITEMS = "permno, permco, date, ret, prc, shrout, vol"
HXZ_BM_ITEMS = "seq, ceq, at, lt, pstk, pstkl, pstkrv, txditc, prc, shrout (Dec ME)"
HXZ_OPERPROF_ITEMS = "revt, cogs, xsga, xint, seq, ceq, at, lt, pstk, pstkl, pstkrv, txditc"
BETA_ITEMS = "crsp.dsf: ret (weekly-compounded); EW market = cross-section mean"
EVENT_ITEMS = "comp.fundq: rdq, ibq; crsp.dsf: ret, vol"
MS_ANNUAL_ITEMS = "ni, oancf, ib, dp, xrd, capx, xad, at"
MS_QUARTERLY_ITEMS = ", ".join(QUARTERLY_FUNDA_ITEMS["roavol"])
BM_IA_ITEMS = "bm (from bm parquet)"

DAILY_ITEMS: dict[str, str] = {
    "maxret": "ret",
    "retvol": "ret",
    "baspread": "askhi, bidlo",
    "std_dolvol": "prc, vol",
    "std_turn": "vol, shrout",
    "ill": "ret, prc, vol",
    "zerotrade": "vol, shrout",
}

SPECIAL_EXPANDED: dict[str, str] = {
    "beta": "Market beta (36-month weekly EW-market regression)",
    "betasq": "Market beta squared",
    "idiovol": "Idiosyncratic return volatility",
    "pricedelay": "Price delay (Hou-Moshirian)",
    "ear": "Earnings announcement return",
    "aeavol": "Abnormal earnings announcement volume",
    "ms": "Mohanram G-score (m1 + ... + m8)",
    "bm": "Book-to-market (HXZ)",
    "operprof": "Operating profitability (HXZ)",
    "bm_ia": "Industry-adjusted book-to-market (SIC2 x month demean of bm)",
}


def _dict_from_ast(node: ast.AST) -> dict[str, str]:
    if not isinstance(node, ast.Dict):
        raise TypeError(f"expected dict literal, got {type(node).__name__}")
    out: dict[str, str] = {}
    for key_node, val_node in zip(node.keys, node.values):
        out[ast.literal_eval(key_node)] = ast.literal_eval(val_node)
    return out


def _extract_dict(source: Path, var_name: str) -> dict[str, str]:
    tree = ast.parse(source.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == var_name:
                    return _dict_from_ast(node.value)
    raise ValueError(f"{var_name} not found in {source}")


def _load_expanded_names() -> dict[str, str]:
    green = SHARED / "green_builders.py"
    quarterly = SHARED / "quarterly_builders.py"
    names: dict[str, str] = {}
    names.update(_extract_dict(green, "_RAW_ANNUAL_CHARACTER_INFO"))
    names.update(_extract_dict(green, "MONTHLY_CHARACTER_INFO"))
    names.update(_extract_dict(green, "DAILY_MONTHLY_CHARACTER_INFO"))
    names.update(_extract_dict(quarterly, "QUARTERLY_CHARACTER_INFO"))
    names.update(SPECIAL_EXPANDED)
    return names


def _format_items(items: tuple[str, ...] | str) -> str:
    if isinstance(items, str):
        return items
    return ", ".join(items) if items else "(none)"


def _stem_type(stem: str) -> str:
    if stem in GREEN_ANNUAL_STEMS and stem != "sic2":
        return "Annual"
    if stem in MONTHLY_CRSP_STEMS:
        return "Monthly"
    if stem in DAILY_MONTHLY_STEMS:
        return "Daily-Monthly"
    if stem in QUARTERLY_STEMS:
        return "Quarterly"
    if stem in HXZ_STEMS:
        return "Annual (HXZ)"
    if stem in {"beta", "betasq", "idiovol", "pricedelay"}:
        return "Daily (weekly rolling)"
    if stem in {"ear", "aeavol"}:
        return "Event (daily)"
    if stem == "ms":
        return "Annual+Quarterly"
    if stem in NO_WRDS_STEMS:
        return "Annual (derived, no WRDS)"
    raise ValueError(f"Unknown stem: {stem}")


def _stem_items(stem: str) -> str:
    if stem in GREEN_ANNUAL_STEMS:
        items = ANNUAL_FUNDA_ITEMS.get(stem, ())
        if stem == "sin":
            return "sic, naics (from comp.company)"
        if stem == "age":
            return "gvkey, datadate (observation count)"
        return _format_items(items)
    if stem in MONTHLY_CRSP_STEMS:
        return MSF_ITEMS
    if stem in DAILY_MONTHLY_STEMS:
        return DAILY_ITEMS[stem]
    if stem in QUARTERLY_STEMS:
        return _format_items(QUARTERLY_FUNDA_ITEMS[stem])
    if stem == "bm":
        return HXZ_BM_ITEMS
    if stem == "operprof":
        return HXZ_OPERPROF_ITEMS
    if stem in {"beta", "betasq", "idiovol", "pricedelay"}:
        return BETA_ITEMS
    if stem in {"ear", "aeavol"}:
        return EVENT_ITEMS
    if stem == "ms":
        return f"annual: {MS_ANNUAL_ITEMS}; quarterly: {MS_QUARTERLY_ITEMS}"
    if stem == "bm_ia":
        return BM_IA_ITEMS
    raise ValueError(f"Unknown stem: {stem}")


def _stem_tables(stem: str) -> str:
    if stem in GREEN_ANNUAL_STEMS and stem != "sic2":
        if stem == "sin":
            return "comp.funda, comp.company, crsp.ccmxpf_linktable, crsp.msf, crsp.msenames"
        if stem == "age":
            return "comp.funda, comp.company, crsp.ccmxpf_linktable, crsp.msf, crsp.msenames"
        return TABLES_ANNUAL
    if stem in MONTHLY_CRSP_STEMS:
        return TABLES_MONTHLY
    if stem in DAILY_MONTHLY_STEMS:
        return TABLES_DAILY_MONTHLY
    if stem in QUARTERLY_STEMS:
        return TABLES_QUARTERLY
    if stem in HXZ_STEMS:
        return TABLES_HXZ
    if stem in {"beta", "betasq", "idiovol", "pricedelay"}:
        return TABLES_BETA
    if stem in {"ear", "aeavol"}:
        return TABLES_EVENT
    if stem == "ms":
        return TABLES_MS
    if stem in NO_WRDS_STEMS:
        return TABLES_BM_IA
    raise ValueError(f"Unknown stem: {stem}")


def _ordered_stems() -> list[str]:
    stems = [s for s in BUILD_ORDER if s != "sic2"]
    assert len(stems) == len(DATASHARE_PREDICTORS) - 1, (
        f"expected {len(DATASHARE_PREDICTORS) - 1} stems, got {len(stems)}"
    )
    return stems


def build_rows() -> list[dict[str, str]]:
    expanded = _load_expanded_names()
    rows: list[dict[str, str]] = []
    for stem in _ordered_stems():
        rows.append(
            {
                "Type": _stem_type(stem),
                "Stem": stem,
                "Expanded Name": expanded.get(stem, ""),
                "Items Used": _stem_items(stem),
                "WRDS Tables": _stem_tables(stem),
                "Checked": "",
            }
        )
    return rows


def write_excel(rows: list[dict[str, str]], path: Path) -> None:
    headers = ["Type", "Stem", "Expanded Name", "Items Used", "WRDS Tables", "Checked"]
    wb = Workbook()
    ws = wb.active
    ws.title = "Characters"

    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for row in rows:
        ws.append([row[h] for h in headers])

    ws.freeze_panes = "A2"

    col_widths = {
        "A": 22,
        "B": 14,
        "C": 48,
        "D": 55,
        "E": 55,
        "F": 10,
    }
    for col, width in col_widths.items():
        ws.column_dimensions[col].width = width

    checked_col = get_column_letter(headers.index("Checked") + 1)
    last_row = len(rows) + 1
    dv = DataValidation(type="list", formula1='"*,✓"', allow_blank=True)
    dv.error = "Choose * or ✓"
    dv.errorTitle = "Invalid entry"
    ws.add_data_validation(dv)
    dv.add(f"{checked_col}2:{checked_col}{last_row}")

    wb.save(path)


def main() -> None:
    rows = build_rows()
    write_excel(rows, OUTPUT)
    print(f"Wrote {len(rows)} rows to {OUTPUT}")


if __name__ == "__main__":
    main()
