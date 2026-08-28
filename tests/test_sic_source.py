"""Tests for hardcoded SIC source conventions."""
from __future__ import annotations

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
from pipeline_config import SIC_SOURCE


class SicSourceTests(unittest.TestCase):
    def test_sic_source_is_hardcoded_comp_company(self):
        self.assertEqual(SIC_SOURCE, "comp_company")
        self.assertEqual(gb._sic_source_mode(), "comp_company")

    def test_attach_monthly_sic_comp_company(self):
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
