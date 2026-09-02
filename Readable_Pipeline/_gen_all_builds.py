#!/usr/bin/env python3
"""Generate 02_builders/all_builds.py with all 95 build_* functions."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "01_definitions"))
OUT = ROOT / "02_builders" / "all_builds.py"

HEADER = '''\
"""All 95 GKX datashare builder entry points (one WRDS pull per stem)."""
from __future__ import annotations

import sys
from pathlib import Path

_DEFS = Path(__file__).resolve().parents[1] / "01_definitions"
if str(_DEFS) not in sys.path:
    sys.path.insert(0, str(_DEFS))

from annual_formulas import apply_annual_formula, needs_industry_adjustment
from annual_runner import fetch_green_funda, finalize_green_annual, write_annual
from beta_runner import build_factor_stem, write_factor
from bm_ia_runner import build_bm_ia_from_parquet, write_bm_ia
from catalog import (
    ANNUAL_FUNDA_ITEMS,
    DAILY_MONTHLY_STEMS,
    GREEN_ANNUAL_STEMS,
    HXZ_STEMS,
    MONTHLY_CRSP_STEMS,
    QUARTERLY_FUNDA_ITEMS,
    QUARTERLY_STEMS,
    SPECIAL_STEMS,
)
from config import DATASHARE_PREDICTORS
from daily_monthly_runner import merge_daily_to_monthly, write_daily_monthly
from event_runner import build_event_stem, write_event
from hxz_runner import build_bm_panel, build_operprof_panel, write_hxz_annual
from monthly_runner import attach_monthly_sic, compute_monthly_feature, fetch_crsp_msf, write_monthly
from ms_runner import build_ms_panel, write_ms
from paths import SINGLE_CHARACTERS_DIR
from quarterly_runner import build_quarterly_stem, write_quarterly
'''

ANNUAL_BODY = '''
def build_{stem}(db, use_cache=True):
    stem = "{stem}"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items{naics_kw}, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)
'''

MONTHLY_BODY = '''
def build_{stem}(db, use_cache=True):
    stem = "{stem}"
    crsp = fetch_crsp_msf(db, stem, use_cache=use_cache)
    crsp = attach_monthly_sic(crsp, db, stem, use_cache=use_cache)
    crsp = compute_monthly_feature(crsp, stem)
    write_monthly(crsp, stem)
'''

DAILY_BODY = '''
def build_{stem}(db, use_cache=True):
    stem = "{stem}"
    out = merge_daily_to_monthly(db, stem, use_cache=use_cache)
    write_daily_monthly(out, stem)
'''

QUARTERLY_BODY = '''
def build_{stem}(db, use_cache=True):
    stem = "{stem}"
    items = QUARTERLY_FUNDA_ITEMS[stem]
    out = build_quarterly_stem(db, stem, items, use_cache=use_cache)
    write_quarterly(out, stem)
'''

HXZ_BM = '''
def build_bm(db, use_cache=True):
    out = build_bm_panel(db, use_cache=use_cache)
    write_hxz_annual(out, "bm")
'''

HXZ_OPE = '''
def build_operprof(db, use_cache=True):
    out = build_operprof_panel(db, use_cache=use_cache)
    write_hxz_annual(out, "operprof")
'''

BM_IA = '''
def build_bm_ia(db, use_cache=True):
    _ = db, use_cache
    out = build_bm_ia_from_parquet(SINGLE_CHARACTERS_DIR / "bm.parquet")
    write_bm_ia(out)
'''

FACTOR_BODY = '''
def build_{stem}(db, use_cache=True):
    stem = "{stem}"
    out = build_factor_stem(db, stem, use_cache=use_cache)
    write_factor(out, stem)
'''

EVENT_BODY = '''
def build_{stem}(db, use_cache=True):
    stem = "{stem}"
    out = build_event_stem(db, stem, use_cache=use_cache)
    write_event(out, stem)
'''

MS_BODY = '''
def build_ms(db, use_cache=True):
    out = build_ms_panel(db, use_cache=use_cache)
    write_ms(out)
'''

FOOTER = '''
BUILDERS: dict[str, callable] = {{
{entries}
}}

assert set(BUILDERS) == set(DATASHARE_PREDICTORS)
assert len(BUILDERS) == 95
'''

from catalog import (  # noqa: E402
    DAILY_MONTHLY_STEMS,
    GREEN_ANNUAL_STEMS,
    HXZ_STEMS,
    MONTHLY_CRSP_STEMS,
    NO_WRDS_STEMS,
    QUARTERLY_STEMS,
    SPECIAL_STEMS,
)
from config import DATASHARE_PREDICTORS  # noqa: E402

parts = [HEADER]
registry: list[str] = []

for stem in DATASHARE_PREDICTORS:
    if stem in GREEN_ANNUAL_STEMS:
        naics_kw = ", include_naics=True" if stem == "sin" else ""
        parts.append(ANNUAL_BODY.format(stem=stem, naics_kw=naics_kw))
        registry.append(stem)
    elif stem in HXZ_STEMS:
        parts.append(HXZ_BM if stem == "bm" else HXZ_OPE)
        registry.append(stem)
    elif stem in NO_WRDS_STEMS:
        parts.append(BM_IA)
        registry.append(stem)
    elif stem in MONTHLY_CRSP_STEMS:
        parts.append(MONTHLY_BODY.format(stem=stem))
        registry.append(stem)
    elif stem in DAILY_MONTHLY_STEMS:
        parts.append(DAILY_BODY.format(stem=stem))
        registry.append(stem)
    elif stem in QUARTERLY_STEMS:
        parts.append(QUARTERLY_BODY.format(stem=stem))
        registry.append(stem)
    elif stem == "ms":
        parts.append(MS_BODY)
        registry.append(stem)
    elif stem in ("beta", "betasq", "idiovol", "pricedelay"):
        parts.append(FACTOR_BODY.format(stem=stem))
        registry.append(stem)
    elif stem in ("ear", "aeavol"):
        parts.append(EVENT_BODY.format(stem=stem))
        registry.append(stem)
    else:
        raise RuntimeError(f"Unhandled stem: {stem}")

entries = ",\n".join(f'    "{s}": build_{s}' for s in registry)
parts.append(FOOTER.format(entries=entries))

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(parts), encoding="utf-8")
print(f"Wrote {OUT} ({len(registry)} builders)")
