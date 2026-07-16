import { Link, useParams } from 'react-router-dom';
import type { TournamentForecast } from '../domain/forecast';
import { ScoreMatrixChart } from '../features/match/ScoreMatrixChart';

export function MatchDetailPage({ forecast }: { forecast: TournamentForecast }) {
  const { matchId } = useParams();
  const match = forecast.matches.find((m) => m.match_id === matchId);
  if (!match) {
    return (
      <main className="page">
        <h1>Match not found</h1>
        <Link to="/tournament">Back to bracket</Link>
      </main>
    );
  }
  const prediction = match.prediction;
  return (
    <main className="page match-detail">
      <nav className="top-nav"><Link to="/tournament">Tournament</Link></nav>
      <h1>{match.home_team ?? match.home_source} vs {match.away_team ?? match.away_source}</h1>
      <p className="match-stage">{match.stage} · {match.match_id}</p>
      {prediction ? (
        <>
          <h2>Expected goals</h2>
          <p>{prediction.expected_home_goals.toFixed(2)} — {prediction.expected_away_goals.toFixed(2)}</p>
          <h2>Outcome probabilities</h2>
          <ul>
            <li>Home {(prediction.outcomes.home * 100).toFixed(1)}%</li>
            <li>Draw {(prediction.outcomes.draw * 100).toFixed(1)}%</li>
            <li>Away {(prediction.outcomes.away * 100).toFixed(1)}%</li>
          </ul>
          <h2>Score probability matrix</h2>
          <ScoreMatrixChart matrix={prediction.score_matrix} homeTeam={match.home_team ?? 'Home'} awayTeam={match.away_team ?? 'Away'} />
          <h2>Evidence</h2>
          <ul>{prediction.evidence_ids.map((id) => <li key={id}>{id}</li>)}</ul>
          <p className="versions">data {forecast.versions.data_version} · model {forecast.versions.model_version}</p>
        </>
      ) : (
        <p>No prediction available for this match slot.</p>
      )}
    </main>
  );
}
