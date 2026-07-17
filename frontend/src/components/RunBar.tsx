import type { RunEvent, RunState } from '../domain/run';

export function RunBar({
  run,
  events,
  onReplay,
  onInjectFailure,
  commandPending = false,
}: {
  run: RunState;
  events: RunEvent[];
  onReplay: () => void;
  onInjectFailure: () => void;
  commandPending?: boolean;
}) {
  const toolCalls = events.filter((event) => event.event_type === 'tool').length;
  const retries = events.filter((event) => event.event_type === 'retry').length;
  return (
    <header className="run-bar">
      <span className={`status status-${run.status}`}>{run.status.toUpperCase()}</span>
      <strong>{run.run_id}</strong>
      <span>{toolCalls} tool calls</span>
      <span>{retries} retries</span>
      <div className="run-actions">
        <button type="button" onClick={onReplay}>Replay</button>
        <button type="button" onClick={onInjectFailure} disabled={commandPending}>Inject tool failure</button>
      </div>
    </header>
  );
}
