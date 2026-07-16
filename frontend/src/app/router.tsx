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
