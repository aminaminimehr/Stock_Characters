"""Write per-character CSVs (same contract as production write_character)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def write_character(df: pd.DataFrame, character: str, output_dir: Path) -> Path:
    out = df.copy()
    out = out[out[character].replace([np.inf, -np.inf], np.nan).notna()].copy()
    output_path = Path(output_dir) / f"{character}.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    print(f"{character}: {len(out):,} rows -> {output_path}", flush=True)
    return output_path
