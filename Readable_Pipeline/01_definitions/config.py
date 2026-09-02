"""Re-export hardcoded pipeline conventions from production pipeline_config."""
from __future__ import annotations

import sys
from pathlib import Path

_STOCK_ROOT = Path(__file__).resolve().parents[2]
if str(_STOCK_ROOT) not in sys.path:
    sys.path.insert(0, str(_STOCK_ROOT))

from pipeline_config import (  # noqa: E402
    CCM_LINKPRIM,
    CCM_LINKTYPES,
    CRSP_EXCHCD,
    CRSP_SHRCD,
    DATASHARE_COLUMNS,
    DATASHARE_PREDICTORS,
    INDUSTRY_AGG,
    SAMPLE_END,
    SAMPLE_START,
    SIC_SOURCE,
    SKIP_IBES,
)

__all__ = [
    "CCM_LINKPRIM",
    "CCM_LINKTYPES",
    "CRSP_EXCHCD",
    "CRSP_SHRCD",
    "DATASHARE_COLUMNS",
    "DATASHARE_PREDICTORS",
    "INDUSTRY_AGG",
    "SAMPLE_END",
    "SAMPLE_START",
    "SIC_SOURCE",
    "SKIP_IBES",
]
