import { useParams } from 'react-router-dom';
import { Workbench } from '../components/Workbench';
import { useRunController } from '../state/use-run-controller';
import { completedRunFixture } from '../test/completed-run';

export function AgentWorkbenchPage() {
  const { runId } = useParams();
  const targetRunId = runId ?? completedRunFixture.state.run_id;
  // Offline portfolio mode falls back to the committed completed-run fixture
  // when the live backend is unavailable.
  const controller = useRunController(targetRunId, false);
  const initial = controller.initialRun ?? completedRunFixture.initial_state;
  const current = controller.run ?? completedRunFixture.state;
  const events = controller.events.length ? controller.events : completedRunFixture.events;
  return (
    <Workbench
      initialState={initial}
      initialRun={current}
      initialEvents={events}
      onInjectFailure={controller.injectFailure}
      onApprove={(choice) => controller.approve(choice, 'portfolio-user')}
    />
  );
}
