# Agent Workbench UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a polished React Agent Workbench that visualizes live and replayed runs, inspects decisions and evidence, injects recoverable failures, and completes human approvals against the Agent Runtime API.

**Architecture:** A typed API client loads a run snapshot and subscribes to append-only SSE events. A small reducer materializes UI state from snapshots and events; `@xyflow/react` renders the execution graph, while focused components render the Run Bar, Step Inspector, Event Timeline, replay controls, failure injection, and approval drawer. The completed-run fixture from the backend enables deterministic component and end-to-end tests.

**Tech Stack:** React 18, TypeScript 5, Vite, `@xyflow/react`, Vitest, Testing Library, Playwright

---

## Dependency

Complete `docs/superpowers/plans/2026-07-15-agent-runtime-foundation.md` first. This plan consumes:

- `POST /api/runs`
- `POST /api/runs/{run_id}/start`
- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/events`
- `POST /api/runs/{run_id}/inject-failure`
- `POST /api/runs/{run_id}/approve`
- `backend/tests/fixtures/completed_run.json`

## File Structure

```text
frontend/
├── package.json
├── tsconfig.json
├── vite.config.ts
├── index.html
├── playwright.config.ts
├── src/
│   ├── main.tsx                    # React bootstrap
│   ├── App.tsx                     # Result page and workbench routing
│   ├── styles.css                  # Theme tokens and responsive layout
│   ├── api/
│   │   ├── client.ts               # Typed HTTP operations
│   │   └── events.ts               # EventSource subscription adapter
│   ├── domain/
│   │   ├── run.ts                  # Runtime types and type guards
│   │   └── graph.ts                # RunState to React Flow projection
│   ├── state/
│   │   ├── run-reducer.ts          # Snapshot/event materialization
│   │   └── use-run-controller.ts   # Fetch, stream, replay, commands
│   ├── components/
│   │   ├── ResultSummary.tsx       # Champion result with workbench entry
│   │   ├── Workbench.tsx           # Main composition
│   │   ├── RunBar.tsx              # Status and commands
│   │   ├── RunGraph.tsx            # Interactive execution graph
│   │   ├── StepInspector.tsx       # Decision, I/O, evidence tabs
│   │   ├── EventTimeline.tsx       # Ordered trace rows
│   │   ├── ReplayControls.tsx      # Deterministic event replay
│   │   └── ApprovalPanel.tsx       # Human-in-the-loop decision
│   └── test/
│       ├── setup.ts
│       └── completed-run.ts        # Imported backend fixture
├── tests/
│   ├── run-reducer.test.ts
│   ├── graph.test.ts
│   ├── workbench.test.tsx
│   ├── inspector.test.tsx
│   └── commands.test.tsx
└── e2e/
    └── portfolio-demo.spec.ts
```

## Task 1: Scaffold the React TypeScript Application

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/test/setup.ts`
- Test: `frontend/tests/workbench.test.tsx`

- [ ] **Step 1: Create the package manifest and test configuration**

```json
{
  "name": "worldcup-agent-workbench",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "test": "vitest run",
    "test:watch": "vitest",
    "e2e": "playwright test"
  },
  "dependencies": {
    "@xyflow/react": "^12.4.4",
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@playwright/test": "^1.50.1",
    "@testing-library/jest-dom": "^6.6.3",
    "@testing-library/react": "^16.1.0",
    "@testing-library/user-event": "^14.5.2",
    "@types/react": "^18.3.18",
    "@types/react-dom": "^18.3.5",
    "@vitejs/plugin-react": "^4.3.4",
    "jsdom": "^25.0.1",
    "typescript": "^5.7.2",
    "vite": "^6.0.7",
    "vitest": "^2.1.8"
  }
}
```

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src", "tests", "vite.config.ts"]
}
```

```ts
// frontend/vite.config.ts
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { '/api': 'http://localhost:8000' },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    globals: true,
  },
});
```

- [ ] **Step 2: Write the failing smoke test**

```tsx
// frontend/tests/workbench.test.tsx
import { render, screen } from '@testing-library/react';
import { App } from '../src/App';

test('shows the prediction result entry point', () => {
  render(<App />);

  expect(screen.getByRole('heading', { name: /world cup prediction agent/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /view agent run/i })).toBeInTheDocument();
});
```

```ts
// frontend/src/test/setup.ts
import '@testing-library/jest-dom/vitest';

class TestResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

globalThis.ResizeObserver = TestResizeObserver as unknown as typeof ResizeObserver;
```

- [ ] **Step 3: Run the smoke test to verify it fails**

Run: `cd frontend && npm install && npm test -- tests/workbench.test.tsx`

Expected: FAIL because `src/App.tsx` does not exist.

- [ ] **Step 4: Add the minimal application shell**

```tsx
// frontend/src/App.tsx
import { useState } from 'react';

export function App() {
  const [showWorkbench, setShowWorkbench] = useState(false);
  return (
    <main>
      <h1>World Cup Prediction Agent</h1>
      {showWorkbench ? (
        <section aria-label="Agent Workbench">Workbench loading…</section>
      ) : (
        <button type="button" onClick={() => setShowWorkbench(true)}>
          View Agent Run
        </button>
      )}
    </main>
  );
}
```

```tsx
// frontend/src/main.tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';
import './styles.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

```html
<!-- frontend/index.html -->
<div id="root"></div>
<script type="module" src="/src/main.tsx"></script>
```

- [ ] **Step 5: Run the smoke test and build**

Run: `cd frontend && npm test -- tests/workbench.test.tsx && npm run build`

Expected: test PASSes and Vite build exits 0.

- [ ] **Step 6: Commit the frontend scaffold**

```bash
git add frontend
git commit -m "build: scaffold agent workbench frontend"
```

## Task 2: Define Typed Run and Event Models

**Files:**
- Create: `frontend/src/domain/run.ts`
- Create: `frontend/src/test/completed-run.ts`
- Test: `frontend/tests/run-reducer.test.ts`

- [ ] **Step 1: Write a failing fixture parsing test**

```ts
// frontend/tests/run-reducer.test.ts
import { completedRunFixture } from '../src/test/completed-run';
import { assertRunState } from '../src/domain/run';

test('accepts the completed backend run fixture', () => {
  expect(() => assertRunState(completedRunFixture.initial_state)).not.toThrow();
  expect(() => assertRunState(completedRunFixture.state)).not.toThrow();
  expect(completedRunFixture.initial_state.event_sequence).toBe(0);
  expect(completedRunFixture.events[0].sequence).toBe(1);
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npm test -- tests/run-reducer.test.ts`

Expected: FAIL because the domain module and fixture adapter do not exist.

- [ ] **Step 3: Define frontend types and a strict runtime assertion**

```ts
// frontend/src/domain/run.ts
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
```

- [ ] **Step 4: Import the generated backend fixture**

```ts
// frontend/src/test/completed-run.ts
import fixture from '../../../backend/tests/fixtures/completed_run.json';
import type { RunEvent, RunState } from '../domain/run';

export const completedRunFixture = fixture as {
  initial_state: RunState;
  state: RunState;
  events: RunEvent[];
};
```

- [ ] **Step 5: Run the type and fixture tests**

Run: `cd frontend && npm test -- tests/run-reducer.test.ts && npm run build`

Expected: fixture test PASSes and TypeScript build exits 0.

- [ ] **Step 6: Commit typed runtime models**

```bash
git add frontend/src/domain frontend/src/test frontend/tests/run-reducer.test.ts
git commit -m "feat: add typed agent run models"
```

## Task 3: Implement Snapshot and Event Materialization

**Files:**
- Create: `frontend/src/state/run-reducer.ts`
- Modify: `frontend/tests/run-reducer.test.ts`

- [ ] **Step 1: Write failing reducer tests**

```ts
// append to frontend/tests/run-reducer.test.ts
import { materializeEvent } from '../src/state/run-reducer';

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
```

- [ ] **Step 2: Run reducer tests to verify they fail**

Run: `cd frontend && npm test -- tests/run-reducer.test.ts`

Expected: FAIL because `materializeEvent` does not exist.

- [ ] **Step 3: Implement the pure event reducer**

```ts
// frontend/src/state/run-reducer.ts
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
```

- [ ] **Step 4: Run reducer tests**

Run: `cd frontend && npm test -- tests/run-reducer.test.ts`

Expected: all reducer tests PASS.

- [ ] **Step 5: Commit the reducer**

```bash
git add frontend/src/state/run-reducer.ts frontend/tests/run-reducer.test.ts
git commit -m "feat: materialize agent state from events"
```

## Task 4: Project Runtime State into an Interactive Graph

**Files:**
- Create: `frontend/src/domain/graph.ts`
- Create: `frontend/src/components/RunGraph.tsx`
- Test: `frontend/tests/graph.test.ts`

- [ ] **Step 1: Write failing graph projection tests**

```ts
// frontend/tests/graph.test.ts
import { buildGraphElements } from '../src/domain/graph';
import { completedRunFixture } from '../src/test/completed-run';

test('projects known execution stages and dynamic decisions', () => {
  const { nodes, edges } = buildGraphElements(completedRunFixture.state);

  expect(nodes.map((node) => node.id)).toEqual(
    expect.arrayContaining(['collect', 'validate', 'predict', 'simulate', 'critique', 'explain']),
  );
  expect(edges.some((edge) => edge.source === 'simulate' && edge.target === 'simulate_more')).toBe(true);
  expect(edges.some((edge) => edge.source === 'simulate_more' && edge.target === 'critique')).toBe(true);
});
```

- [ ] **Step 2: Run graph tests to verify they fail**

Run: `cd frontend && npm test -- tests/graph.test.ts`

Expected: FAIL because graph projection does not exist.

- [ ] **Step 3: Implement graph projection**

```ts
// frontend/src/domain/graph.ts
import type { Edge, Node } from '@xyflow/react';
import type { RunState } from './run';

const stages = ['collect', 'validate', 'predict', 'simulate', 'critique', 'explain'] as const;

export function buildGraphElements(state: RunState): { nodes: Node[]; edges: Edge[] } {
  const dynamicStages = state.decisions.some((item) => item.action === 'simulate_more')
    ? [...stages.slice(0, 4), 'simulate_more', ...stages.slice(4)]
    : [...stages];

  const nodes = dynamicStages.map((id, index) => ({
    id,
    position: { x: (index % 4) * 190, y: Math.floor(index / 4) * 110 },
    data: {
      label: id.replace('_', ' '),
      status: state.step_statuses[id] ?? (id === state.current_step_id ? 'running' : 'pending'),
    },
    type: 'default',
  }));
  const edges = dynamicStages.slice(0, -1).map((source, index) => ({
    id: `${source}-${dynamicStages[index + 1]}`,
    source,
    target: dynamicStages[index + 1],
    animated: dynamicStages[index + 1] === state.current_step_id,
  }));
  return { nodes, edges };
}
```

- [ ] **Step 4: Implement the accessible graph component**

```tsx
// frontend/src/components/RunGraph.tsx
import { Background, Controls, ReactFlow } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { buildGraphElements } from '../domain/graph';
import type { RunState } from '../domain/run';

interface Props {
  run: RunState;
  selectedStepId: string | null;
  onSelectStep: (stepId: string) => void;
}

export function RunGraph({ run, selectedStepId, onSelectStep }: Props) {
  const { nodes, edges } = buildGraphElements(run);
  return (
    <section className="run-graph" aria-label="Agent run graph">
      <ReactFlow
        nodes={nodes.map((node) => ({ ...node, selected: node.id === selectedStepId }))}
        edges={edges}
        fitView
        nodesDraggable={false}
        nodesConnectable={false}
        onNodeClick={(_, node) => onSelectStep(node.id)}
      >
        <Background />
        <Controls showInteractive={false} />
      </ReactFlow>
    </section>
  );
}
```

- [ ] **Step 5: Run graph tests and build**

Run: `cd frontend && npm test -- tests/graph.test.ts && npm run build`

Expected: graph test PASSes and build exits 0.

- [ ] **Step 6: Commit graph projection**

```bash
git add frontend/src/domain/graph.ts frontend/src/components/RunGraph.tsx frontend/tests/graph.test.ts
git commit -m "feat: visualize dynamic agent execution graph"
```

## Task 5: Build the Step Inspector and Evidence Views

**Files:**
- Create: `frontend/src/components/StepInspector.tsx`
- Test: `frontend/tests/inspector.test.tsx`

- [ ] **Step 1: Write a failing inspector interaction test**

```tsx
// frontend/tests/inspector.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StepInspector } from '../src/components/StepInspector';
import { completedRunFixture } from '../src/test/completed-run';

test('switches between decision, io, and evidence tabs', async () => {
  const user = userEvent.setup();
  render(<StepInspector run={completedRunFixture.state} stepId="simulate" />);

  expect(screen.getByText(/probability_delta/i)).toBeInTheDocument();
  await user.click(screen.getByRole('tab', { name: /evidence/i }));
  expect(screen.getByText(/SIM-/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the inspector test to verify it fails**

Run: `cd frontend && npm test -- tests/inspector.test.tsx`

Expected: FAIL because `StepInspector` does not exist.

- [ ] **Step 3: Implement the three-tab inspector**

```tsx
// frontend/src/components/StepInspector.tsx
import { useMemo, useState } from 'react';
import type { RunState } from '../domain/run';

type Panel = 'decision' | 'io' | 'evidence';

export function StepInspector({ run, stepId }: { run: RunState; stepId: string | null }) {
  const [panel, setPanel] = useState<Panel>('decision');
  const decision = useMemo(
    () => run.decisions.find((item) => item.action.includes(stepId ?? '')) ?? run.decisions.at(-1),
    [run.decisions, stepId],
  );

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
          <dt>Observation</dt><dd>{decision?.observation ?? 'No decision recorded'}</dd>
          <dt>Rule</dt><dd>{decision?.rule ?? '—'}</dd>
          <dt>Action</dt><dd>{decision?.action ?? '—'}</dd>
          <dt>Reason</dt><dd>{decision?.reason ?? '—'}</dd>
        </dl>
      )}
      {panel === 'io' && <pre>{JSON.stringify(run.tool_results[stepId ?? ''] ?? {}, null, 2)}</pre>}
      {panel === 'evidence' && (
        <ul>{(decision?.evidence_ids ?? run.evidence_refs).map((id) => <li key={id}>{id}</li>)}</ul>
      )}
    </aside>
  );
}
```

- [ ] **Step 4: Run inspector tests**

Run: `cd frontend && npm test -- tests/inspector.test.tsx`

Expected: inspector test PASSes.

- [ ] **Step 5: Commit the inspector**

```bash
git add frontend/src/components/StepInspector.tsx frontend/tests/inspector.test.tsx
git commit -m "feat: add decision and evidence inspector"
```

## Task 6: Build the Run Bar and Event Timeline

**Files:**
- Create: `frontend/src/components/RunBar.tsx`
- Create: `frontend/src/components/EventTimeline.tsx`
- Test: `frontend/tests/workbench.test.tsx`

- [ ] **Step 1: Add failing Run Bar and timeline assertions**

```tsx
// append to frontend/tests/workbench.test.tsx
import { RunBar } from '../src/components/RunBar';
import { EventTimeline } from '../src/components/EventTimeline';
import { completedRunFixture } from '../src/test/completed-run';

test('run bar exposes operational metrics', () => {
  render(<RunBar run={completedRunFixture.state} events={completedRunFixture.events} onReplay={() => {}} onInjectFailure={() => {}} />);
  expect(screen.getByText(completedRunFixture.state.status.toUpperCase())).toBeInTheDocument();
  expect(screen.getByText(/tool calls/i)).toBeInTheDocument();
});

test('timeline orders events by sequence', () => {
  render(<EventTimeline events={[...completedRunFixture.events].reverse()} />);
  const rows = screen.getAllByRole('listitem');
  expect(rows[0]).toHaveTextContent(String(Math.min(...completedRunFixture.events.map((event) => event.sequence))));
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- tests/workbench.test.tsx`

Expected: FAIL because Run Bar and timeline components do not exist.

- [ ] **Step 3: Implement operational Run Bar**

```tsx
// frontend/src/components/RunBar.tsx
import type { RunEvent, RunState } from '../domain/run';

export function RunBar({
  run,
  events,
  onReplay,
  onInjectFailure,
}: {
  run: RunState;
  events: RunEvent[];
  onReplay: () => void;
  onInjectFailure: () => void;
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
        <button type="button" onClick={onInjectFailure}>Inject tool failure</button>
      </div>
    </header>
  );
}
```

- [ ] **Step 4: Implement ordered timeline rows**

```tsx
// frontend/src/components/EventTimeline.tsx
import type { RunEvent } from '../domain/run';

export function EventTimeline({ events }: { events: RunEvent[] }) {
  const ordered = [...events].sort((a, b) => a.sequence - b.sequence);
  return (
    <section aria-label="Event timeline">
      <h2>Event Timeline</h2>
      <ol className="event-timeline">
        {ordered.map((event) => (
          <li key={event.sequence}>
            <time>{event.sequence}</time>
            <span>{event.event_type.toUpperCase()}</span>
            <strong>{event.step_id ?? 'run'}</strong>
            <code>{JSON.stringify(event.payload)}</code>
          </li>
        ))}
      </ol>
    </section>
  );
}
```

- [ ] **Step 5: Run component tests**

Run: `cd frontend && npm test -- tests/workbench.test.tsx`

Expected: Run Bar and timeline tests PASS.

- [ ] **Step 6: Commit Run Bar and timeline**

```bash
git add frontend/src/components/RunBar.tsx frontend/src/components/EventTimeline.tsx frontend/tests/workbench.test.tsx
git commit -m "feat: add agent run status and event timeline"
```

## Task 7: Implement the API Client, SSE Adapter, and Run Controller

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/events.ts`
- Create: `frontend/src/state/use-run-controller.ts`
- Test: `frontend/tests/commands.test.tsx`

- [ ] **Step 1: Write a failing command test with mocked fetch**

```tsx
// frontend/tests/commands.test.tsx
import { renderHook, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { useRunController } from '../src/state/use-run-controller';
import { completedRunFixture } from '../src/test/completed-run';

test('loads a snapshot and injects a recoverable failure', async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify(completedRunFixture.state)))
    .mockResolvedValueOnce(new Response(JSON.stringify(completedRunFixture.initial_state)))
    .mockResolvedValueOnce(new Response(JSON.stringify({ ...completedRunFixture.state, status: 'recovering' })));
  vi.stubGlobal('fetch', fetchMock);

  const { result } = renderHook(() => useRunController(completedRunFixture.state.run_id, false));
  await waitFor(() => expect(result.current.run).not.toBeNull());
  await waitFor(() => expect(result.current.initialRun?.event_sequence).toBe(0));
  await result.current.injectFailure();

  expect(fetchMock).toHaveBeenLastCalledWith(
    expect.stringContaining('/inject-failure'),
    expect.objectContaining({ method: 'POST' }),
  );
});
```

- [ ] **Step 2: Run command tests to verify they fail**

Run: `cd frontend && npm test -- tests/commands.test.tsx`

Expected: FAIL because the controller does not exist.

- [ ] **Step 3: Implement typed HTTP operations**

```ts
// frontend/src/api/client.ts
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
```

- [ ] **Step 4: Implement the EventSource adapter**

```ts
// frontend/src/api/events.ts
import type { RunEvent } from '../domain/run';

export function subscribeToRunEvents(
  runId: string,
  onEvent: (event: RunEvent) => void,
  eventSourceFactory: (url: string) => EventSource = (url) => new EventSource(url),
): () => void {
  const source = eventSourceFactory(`/api/runs/${runId}/events`);
  const handler = (message: MessageEvent<string>) => onEvent(JSON.parse(message.data) as RunEvent);
  ['plan', 'tool', 'state', 'decision', 'guardrail', 'checkpoint', 'retry', 'human', 'complete']
    .forEach((name) => source.addEventListener(name, handler as EventListener));
  return () => source.close();
}
```

- [ ] **Step 5: Implement the controller and optional streaming**

```tsx
// frontend/src/state/use-run-controller.ts
import { useCallback, useEffect, useState } from 'react';
import { runApi } from '../api/client';
import { subscribeToRunEvents } from '../api/events';
import type { RunEvent, RunState } from '../domain/run';
import { materializeEvent } from './run-reducer';

export function useRunController(runId: string, stream = true) {
  const [run, setRun] = useState<RunState | null>(null);
  const [initialRun, setInitialRun] = useState<RunState | null>(null);
  const [events, setEvents] = useState<RunEvent[]>([]);

  useEffect(() => {
    void runApi.get(runId).then(setRun);
    void runApi.getInitial(runId).then(setInitialRun);
  }, [runId]);

  useEffect(() => {
    if (!stream) return;
    return subscribeToRunEvents(runId, (event) => {
      setEvents((current) => current.some((item) => item.sequence === event.sequence) ? current : [...current, event]);
      setRun((current) => current ? materializeEvent(current, event) : current);
    });
  }, [runId, stream]);

  const injectFailure = useCallback(async () => {
    const updated = await runApi.injectFailure(runId);
    setRun(updated);
  }, [runId]);

  const approve = useCallback(async (choice: string, actor: string) => {
    const updated = await runApi.approve(runId, choice, actor);
    setRun(updated);
  }, [runId]);

  return { run, initialRun, events, injectFailure, approve, setRun };
}
```

- [ ] **Step 6: Run command tests**

Run: `cd frontend && npm test -- tests/commands.test.tsx`

Expected: command test PASSes.

- [ ] **Step 7: Commit API and streaming state**

```bash
git add frontend/src/api frontend/src/state/use-run-controller.ts frontend/tests/commands.test.tsx
git commit -m "feat: stream and control live agent runs"
```

## Task 8: Compose the Workbench, Replay, and Approval Panel

**Files:**
- Create: `frontend/src/components/Workbench.tsx`
- Create: `frontend/src/components/ReplayControls.tsx`
- Create: `frontend/src/components/ApprovalPanel.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/tests/workbench.test.tsx`

- [ ] **Step 1: Write failing workbench behavior tests**

```tsx
// append to frontend/tests/workbench.test.tsx
import userEvent from '@testing-library/user-event';
import { Workbench } from '../src/components/Workbench';

test('selecting a graph step updates the inspector', async () => {
  const user = userEvent.setup();
  render(
    <Workbench
      initialState={completedRunFixture.initial_state}
      initialRun={completedRunFixture.state}
      initialEvents={completedRunFixture.events}
    />,
  );

  await user.click(screen.getByText('simulate'));
  expect(screen.getByRole('heading', { name: 'simulate' })).toBeInTheDocument();
});

test('waiting run shows approval choices', () => {
  render(
    <Workbench
      initialState={completedRunFixture.initial_state}
      initialRun={{ ...completedRunFixture.state, status: 'waiting_for_human' }}
      initialEvents={completedRunFixture.events}
    />,
  );
  expect(screen.getByRole('button', { name: /use official snapshot/i })).toBeInTheDocument();
});
```

- [ ] **Step 2: Run workbench tests to verify they fail**

Run: `cd frontend && npm test -- tests/workbench.test.tsx`

Expected: FAIL because Workbench and ApprovalPanel do not exist.

- [ ] **Step 3: Implement deterministic Replay controls**

```tsx
// frontend/src/components/ReplayControls.tsx
export function ReplayControls({
  sequence,
  min,
  max,
  onChange,
}: {
  sequence: number;
  min: number;
  max: number;
  onChange: (sequence: number) => void;
}) {
  return (
    <label className="replay-controls">
      Replay event {sequence} / {max}
      <input
        aria-label="Replay event sequence"
        type="range"
        min={min}
        max={max}
        value={sequence}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  );
}
```

- [ ] **Step 4: Implement human approval panel**

```tsx
// frontend/src/components/ApprovalPanel.tsx
export function ApprovalPanel({ onApprove }: { onApprove: (choice: string) => void }) {
  return (
    <section className="approval-panel" aria-label="Human approval required">
      <p className="eyebrow">HUMAN IN THE LOOP</p>
      <h2>Data snapshots conflict</h2>
      <p>Choose which snapshot should continue through the prediction graph.</p>
      <button type="button" onClick={() => onApprove('official')}>Use official snapshot</button>
      <button type="button" onClick={() => onApprove('cached')}>Use cached snapshot</button>
    </section>
  );
}
```

- [ ] **Step 5: Compose workbench state and components**

```tsx
// frontend/src/components/Workbench.tsx
import { useMemo, useState } from 'react';
import type { RunEvent, RunState } from '../domain/run';
import { replayEvents } from '../state/run-reducer';
import { ApprovalPanel } from './ApprovalPanel';
import { EventTimeline } from './EventTimeline';
import { ReplayControls } from './ReplayControls';
import { RunBar } from './RunBar';
import { RunGraph } from './RunGraph';
import { StepInspector } from './StepInspector';

export function Workbench({
  initialState,
  initialRun,
  initialEvents,
}: {
  initialState: RunState;
  initialRun: RunState;
  initialEvents: RunEvent[];
}) {
  const [selectedStepId, setSelectedStepId] = useState<string | null>('simulate');
  const [replaySequence, setReplaySequence] = useState(initialRun.event_sequence);
  const replayedRun = useMemo(
    () => replayEvents(initialState, initialEvents, replaySequence),
    [initialEvents, initialState, replaySequence],
  );

  return (
    <main className="workbench">
      <RunBar run={replayedRun} events={initialEvents} onReplay={() => setReplaySequence(0)} onInjectFailure={() => {}} />
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
      {replayedRun.status === 'waiting_for_human' && <ApprovalPanel onApprove={() => {}} />}
      <EventTimeline events={initialEvents.filter((event) => event.sequence <= replaySequence)} />
    </main>
  );
}
```

- [ ] **Step 6: Replace the App placeholder with fixture-backed portfolio mode**

```tsx
// frontend/src/App.tsx
import { useState } from 'react';
import { ResultSummary } from './components/ResultSummary';
import { Workbench } from './components/Workbench';
import { completedRunFixture } from './test/completed-run';

export function App() {
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
```

```tsx
// frontend/src/components/ResultSummary.tsx
export function ResultSummary({ onOpenWorkbench }: { onOpenWorkbench: () => void }) {
  return (
    <main className="result-summary">
      <p className="eyebrow">2026 TOURNAMENT FORECAST</p>
      <h1>World Cup Prediction Agent</h1>
      <p>The result is a probability distribution backed by a replayable Agent run.</p>
      <button type="button" onClick={onOpenWorkbench}>View Agent Run</button>
    </main>
  );
}
```

- [ ] **Step 7: Run workbench tests**

Run: `cd frontend && npm test -- tests/workbench.test.tsx`

Expected: workbench and approval tests PASS.

- [ ] **Step 8: Commit the workbench composition**

```bash
git add frontend/src/App.tsx frontend/src/components frontend/tests/workbench.test.tsx
git commit -m "feat: compose replayable agent workbench"
```

## Task 9: Apply the Production Visual System and Responsive Layout

**Files:**
- Create: `frontend/src/styles.css`
- Modify: `frontend/src/domain/graph.ts`
- Modify: `frontend/src/components/RunGraph.tsx`
- Modify: `frontend/src/components/StepInspector.tsx`
- Test: `frontend/tests/workbench.test.tsx`

- [ ] **Step 1: Add semantic layout assertions**

```tsx
// append to frontend/tests/workbench.test.tsx
test('workbench exposes graph, inspector, replay, and timeline landmarks', () => {
  render(
    <Workbench
      initialState={completedRunFixture.initial_state}
      initialRun={completedRunFixture.state}
      initialEvents={completedRunFixture.events}
    />,
  );

  expect(screen.getByLabelText('Agent run graph')).toBeInTheDocument();
  expect(screen.getByLabelText('Step inspector')).toBeInTheDocument();
  expect(screen.getByLabelText('Replay event sequence')).toBeInTheDocument();
  expect(screen.getByLabelText('Event timeline')).toBeInTheDocument();
});
```

- [ ] **Step 2: Create a restrained theme and responsive workbench layout**

```css
/* frontend/src/styles.css */
:root {
  color-scheme: dark;
  font-family: Inter, ui-sans-serif, system-ui, sans-serif;
  color: #e7edf7;
  background: #080b12;
  --surface: #101722;
  --surface-raised: #151f2e;
  --border: #26364c;
  --muted: #8ea0b8;
  --accent: #68d8c5;
  --warning: #f3bc67;
  --danger: #ff7b7b;
}

* { box-sizing: border-box; }
body { margin: 0; min-width: 320px; min-height: 100vh; }
button, input { font: inherit; }
button { cursor: pointer; }

.workbench {
  display: grid;
  gap: 18px;
  padding: 24px;
  max-width: 1480px;
  margin: 0 auto;
}

.run-bar {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--border);
}

.run-actions { display: flex; gap: 8px; margin-left: auto; }
.workbench-grid { display: grid; grid-template-columns: minmax(0, 1fr) 330px; gap: 18px; }
.run-graph { min-height: 410px; background: var(--surface); border-radius: 14px; overflow: hidden; }
.step-inspector { background: var(--surface-raised); border: 1px solid var(--border); border-radius: 14px; padding: 18px; }
.event-timeline { display: grid; gap: 2px; padding: 0; list-style: none; }
.event-timeline li { display: grid; grid-template-columns: 60px 90px 150px 1fr; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--border); }
.eyebrow { color: var(--accent); letter-spacing: .12em; text-transform: uppercase; }
.status-recovering { color: var(--warning); }
.status-failed { color: var(--danger); }

@media (max-width: 860px) {
  .workbench { padding: 16px; }
  .workbench-grid { grid-template-columns: 1fr; }
  .run-actions { margin-left: 0; width: 100%; }
  .event-timeline li { grid-template-columns: 50px 1fr; }
  .event-timeline code { grid-column: 2; overflow-wrap: anywhere; }
}
```

- [ ] **Step 3: Add visible selected/running/recovering graph states**

```tsx
// replace `type: 'default'` with `type: 'run'` in frontend/src/domain/graph.ts

// add to frontend/src/components/RunGraph.tsx
import type { NodeProps } from '@xyflow/react';

type RunNodeData = { label: string; status: string };

function RunNode({ data }: NodeProps) {
  const node = data as RunNodeData;
  return (
    <div className={`run-node node-${node.status}`}>
      <strong>{node.label}</strong>
      <span aria-label={`Status: ${node.status}`}>{node.status}</span>
    </div>
  );
}

const nodeTypes = { run: RunNode };

// add this prop to the existing ReactFlow element
nodeTypes={nodeTypes}
```

Append the node styles:

```css
.run-node {
  min-width: 150px;
  display: grid;
  grid-template-columns: 24px 1fr;
  gap: 4px 8px;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface-raised);
}
.run-node::before { content: '○'; grid-row: 1 / 3; }
.run-node span { color: var(--muted); font-size: .78rem; text-transform: uppercase; }
.node-running::before { content: '▶'; }
.node-done::before { content: '✓'; }
.node-recovering::before { content: '↻'; }
.node-waiting::before { content: '…'; }
.node-failed::before { content: '!'; }
.react-flow__node.selected .run-node { outline: 2px solid var(--accent); outline-offset: 3px; }
```

- [ ] **Step 4: Run tests and production build**

Run: `cd frontend && npm test && npm run build`

Expected: all component tests PASS and build exits 0.

- [ ] **Step 5: Commit the visual system**

```bash
git add frontend/src/styles.css frontend/src/components frontend/tests/workbench.test.tsx
git commit -m "feat: polish agent workbench presentation"
```

## Task 10: Wire Live Failure Injection and Human Approval

**Files:**
- Modify: `frontend/src/components/Workbench.tsx`
- Modify: `frontend/src/components/RunBar.tsx`
- Modify: `frontend/src/components/ApprovalPanel.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/tests/commands.test.tsx`

- [ ] **Step 1: Write failing live command integration tests**

```tsx
// append to frontend/tests/commands.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Workbench } from '../src/components/Workbench';

test('failure command changes the run to recovery state', async () => {
  const user = userEvent.setup();
  const onInjectFailure = vi.fn().mockResolvedValue(undefined);
  render(
    <Workbench
      initialState={completedRunFixture.initial_state}
      initialRun={completedRunFixture.state}
      initialEvents={completedRunFixture.events}
      onInjectFailure={onInjectFailure}
    />,
  );
  await user.click(screen.getByRole('button', { name: /inject tool failure/i }));
  expect(onInjectFailure).toHaveBeenCalledOnce();
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npm test -- tests/commands.test.tsx`

Expected: FAIL because Workbench does not accept command callbacks.

- [ ] **Step 3: Add real command callbacks to Workbench**

Extend `Workbench` props and replace its no-op command callbacks with a single pending-state wrapper:

```tsx
interface WorkbenchProps {
  initialState: RunState;
  initialRun: RunState;
  initialEvents: RunEvent[];
  onInjectFailure?: () => Promise<void>;
  onApprove?: (choice: string) => Promise<void>;
}

// change the React import to: import { useEffect, useMemo, useState } from 'react';
// inside Workbench
const [commandStatus, setCommandStatus] = useState('');
const [commandPending, setCommandPending] = useState(false);

useEffect(() => {
  setReplaySequence(initialRun.event_sequence);
}, [initialRun.event_sequence]);

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
```

Use the wrapper at the two composition points and expose command status:

```tsx
<RunBar
  run={replayedRun}
  events={initialEvents}
  onReplay={() => setReplaySequence(0)}
  commandPending={commandPending}
  onInjectFailure={() => executeCommand('Injecting tool failure', onInjectFailure ?? (async () => {}))}
/>

{replayedRun.status === 'waiting_for_human' && (
  <ApprovalPanel
    disabled={commandPending}
    onApprove={(choice) => executeCommand('Submitting approval', () => onApprove?.(choice) ?? Promise.resolve())}
  />
)}
<p className="command-status" aria-live="polite">{commandStatus}</p>
```

Add `commandPending: boolean` to `RunBar`, set `disabled={commandPending}` on its failure button, add `disabled: boolean` to `ApprovalPanel`, and set that value on both approval buttons.

- [ ] **Step 4: Add a live App mode using the controller**

```tsx
// frontend/src/App.tsx
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
```

- [ ] **Step 5: Run command and workbench tests**

Run: `cd frontend && npm test -- tests/commands.test.tsx tests/workbench.test.tsx`

Expected: all command and workbench tests PASS.

- [ ] **Step 6: Commit live commands**

```bash
git add frontend/src/App.tsx frontend/src/components/Workbench.tsx frontend/tests/commands.test.tsx
git commit -m "feat: connect workbench recovery and approval commands"
```

## Task 11: Add the Six-Minute Portfolio End-to-End Test

**Files:**
- Create: `frontend/playwright.config.ts`
- Create: `frontend/e2e/portfolio-demo.spec.ts`
- Create: `frontend/README.md`
- Modify: `README.md`

- [ ] **Step 1: Configure Playwright against the local Vite server**

```ts
// frontend/playwright.config.ts
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  use: { baseURL: 'http://127.0.0.1:4173' },
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1 --port 4173',
    port: 4173,
    reuseExistingServer: true,
  },
});
```

- [ ] **Step 2: Write the end-to-end portfolio flow**

```ts
// frontend/e2e/portfolio-demo.spec.ts
import { expect, test } from '@playwright/test';

test('portfolio visitor can inspect and replay an agent run', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: /world cup prediction agent/i })).toBeVisible();
  await page.getByRole('button', { name: /view agent run/i }).click();

  await expect(page.getByLabel('Agent run graph')).toBeVisible();
  await page.getByText('simulate', { exact: true }).click();
  await expect(page.getByLabel('Step inspector')).toContainText('probability_delta');

  await page.getByRole('tab', { name: /evidence/i }).click();
  await expect(page.getByLabel('Step inspector')).toContainText(/SIM-/);

  await page.getByRole('button', { name: /replay/i }).click();
  await expect(page.getByLabel('Replay event sequence')).toHaveValue('0');
});

test('mobile workbench keeps every inspection surface reachable', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.getByRole('button', { name: /view agent run/i }).click();

  await expect(page.getByLabel('Agent run graph')).toBeVisible();
  await expect(page.getByLabel('Step inspector')).toBeVisible();
  await expect(page.getByLabel('Event timeline')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
```

- [ ] **Step 3: Install the browser and run end-to-end tests**

Run: `cd frontend && npx playwright install chromium && npm run e2e`

Expected: Playwright reports `2 passed`.

- [ ] **Step 4: Document portfolio and live modes**

````markdown
<!-- frontend/README.md -->
# Agent Workbench

Offline portfolio mode uses the committed completed-run fixture:

```powershell
npm install
npm run dev
```

Live mode connects to a backend run:

```powershell
$env:VITE_DEMO_RUN_ID="wc26-demo-run"
npm run dev
```

The interview path is: result summary → Run Graph → Step Inspector → dynamic branch → failure recovery → Evidence → Replay.
````

Update the root `README.md` with backend and frontend startup commands and the six-minute demonstration sequence.

- [ ] **Step 5: Run the complete frontend verification**

Run: `cd frontend && npm test && npm run build && npm run e2e`

Expected: all Vitest tests PASS, production build exits 0, and Playwright reports `2 passed`.

- [ ] **Step 6: Commit E2E coverage and documentation**

```bash
git add README.md frontend/playwright.config.ts frontend/e2e frontend/README.md
git commit -m "test: cover agent workbench portfolio flow"
```

## Frontend Plan Completion Gate

Run all of the following:

```bash
cd frontend
npm test
npm run build
npm run e2e
```

Then run the backend verification from the first plan. Required evidence:

- fixture-backed mode works without the backend;
- live mode consumes snapshots and SSE events without duplicate sequences;
- selecting graph nodes updates the inspector;
- Decision, Input/Output, and Evidence tabs render structured data;
- Replay makes no network calls;
- injected failure displays recovering/retry/checkpoint state;
- waiting runs display approval choices and resume after selection;
- layout remains usable at desktop and mobile Playwright viewports.
