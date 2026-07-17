import type { RunEvent, RunState } from '../domain/run';

export function materializeEvent(state: RunState, event: RunEvent): RunState {
  if (event.sequence <= state.event_sequence) return state;
  const patch = event.payload.patch ?? {};
  return {
    ...state,
    ...(patch as Partial<RunState>),
    event_sequence: event.sequence,
  };
}

export function replayEvents(initial: RunState, events: RunEvent[], through?: number): RunState {
  return events
    .filter((event) => through === undefined || event.sequence <= through)
    .sort((a, b) => a.sequence - b.sequence)
    .reduce(materializeEvent, initial);
}
