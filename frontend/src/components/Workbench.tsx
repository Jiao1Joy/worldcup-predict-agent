import { useEffect, useMemo, useState } from 'react';
import type { RunEvent, RunState } from '../domain/run';
import { replayEvents } from '../state/run-reducer';
import { ApprovalPanel } from './ApprovalPanel';
import { EventTimeline } from './EventTimeline';
import { ReplayControls } from './ReplayControls';
import { RunBar } from './RunBar';
import { RunGraph } from './RunGraph';
import { StepInspector } from './StepInspector';

interface WorkbenchProps {
  initialState: RunState;
  initialRun: RunState;
  initialEvents: RunEvent[];
  onInjectFailure?: () => Promise<void>;
  onApprove?: (choice: string) => Promise<void>;
}

export function Workbench({ initialState, initialRun, initialEvents, onInjectFailure, onApprove }: WorkbenchProps) {
  const [selectedStepId, setSelectedStepId] = useState<string | null>('simulate');
  const [replaySequence, setReplaySequence] = useState(initialRun.event_sequence);
  const [commandStatus, setCommandStatus] = useState('');
  const [commandPending, setCommandPending] = useState(false);

  useEffect(() => {
    setReplaySequence(initialRun.event_sequence);
  }, [initialRun.event_sequence]);

  const replayedRun = useMemo(
    () => replayEvents(initialState, initialEvents, replaySequence),
    [initialEvents, initialState, replaySequence],
  );

  async function executeCommand(label: string, command: () => Promise<void>) {
    setCommandPending(true);
    setCommandStatus(label);
    try {
      await command();
      setCommandStatus(`${label} complete`);
    } catch (error) {
      setCommandStatus(error instanceof Error ? error.message : 'Command failed');
    } finally {
      setCommandPending(false);
    }
  }

  return (
    <main className="workbench">
      <RunBar
        run={replayedRun}
        events={initialEvents}
        onReplay={() => setReplaySequence(0)}
        commandPending={commandPending}
        onInjectFailure={() => executeCommand('Injecting tool failure', onInjectFailure ?? (async () => {}))}
      />
      <div className="workbench-grid">
        <RunGraph run={replayedRun} selectedStepId={selectedStepId} onSelectStep={setSelectedStepId} />
        <StepInspector run={replayedRun} stepId={selectedStepId} />
      </div>
      <ReplayControls
        sequence={replaySequence}
        min={0}
        max={Math.max(0, ...initialEvents.map((event) => event.sequence))}
        onChange={setReplaySequence}
      />
      {(replayedRun.status === 'waiting_for_human' || initialRun.status === 'waiting_for_human') && (
        <ApprovalPanel
          disabled={commandPending}
          onApprove={(choice) => executeCommand('Submitting approval', () => onApprove?.(choice) ?? Promise.resolve())}
        />
      )}
      <p className="command-status" aria-live="polite">{commandStatus}</p>
      <EventTimeline events={initialEvents.filter((event) => event.sequence <= replaySequence)} />
    </main>
  );
}
