import { Link } from 'react-router-dom';
import type { TournamentForecast } from '../../domain/forecast';
import { sortedTeamProbabilities } from '../../domain/forecast';

export function ChampionHero({ forecast }: { forecast: TournamentForecast }) {
  const sorted = sortedTeamProbabilities(forecast);
  const champion = forecast.champion;
  const runnerUp = sorted[1];
  return (
    <section className="champion-hero">
      <p className="eyebrow">2026 TOURNAMENT FORECAST</p>
      <h1>{champion.team}</h1>
      <p className="champion-probability">{(champion.probability * 100).toFixed(1)}% modeled champion probability</p>
      <p className="most-likely-final">
        Most likely final: {champion.team} vs {runnerUp?.team ?? '—'}
      </p>
      <p className="simulation-meta">{forecast.simulation_runs} simulations · seed {forecast.seed}</p>
      <p className="explanation">{forecast.explanation.summary}</p>
      <p className="uncertainty">{forecast.explanation.uncertainty}</p>
      <p className="versions">
        data {forecast.versions.data_version} · model {forecast.versions.model_version} · rules {forecast.versions.rules_version}
      </p>
      <Link className="primary" to={`/agent/${forecast.run_id}`}>View Agent Run</Link>
    </section>
  );
}
