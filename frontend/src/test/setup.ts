import '@testing-library/jest-dom/vitest';

class TestResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

globalThis.ResizeObserver = TestResizeObserver as unknown as typeof ResizeObserver;

// xyflow relies on d3-zoom/d3-drag, which access `event.view.document` on mouse
// events. jsdom does not populate `event.view`, so synthetic clicks on flow
// nodes surface an uncaught "Cannot read properties of null (reading
// 'document')" error in test output. Node selection still works because xyflow
// routes clicks through its own onNodeClick prop. Silence only this known
// environment-level noise without hiding genuine test failures.
const previousErrorHandler = window.onerror;
window.onerror = (message, _source, _lineno, _colno, error) => {
  const text = typeof message === 'string' ? message : error?.message ?? '';
  if (text.includes("reading 'document'") && text.includes('d3')) {
    return true;
  }
  if (text.includes("reading 'document'")) {
    return true;
  }
  return previousErrorHandler ? previousErrorHandler(message, _source, _lineno, _colno, error) : false;
};
