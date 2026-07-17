export type RunStatus =
  | 'pending'
  | 'running'
  | 'waiting_for_human'
  | 'recovering'
  | 'completed'
  | 'failed';

export type EventType =
  | 'plan'
  | 'tool'
  | 'state'
  | 'decision'
  | 'guardrail'
  | 'checkpoint'
  | 'retry'
  | 'human'
  | 'complete';

export interface DecisionRecord {
  decision_id: string;
  observation: string;
  rule: string;
  action: string;
  reason: string;
  evidence_ids: string[];
}

export interface RunState {
  run_id: string;
  task_spec: Record<string, unknown>;
  status: RunStatus;
  current_step_id: string | null;
  step_statuses: Record<string, string>;
  data_snapshot: Record<string, unknown>;
  model_snapshot: Record<string, unknown>;
  tournament_state: Record<string, unknown>;
  tool_results: Record<string, unknown>;
  decisions: DecisionRecord[];
  evidence_refs: string[];
  errors: Array<Record<string, unknown>>;
  checkpoint_id: string | null;
  event_sequence: number;
}

export interface RunEvent {
  run_id: string;
  sequence: number;
  event_type: EventType;
  step_id: string | null;
  tool_call_id: string | null;
  parent_step_id: string | null;
  created_at: string;
  payload: Record<string, unknown>;
}

export function assertRunState(value: unknown): asserts value is RunState {
  if (!value || typeof value !== 'object') throw new Error('run state must be an object');
  const state = value as Partial<RunState>;
  if (typeof state.run_id !== 'string') throw new Error('run_id is required');
  if (typeof state.status !== 'string') throw new Error('status is required');
  if (!Array.isArray(state.decisions)) throw new Error('decisions must be an array');
  if (typeof state.event_sequence !== 'number') throw new Error('event_sequence is required');
}
