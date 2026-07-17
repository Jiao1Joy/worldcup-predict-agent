import { Link } from 'react-router-dom';
import type { TournamentForecast } from '../domain/forecast';
import { TournamentBracket } from '../features/bracket/TournamentBracket';

export function TournamentPage({ forecast }: { forecast: TournamentForecast }) {
  return (
    <main className="page tournament-page">
      <nav className="top-nav">
        <Link to="/">Overview</Link>
        <Link to="/explore">Visual Explorer</Link>
        <Link to="/backtest">2022 Backtest</Link>
      </nav>
      <h1>Tournament Bracket</h1>
      <TournamentBracket matches={forecast.matches} />
    </main>
  );
}
