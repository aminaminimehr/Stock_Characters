"""Tests for configurable SIC source conventions."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Character_Builders"))

from _shared import green_builders as gb


class SicSourceTests(unittest.TestCase):
    def tearDown(self):
        if hasattr(self, "_old_sic_source"):
            if self._old_sic_source is None:
                os.environ.pop("STOCK_CHARACTERS_SIC_SOURCE", None)
            else:
                os.environ["STOCK_CHARACTERS_SIC_SOURCE"] = self._old_sic_source

    def setUp(self):
        self._old_sic_source = os.environ.get("STOCK_CHARACTERS_SIC_SOURCE")

    def test_sic_source_mode_defaults_to_comp_company(self):
        os.environ.pop("STOCK_CHARACTERS_SIC_SOURCE", None)
        self.assertEqual(gb._sic_source_mode(), "comp_company")

    def test_sic_source_mode_rejects_invalid(self):
        os.environ["STOCK_CHARACTERS_SIC_SOURCE"] = "invalid"
        with self.assertRaises(ValueError):
            gb._sic_source_mode()

    def test_attach_monthly_sic_crsp_legacy_hybrid(self):
        os.environ["STOCK_CHARACTERS_SIC_SOURCE"] = "crsp_msenames"
        frame = pd.DataFrame(
            {
                "permno": [10001, 10001],
                "signal_yyyymm": [202001, 202002],
                "siccd": [7372, 7372],
            }
        )

        def fake_map(db, crsp):
            return pd.DataFrame(
                {
                    "permno": [10001],
                    "signal_yyyymm": [202001],
                    "sic2_comp": ["28"],
                }
            )

        with patch.object(gb, "_compustat_sic2_monthly_map", fake_map):
            out = gb.attach_monthly_sic_metadata(frame, db=object())
        self.assertEqual(out.loc[out["signal_yyyymm"] == 202001, "sic"].iloc[0], 7372)
        self.assertEqual(out.loc[out["signal_yyyymm"] == 202001, "sic2"].iloc[0], "28")
        self.assertEqual(out.loc[out["signal_yyyymm"] == 202002, "sic2"].iloc[0], "73")

    def test_attach_monthly_sic_comp_company(self):
        os.environ["STOCK_CHARACTERS_SIC_SOURCE"] = "comp_company"
        frame = pd.DataFrame(
            {
                "permno": [10001, 10001],
                "signal_yyyymm": [202001, 202002],
                "siccd": [9999, 9999],
            }
        )

        def fake_expanded(db, crsp):
            return pd.DataFrame(
                {
                    "permno": [10001, 10001],
                    "signal_yyyymm": [202001, 202002],
                    "sic_comp": [2834, 2834],
                    "sic2_comp": ["28", "28"],
                }
            )

        with patch.object(gb, "_compustat_sic_annual_expanded", fake_expanded):
            out = gb.attach_monthly_sic_metadata(frame, db=object())
        self.assertNotIn("siccd", out.columns)
        self.assertEqual(out["sic"].tolist(), [2834, 2834])
        self.assertEqual(out["sic2"].tolist(), ["28", "28"])

    def test_sic2_from_sic_series(self):
        series = pd.Series([2834, np.nan, 7372.0])
        out = gb._sic2_from_sic_series(series)
        self.assertEqual(out.tolist()[0], "28")
        self.assertTrue(pd.isna(out.tolist()[1]))
        self.assertEqual(out.tolist()[2], "73")


if __name__ == "__main__":
    unittest.main()
