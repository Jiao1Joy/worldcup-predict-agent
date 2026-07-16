import { useState } from 'react';
import type { ForecastMatch } from '../../domain/forecast';
import { MatchCard } from './MatchCard';

const STAGE_ORDER = ['round_of_32', 'round_of_16', 'quarter_final', 'semi_final', 'third_place', 'final'];
const STAGE_LABEL: Record<string, string> = {
  round_of_32: 'Round of 32',
  round_of_16: 'Round of 16',
  quarter_final: 'Quarter Final',
  semi_final: 'Semi Final',
  third_place: 'Third Place',
  final: 'Final',
};

export function TournamentBracket({ matches }: { matches: ForecastMatch[] }) {
  const [groupFilter, setGroupFilter] = useState<string>('knockout');
  const knockout = matches.filter((m) => m.stage !== 'group');
  const groups = matches.filter((m) => m.stage === 'group');

  return (
    <section className="bracket" aria-label="Tournament bracket">
      <div className="bracket-controls">
        <button onClick={() => setGroupFilter('knockout')}>Knockout</button>
        <select value={groupFilter} onChange={(e) => setGroupFilter(e.target.value)} aria-label="Group selector">
          <option value="knockout">Knockout bracket</option>
          {Array.from(new Set(groups.map((m) => m.home_source[1]))).map((g) => (
            <option key={g} value={g}>Group {g}</option>
          ))}
        </select>
      </div>
      {groupFilter === 'knockout' ? (
        <div className="bracket-columns">
          {STAGE_ORDER.map((stage) => {
            const stageMatches = knockout.filter((m) => m.stage === stage);
            if (stageMatches.length === 0) return null;
            return (
              <div key={stage} className="bracket-column">
                <h2>{STAGE_LABEL[stage]}</h2>
                {stageMatches.map((m) => <MatchCard key={m.match_id} match={m} />)}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="group-list">
          {groups.filter((m) => m.home_source[1] === groupFilter).map((m) => (
            <MatchCard key={m.match_id} match={m} />
          ))}
        </div>
      )}
    </section>
  );
}
