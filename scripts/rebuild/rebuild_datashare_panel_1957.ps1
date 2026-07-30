# Rebuild a datashare-equivalent ranked panel with Dacheng conventions.
#
# Download window: 1950-01-01 (full lookback for long-horizon chars).
# Final trim: target_yyyymm >= 195701 (inside build_research_panel_1957.py).
#
# Usage (Windows):
#   $env:WRDS_USER = "your_wrds_username"
#   $env:STOCK_CHARACTERS_WORKERS = "8"
#   .\scripts\rebuild\rebuild_datashare_panel_1957.ps1
$ErrorActionPreference = "Stop"

$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location $Root

$WrdsUser = if ($env:WRDS_USER) { $env:WRDS_USER } elseif ($env:WRDS_USERNAME) { $env:WRDS_USERNAME } else { $null }
if (-not $WrdsUser) {
    throw "Set `$env:WRDS_USER (or `$env:WRDS_USERNAME) before running this script."
}

$Python = if ($env:STOCK_CHARACTERS_PYTHON) { $env:STOCK_CHARACTERS_PYTHON } else { "python" }
$Workers = if ($env:STOCK_CHARACTERS_WORKERS) { $env:STOCK_CHARACTERS_WORKERS } else { "8" }

Write-Host "==> Step 1: Full pipeline (Dacheng conventions, 1950+ lookback, 1957+ research panel)"
& $Python Character_Panels/run_full_pipeline.py `
  --wrds-user $WrdsUser `
  --profile research `
  --ccm-linktypes "L*" `
  --ccm-linkprim "P,C" `
  --crsp-shrcd ALL `
  --crsp-exchcd 1,2,3 `
  --industry-agg post_ccm `
  --sample-start 1950-01-01 `
  --skip-ibes `
  --workers $Workers

Write-Host "==> Step 2: Trim ranked research panel to datashare-matched columns"
& $Python Character_Panels/trim_research_panel_to_datashare.py `
  --input  outputs/panels/research_panel_1957_ranked.csv `
  --output outputs/panels/research_panel_1957_datashare_matched.csv

Write-Host "==> Step 3: Validate vs datashare.csv"
& $Python scripts/validation/compare_panel_vs_gkx_datashare.py `
  --panel outputs/panels/all_character_signal_panel.csv `
  --datashare Supplementary_assistive_files/datashare.csv

& $Python scripts/diagnose_sic_source_mismatch.py

Write-Host "Done. Outputs:"
Write-Host "  - outputs/panels/all_character_signal_panel.csv"
Write-Host "  - outputs/panels/research_panel_1957_ranked.csv"
Write-Host "  - outputs/panels/research_panel_1957_datashare_matched.csv"
