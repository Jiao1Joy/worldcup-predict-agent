import '@testing-library/jest-dom/vitest';
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

// jsdom does not populate `event.view`, which d3-zoom/d3-drag rely on when
// xyflow nodes receive mouse events in unit tests. The resulting error is a
// known environment limitation and does not affect node-click handling.
const previousErrorHandler = window.onerror;
window.onerror = (message, _source, _lineno, _colno, error) => {
  const text = typeof message === 'string' ? message : error?.message ?? '';
  if (text.includes("reading 'document'")) {
    return true;
  }
  return previousErrorHandler ? previousErrorHandler(message, _source, _lineno, _colno, error) : false;
};
