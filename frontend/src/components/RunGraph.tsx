import { Background, Controls, ReactFlow } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { NodeProps } from '@xyflow/react';
import { buildGraphElements } from '../domain/graph';
import type { RunState } from '../domain/run';

interface Props {
  run: RunState;
  selectedStepId: string | null;
  onSelectStep: (stepId: string) => void;
}

type RunNodeData = { label: string; status: string };

function RunNode({ data, id }: NodeProps) {
  const node = data as unknown as RunNodeData;
  return (
    <div className={`run-node node-${node.status}`} data-testid={`graph-node-${id}`}>
      <strong>{node.label}</strong>
      <span aria-label={`Status: ${node.status}`}>{node.status}</span>
    </div>
  );
}

const nodeTypes = { run: RunNode };

export function RunGraph({ run, selectedStepId, onSelectStep }: Props) {
  const { nodes, edges } = buildGraphElements(run);
  return (
    <section className="run-graph" aria-label="Agent run graph">
      <ReactFlow
        nodes={nodes.map((node) => ({ ...node, selected: node.id === selectedStepId }))}
        edges={edges}
        nodeTypes={nodeTypes}
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
