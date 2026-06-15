"""Tests for source-specific panel timing conventions."""
import pandas as pd

from Character_Panels.timing import (
    expand_annual_file_green,
    expand_annual_file_june,
    green_signal_month_ends,
    timing_convention_for_stem,
)


def test_green_window_june_2017_fiscal():
    months = green_signal_month_ends(pd.Timestamp("2017-06-30"))
    yyyymm = [d.year * 100 + d.month for d in months]
    assert yyyymm[0] == 201801
    assert yyyymm[-1] == 201901
    assert 201806 in yyyymm
    assert 201905 not in yyyymm


def test_green_expansion_keeps_latest_fiscal_per_month():
    annual = pd.DataFrame(
        {
            "permno": [1, 1],
            "permco": [1, 1],
            "gvkey": ["A", "A"],
            "datadate": ["2016-12-31", "2017-12-31"],
            "sic": [1000, 1000],
            "fyear": [2016, 2017],
            "chatoia": [0.1, 0.2],
        }
    )
    panel = expand_annual_file_green(annual, ["chatoia"])
    july_2018 = panel[panel["signal_yyyymm"] == 201807]
    assert len(july_2018) == 1
    assert july_2018.iloc[0]["chatoia"] == 0.2


def test_june_expansion_starts_june_after_fiscal_year():
    annual = pd.DataFrame(
        {
            "permno": [1],
            "permco": [1],
            "gvkey": ["A"],
            "datadate": ["2017-12-31"],
            "sic": [1000],
            "fyear": [2017],
            "bm": [1.5],
        }
    )
    panel = expand_annual_file_june(annual, ["bm"])
    expected = {201806, 201807, 201808, 201809, 201810, 201811, 201812,
                201901, 201902, 201903, 201904, 201905}
    assert set(panel["signal_yyyymm"]) == expected


def test_green_annual_stem_classification():
    assert timing_convention_for_stem("chatoia").value == "green_annual_rolling"
    assert timing_convention_for_stem("book_to_market").value == "hxz_june"
