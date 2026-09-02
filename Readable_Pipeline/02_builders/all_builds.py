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


def build_convind(db, use_cache=True):
    stem = "convind"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_rd_sale(db, use_cache=True):
    stem = "rd_sale"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_rd_mve(db, use_cache=True):
    stem = "rd_mve"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_realestate(db, use_cache=True):
    stem = "realestate"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_dy(db, use_cache=True):
    stem = "dy"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_dolvol(db, use_cache=True):
    stem = "dolvol"
    crsp = fetch_crsp_msf(db, stem, use_cache=use_cache)
    crsp = attach_monthly_sic(crsp, db, stem, use_cache=use_cache)
    crsp = compute_monthly_feature(crsp, stem)
    write_monthly(crsp, stem)


def build_saleinv(db, use_cache=True):
    stem = "saleinv"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_mom1m(db, use_cache=True):
    stem = "mom1m"
    crsp = fetch_crsp_msf(db, stem, use_cache=use_cache)
    crsp = attach_monthly_sic(crsp, db, stem, use_cache=use_cache)
    crsp = compute_monthly_feature(crsp, stem)
    write_monthly(crsp, stem)


def build_secured(db, use_cache=True):
    stem = "secured"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_depr(db, use_cache=True):
    stem = "depr"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_beta(db, use_cache=True):
    stem = "beta"
    out = build_factor_stem(db, stem, use_cache=use_cache)
    write_factor(out, stem)


def build_betasq(db, use_cache=True):
    stem = "betasq"
    out = build_factor_stem(db, stem, use_cache=use_cache)
    write_factor(out, stem)


def build_sp(db, use_cache=True):
    stem = "sp"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_mvel1(db, use_cache=True):
    stem = "mvel1"
    crsp = fetch_crsp_msf(db, stem, use_cache=use_cache)
    crsp = attach_monthly_sic(crsp, db, stem, use_cache=use_cache)
    crsp = compute_monthly_feature(crsp, stem)
    write_monthly(crsp, stem)


def build_ill(db, use_cache=True):
    stem = "ill"
    out = merge_daily_to_monthly(db, stem, use_cache=use_cache)
    write_daily_monthly(out, stem)


def build_lev(db, use_cache=True):
    stem = "lev"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_salecash(db, use_cache=True):
    stem = "salecash"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_roic(db, use_cache=True):
    stem = "roic"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_cashpr(db, use_cache=True):
    stem = "cashpr"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_ep(db, use_cache=True):
    stem = "ep"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_baspread(db, use_cache=True):
    stem = "baspread"
    out = merge_daily_to_monthly(db, stem, use_cache=use_cache)
    write_daily_monthly(out, stem)


def build_tang(db, use_cache=True):
    stem = "tang"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_quick(db, use_cache=True):
    stem = "quick"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_currat(db, use_cache=True):
    stem = "currat"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_salerec(db, use_cache=True):
    stem = "salerec"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_zerotrade(db, use_cache=True):
    stem = "zerotrade"
    out = merge_daily_to_monthly(db, stem, use_cache=use_cache)
    write_daily_monthly(out, stem)


def build_std_dolvol(db, use_cache=True):
    stem = "std_dolvol"
    out = merge_daily_to_monthly(db, stem, use_cache=use_cache)
    write_daily_monthly(out, stem)


def build_retvol(db, use_cache=True):
    stem = "retvol"
    out = merge_daily_to_monthly(db, stem, use_cache=use_cache)
    write_daily_monthly(out, stem)


def build_std_turn(db, use_cache=True):
    stem = "std_turn"
    out = merge_daily_to_monthly(db, stem, use_cache=use_cache)
    write_daily_monthly(out, stem)


def build_securedind(db, use_cache=True):
    stem = "securedind"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_gma(db, use_cache=True):
    stem = "gma"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_mom6m(db, use_cache=True):
    stem = "mom6m"
    crsp = fetch_crsp_msf(db, stem, use_cache=use_cache)
    crsp = attach_monthly_sic(crsp, db, stem, use_cache=use_cache)
    crsp = compute_monthly_feature(crsp, stem)
    write_monthly(crsp, stem)


def build_pctacc(db, use_cache=True):
    stem = "pctacc"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_maxret(db, use_cache=True):
    stem = "maxret"
    out = merge_daily_to_monthly(db, stem, use_cache=use_cache)
    write_daily_monthly(out, stem)


def build_mom12m(db, use_cache=True):
    stem = "mom12m"
    crsp = fetch_crsp_msf(db, stem, use_cache=use_cache)
    crsp = attach_monthly_sic(crsp, db, stem, use_cache=use_cache)
    crsp = compute_monthly_feature(crsp, stem)
    write_monthly(crsp, stem)


def build_acc(db, use_cache=True):
    stem = "acc"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_absacc(db, use_cache=True):
    stem = "absacc"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_chmom(db, use_cache=True):
    stem = "chmom"
    crsp = fetch_crsp_msf(db, stem, use_cache=use_cache)
    crsp = attach_monthly_sic(crsp, db, stem, use_cache=use_cache)
    crsp = compute_monthly_feature(crsp, stem)
    write_monthly(crsp, stem)


def build_mom36m(db, use_cache=True):
    stem = "mom36m"
    crsp = fetch_crsp_msf(db, stem, use_cache=use_cache)
    crsp = attach_monthly_sic(crsp, db, stem, use_cache=use_cache)
    crsp = compute_monthly_feature(crsp, stem)
    write_monthly(crsp, stem)


def build_cfp(db, use_cache=True):
    stem = "cfp"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_orgcap(db, use_cache=True):
    stem = "orgcap"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_idiovol(db, use_cache=True):
    stem = "idiovol"
    out = build_factor_stem(db, stem, use_cache=use_cache)
    write_factor(out, stem)


def build_cashdebt(db, use_cache=True):
    stem = "cashdebt"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_chcsho(db, use_cache=True):
    stem = "chcsho"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_sgr(db, use_cache=True):
    stem = "sgr"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_pchsale_pchxsga(db, use_cache=True):
    stem = "pchsale_pchxsga"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_chinv(db, use_cache=True):
    stem = "chinv"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_pchsale_pchinvt(db, use_cache=True):
    stem = "pchsale_pchinvt"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_pchsaleinv(db, use_cache=True):
    stem = "pchsaleinv"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_hire(db, use_cache=True):
    stem = "hire"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_grltnoa(db, use_cache=True):
    stem = "grltnoa"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_lgr(db, use_cache=True):
    stem = "lgr"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_turn(db, use_cache=True):
    stem = "turn"
    crsp = fetch_crsp_msf(db, stem, use_cache=use_cache)
    crsp = attach_monthly_sic(crsp, db, stem, use_cache=use_cache)
    crsp = compute_monthly_feature(crsp, stem)
    write_monthly(crsp, stem)


def build_pchgm_pchsale(db, use_cache=True):
    stem = "pchgm_pchsale"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_egr(db, use_cache=True):
    stem = "egr"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_pchquick(db, use_cache=True):
    stem = "pchquick"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_pchcurrat(db, use_cache=True):
    stem = "pchcurrat"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_pchdepr(db, use_cache=True):
    stem = "pchdepr"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_pchsale_pchrect(db, use_cache=True):
    stem = "pchsale_pchrect"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_invest(db, use_cache=True):
    stem = "invest"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_divi(db, use_cache=True):
    stem = "divi"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_stdcf(db, use_cache=True):
    stem = "stdcf"
    items = QUARTERLY_FUNDA_ITEMS[stem]
    out = build_quarterly_stem(db, stem, items, use_cache=use_cache)
    write_quarterly(out, stem)


def build_stdacc(db, use_cache=True):
    stem = "stdacc"
    items = QUARTERLY_FUNDA_ITEMS[stem]
    out = build_quarterly_stem(db, stem, items, use_cache=use_cache)
    write_quarterly(out, stem)


def build_divo(db, use_cache=True):
    stem = "divo"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_cash(db, use_cache=True):
    stem = "cash"
    items = QUARTERLY_FUNDA_ITEMS[stem]
    out = build_quarterly_stem(db, stem, items, use_cache=use_cache)
    write_quarterly(out, stem)


def build_grcapx(db, use_cache=True):
    stem = "grcapx"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_rd(db, use_cache=True):
    stem = "rd"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_sin(db, use_cache=True):
    stem = "sin"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, include_naics=True, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_sic2(db, use_cache=True):
    stem = "sic2"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_pricedelay(db, use_cache=True):
    stem = "pricedelay"
    out = build_factor_stem(db, stem, use_cache=use_cache)
    write_factor(out, stem)


def build_tb(db, use_cache=True):
    stem = "tb"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_chatoia(db, use_cache=True):
    stem = "chatoia"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_age(db, use_cache=True):
    stem = "age"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_herf(db, use_cache=True):
    stem = "herf"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_ps(db, use_cache=True):
    stem = "ps"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_mve_ia(db, use_cache=True):
    stem = "mve_ia"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_roaq(db, use_cache=True):
    stem = "roaq"
    items = QUARTERLY_FUNDA_ITEMS[stem]
    out = build_quarterly_stem(db, stem, items, use_cache=use_cache)
    write_quarterly(out, stem)


def build_bm(db, use_cache=True):
    out = build_bm_panel(db, use_cache=use_cache)
    write_hxz_annual(out, "bm")


def build_chempia(db, use_cache=True):
    stem = "chempia"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_rsup(db, use_cache=True):
    stem = "rsup"
    items = QUARTERLY_FUNDA_ITEMS[stem]
    out = build_quarterly_stem(db, stem, items, use_cache=use_cache)
    write_quarterly(out, stem)


def build_roeq(db, use_cache=True):
    stem = "roeq"
    items = QUARTERLY_FUNDA_ITEMS[stem]
    out = build_quarterly_stem(db, stem, items, use_cache=use_cache)
    write_quarterly(out, stem)


def build_operprof(db, use_cache=True):
    out = build_operprof_panel(db, use_cache=use_cache)
    write_hxz_annual(out, "operprof")


def build_chtx(db, use_cache=True):
    stem = "chtx"
    items = QUARTERLY_FUNDA_ITEMS[stem]
    out = build_quarterly_stem(db, stem, items, use_cache=use_cache)
    write_quarterly(out, stem)


def build_nincr(db, use_cache=True):
    stem = "nincr"
    items = QUARTERLY_FUNDA_ITEMS[stem]
    out = build_quarterly_stem(db, stem, items, use_cache=use_cache)
    write_quarterly(out, stem)


def build_cinvest(db, use_cache=True):
    stem = "cinvest"
    items = QUARTERLY_FUNDA_ITEMS[stem]
    out = build_quarterly_stem(db, stem, items, use_cache=use_cache)
    write_quarterly(out, stem)


def build_aeavol(db, use_cache=True):
    stem = "aeavol"
    out = build_event_stem(db, stem, use_cache=use_cache)
    write_event(out, stem)


def build_bm_ia(db, use_cache=True):
    _ = db, use_cache
    out = build_bm_ia_from_parquet(SINGLE_CHARACTERS_DIR / "bm.parquet")
    write_bm_ia(out)


def build_ear(db, use_cache=True):
    stem = "ear"
    out = build_event_stem(db, stem, use_cache=use_cache)
    write_event(out, stem)


def build_chpmia(db, use_cache=True):
    stem = "chpmia"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_cfp_ia(db, use_cache=True):
    stem = "cfp_ia"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_roavol(db, use_cache=True):
    stem = "roavol"
    items = QUARTERLY_FUNDA_ITEMS[stem]
    out = build_quarterly_stem(db, stem, items, use_cache=use_cache)
    write_quarterly(out, stem)


def build_ms(db, use_cache=True):
    out = build_ms_panel(db, use_cache=use_cache)
    write_ms(out)


def build_pchcapx_ia(db, use_cache=True):
    stem = "pchcapx_ia"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


def build_indmom(db, use_cache=True):
    stem = "indmom"
    crsp = fetch_crsp_msf(db, stem, use_cache=use_cache)
    crsp = attach_monthly_sic(crsp, db, stem, use_cache=use_cache)
    crsp = compute_monthly_feature(crsp, stem)
    write_monthly(crsp, stem)


def build_agr(db, use_cache=True):
    stem = "agr"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)


BUILDERS: dict[str, callable] = {
    "convind": build_convind,
    "rd_sale": build_rd_sale,
    "rd_mve": build_rd_mve,
    "realestate": build_realestate,
    "dy": build_dy,
    "dolvol": build_dolvol,
    "saleinv": build_saleinv,
    "mom1m": build_mom1m,
    "secured": build_secured,
    "depr": build_depr,
    "beta": build_beta,
    "betasq": build_betasq,
    "sp": build_sp,
    "mvel1": build_mvel1,
    "ill": build_ill,
    "lev": build_lev,
    "salecash": build_salecash,
    "roic": build_roic,
    "cashpr": build_cashpr,
    "ep": build_ep,
    "baspread": build_baspread,
    "tang": build_tang,
    "quick": build_quick,
    "currat": build_currat,
    "salerec": build_salerec,
    "zerotrade": build_zerotrade,
    "std_dolvol": build_std_dolvol,
    "retvol": build_retvol,
    "std_turn": build_std_turn,
    "securedind": build_securedind,
    "gma": build_gma,
    "mom6m": build_mom6m,
    "pctacc": build_pctacc,
    "maxret": build_maxret,
    "mom12m": build_mom12m,
    "acc": build_acc,
    "absacc": build_absacc,
    "chmom": build_chmom,
    "mom36m": build_mom36m,
    "cfp": build_cfp,
    "orgcap": build_orgcap,
    "idiovol": build_idiovol,
    "cashdebt": build_cashdebt,
    "chcsho": build_chcsho,
    "sgr": build_sgr,
    "pchsale_pchxsga": build_pchsale_pchxsga,
    "chinv": build_chinv,
    "pchsale_pchinvt": build_pchsale_pchinvt,
    "pchsaleinv": build_pchsaleinv,
    "hire": build_hire,
    "grltnoa": build_grltnoa,
    "lgr": build_lgr,
    "turn": build_turn,
    "pchgm_pchsale": build_pchgm_pchsale,
    "egr": build_egr,
    "pchquick": build_pchquick,
    "pchcurrat": build_pchcurrat,
    "pchdepr": build_pchdepr,
    "pchsale_pchrect": build_pchsale_pchrect,
    "invest": build_invest,
    "divi": build_divi,
    "stdcf": build_stdcf,
    "stdacc": build_stdacc,
    "divo": build_divo,
    "cash": build_cash,
    "grcapx": build_grcapx,
    "rd": build_rd,
    "sin": build_sin,
    "sic2": build_sic2,
    "pricedelay": build_pricedelay,
    "tb": build_tb,
    "chatoia": build_chatoia,
    "age": build_age,
    "herf": build_herf,
    "ps": build_ps,
    "mve_ia": build_mve_ia,
    "roaq": build_roaq,
    "bm": build_bm,
    "chempia": build_chempia,
    "rsup": build_rsup,
    "roeq": build_roeq,
    "operprof": build_operprof,
    "chtx": build_chtx,
    "nincr": build_nincr,
    "cinvest": build_cinvest,
    "aeavol": build_aeavol,
    "bm_ia": build_bm_ia,
    "ear": build_ear,
    "chpmia": build_chpmia,
    "cfp_ia": build_cfp_ia,
    "roavol": build_roavol,
    "ms": build_ms,
    "pchcapx_ia": build_pchcapx_ia,
    "indmom": build_indmom,
    "agr": build_agr
}

assert set(BUILDERS) == set(DATASHARE_PREDICTORS)
assert len(BUILDERS) == 95
