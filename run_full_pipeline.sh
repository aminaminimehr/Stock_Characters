#!/usr/bin/env bash
# Full Stock Characters pipeline (Linux/macOS).
# Usage:
#   export WRDS_USER=your_wrds_username
#   export PGPASSFILE=~/.pgpass
#   bash run_full_pipeline.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

: "${WRDS_USER:?Set WRDS_USER to your WRDS PostgreSQL username}"
export PGPASSFILE="${PGPASSFILE:-${HOME}/.pgpass}"

PYTHON="${STOCK_CHARACTERS_PYTHON:-python}"
LOG="${ROOT}/outputs/pipeline_run.log"
mkdir -p "${ROOT}/outputs"

SKIP_IBES="${SKIP_IBES:-1}"
RESUME="${RESUME:-0}"

args=(--wrds-user "${WRDS_USER}")
if [[ "${SKIP_IBES}" == "1" ]]; then
  args+=(--skip-ibes)
fi
if [[ "${RESUME}" == "1" ]]; then
  args+=(--resume)
fi

"${PYTHON}" Character_Panels/run_full_pipeline.py "${args[@]}" 2>&1 | tee -a "${LOG}"
