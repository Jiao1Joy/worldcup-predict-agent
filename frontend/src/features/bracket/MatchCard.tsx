import { Link } from 'react-router-dom';
import type { ForecastMatch } from '../../domain/forecast';

export function MatchCard({ match }: { match: ForecastMatch }) {
  const home = match.home_team ?? match.home_source;
  const away = match.away_team ?? match.away_source;
  return (
    <Link to={`/matches/${match.match_id}`} className="match-card" data-testid="knockout-match">
      <span className="match-id">{match.match_id}</span>
      <span className={`team ${match.winner === home ? 'winner' : ''}`}>{home}</span>
      <span className="vs">vs</span>
      <span className={`team ${match.winner === away ? 'winner' : ''}`}>{away}</span>
      {match.winner && <span className="badge">Evidence</span>}
    </Link>
  );
}
