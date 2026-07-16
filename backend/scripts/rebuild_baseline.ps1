param(
  [Parameter(Mandatory=$true)][string]$Source,
  [string]$Output = "../artifacts/generated"
)
$ErrorActionPreference = "Stop"
worldcup-rebuild --source $Source --output $Output --forecast-cutoff 2026-06-10T23:59:59Z --train-end 2022-11-19 --backtest-end 2022-12-18 --seed 20260611 --profile baseline
