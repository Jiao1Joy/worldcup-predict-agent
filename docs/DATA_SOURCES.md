# Data Sources

## Historical international results

- **Source:** martj42 international football results (`results.csv`)
- **URL:** https://github.com/martj42/football_results
- **License:** CC0 1.0 (public domain). Redistributable; included in this repository under `international_results-master/`.
- **Schema:** `date,home_team,away_team,home_score,away_score,tournament,city,country,neutral`
- **Rows:** 49,459 internationals from 1872 to 2024+.
- **Attribution:** Aggregated from Wikipedia, rsssf.com, and football association websites by the dataset maintainer.

## FIFA World Cup 2026 regulations

- **Annexe C:** `backend/rules/fifa_2026/annex_c.csv` (495 best-third combinations), extracted from the official FIFA World Cup 26 Regulations PDF.
- **Source PDF SHA-256:** `bad4ea83cf1f51055598b0c12c3dab280a78777e08a623b9e9098508b4ecc8d9`
- **Retrieved:** 2026-07-16
- **Extraction script:** `scripts/extract_fifa_annex_c.py` (validated: all 495 combinations, eight unique groups per row, slot mappings consistent).
- **Official fixtures:** `backend/rules/fifa_2026/fixtures.json`, including the FIFA M073-M104 knockout source graph.
- **FIFA ranking snapshot:** `backend/rules/fifa_2026/fifa_rankings.json`, official men's ranking dated 2026-06-11.
- **Ranking source:** https://inside.fifa.com/fifa-world-ranking/men
- **Ranking JSON SHA-256:** `b55a6afcd78fdf81c461319da3e406eb2a6f402b0abb7883ccbb22c40e338446`

## Rebuild

```powershell
worldcup-rebuild --source ../international_results-master/results.csv `
  --output ../artifacts/generated `
  --forecast-cutoff 2026-06-10T23:59:59Z `
  --train-end 2022-11-19 --backtest-end 2022-12-18 `
  --seed 20260611 --profile baseline
```

## Redistribution status

- martj42 results (CC0): redistributed in-repo.
- FIFA regulations: only the extracted Annexe C table and schedule structure are committed; the source PDF is not redistributed.
- Model artifacts: baseline Logistic weights are small and regenerable; large GBDT binaries are gitignored.
