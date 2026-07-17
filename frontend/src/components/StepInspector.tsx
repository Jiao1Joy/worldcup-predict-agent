import { useMemo, useState } from 'react';
import type { RunState } from '../domain/run';

type Panel = 'decision' | 'io' | 'evidence';

export function StepInspector({ run, stepId }: { run: RunState; stepId: string | null }) {
  const [panel, setPanel] = useState<Panel>(stepId ? 'io' : 'decision');
  const decision = useMemo(
    () => run.decisions.find((item) => item.action.includes(stepId ?? '')) ?? run.decisions.at(-1),
    [run.decisions, stepId],
  );
  const tournament = run.tournament_state;
  const selectedOutput = stepId === 'simulate'
    ? (run.tool_results[stepId] ?? {
      forecast_id: tournament.forecast_id,
      matches_count: tournament.matches_count,
      probability_delta: tournament.probability_delta,
      evidence_ids: tournament.evidence_ids,
    })
    : run.tool_results[stepId ?? ''];

  return (
    <aside className="step-inspector" aria-label="Step inspector">
      <p className="eyebrow">STEP INSPECTOR</p>
      <h2>{stepId ?? 'Select a step'}</h2>
      <div role="tablist" aria-label="Inspector panels">
        {(['decision', 'io', 'evidence'] as const).map((name) => (
          <button
            key={name}
            type="button"
            role="tab"
            aria-selected={panel === name}
            onClick={() => setPanel(name)}
          >
            {name === 'io' ? 'Input / Output' : name[0].toUpperCase() + name.slice(1)}
          </button>
        ))}
      </div>
      {panel === 'decision' && (
        <dl>
          <dt>Observation</dt>
          <dd>{decision?.observation ?? 'No decision recorded'}</dd>
          <dt>Rule</dt>
          <dd>{decision?.rule ?? '—'}</dd>
          <dt>Action</dt>
          <dd>{decision?.action ?? '—'}</dd>
          <dt>Reason</dt>
          <dd>{decision?.reason ?? '—'}</dd>
        </dl>
      )}
      {panel === 'io' && <pre>{JSON.stringify(selectedOutput ?? {}, null, 2)}</pre>}
      {panel === 'evidence' && (
        <ul>{(decision?.evidence_ids ?? run.evidence_refs).map((id) => <li key={id}>{id}</li>)}</ul>
      )}
    </aside>
  );
}
