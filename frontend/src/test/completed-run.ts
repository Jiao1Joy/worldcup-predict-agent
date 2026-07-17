import fixture from '../../../backend/tests/fixtures/completed_run.json';
import type { RunEvent, RunState } from '../domain/run';

export const completedRunFixture = fixture as {
  initial_state: RunState;
  state: RunState;
  events: RunEvent[];
};
