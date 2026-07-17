import type { TournamentForecast } from '../../domain/forecast';
import { sortedTeamProbabilities } from '../../domain/forecast';

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

export function TeamProbabilityTable({ forecast }: { forecast: TournamentForecast }) {
  const rows = sortedTeamProbabilities(forecast);
  return (
    <section className="team-table" aria-label="Team advancement probabilities">
      <h2>All 48 teams</h2>
      <table>
        <thead>
          <tr>
            <th>Team</th>
            <th>R32</th>
            <th>R16</th>
            <th>QF</th>
            <th>SF</th>
            <th>Final</th>
            <th>Champion</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.team}>
              <td>{r.team}</td>
              <td>{pct(r.r32)}</td>
              <td>{pct(r.r16)}</td>
              <td>{pct(r.qf)}</td>
              <td>{pct(r.sf)}</td>
              <td>{pct(r.final)}</td>
              <td>{pct(r.champion)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
