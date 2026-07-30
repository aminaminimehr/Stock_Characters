#!/usr/bin/env bash
# Rebuild a datashare-equivalent ranked panel with Dacheng conventions.
#
# Download window: 1950-01-01 (full lookback for long-horizon chars).
# Final trim: target_yyyymm >= 195701 (inside build_research_panel_1957.py).
#
# Usage (Linux server):
#   export WRDS_USER=your_wrds_username
#   export PGPASSFILE=~/.pgpass
#   export STOCK_CHARACTERS_WORKERS=8
#   bash scripts/rebuild/rebuild_datashare_panel_1957.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

: "${WRDS_USER:?Set WRDS_USER to your WRDS PostgreSQL username}"
export PGPASSFILE="${PGPASSFILE:-${HOME}/.pgpass}"

PYTHON="${STOCK_CHARACTERS_PYTHON:-python}"
WORKERS="${STOCK_CHARACTERS_WORKERS:-8}"

echo "==> Step 1: Full pipeline (Dacheng conventions, 1950+ lookback, 1957+ research panel)"
"${PYTHON}" Character_Panels/run_full_pipeline.py \
  --wrds-user "${WRDS_USER}" \
  --profile research \
  --ccm-linktypes "L*" \
  --ccm-linkprim "P,C" \
  --crsp-shrcd ALL \
  --crsp-exchcd 1,2,3 \
  --industry-agg post_ccm \
  --sample-start 1950-01-01 \
  --skip-ibes \
  --workers "${WORKERS}"

echo "==> Step 2: Trim ranked research panel to datashare-matched columns"
"${PYTHON}" Character_Panels/trim_research_panel_to_datashare.py \
  --input  outputs/panels/research_panel_1957_ranked.csv \
  --output outputs/panels/research_panel_1957_datashare_matched.csv

echo "==> Step 3: Validate vs datashare.csv"
"${PYTHON}" scripts/validation/compare_panel_vs_gkx_datashare.py \
  --panel outputs/panels/all_character_signal_panel.csv \
  --datashare Supplementary_assistive_files/datashare.csv

"${PYTHON}" scripts/diagnose_sic_source_mismatch.py

echo "Done. Outputs:"
echo "  - outputs/panels/all_character_signal_panel.csv"
echo "  - outputs/panels/research_panel_1957_ranked.csv"
echo "  - outputs/panels/research_panel_1957_datashare_matched.csv"
