#!/usr/bin/env python3
"""Compare built characteristics against GKX datashare columns (header-only)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from output_paths import DIAGNOSTICS_DIR, list_character_stems  # noqa: E402

GKX_TXT = PROJECT_ROOT / "Supplementary_assistive_files" / "GKX_characters.txt"
DATASHARE = PROJECT_ROOT / "Supplementary_assistive_files" / "datashare.csv"
DOCS_GKX = PROJECT_ROOT / "docs" / "gkx"

META_COLS = {"permno", "date", "sic2"}

# GKX datashare name -> repo stem(s) that may represent the same economic object.
# Final validation against datashare.csv is deferred.
GKX_ALIAS_CANDIDATES = {
    "operprof": ("op", "operating_profitability"),
    "rd_mve": ("rdm",),
    "retvol": ("rvar_mean",),
    "roaq": ("roa1",),
    "roeq": ("roe",),
    "mve_ia": ("me_ia",),
    "ear": ("abr",),
    "bm": ("book_to_market",),  # repo also has separate HXZ book_to_market
    "cfp": ("cash_flow_to_price",),
}


def norm(name: str) -> str:
    return re.sub(r"[^a-z0-9_]", "", str(name).strip().lower())


def load_gkx_datashare_predictors() -> list[str]:
    cols = [norm(c) for c in pd.read_csv(DATASHARE, nrows=0).columns]
    return sorted(c for c in cols if c not in META_COLS)


def resolve_built(gkx_name: str, built: set[str]) -> list[str]:
    if gkx_name in built:
        return [gkx_name]
    return [s for s in GKX_ALIAS_CANDIDATES.get(gkx_name, ()) if s in built]


def main():
    gkx = load_gkx_datashare_predictors()
    built = {norm(s) for s in list_character_stems()}

    direct = []
    via_alias = []
    missing = []
    for name in gkx:
        matches = resolve_built(name, built)
        if name in built:
            direct.append(name)
        elif matches:
            via_alias.append((name, matches))
        else:
            missing.append(name)

    extras = sorted(
        s
        for s in built
        if s not in gkx
        and not any(s in cands for cands in GKX_ALIAS_CANDIDATES.values())
    )

    lines = [
        "# GKX (Gu-Kelly-Xiu) gap audit",
        "",
        f"- GKX datashare predictors: **{len(gkx)}**",
        f"- Built character CSV stems: **{len(built)}**",
        f"- Direct name match: **{len(direct)}**",
        f"- Covered via alias (validation deferred): **{len(via_alias)}**",
        f"- Missing: **{len(missing)}**",
        "",
        "## Likely duplicates (different names; validate later vs datashare)",
        "",
    ]
    for gkx_name, repo_stems in sorted(via_alias):
        lines.append(f"- `{gkx_name}` (datashare) -> {', '.join(f'`{s}`' for s in repo_stems)} (repo)")
    if not via_alias:
        lines.append("(none)")

    lines.extend(["", "## Missing GKX predictors", ""])
    for name in missing:
        lines.append(f"- `{name}`")

    lines.extend(["", "## Built but not in GKX datashare", "", ", ".join(extras) if extras else "(none)", ""])

    out = DOCS_GKX / "gkx_gap_audit.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    mirror = DIAGNOSTICS_DIR / "gkx_gap_audit.md"
    mirror.parent.mkdir(parents=True, exist_ok=True)
    mirror.write_text(out.read_text(encoding="utf-8"), encoding="utf-8")
    print(out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
