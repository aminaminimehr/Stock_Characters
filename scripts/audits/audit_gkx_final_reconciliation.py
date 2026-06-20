#!/usr/bin/env python3
"""Final GKX reconciliation: datashare predictors vs repository panels."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from output_paths import (  # noqa: E402
    COMPLETE_ALL_PANEL_FILE,
    DIAGNOSTICS_DIR,
    SIGNAL_PANEL_FILE,
)

DATASHARE = PROJECT_ROOT / "Supplementary_assistive_files" / "datashare.csv"
GKX_TXT = PROJECT_ROOT / "Supplementary_assistive_files" / "GKX_characters.txt"
DOCS_OUT = PROJECT_ROOT / "docs" / "gkx" / "gkx_final_reconciliation_audit.md"

META = {
    "permno", "permco", "gvkey", "date", "sic", "sic2",
    "signal_yyyymm", "target_yyyymm", "excess_return", "DATE",
}
RETURN_COLS = {"date", "ret", "dlret", "dlstcd", "retadj", "rf"}

ALIAS = {
    "ear": ("abr",),
    "mve_ia": ("me_ia",),
    "operprof": ("op", "operating_profitability"),
    "rd_mve": ("rdm",),
    "retvol": ("rvar_mean",),
    "roaq": ("roa1",),
    "roeq": ("roe",),
}
PARALLEL = {
    "bm": ("book_to_market",),
    "cfp": ("cash_flow_to_price",),
    "operprof": ("operating_profitability",),
}
BUILDER = {
    "book_to_market": "HXZ_BM_Generalized",
    "bmj": "HXZ_BMJ_Generalized",
    "operating_profitability": "HXZ_OPE_Generalized",
    "cash_flow_to_price": "HXZ_CFP_Generalized",
    "beta": "_shared/beta_builder.py",
    "betasq": "_shared/beta_builder.py",
    "abr": "_shared/event_builders.py",
    "rvar_capm": "_shared/rvar_factor_builders.py",
    "rvar_ff3": "_shared/rvar_factor_builders.py",
}
QUARTERLY = {"chtx", "cinvest", "ni", "nincr", "rna", "roa1", "rsup", "sue"}
MONTHLY = {
    "dolvol", "me", "mvel1", "mom1m", "mom6m", "mom12m", "mom36m", "mom60m",
    "seas1a", "turn",
}
DAILY = {
    "baspread", "ill", "maxret", "rvar_mean", "std_dolvol", "std_turn", "zerotrade",
}
EXTRA_NOTES = {
    "adm": "Advertising/MKT; Green/chars60",
    "alm": "Asset liquidity; Green/chars60",
    "ato": "Asset turnover; Green/chars60",
    "bmj": "HXZ June ME variant; not in GKX 94",
    "chobklg": "Green/chars60 backlog",
    "chpm": "Industry-adj PM; GKX uses chpmia",
    "me": "Raw ME; GKX uses mvel1 (log lag ME)",
    "mom60m": "60-month momentum extension",
    "ni": "Net stock issues; quarterly Green",
    "noa": "Net operating assets; Green/chars60",
    "obklg": "Green/chars60 backlog",
    "pchcapx": "Green pct change capx; GKX uses pchcapx_ia",
    "pm": "Profit margin; Green/chars60",
    "rna": "Quarterly RNA; Green/chars60",
    "rvar_capm": "CAPM residual var; GKX uses retvol",
    "rvar_ff3": "FF3 residual var; not in GKX",
    "seas1a": "Seasonality; Green/chars60",
    "sue": "SUE; quarterly Green, not in datashare",
}


def builder_loc(name: str) -> str:
    if name in BUILDER:
        return f"Character_Builders/{BUILDER[name]}"
    if name in QUARTERLY:
        return "Character_Builders/_shared/quarterly_builders.py"
    if name in MONTHLY:
        return "Character_Builders/_shared/green_builders.py (monthly)"
    if name in DAILY:
        return "Character_Builders/_shared/green_builders.py (daily/monthly)"
    return "Character_Builders/_shared/green_builders.py (annual)"


def load_gkx_descriptions() -> dict[str, str]:
    desc: dict[str, str] = {}
    if not GKX_TXT.exists():
        return desc
    for line in GKX_TXT.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = re.match(r"\s*(\w+)\s+(.+)", line.strip())
        if match:
            desc[match.group(1).lower()] = match.group(2).strip()
    return desc


def characteristic_columns(path: Path) -> set[str]:
    cols = set(pd.read_csv(path, nrows=0).columns)
    return cols - META - RETURN_COLS - {"excess_return"}


def reconcile() -> str:
    desc = load_gkx_descriptions()
    gkx_cols = [c for c in pd.read_csv(DATASHARE, nrows=0).columns if c not in META]
    signal = characteristic_columns(SIGNAL_PANEL_FILE)
    complete = characteristic_columns(COMPLETE_ALL_PANEL_FILE)

    rows: list[tuple[str, str, str, str, str]] = []
    for g in sorted(gkx_cols, key=str.lower):
        status = "missing"
        repo: list[str] = []
        notes: list[str] = []

        if g in signal and g in complete:
            status = "exact match"
            repo = [g]
        elif g in ALIAS:
            hits = [a for a in ALIAS[g] if a in signal]
            if hits:
                status = "implemented under different name"
                repo = hits
                notes.append("GKX column name not in panel")

        if status != "missing" and g in PARALLEL:
            parallel = [p for p in PARALLEL[g] if p in signal and p not in repo]
            if parallel:
                status = "partially matched"
                repo = repo + parallel
                notes.append("GKX/Green column plus HXZ parallel variant in panel")

        if status == "missing" and g in ALIAS:
            notes.append(f"Expected alias {ALIAS[g]} not found")

        builder = "; ".join(builder_loc(x) for x in repo) if repo else "—"
        note_text = "; ".join(notes) if notes else desc.get(g.lower(), "—")
        rows.append((g, ", ".join(repo) if repo else "—", status, builder, note_text))

    extras: list[str] = []
    for col in sorted(signal):
        if col in gkx_cols:
            continue
        if any(col in ALIAS[g] for g in ALIAS):
            continue
        if any(col in PARALLEL.get(g, ()) for g in PARALLEL):
            continue
        extras.append(col)

    exact = sum(1 for *_, status, _, _ in rows if status == "exact match")
    alias = sum(1 for *_, status, _, _ in rows if status == "implemented under different name")
    partial = sum(1 for *_, status, _, _ in rows if status == "partially matched")
    missing = sum(1 for *_, status, _, _ in rows if status == "missing")
    covered = exact + alias + partial

    lines = [
        "# GKX final reconciliation audit",
        "",
        f"Compared `Supplementary_assistive_files/datashare.csv` ({len(gkx_cols)} predictors) "
        f"against repository panels:",
        f"- `{SIGNAL_PANEL_FILE.relative_to(PROJECT_ROOT)}`",
        f"- `{COMPLETE_ALL_PANEL_FILE.relative_to(PROJECT_ROOT)}`",
        "",
        "Characteristic columns exclude merge metadata (`permno`, `signal_yyyymm`, etc.) "
        "and CRSP return fields (`ret`, `rf`, `dlret`, …).",
        "",
        "## Summary counts",
        "",
        "| Metric | Count |",
        "| --- | ---: |",
        f"| Total GKX/datashare predictors | {len(gkx_cols)} |",
        f"| Exact name matches (in both panels) | {exact} |",
        f"| Implemented under different name (alias) | {alias} |",
        f"| Partially matched (alias + parallel variant) | {partial} |",
        f"| **GKX predictors covered** | **{covered}** |",
        f"| **GKX predictors still missing** | **{missing}** |",
        f"| Repository-only extras (signal panel) | {len(extras)} |",
        f"| Signal panel characteristic columns | {len(signal)} |",
        f"| Complete panel characteristic columns | {len(complete)} |",
        f"| Complete panel merged columns incl. return fields | {len(complete) + len(RETURN_COLS)} |",
        f"| Unique economic concepts in signal panel | {len(signal)} |",
        "",
        "## Verdict",
        "",
        f"**Answer: B.** The complete prediction panel has **{len(complete) + len(RETURN_COLS)} merged columns**, but only "
        f"**{len(complete)}** are characteristics. **{missing} of 94 GKX predictors remain missing**. "
        f"The panel also carries **{len(extras)} repository-only extras** and **duplicate implementations** "
        "for three GKX concepts (`bm`, `cfp`, `operprof`). We do **not** yet have all GKX predictors implemented.",
        "",
        "## GKX predictor reconciliation",
        "",
        "| GKX/datashare name | Repository name(s) | Status | Builder location | Notes |",
        "| --- | --- | --- | --- | --- |",
    ]
    for g, repo, status, builder, note in rows:
        lines.append(f"| `{g}` | `{repo}` | {status} | {builder} | {note} |")

    lines.extend([
        "",
        "## Repository-only extras (not in GKX datashare)",
        "",
        "| Repository name | Builder location | Notes |",
        "| --- | --- | --- |",
    ])
    for col in extras:
        lines.append(
            f"| `{col}` | {builder_loc(col)} | {EXTRA_NOTES.get(col, 'Not in GKX datashare')} |"
        )

    lines.extend([
        "",
        "## Missing predictors — suggested next batch (by difficulty)",
        "",
        "### Batch A — trivial / one-liner transforms",
        "",
        "Square existing `beta` panel column.",
        "",
        "`betasq`",
        "",
        "### Batch B — annual Compustat (Green/GKX)",
        "",
        "Follow Green SAS / `accounting_100.py`; fiscal ratios and event indicators.",
        "",
        "`rd`, `divi`, `divo`, `roic`, `tb`, `convind`, `secured`, `securedind`, "
        "`pchgm_pchsale`, `pchsale_pchinvt`, `pchsale_pchrect`, `pchsale_pchxsga`",
        "",
        "### Batch C — industry-adjusted annual",
        "",
        "Extend existing base variables with sic2 demeaning (pattern used for `bm_ia`, `me_ia`).",
        "",
        "`cfp_ia`, `chatoia`, `chempia`, `chpmia`, `pchcapx_ia`",
        "",
        "### Batch D — CRSP momentum / daily",
        "",
        "Rolling momentum changes and industry aggregates on monthly CRSP.",
        "",
        "`chmom`, `indmom`, `pricedelay`",
        "",
        "### Batch E — volatility / event volume",
        "",
        "Multi-month or multi-year windows; daily CRSP and possibly event dates.",
        "",
        "`idiovol`, `aeavol`, `roavol`, `stdacc`, `stdcf`",
        "",
        "### Batch F — ambiguous / verify first",
        "",
        "GKX lists both `ms` and `ps`; confirm whether `ms` duplicates `ps` or needs a separate score.",
        "",
        "`ms`",
        "",
    ])
    return "\n".join(lines)


def main():
    text = reconcile()
    DOCS_OUT.parent.mkdir(parents=True, exist_ok=True)
    DOCS_OUT.write_text(text, encoding="utf-8")
    mirror = DIAGNOSTICS_DIR / "gkx_final_reconciliation_audit.md"
    mirror.parent.mkdir(parents=True, exist_ok=True)
    mirror.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
