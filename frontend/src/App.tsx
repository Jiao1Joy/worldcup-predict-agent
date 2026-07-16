import { useState } from 'react';
import { ResultSummary } from './components/ResultSummary';
import { Workbench } from './components/Workbench';
import { useRunController } from './state/use-run-controller';
import { completedRunFixture } from './test/completed-run';

const demoRunId = import.meta.env.VITE_DEMO_RUN_ID as string | undefined;

function FixtureAgentApp() {
  const [showWorkbench, setShowWorkbench] = useState(false);
  return showWorkbench ? (
    <Workbench
      initialState={completedRunFixture.initial_state}
      initialRun={completedRunFixture.state}
      initialEvents={completedRunFixture.events}
    />
  ) : (
    <ResultSummary onOpenWorkbench={() => setShowWorkbench(true)} />
  );
}

function LiveAgentApp({ runId }: { runId: string }) {
  const [showWorkbench, setShowWorkbench] = useState(false);
  const controller = useRunController(runId);
  if (!showWorkbench) {
    return <ResultSummary onOpenWorkbench={() => setShowWorkbench(true)} />;
  }
  if (!controller.run || !controller.initialRun) {
    return <main aria-live="polite">Loading Agent run…</main>;
  }
  return (
    <Workbench
      initialState={controller.initialRun}
      initialRun={controller.run}
      initialEvents={controller.events}
      onInjectFailure={controller.injectFailure}
      onApprove={(choice) => controller.approve(choice, 'portfolio-user')}
    />
  );
}

export function App() {
  return demoRunId ? <LiveAgentApp runId={demoRunId} /> : <FixtureAgentApp />;
}
