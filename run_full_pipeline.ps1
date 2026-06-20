# Full Stock Characters pipeline (Windows).
$ErrorActionPreference = "Stop"

if (-not $env:PGPASSFILE) {
    $env:PGPASSFILE = "$env:APPDATA\postgresql\pgpass.conf"
}

$Python = if ($env:STOCK_CHARACTERS_PYTHON) { $env:STOCK_CHARACTERS_PYTHON } else { "python" }
$WrdsUser = if ($env:WRDS_USERNAME) { $env:WRDS_USERNAME } elseif ($env:WRDS_USER) { $env:WRDS_USER } else { "YOUR_WRDS_USERNAME" }
$Root = $PSScriptRoot
$Log = Join-Path $Root "outputs\logs\pipeline_run.log"

Set-Location $Root
New-Item -ItemType Directory -Force -Path (Split-Path $Log) | Out-Null

if ($WrdsUser -eq "YOUR_WRDS_USERNAME") {
    Write-Error "Set `$env:WRDS_USERNAME (or `$env:WRDS_USER) or edit `$WrdsUser in run_full_pipeline.ps1"
}

$args = @("Character_Panels/run_full_pipeline.py", "--wrds-user", $WrdsUser, "--skip-ibes")
if ($env:RESUME -eq "1") { $args += "--resume" }
if ($env:SAMPLE_START) { $args += @("--sample-start", $env:SAMPLE_START) }
if ($env:SAMPLE_END) { $args += @("--sample-end", $env:SAMPLE_END) }
if ($env:STOCK_CHARACTERS_WORKERS) { $args += @("--workers", $env:STOCK_CHARACTERS_WORKERS) }
if ($env:STOCK_CHARACTERS_PROFILE) { $args += @("--profile", $env:STOCK_CHARACTERS_PROFILE) }
if ($env:GREEN_UNIVERSE -eq "1") { $args += "--green-universe" }

& $Python @args 2>&1 | Tee-Object -FilePath $Log -Append
