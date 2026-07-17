import type { Edge, Node } from '@xyflow/react';
import type { RunState } from './run';

const stages = ['collect', 'validate', 'predict', 'simulate', 'critique', 'explain'] as const;

export function buildGraphElements(state: RunState): { nodes: Node[]; edges: Edge[] } {
  const dynamicStages = state.decisions.some((item) => item.action === 'simulate_more')
    ? [...stages.slice(0, 4), 'simulate_more', ...stages.slice(4)]
    : [...stages];

  const nodes: Node[] = dynamicStages.map((id, index) => ({
    id,
    position: { x: (index % 4) * 190, y: Math.floor(index / 4) * 110 },
    data: {
      label: id.replace('_', ' '),
      status: state.step_statuses[id] ?? (id === state.current_step_id ? 'running' : 'pending'),
    },
    type: 'run',
  }));
  const edges: Edge[] = dynamicStages.slice(0, -1).map((source, index) => ({
    id: `${source}-${dynamicStages[index + 1]}`,
    source,
    target: dynamicStages[index + 1],
    animated: dynamicStages[index + 1] === state.current_step_id,
  }));
  return { nodes, edges };
}
