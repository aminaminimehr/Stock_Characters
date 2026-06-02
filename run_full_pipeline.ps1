# Full Stock Characters pipeline (Windows).
# Set $WrdsUser and $Python before running, or edit the defaults below.
$ErrorActionPreference = "Stop"

if (-not $env:PGPASSFILE) {
    $env:PGPASSFILE = "$env:APPDATA\postgresql\pgpass.conf"
}

$Python = if ($env:STOCK_CHARACTERS_PYTHON) { $env:STOCK_CHARACTERS_PYTHON } else { "python" }
$WrdsUser = if ($env:WRDS_USER) { $env:WRDS_USER } else { "YOUR_WRDS_USERNAME" }
$Root = $PSScriptRoot
$Log = Join-Path $Root "outputs\pipeline_run.log"

Set-Location $Root
New-Item -ItemType Directory -Force -Path (Split-Path $Log) | Out-Null

if ($WrdsUser -eq "YOUR_WRDS_USERNAME") {
    Write-Error "Set `$env:WRDS_USER or edit `$WrdsUser in run_full_pipeline.ps1"
}

& $Python Character_Panels/run_full_pipeline.py --wrds-user $WrdsUser --skip-ibes 2>&1 |
    Tee-Object -FilePath $Log
