import { completedRunFixture } from '../src/test/completed-run';
import { assertRunState } from '../src/domain/run';
import { materializeEvent } from '../src/state/run-reducer';

test('accepts the completed backend run fixture', () => {
  expect(() => assertRunState(completedRunFixture.initial_state)).not.toThrow();
  expect(() => assertRunState(completedRunFixture.state)).not.toThrow();
  expect(completedRunFixture.initial_state.event_sequence).toBe(0);
  expect(completedRunFixture.events[0].sequence).toBe(1);
});

test('applies a state patch event without mutating the previous state', () => {
  const before = structuredClone(completedRunFixture.state);
  const event = {
    run_id: before.run_id,
    sequence: before.event_sequence + 1,
    event_type: 'state' as const,
    step_id: 'simulate',
    tool_call_id: null,
    parent_step_id: null,
    created_at: new Date().toISOString(),
    payload: { patch: { status: 'recovering' } },
  };

  const after = materializeEvent(before, event);

  expect(after.status).toBe('recovering');
  expect(after.event_sequence).toBe(event.sequence);
  expect(before.status).toBe(completedRunFixture.state.status);
});

test('ignores duplicate or old events', () => {
  const state = completedRunFixture.state;
  const old = { ...completedRunFixture.events[0], sequence: state.event_sequence };
  expect(materializeEvent(state, old)).toBe(state);
});
