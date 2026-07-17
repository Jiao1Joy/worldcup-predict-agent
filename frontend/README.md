# World Cup Prediction Agent — Frontend

Combines the user-facing forecast product (champion overview, tournament bracket, match/team details, 2022 backtest) with the Agent Workbench (run graph, step inspector, replay, failure recovery, human approval).

## Routes

- `/explore` — Runtime-derived visual explorer for probabilities, groups, Annex C, and the knockout bracket

- `/` — Forecast overview: champion, top-10 probabilities, all 48 teams, evidence link
- `/tournament` — Full bracket (knockout columns + group selector)
- `/matches/:matchId` — Outcome probabilities, expected goals, score matrix, evidence
- `/teams/:teamId` — Stage probabilities and likely path
- `/backtest` — 2022 metrics and calibration
- `/agent/:runId` — Agent Workbench

## Offline portfolio mode

Uses committed fixtures (no backend or network required):

```powershell
npm install
npm run dev
```

The offline mode is the default for local portfolio and E2E use. Live mode
loads `/api/forecasts/current` and never silently falls back after an integrity
or network error:

```powershell
$env:VITE_PORTFOLIO_OFFLINE="false"
npm run dev
```

The interview path is: champion result → Run Graph → Step Inspector → dynamic branch → failure recovery → Evidence → Replay.

## Verification

```powershell
npm test        # Vitest unit/component tests
npm run build   # TypeScript + Vite production build
npm run e2e     # Playwright portfolio + product journeys
```

All charts expose an aria-label and/or a screen-reader table; the layout stays within the viewport at 390px.
