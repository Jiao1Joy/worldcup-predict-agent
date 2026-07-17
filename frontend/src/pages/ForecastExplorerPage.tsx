import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import type { ForecastMatch, TournamentForecast } from '../domain/forecast';
import { sortedTeamProbabilities } from '../domain/forecast';

type ExplorerView = 'probability' | 'groups' | 'annex' | 'knockout';

const stageLabels: Record<string, string> = {
  round_of_32: 'Round of 32',
  round_of_16: 'Round of 16',
  quarter_final: 'Quarter-finals',
  semi_final: 'Semi-finals',
  third_place: 'Third place',
  final: 'Final',
};

const stageOrder = Object.keys(stageLabels);

export function deriveGroups(matches: ForecastMatch[]) {
  const positions: Record<string, Record<number, string>> = {};
  for (const match of matches.filter((item) => item.stage === 'group')) {
    for (const [source, team] of [
      [match.home_source, match.home_team],
      [match.away_source, match.away_team],
    ] as const) {
      const parsed = /^G([A-L])(\d)$/.exec(source);
      if (!parsed || !team) continue;
      const [, group, position] = parsed;
      positions[group] ??= {};
      positions[group][Number(position)] = team;
    }
  }
  return Object.fromEntries(
    Object.entries(positions)
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([group, teams]) => [
        group,
        Object.entries(teams)
          .sort(([left], [right]) => Number(left) - Number(right))
          .map(([, team]) => team),
      ]),
  );
}

export function deriveAnnexMappings(
  matches: ForecastMatch[],
  groups: Record<string, string[]>,
) {
  const teamGroups = Object.fromEntries(
    Object.entries(groups).flatMap(([group, teams]) => teams.map((team) => [team, group])),
  );
  return matches
    .filter((match) => match.stage === 'round_of_32')
    .flatMap((match) => {
      if (match.home_source === '3' && match.home_team) {
        return [{ slot: match.away_source, group: teamGroups[match.home_team], team: match.home_team }];
      }
      if (match.away_source === '3' && match.away_team) {
        return [{ slot: match.home_source, group: teamGroups[match.away_team], team: match.away_team }];
      }
      return [];
    })
    .sort((left, right) => left.slot.localeCompare(right.slot));
}

export function ForecastExplorerPage({ forecast }: { forecast: TournamentForecast }) {
  const [view, setView] = useState<ExplorerView>('probability');
  const [selectedGroup, setSelectedGroup] = useState('A');
  const [selectedStage, setSelectedStage] = useState('round_of_32');
  const groups = useMemo(() => deriveGroups(forecast.matches), [forecast.matches]);
  const annexMappings = useMemo(
    () => deriveAnnexMappings(forecast.matches, groups),
    [forecast.matches, groups],
  );
  const topTeams = useMemo(
    () => sortedTeamProbabilities(forecast).slice(0, 16),
    [forecast],
  );
  const stageMatches = forecast.matches.filter((match) => match.stage === selectedStage);
  const [selectedMatchId, setSelectedMatchId] = useState('M073');
  const selectedMatch = stageMatches.find((match) => match.match_id === selectedMatchId)
    ?? stageMatches[0];
  const maxChampion = Math.max(...topTeams.map((team) => team.champion), 0.001);

  function changeStage(stage: string) {
    setSelectedStage(stage);
    const firstMatch = forecast.matches.find((match) => match.stage === stage);
    if (firstMatch) setSelectedMatchId(firstMatch.match_id);
  }

  return (
    <main className="page explorer-page">
      <nav className="top-nav">
        <Link to="/">Overview</Link>
        <Link to="/tournament">Tournament</Link>
        <Link to="/backtest">2022 Backtest</Link>
      </nav>
      <header className="explorer-heading">
        <div>
          <p className="eyebrow">Forecast {forecast.forecast_id}</p>
          <h1>2026 Forecast Explorer</h1>
        </div>
        <p>{forecast.simulation_runs.toLocaleString()} simulations · {forecast.matches.length} predicted matches</p>
      </header>

      <section className="explorer-summary" aria-label="Forecast summary">
        <div><span>Model champion</span><strong>{forecast.champion.team}</strong><small>{(forecast.champion.probability * 100).toFixed(1)}%</small></div>
        <div><span>Teams</span><strong>{Object.keys(forecast.team_probabilities).length}</strong><small>{Object.keys(groups).length} groups</small></div>
        <div><span>Predictions</span><strong>{forecast.matches.filter((match) => match.prediction).length}/{forecast.matches.length}</strong><small>complete matrices</small></div>
      </section>

      <div className="explorer-tabs" role="tablist" aria-label="Explorer views">
        {([
          ['probability', 'Champion probability'],
          ['groups', '48-team groups'],
          ['annex', 'Annex C'],
          ['knockout', 'Knockout path'],
        ] as const).map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={view === id}
            onClick={() => setView(id)}
          >
            {label}
          </button>
        ))}
      </div>

      {view === 'probability' && (
        <section className="explorer-bars" aria-label="Top champion probabilities">
          {topTeams.map((team) => (
            <div className="explorer-bar-row" key={team.team} aria-label={`${team.team} ${(team.champion * 100).toFixed(1)}%`}>
              <Link to={`/teams/${encodeURIComponent(team.team)}`}>{team.team}</Link>
              <span className="explorer-bar-track"><span style={{ width: `${team.champion / maxChampion * 100}%` }} /></span>
              <strong>{(team.champion * 100).toFixed(1)}%</strong>
            </div>
          ))}
        </section>
      )}

      {view === 'groups' && (
        <section aria-label="Tournament groups">
          <div className="group-selector" role="group" aria-label="Select group">
            {Object.keys(groups).map((group) => (
              <button
                key={group}
                type="button"
                aria-label={`Group ${group}`}
                aria-pressed={selectedGroup === group}
                onClick={() => setSelectedGroup(group)}
              >
                {group}
              </button>
            ))}
          </div>
          <div className="explorer-group" aria-live="polite">
            <h2>Group {selectedGroup}</h2>
            <ol>{groups[selectedGroup]?.map((team) => <li key={team}>{team}</li>)}</ol>
          </div>
        </section>
      )}

      {view === 'annex' && (
        <section aria-label="Annex C mapping">
          <p className="explorer-note">The representative simulation’s eight qualified third-place teams are mapped directly to their official group-winner slots.</p>
          <div className="annex-grid">
            {annexMappings.map((mapping) => (
              <div className="annex-row" key={mapping.slot}>
                <code>{mapping.slot}</code><span aria-hidden="true">→</span><strong>3{mapping.group}</strong><span>{mapping.team}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {view === 'knockout' && (
        <section aria-label="Knockout path">
          <div className="stage-selector" role="group" aria-label="Select knockout stage">
            {stageOrder.map((stage) => (
              <button
                key={stage}
                type="button"
                aria-pressed={selectedStage === stage}
                onClick={() => changeStage(stage)}
              >
                {stageLabels[stage]}
              </button>
            ))}
          </div>
          <div className="explorer-matches">
            {stageMatches.map((match) => (
              <button
                type="button"
                key={match.match_id}
                aria-pressed={selectedMatch?.match_id === match.match_id}
                onClick={() => setSelectedMatchId(match.match_id)}
              >
                <code>{match.match_id}</code>
                <span className={match.winner === match.home_team ? 'winner' : ''}>{match.home_team}</span>
                <span aria-hidden="true">–</span>
                <span className={match.winner === match.away_team ? 'winner' : ''}>{match.away_team}</span>
              </button>
            ))}
          </div>
          {selectedMatch && (
            <div className="explorer-match-detail" aria-live="polite">
              <div><strong>{selectedMatch.match_id}</strong><span>{selectedMatch.home_team} vs {selectedMatch.away_team}</span><small>Winner: {selectedMatch.winner}</small></div>
              {selectedMatch.prediction && (
                <dl>
                  <div><dt>{selectedMatch.home_team}</dt><dd>{(selectedMatch.prediction.outcomes.home * 100).toFixed(1)}%</dd></div>
                  <div><dt>Draw</dt><dd>{(selectedMatch.prediction.outcomes.draw * 100).toFixed(1)}%</dd></div>
                  <div><dt>{selectedMatch.away_team}</dt><dd>{(selectedMatch.prediction.outcomes.away * 100).toFixed(1)}%</dd></div>
                </dl>
              )}
            </div>
          )}
        </section>
      )}
    </main>
  );
}
