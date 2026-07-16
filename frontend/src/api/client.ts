import { assertRunState, type RunState } from '../domain/run';

async function parseRun(response: Response): Promise<RunState> {
  if (!response.ok) throw new Error(`request failed: ${response.status}`);
  const value: unknown = await response.json();
  assertRunState(value);
  return value;
}

export const runApi = {
  get: (runId: string) => fetch(`/api/runs/${runId}`).then(parseRun),
  getInitial: (runId: string) => fetch(`/api/runs/${runId}/initial`).then(parseRun),
  injectFailure: (runId: string) =>
    fetch(`/api/runs/${runId}/inject-failure`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ failure: 'timeout-once' }),
    }).then(parseRun),
  approve: (runId: string, choice: string, actor: string) =>
    fetch(`/api/runs/${runId}/approve`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ choice, actor }),
    }).then(parseRun),
};
