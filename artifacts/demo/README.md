# Offline Portfolio Bundle

This bundle powers the offline Portfolio Frozen demo. It is generated
deterministically from the committed miniature snapshot, versioned FIFA 2026
rules, and the baseline prediction model — no network, LLM key, or live data is
required to browse every page.

## Contents

- `forecast.json` — published 104-match tournament forecast read model
- `completed-run.json` — materialized Agent run (initial state, final state, ordered events)
- `evidence.json` — evidence bundle backing every published numeric claim
- `backtest-2022.json` / `backtest-2022-predictions.csv` — 2022 backtest metrics and per-match rows
- `artifact-manifest.json` — SHA-256 of each artifact file
- `portfolio.sqlite3` — SQLite run/event store backing the Agent run

## Provenance

- Source snapshot: `international_results-master/results.csv` (CC0 1.0)
- Forecast cutoff: `2026-06-10T23:59:59Z`
- Rules: `backend/rules/fifa_2026` (FIFA 2026 regulations)
- Simulation: 300 Monte Carlo runs (reduced from the 30,000-run rebuild profile for CI speed)
- Random seed: `20260611`

The reduced simulation count means champion probabilities are noisier than the
full rebuild; the generation path and invariants (104 matches, 495 Annexe C
combinations, probability sums) remain identical.

## Regeneration

```powershell
worldcup-generate-portfolio --output ../artifacts/demo --runs 300 --seed 20260611
```

Two consecutive runs with the same seed produce byte-identical canonical JSON
hashes (ignoring filesystem mtimes).
