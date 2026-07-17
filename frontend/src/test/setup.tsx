import '@testing-library/jest-dom/vitest';
import { createElement, type ComponentType } from 'react';
import { vi } from 'vitest';

class TestResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

globalThis.ResizeObserver = TestResizeObserver as unknown as typeof ResizeObserver;

// ECharts relies on canvas APIs that jsdom does not implement. Render a stub
// with an aria-label so accessibility-oriented assertions still work.
vi.mock('echarts-for-react', () => ({
  default: function MockECharts() {
    return null;
  },
}));

// React Flow delegates pointer handling to d3, whose browser-only event view
// is unavailable in jsdom. Keep unit tests focused on our graph nodes/clicks.
vi.mock('@xyflow/react', () => ({
  Background: () => null,
  Controls: () => null,
  ReactFlow: ({ nodes, nodeTypes, onNodeClick, children }: {
    nodes: Array<{ id: string; type?: string; data: unknown }>;
    nodeTypes: Record<string, ComponentType<{ id: string; data: unknown }>>;
    onNodeClick?: (event: unknown, node: { id: string }) => void;
    children?: unknown;
  }) => createElement(
    'div',
    null,
    ...nodes.map((node) => createElement(
      'button',
      { key: node.id, type: 'button', onClick: () => onNodeClick?.({}, node) },
      createElement(nodeTypes[node.type ?? 'run'], { id: node.id, data: node.data }),
    )),
    children as never,
  ),
}));
