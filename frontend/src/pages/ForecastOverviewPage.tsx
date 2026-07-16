import { Link } from 'react-router-dom';
import type { TournamentForecast } from '../domain/forecast';
import { ChampionHero } from '../features/forecast/ChampionHero';
import { ChampionProbabilityChart } from '../features/forecast/ChampionProbabilityChart';
import { TeamProbabilityTable } from '../features/forecast/TeamProbabilityTable';

export function ForecastOverviewPage({ forecast }: { forecast: TournamentForecast }) {
  return (
    <main className="page overview-page">
      <nav className="top-nav">
        <Link to="/tournament">Tournament</Link>
        <Link to="/backtest">2022 Backtest</Link>
      </nav>
      <ChampionHero forecast={forecast} />
      <ChampionProbabilityChart forecast={forecast} />
      <TeamProbabilityTable forecast={forecast} />
    </main>
  );
}
