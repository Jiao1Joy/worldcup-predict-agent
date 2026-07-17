# Prediction Product UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the user-facing World Cup forecast product—champion overview, team probabilities, tournament bracket, match score details, 2022 backtest—and connect every result to the Agent Workbench.

**Architecture:** A typed forecast client loads immutable read models from the backend. Route-level pages compose accessible ECharts visualizations and a CSS bracket; the existing Agent Workbench remains a separate deep-dive route reached from published forecast evidence.

**Tech Stack:** React 18, TypeScript 5, Vite, React Router, ECharts, `echarts-for-react`, `@xyflow/react`, Vitest, Testing Library, Playwright

---

## Dependencies

Complete:

- `docs/superpowers/plans/2026-07-15-agent-workbench-ui.md`;
- `docs/superpowers/plans/2026-07-16-tournament-simulator.md`;
- Forecast read endpoints from `docs/superpowers/specs/2026-07-16-complete-product-handoff-design.md`.

## File Structure

```text
frontend/src/
├── api/
│   ├── forecast-client.ts
│   └── forecast-schemas.ts
├── domain/
│   └── forecast.ts
├── app/
│   └── router.tsx
├── pages/
│   ├── ForecastOverviewPage.tsx
│   ├── TournamentPage.tsx
│   ├── MatchDetailPage.tsx
│   ├── TeamDetailPage.tsx
│   ├── BacktestPage.tsx
│   └── AgentWorkbenchPage.tsx
├── features/
│   ├── forecast/
│   │   ├── ChampionHero.tsx
│   │   ├── ChampionProbabilityChart.tsx
│   │   └── TeamProbabilityTable.tsx
│   ├── bracket/
│   │   ├── TournamentBracket.tsx
│   │   └── MatchCard.tsx
│   ├── match/
│   │   └── ScoreMatrixChart.tsx
│   └── backtest/
│       ├── MetricsStrip.tsx
│       └── CalibrationChart.tsx
├── styles/
│   ├── tokens.css
│   └── product.css
└── test/
    └── forecast-fixture.ts
frontend/tests/
frontend/e2e/forecast-product.spec.ts
```

## Task 1: Add Product Dependencies and Typed Forecast Models

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/src/domain/forecast.ts`
- Create: `frontend/src/api/forecast-client.ts`
- Create: `frontend/src/test/forecast-fixture.ts`
- Test: `frontend/tests/forecast-client.test.ts`

- [ ] **Step 1: Add runtime dependencies without removing Workbench packages**

```json
"dependencies": {
  "@xyflow/react": "^12.4.4",
  "echarts": "^5.6.0",
  "echarts-for-react": "^3.0.2",
  "react": "^18.3.1",
  "react-dom": "^18.3.1",
  "react-router-dom": "^7.1.1"
}
```

- [ ] **Step 2: Write a failing read-model parsing test**

```ts
// frontend/tests/forecast-client.test.ts
import { assertTournamentForecast } from '../src/domain/forecast';
import { forecastFixture } from '../src/test/forecast-fixture';

test('accepts a complete 104-match forecast fixture', () => {
  expect(() => assertTournamentForecast(forecastFixture)).not.toThrow();
  expect(forecastFixture.matches).toHaveLength(104);
  expect(Object.values(forecastFixture.team_probabilities)).toHaveLength(48);
});

test('rejects an incomplete bracket', () => {
  expect(() => assertTournamentForecast({ ...forecastFixture, matches: [] })).toThrow(/104/);
});
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `cd frontend && npm test -- tests/forecast-client.test.ts`

Expected: FAIL because forecast domain types do not exist.

- [ ] **Step 4: Define the frontend domain**

```ts
// frontend/src/domain/forecast.ts
export interface StageProbabilities {
  r32: number;
  r16: number;
  qf: number;
  sf: number;
  final: number;
  champion: number;
}

export interface MatchPrediction {
  match_id: string;
  home_team: string;
  away_team: string;
  expected_home_goals: number;
  expected_away_goals: number;
  outcomes: { home: number; draw: number; away: number };
  score_matrix: number[][];
  evidence_ids: string[];
}

export interface ForecastMatch {
  match_id: string;
  stage: string;
  home_source: string;
  away_source: string;
  home_team: string | null;
  away_team: string | null;
  prediction: MatchPrediction | null;
  winner: string | null;
}

export interface TournamentForecast {
  forecast_id: string;
  run_id: string;
  champion: { team: string; probability: number };
  matches: ForecastMatch[];
  team_probabilities: Record<string, StageProbabilities>;
  simulation_runs: number;
  seed: number;
  versions: Record<string, string>;
  evidence_ids: string[];
  explanation: { summary: string; uncertainty: string };
}

export function assertTournamentForecast(value: unknown): asserts value is TournamentForecast {
  if (!value || typeof value !== 'object') throw new Error('forecast must be an object');
  const forecast = value as Partial<TournamentForecast>;
  if (typeof forecast.forecast_id !== 'string') throw new Error('forecast_id is required');
  if (!Array.isArray(forecast.matches) || forecast.matches.length !== 104) throw new Error('forecast requires 104 matches');
  if (!forecast.team_probabilities || Object.keys(forecast.team_probabilities).length !== 48) throw new Error('forecast requires 48 teams');
  if (!forecast.champion || typeof forecast.champion.probability !== 'number') throw new Error('champion is required');
}
```

- [ ] **Step 5: Implement typed client operations**

```ts
// frontend/src/api/forecast-client.ts
import { assertTournamentForecast, type TournamentForecast } from '../domain/forecast';

async function parseForecast(response: Response): Promise<TournamentForecast> {
  if (!response.ok) throw new Error(`forecast request failed: ${response.status}`);
  const value: unknown = await response.json();
  assertTournamentForecast(value);
  return value;
}

export const forecastApi = {
  current: () => fetch('/api/forecasts/current').then(parseForecast),
  get: (forecastId: string) => fetch(`/api/forecasts/${forecastId}`).then(parseForecast),
  backtest2022: async () => {
    const response = await fetch('/api/backtests/2022');
    if (!response.ok) throw new Error(`backtest request failed: ${response.status}`);
    return response.json() as Promise<BacktestReport>;
  },
};

export interface BacktestReport {
  rps: number;
  log_loss: number;
  brier: number;
  accuracy: number;
  calibration_bins: Array<{ predicted: number; observed: number; count: number }>;
}
```

- [ ] **Step 6: Run tests and build**

Run: `cd frontend && npm test -- tests/forecast-client.test.ts && npm run build`

Expected: tests PASS and build exits 0.

- [ ] **Step 7: Commit typed forecast models**

```bash
git add frontend/package.json frontend/src/domain frontend/src/api/forecast-client.ts frontend/src/test frontend/tests/forecast-client.test.ts
git commit -m "feat: add typed tournament forecast client"
```

## Task 2: Add Routing and the Forecast Overview Shell

**Files:**
- Create: `frontend/src/app/router.tsx`
- Create: `frontend/src/pages/ForecastOverviewPage.tsx`
- Create: `frontend/src/pages/TournamentPage.tsx`
- Create: `frontend/src/pages/MatchDetailPage.tsx`
- Create: `frontend/src/pages/TeamDetailPage.tsx`
- Create: `frontend/src/pages/BacktestPage.tsx`
- Create: `frontend/src/pages/AgentWorkbenchPage.tsx`
- Modify: `frontend/src/App.tsx`
- Test: `frontend/tests/router.test.tsx`

- [ ] **Step 1: Write failing route tests**

```tsx
// frontend/tests/router.test.tsx
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AppRoutes } from '../src/app/router';
import { forecastFixture } from '../src/test/forecast-fixture';

test.each([
  ['/', /world cup prediction agent/i],
  ['/tournament', /tournament bracket/i],
  ['/backtest', /2022 backtest/i],
  [`/agent/${forecastFixture.run_id}`, /agent workbench/i],
])('route %s renders its page', async (path, heading) => {
  render(<MemoryRouter initialEntries={[path]}><AppRoutes forecast={forecastFixture} /></MemoryRouter>);
  expect(await screen.findByRole('heading', { name: heading })).toBeInTheDocument();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- tests/router.test.tsx`

Expected: FAIL because route components do not exist.

- [ ] **Step 3: Implement explicit routes**

```tsx
// frontend/src/app/router.tsx
import { Route, Routes } from 'react-router-dom';
import type { TournamentForecast } from '../domain/forecast';
import { AgentWorkbenchPage } from '../pages/AgentWorkbenchPage';
import { BacktestPage } from '../pages/BacktestPage';
import { ForecastOverviewPage } from '../pages/ForecastOverviewPage';
import { MatchDetailPage } from '../pages/MatchDetailPage';
import { TeamDetailPage } from '../pages/TeamDetailPage';
import { TournamentPage } from '../pages/TournamentPage';

export function AppRoutes({ forecast }: { forecast: TournamentForecast }) {
  return (
    <Routes>
      <Route path="/" element={<ForecastOverviewPage forecast={forecast} />} />
      <Route path="/tournament" element={<TournamentPage forecast={forecast} />} />
      <Route path="/matches/:matchId" element={<MatchDetailPage forecast={forecast} />} />
      <Route path="/teams/:teamId" element={<TeamDetailPage forecast={forecast} />} />
      <Route path="/backtest" element={<BacktestPage />} />
      <Route path="/agent/:runId" element={<AgentWorkbenchPage />} />
    </Routes>
  );
}
```

- [ ] **Step 4: Implement loading and error boundaries in App**

`App` loads `forecastApi.current()` once, renders an accessible loading status, renders a retry button on failure, and wraps `AppRoutes` in `BrowserRouter`. Portfolio mode imports the committed fixture only when `VITE_PORTFOLIO_OFFLINE=true`; production mode never silently falls back to a fixture after an API integrity error.

- [ ] **Step 5: Run route tests**

Run: `cd frontend && npm test -- tests/router.test.tsx`

Expected: PASS.

- [ ] **Step 6: Commit routing**

```bash
git add frontend/src/app frontend/src/pages frontend/src/App.tsx frontend/tests/router.test.tsx
git commit -m "feat: route world cup forecast product pages"
```

## Task 3: Build the Champion Overview and Probability Table

**Files:**
- Create: `frontend/src/features/forecast/ChampionHero.tsx`
- Create: `frontend/src/features/forecast/ChampionProbabilityChart.tsx`
- Create: `frontend/src/features/forecast/TeamProbabilityTable.tsx`
- Modify: `frontend/src/pages/ForecastOverviewPage.tsx`
- Test: `frontend/tests/overview.test.tsx`

- [ ] **Step 1: Write failing champion and version tests**

```tsx
// frontend/tests/overview.test.tsx
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ForecastOverviewPage } from '../src/pages/ForecastOverviewPage';
import { forecastFixture } from '../src/test/forecast-fixture';

test('shows champion probability, uncertainty, and version provenance', () => {
  render(<MemoryRouter><ForecastOverviewPage forecast={forecastFixture} /></MemoryRouter>);
  expect(screen.getByRole('heading', { name: forecastFixture.champion.team })).toBeInTheDocument();
  expect(screen.getByText(`${(forecastFixture.champion.probability * 100).toFixed(1)}%`)).toBeInTheDocument();
  expect(screen.getByText(forecastFixture.versions.data_version)).toBeInTheDocument();
  expect(screen.getByText(forecastFixture.explanation.uncertainty)).toBeInTheDocument();
  expect(screen.getByRole('link', { name: /view agent run/i })).toHaveAttribute('href', `/agent/${forecastFixture.run_id}`);
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npm test -- tests/overview.test.tsx`

Expected: FAIL because overview components do not exist.

- [ ] **Step 3: Implement a result-first hero**

`ChampionHero` renders the champion name, percentage, simulation count, most likely final, structured explanation summary, uncertainty, forecast cutoff, and a primary “View Agent Run” link. Do not use trophy gradients, fake live badges, or deterministic language such as “will win”.

- [ ] **Step 4: Implement chart and accessible table from the same sorted data**

`ChampionProbabilityChart` uses a horizontal ECharts bar chart for the top ten. `TeamProbabilityTable` contains all 48 teams with columns R32, R16, QF, SF, Final, Champion. Both call one `sortedTeamProbabilities(forecast)` helper; values are formatted to one decimal percentage point. The chart container has an aria description and the table remains available to screen readers.

- [ ] **Step 5: Run overview tests and build**

Run: `cd frontend && npm test -- tests/overview.test.tsx && npm run build`

Expected: PASS and build exits 0.

- [ ] **Step 6: Commit overview**

```bash
git add frontend/src/features/forecast frontend/src/pages/ForecastOverviewPage.tsx frontend/tests/overview.test.tsx
git commit -m "feat: present champion forecast overview"
```

## Task 4: Build the Complete Tournament Bracket

**Files:**
- Create: `frontend/src/features/bracket/TournamentBracket.tsx`
- Create: `frontend/src/features/bracket/MatchCard.tsx`
- Modify: `frontend/src/pages/TournamentPage.tsx`
- Test: `frontend/tests/bracket.test.tsx`

- [ ] **Step 1: Write failing slot and navigation tests**

```tsx
// frontend/tests/bracket.test.tsx
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { TournamentBracket } from '../src/features/bracket/TournamentBracket';
import { forecastFixture } from '../src/test/forecast-fixture';

test('renders every knockout match in official stage columns', () => {
  render(<MemoryRouter><TournamentBracket matches={forecastFixture.matches} /></MemoryRouter>);
  expect(screen.getAllByTestId('knockout-match')).toHaveLength(32);
  expect(screen.getByRole('heading', { name: /round of 32/i })).toBeInTheDocument();
  expect(screen.getByRole('heading', { name: /final/i })).toBeInTheDocument();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- tests/bracket.test.tsx`

Expected: FAIL because bracket components do not exist.

- [ ] **Step 3: Implement semantic stage columns**

Group matches are available through a group selector above the bracket. Knockout matches M073-M104 are grouped by stage in official order. Each `MatchCard` shows teams or unresolved source labels, top predicted score, win/advance probability, Evidence indicator, and a link to `/matches/{match_id}`. The bronze match is labeled separately and must not appear as a championship branch.

- [ ] **Step 4: Implement responsive interaction**

Desktop uses horizontally scrollable stage columns with a sticky stage header; mobile uses a stage select and one vertical list. Keyboard users can tab through match cards in match-ID order. No SVG connector is required for acceptance; when connectors are added, they must be decorative and hidden from accessibility APIs.

- [ ] **Step 5: Run bracket tests**

Run: `cd frontend && npm test -- tests/bracket.test.tsx`

Expected: PASS.

- [ ] **Step 6: Commit bracket**

```bash
git add frontend/src/features/bracket frontend/src/pages/TournamentPage.tsx frontend/tests/bracket.test.tsx
git commit -m "feat: visualize the complete tournament bracket"
```

## Task 5: Build Match and Team Detail Pages

**Files:**
- Create: `frontend/src/features/match/ScoreMatrixChart.tsx`
- Modify: `frontend/src/pages/MatchDetailPage.tsx`
- Modify: `frontend/src/pages/TeamDetailPage.tsx`
- Test: `frontend/tests/details.test.tsx`

- [ ] **Step 1: Write failing probability-consistency UI tests**

```tsx
// frontend/tests/details.test.tsx
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { MatchDetailPage } from '../src/pages/MatchDetailPage';
import { forecastFixture } from '../src/test/forecast-fixture';

test('match detail renders outcomes, xg, scores, and evidence', () => {
  const match = forecastFixture.matches.find((item) => item.prediction)!;
  render(
    <MemoryRouter initialEntries={[`/matches/${match.match_id}`]}>
      <Routes><Route path="/matches/:matchId" element={<MatchDetailPage forecast={forecastFixture} />} /></Routes>
    </MemoryRouter>,
  );
  expect(screen.getByText(/expected goals/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/score probability matrix/i)).toBeInTheDocument();
  expect(screen.getByText(match.prediction!.evidence_ids[0])).toBeInTheDocument();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- tests/details.test.tsx`

Expected: FAIL because detail components do not exist.

- [ ] **Step 3: Implement the score heatmap**

Use ECharts heatmap data `[awayGoals, homeGoals, probability]`. Axes are labeled by team name, cells format percentages, and the top three score cells have visible labels. Add an off-screen table listing the same cells and `aria-label="Score probability matrix"` on the chart region.

- [ ] **Step 4: Implement detail read models**

Match Detail shows outcome probabilities, expected goals, top scores, advancement probability when applicable, data/model versions, and Evidence IDs. Team Detail shows the six stage probabilities, matches on the most likely path, and no unsupported “squad strength” score. Unknown IDs render a route-level Not Found message instead of throwing.

- [ ] **Step 5: Run detail tests**

Run: `cd frontend && npm test -- tests/details.test.tsx`

Expected: PASS.

- [ ] **Step 6: Commit details**

```bash
git add frontend/src/features/match frontend/src/pages/MatchDetailPage.tsx frontend/src/pages/TeamDetailPage.tsx frontend/tests/details.test.tsx
git commit -m "feat: inspect match and team forecasts"
```

## Task 6: Build the 2022 Backtest Evidence Page

**Files:**
- Create: `frontend/src/features/backtest/MetricsStrip.tsx`
- Create: `frontend/src/features/backtest/CalibrationChart.tsx`
- Modify: `frontend/src/pages/BacktestPage.tsx`
- Test: `frontend/tests/backtest.test.tsx`

- [ ] **Step 1: Write a failing non-hardcoded metrics test**

Mock `forecastApi.backtest2022()` with known values and render `BacktestPage`. Assert RPS, Log Loss, Brier, accuracy, evaluation match count, model version, data version, and at least one calibration bin. Change the mocked RPS and assert the page changes, proving the metric is not embedded in the component.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- tests/backtest.test.tsx`

Expected: FAIL because backtest components do not exist.

- [ ] **Step 3: Implement metrics and calibration chart**

`MetricsStrip` explains that RPS is primary and accuracy is secondary. `CalibrationChart` plots predicted vs observed with a dashed perfect-calibration diagonal and exposes the bins in a table. The page states training cutoff 2022-11-19 and evaluation window 2022-11-20 through 2022-12-18.

- [ ] **Step 4: Add per-match disclosure**

Render a sortable table containing teams, actual outcome, predicted home/draw/away probabilities, selected top outcome, and per-match RPS. The aggregate displayed RPS must equal the mean of the received per-match values within `1e-12` or the page shows an integrity error.

- [ ] **Step 5: Run backtest tests**

Run: `cd frontend && npm test -- tests/backtest.test.tsx`

Expected: PASS.

- [ ] **Step 6: Commit backtest UI**

```bash
git add frontend/src/features/backtest frontend/src/pages/BacktestPage.tsx frontend/tests/backtest.test.tsx
git commit -m "feat: show reproducible 2022 backtest"
```

## Task 7: Connect Published Forecasts to the Agent Workbench

**Files:**
- Modify: `frontend/src/pages/AgentWorkbenchPage.tsx`
- Modify: `frontend/src/components/Workbench.tsx`
- Test: `frontend/tests/agent-forecast-link.test.tsx`

- [ ] **Step 1: Write a failing run-link test**

Navigate from Overview to `/agent/{run_id}`, mock the Run snapshot, initial state, and SSE events, then assert the Workbench selected `simulate_tournament` node shows the same `forecast_id`, model version, and forecast Evidence ID as the Overview fixture.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- tests/agent-forecast-link.test.tsx`

Expected: FAIL because the Workbench does not display forecast provenance.

- [ ] **Step 3: Load the run route parameter**

`AgentWorkbenchPage` reads `runId`, uses `useRunController`, and renders loading/error/Workbench states. It never reads `VITE_DEMO_RUN_ID` for routed runs. Offline portfolio routing maps the committed forecast fixture to its committed completed-run fixture.

- [ ] **Step 4: Add forecast provenance to Step Inspector**

For Tool and Evidence events, display forecast ID, match count, simulation runs, data/model/rules versions, convergence delta, and clickable Evidence IDs. Do not render raw prompt text or chain-of-thought fields even if a provider payload contains them.

- [ ] **Step 5: Run linking tests**

Run: `cd frontend && npm test -- tests/agent-forecast-link.test.tsx`

Expected: PASS.

- [ ] **Step 6: Commit Workbench integration**

```bash
git add frontend/src/pages/AgentWorkbenchPage.tsx frontend/src/components/Workbench.tsx frontend/tests/agent-forecast-link.test.tsx
git commit -m "feat: trace published forecasts in agent workbench"
```

## Task 8: Apply Product Visual System, Accessibility, and E2E Coverage

**Files:**
- Create: `frontend/src/styles/tokens.css`
- Create: `frontend/src/styles/product.css`
- Modify: `frontend/src/styles.css`
- Create: `frontend/e2e/forecast-product.spec.ts`
- Modify: `frontend/playwright.config.ts`
- Create: `frontend/README.md`

- [ ] **Step 1: Establish shared visual tokens**

Use one dark editorial system shared by prediction pages and Workbench: near-black background, navy surfaces, one teal evidence accent, amber warning, tabular numerals, 12/16/24/36px spacing scale, maximum content width 1480px. Champion probability is visually dominant; Agent controls remain secondary until the user enters Workbench.

- [ ] **Step 2: Add accessibility checks**

All charts have an accessible text/table equivalent; focus is visible; route changes move focus to the page heading; percentages include text; status never relies on color alone; controls have 44px minimum touch target; reduced-motion disables animated chart transitions and graph edges.

- [ ] **Step 3: Write the portfolio E2E journey**

```ts
// frontend/e2e/forecast-product.spec.ts
import { expect, test } from '@playwright/test';

test('visitor moves from champion result to bracket, match, and agent evidence', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await page.getByRole('link', { name: /tournament/i }).click();
  await expect(page.getByRole('heading', { name: /tournament bracket/i })).toBeVisible();
  await page.getByTestId('knockout-match').first().click();
  await expect(page.getByLabel(/score probability matrix/i)).toBeVisible();
  await page.getByRole('link', { name: /view agent run/i }).click();
  await expect(page.getByLabel('Agent run graph')).toBeVisible();
});

test('mobile product has no page-level horizontal overflow', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.goto('/tournament');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
```

- [ ] **Step 4: Run the full frontend completion gate**

Run: `cd frontend && npm test`

Expected: all Vitest tests PASS.

Run: `cd frontend && npm run build`

Expected: production build exits 0.

Run: `cd frontend && npm run e2e`

Expected: all Workbench and forecast-product Playwright tests PASS.

- [ ] **Step 5: Document offline and live modes**

`frontend/README.md` documents routes, required API shapes, `VITE_PORTFOLIO_OFFLINE`, chart accessibility, desktop/mobile behavior, the result-to-Workbench journey, and commands for tests/build/E2E.

- [ ] **Step 6: Commit the finished product UI**

```bash
git add frontend/src/styles frontend/src/styles.css frontend/e2e frontend/playwright.config.ts frontend/README.md
git commit -m "feat: finish world cup forecast product ui"
```

## Product UI Completion Gate

- Overview displays champion, probability, simulation count, versions, explanation, and uncertainty;
- all 48 teams and six advancement stages are available in an accessible table;
- bracket contains 32 knockout matches plus access to 72 group matches;
- match detail renders outcomes, expected goals, score matrix, and Evidence;
- Backtest metrics come from API per-match rows and pass the integrity check;
- Forecast and Agent Workbench display the same forecast ID and versions;
- desktop and 390px viewport E2E tests pass;
- offline portfolio mode requires no backend or network;
- production API integrity errors never silently display fixture data.
