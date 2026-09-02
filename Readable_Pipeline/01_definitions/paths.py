"""Output paths for the readable reconstruction (isolated from production outputs/)."""
from __future__ import annotations

from pathlib import Path

READABLE_ROOT = Path(__file__).resolve().parents[1]
STOCK_ROOT = READABLE_ROOT.parent
OUTPUT_ROOT = READABLE_ROOT / "03_outputs"
CACHE_DIR = OUTPUT_ROOT / "cache"
SINGLE_CHARACTERS_DIR = OUTPUT_ROOT / "single_characters"
PANELS_DIR = OUTPUT_ROOT / "panels"
LOGS_DIR = OUTPUT_ROOT / "logs"
DIAGNOSTICS_DIR = OUTPUT_ROOT / "diagnostics"
SIGNAL_PANEL_FILE = PANELS_DIR / "all_character_signal_panel.csv"
NON_CHARACTER_STEMS = frozenset({"all_character_signal_panel"})


def ensure_output_tree() -> None:
    for path in (CACHE_DIR, SINGLE_CHARACTERS_DIR, PANELS_DIR, LOGS_DIR, DIAGNOSTICS_DIR):
        path.mkdir(parents=True, exist_ok=True)
    gitkeep = OUTPUT_ROOT / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()


def character_csv_path(stem: str) -> Path:
    return SINGLE_CHARACTERS_DIR / f"{stem}.csv"


def stem_cache_path(stem: str, suffix: str) -> Path:
    return CACHE_DIR / f"{stem}_{suffix}"
