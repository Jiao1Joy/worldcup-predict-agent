# Prediction Engine

## Data source

- **martj42 international results** (`results.csv`): men's full internationals since 1872.
  - Columns: `date,home_team,away_team,home_score,away_score,tournament,city,country,neutral`
  - License: CC0 1.0 (public domain). Redistributable.
  - Attribution: see `docs/DATA_SOURCES.md`.

## Leakage boundary

- Portfolio Frozen cutoff: `2026-06-10T23:59:59Z`. No match after this date may enter a frozen forecast.
- 2022 backtest training cutoff: `2022-11-19`. Evaluation window: `2022-11-20` through `2022-12-18`.
- Splits are temporal, not random. The 2022 World Cup is never in the training partition.

## Rebuild profiles

- `baseline` (default, CI-runnable on CPU): Elo + three goal models (Poisson, Bivariate Poisson, Dixon-Coles) + Logistic calibration.
- `full` (optional): additionally loads LightGBM/XGBoost/CatBoost adapters. Exits with code 2 if `full-training` extras are absent.

```powershell
python -m pip install -e ".[dev]"
worldcup-rebuild --source ../international_results-master/results.csv `
  --output ../artifacts/generated `
  --forecast-cutoff 2026-06-10T23:59:59Z `
  --train-end 2022-11-19 --backtest-end 2022-12-18 `
  --seed 20260611 --profile baseline
```

## Artifact manifest

Each rebuild writes a `ModelArtifactManifest` with model/data versions, trained-until timestamp, validation window, selected goal model, fusion weights, file SHA-256 hashes, and metrics. The runtime loader rejects any data-version mismatch or hash mismatch.

## Invariants

- Score matrices are non-negative and sum to 1.
- Fused outcome probabilities and score-matrix regions agree within `1e-9` (iterative proportional fitting).
- Backtest aggregate metrics are recomputable from exported per-match rows within `1e-12`.
