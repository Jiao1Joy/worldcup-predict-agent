import { Link, useParams } from 'react-router-dom';
import type { TournamentForecast } from '../domain/forecast';

export function TeamDetailPage({ forecast }: { forecast: TournamentForecast }) {
  const { teamId } = useParams();
  const probs = forecast.team_probabilities[teamId ?? ''];
  if (!probs) {
    return (
      <main className="page">
        <h1>Team not found</h1>
        <Link to="/">Back to overview</Link>
      </main>
    );
  }
  const pathMatches = forecast.matches
    .filter((m) => m.home_team === teamId || m.away_team === teamId)
    .slice(0, 6);
  return (
    <main className="page team-detail">
      <nav className="top-nav"><Link to="/">Overview</Link></nav>
      <h1>{teamId}</h1>
      <h2>Stage probabilities</h2>
      <ul>
        <li>R32 {(probs.r32 * 100).toFixed(1)}%</li>
        <li>R16 {(probs.r16 * 100).toFixed(1)}%</li>
        <li>QF {(probs.qf * 100).toFixed(1)}%</li>
        <li>SF {(probs.sf * 100).toFixed(1)}%</li>
        <li>Final {(probs.final * 100).toFixed(1)}%</li>
        <li>Champion {(probs.champion * 100).toFixed(1)}%</li>
      </ul>
      <h2>Matches on likely path</h2>
      <ul>
        {pathMatches.map((m) => (
          <li key={m.match_id}><Link to={`/matches/${m.match_id}`}>{m.match_id}: {m.home_team} vs {m.away_team}</Link></li>
        ))}
      </ul>
    </main>
  );
}
